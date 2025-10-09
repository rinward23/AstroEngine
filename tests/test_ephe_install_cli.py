from __future__ import annotations

from pathlib import Path

import pytest

from astroengine.ephe import install


class DummyResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.headers = {"content-length": str(len(payload))}
        self.status_code = 200
        self.closed = False

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        yield self._payload

    def close(self) -> None:
        self.closed = True


def test_requires_license_acknowledgement() -> None:
    with pytest.raises(SystemExit) as exc:
        install.main(["--install", "https://example.com/sweph.zip"])
    assert exc.value.code == 2


def test_downloads_when_license_confirmed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = b"sweph"

    def fake_get(url: str, stream: bool, timeout: int):
        assert stream is True
        assert "sweph.zip" in url
        return DummyResponse(payload)

    monkeypatch.setattr(install.requests, "get", fake_get)

    exit_code = install.main(
        [
            "--install",
            "https://example.com/sweph.zip",
            "--target",
            str(tmp_path),
            "--agree-license",
            "--skip-extract",
        ]
    )

    assert exit_code == 0
    output_file = tmp_path / "sweph.zip"
    assert output_file.exists()
    assert output_file.read_bytes() == payload
