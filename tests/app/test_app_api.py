import sys
import types
from contextlib import contextmanager
from dataclasses import dataclass

import pytest

import astroengine.app_api as app_api


@pytest.mark.parametrize(
    "spec, expected",
    [
        (" astroengine.engine:scan_window ", ("astroengine.engine", "scan_window")),
        ("astroengine.engine.scan_contacts", ("astroengine.engine", "scan_contacts")),
        ("foo.bar#comment", ("foo", "bar")),
        ("", None),
        ("invalid", None),
        ("module: \t", None),
    ],
)
def test_parse_entrypoint_spec(spec, expected):
    assert app_api._parse_entrypoint_spec(spec) == expected


def test_normalize_entrypoints_handles_strings_and_tuples():
    entrypoints = [
        (" astroengine.core ", " scan_window"),
        "astroengine.engine:scan_contacts",
        123,
    ]
    result = app_api._normalize_entrypoints(entrypoints)
    assert result == [
        ("astroengine.core", "scan_window"),
        ("astroengine.engine", "scan_contacts"),
    ]


def test_candidate_order_prefers_explicit_and_env(monkeypatch):
    monkeypatch.setenv(
        app_api.SCAN_ENTRYPOINT_ENV,
        "pkg.alpha:run pkg.beta:run, astroengine.engine:scan_window",
    )
    explicit = [("pkg.alpha", "run"), ("default", "fn")]
    ordered = app_api._candidate_order(explicit)
    # explicit candidates first (deduped), then env, then defaults
    assert ordered[:3] == [
        ("pkg.alpha", "run"),
        ("default", "fn"),
        ("pkg.beta", "run"),
    ]
    assert ("astroengine.engine", "scan_window") in ordered


def test_filter_kwargs_for_includes_aliases():
    def fn(start, end, moving, targets, provider, profile=None, sidereal=None):
        return locals()

    proposed = {
        "start_utc": "2024-01-01T00:00:00Z",
        "end_utc": "2024-01-02T00:00:00Z",
        "moving": ["Sun"],
        "targets": ["Earth"],
        "natal": ["Earth"],
        "provider": "swiss",
        "profile_id": "p1",
        "sidereal": True,
        "sidereal_flag": False,
        "unused": "value",
    }
    filtered = app_api._filter_kwargs_for(fn, proposed)
    assert filtered == {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",
        "moving": ["Sun"],
        "targets": ["Earth"],
        "provider": "swiss",
        "profile": "p1",
        "sidereal": True,
    }


@dataclass
class Event:
    body: str
    detail: str


class DummyEvents:
    def __init__(self, events):
        self._events = events

    def events(self):
        return self._events


def test_normalize_result_payload_accepts_iterables_and_dataclasses():
    payload = DummyEvents([Event("Sun", "ok"), {"body": "Moon", "detail": "ok"}])
    normalized = app_api._normalize_result_payload(payload)
    assert normalized == [
        {"body": "Sun", "detail": "ok"},
        {"body": "Moon", "detail": "ok"},
    ]


def test_normalize_result_payload_rejects_strings():
    assert app_api._normalize_result_payload("not-events") is None


class DummySpan:
    def __init__(self, name, attributes):
        self.name = name
        self.attributes = attributes or {}
        self.events = []
        self.exceptions = []
        self.status = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def add_event(self, name, attributes=None):
        self.events.append((name, attributes or {}))

    def record_exception(self, exc):
        self.exceptions.append(type(exc))

    def set_status(self, status):
        self.status = status


class DummySpanContext:
    def __init__(self, span):
        self._span = span

    def __enter__(self):
        return self._span

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyTracer:
    def __init__(self, spans):
        self.spans = spans

    def start_as_current_span(self, name, attributes=None):
        span = DummySpan(name, attributes)
        self.spans.append(span)
        return DummySpanContext(span)


class DummyTraceAPI:
    def __init__(self, spans):
        self.tracer = DummyTracer(spans)

    def get_tracer(self, name):
        return self.tracer


class DummyStatus:
    def __init__(self, code, description):
        self.code = code
        self.description = description


class DummyStatusCode:
    ERROR = "ERROR"


def _install_scan_module(name, fn):
    module = types.ModuleType(name)
    setattr(module, fn.__name__, fn)
    sys.modules[name] = module
    return module


