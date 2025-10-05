"""Tests for developer-mode PIN enforcement."""

from __future__ import annotations

import importlib
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_client() -> TestClient:
    """Return a TestClient with the devmode router attached."""

    for module in ["app.devmode.api", "app.devmode.security"]:
        if module in sys.modules:
            del sys.modules[module]

    os.environ["DEV_MODE"] = "1"
    os.environ["DEV_PIN"] = "pin-code"

    devmode_api = importlib.import_module("app.devmode.api")
    app = FastAPI()
    app.include_router(devmode_api.router)
    return TestClient(app)


def test_dev_actions_require_pin() -> None:
    """Requests without the developer PIN are rejected."""

    client = build_client()
    response = client.get("/v1/dev/history")
    assert response.status_code == 401
    assert response.json()["detail"] == "Developer PIN required"


def test_dev_actions_accept_valid_pin() -> None:
    """Requests proceed when the correct PIN is supplied."""

    client = build_client()
    response = client.get("/v1/dev/history", headers={"X-Dev-Pin": "pin-code"})
    assert response.status_code == 200
    assert response.json() == []
