# >>> AUTO-GEN BEGIN: test_diagnostics v1.0
import importlib.util
import json
import pathlib
import sys
from types import ModuleType


def _load_diagnostics_module() -> ModuleType:
    try:
        from astroengine import diagnostics as diag  # type: ignore

        return diag  # pragma: no cover - uses package path
    except Exception:
        module_path = (
            pathlib.Path(__file__).resolve().parents[1]
            / "astroengine"
            / "diagnostics.py"
        )
        spec = importlib.util.spec_from_file_location(
            "astroengine.diagnostics_test", module_path
        )
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise RuntimeError(
                "unable to load diagnostics module for testing"
            ) from None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def test_collect_diagnostics_smoke():
    diag = _load_diagnostics_module()

    payload = diag.collect_diagnostics(strict=False)
    assert "summary" in payload and "checks" in payload
    summary = payload["summary"]
    assert isinstance(summary.get("exit_code"), int)
    names = [check["name"] for check in payload["checks"]]
    assert any(name.startswith("Python") for name in names)
    assert "Ephemeris config" in names


def test_json_roundtrip():
    diag = _load_diagnostics_module()

    payload = diag.collect_diagnostics(strict=False)
    dumped = json.dumps(payload)
    assert isinstance(dumped, str) and dumped.startswith("{")


# >>> AUTO-GEN END: test_diagnostics v1.0