def test_run_scan_or_raise_success(monkeypatch):
    events = [{"body": "Sun", "detail": "ok"}]

    def scan_ok(start_utc, end_utc, moving, targets, **kwargs):
        assert start_utc == "2024-01-01T00:00:00Z"
        assert targets == ["Earth"]
        return events

    module = _install_scan_module("scan_success", scan_ok)

    monkeypatch.setattr(
        app_api,
        "_candidate_order",
        lambda entrypoints=None: [(module.__name__, "scan_ok")],
    )

    result, used = app_api.run_scan_or_raise(
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        ["Sun"],
        ["Earth"],
        return_used_entrypoint=True,
    )
    assert result == events
    assert used == (module.__name__, "scan_ok")


def test_run_scan_or_raise_tracing_records_errors(monkeypatch):
    spans: list[DummySpan] = []
    monkeypatch.setattr(app_api, "_scan_trace", DummyTraceAPI(spans))
    monkeypatch.setattr(app_api, "Status", DummyStatus)
    monkeypatch.setattr(app_api, "StatusCode", DummyStatusCode)

    failure = RuntimeError("boom")

    def scan_fail(start_utc, end_utc, moving, targets, **kwargs):
        raise failure

    def scan_ok(start_utc, end_utc, moving, targets, **kwargs):
        return [{"body": "Moon", "detail": "ok"}]

    mod_fail = _install_scan_module("scan_fail_mod", scan_fail)
    mod_ok = _install_scan_module("scan_ok_mod", scan_ok)

    monkeypatch.setattr(
        app_api,
        "_candidate_order",
        lambda entrypoints=None: [
            (mod_fail.__name__, "scan_fail"),
            (mod_ok.__name__, "scan_ok"),
        ],
    )

    result = app_api.run_scan_or_raise(
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        ["Sun"],
        ["Earth"],
    )
    assert result == [{"body": "Moon", "detail": "ok"}]

    # first span is run span, next spans correspond to entrypoints
    assert any(span.exceptions for span in spans if span.name.endswith("entrypoint"))
    run_span = next(span for span in spans if span.name.endswith("run"))
    assert any(name == "astroengine.scan.entrypoint_error" for name, _ in run_span.events)


def test_run_scan_or_raise_failure(monkeypatch):
    def scan_none(start_utc, end_utc, moving, targets, **kwargs):
        return None

    mod = _install_scan_module("scan_none_mod", scan_none)

    monkeypatch.setattr(
        app_api,
        "_candidate_order",
        lambda entrypoints=None: [(mod.__name__, "scan_none")],
    )

    with pytest.raises(RuntimeError) as exc:
        app_api.run_scan_or_raise(
            "2024-01-01T00:00:00Z",
            "2024-01-02T00:00:00Z",
            ["Sun"],
            ["Earth"],
        )
    assert "No usable scan entrypoint found" in str(exc.value)
    assert "returned no events" in str(exc.value)


def test_run_sign_ingress_detector_wires_parameters(monkeypatch):
    captured = {}

    def fake_iso_to_jd(value):
        captured.setdefault("iso", []).append(value)
        return {"value": value}

    def fake_find_sign_ingresses(start_jd, end_jd, **kwargs):
        captured["args"] = (start_jd, end_jd, kwargs)
        return ["ok"]

    monkeypatch.setattr(app_api, "iso_to_jd", fake_iso_to_jd)
    monkeypatch.setattr(app_api, "find_sign_ingresses", fake_find_sign_ingresses)

    result = app_api.run_sign_ingress_detector(
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        bodies=["Sun"],
        include_moon=True,
        inner_mode="fast",
        profile={"name": "custom"},
        profile_id="ignored",
        step_hours=3.0,
    )

    assert result == ["ok"]
    assert captured["iso"] == ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"]
    start_jd, end_jd, kwargs = captured["args"]
    assert start_jd == {"value": "2024-01-01T00:00:00Z"}
    assert end_jd == {"value": "2024-01-02T00:00:00Z"}
    assert kwargs == {
        "bodies": ["Sun"],
        "include_moon": True,
        "inner_mode": "fast",
        "profile": {"name": "custom"},
        "step_hours": 3.0,
    }


