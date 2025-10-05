"""Materialise OpenAPI documents for the Relationship docs site."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

SCRIPT_PATH = Path(__file__).resolve()
DOCS_SITE_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from astroengine.api_server import app as core_app
from app.routers.relationship import router as plus_relationship_router
from app.routers.interpret import router as plus_interpret_router

DEFAULT_OUTPUT = DOCS_SITE_ROOT / "docs" / "api" / "openapi"
DEFAULT_EXAMPLES = DOCS_SITE_ROOT / "docs" / "api" / "examples"
DEFAULT_POSTMAN = DOCS_SITE_ROOT / "docs" / "api" / "relationship.postman.json"

SYN_SAMPLE = {
    "subject": {"ts": "1990-07-11T08:00:00Z", "lat": 40.7128, "lon": -74.006},
    "partner": {"ts": "1992-03-15T20:15:00Z", "lat": 34.0522, "lon": -118.2437},
    "aspects": [0, 60, 90, 120, 180],
    "orb": 2.0,
}

SCAN_SAMPLE = {
    "natal_inline": {
        "ts": "1990-07-11T08:00:00Z",
        "lat": 40.7128,
        "lon": -74.006,
    },
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-06-01T00:00:00Z",
    "bodies": ["Mars", "Jupiter"],
    "targets": ["Sun", "Saturn"],
    "aspects": ["conjunction", "opposition"],
    "orb": 1.5,
    "step_days": 3,
}

RETURNS_SAMPLE = {
    "natal_inline": {
        "ts": "1990-07-11T08:00:00Z",
        "lat": 40.7128,
        "lon": -74.006,
    },
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T00:00:00Z",
    "bodies": ["Sun", "Moon"],
}

NATAL_SAMPLE = {
    "name": "Sample Chart",
    "utc": "1990-07-11T08:00:00Z",
    "lat": 40.7128,
    "lon": -74.006,
    "tz": "America/New_York",
    "place": "New York, NY",
}

INTERPRET_SAMPLE = {
    "scope": "synastry",
    "rulepack_id": "relationship_basic",
    "hits": [
        {
            "a": "Sun",
            "b": "Moon",
            "aspect": "conjunction",
            "severity": 0.85,
        },
        {
            "a": "Venus",
            "b": "Saturn",
            "aspect": "trine",
            "severity": 0.72,
        },
    ],
    "top_k": 5,
}


def _slugify(tag: str) -> str:
    return tag.lower().replace(" ", "-")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_specs(client: TestClient, output: Path, *, prefix: str = "") -> dict[str, Path]:
    """Return mapping of tag -> json path after writing files."""

    openapi = client.get("/openapi.json").json()

    _ensure_dir(output)

    def _name(suffix: str) -> str:
        return f"{prefix}{suffix}" if prefix else suffix

    full_path = output / f"{_name('full')}.json"
    full_path.write_text(json.dumps(openapi, indent=2), encoding="utf-8")

    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for route, methods in openapi.get("paths", {}).items():
        for method, payload in methods.items():
            tags = payload.get("tags") or ["untagged"]
            for tag in tags:
                slug = _slugify(tag)
                entry = grouped[slug].setdefault(route, {})
                entry[method] = deepcopy(payload)

    written: dict[str, Path] = { _name("full"): full_path }
    for tag, paths in sorted(grouped.items()):
        spec = {
            "openapi": openapi.get("openapi", "3.1.0"),
            "info": deepcopy(openapi.get("info", {})),
            "servers": deepcopy(openapi.get("servers", [])),
            "components": deepcopy(openapi.get("components", {})),
            "paths": paths,
        }
        spec_path = output / f"{_name(tag)}.json"
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        written[_name(tag)] = spec_path

    return written


def build_examples(directory: Path) -> None:
    _ensure_dir(directory)
    (directory / "synastry-request.json").write_text(
        json.dumps(SYN_SAMPLE, indent=2), encoding="utf-8"
    )
    (directory / "scan-transits-request.json").write_text(
        json.dumps(SCAN_SAMPLE, indent=2), encoding="utf-8"
    )
    (directory / "scan-returns-request.json").write_text(
        json.dumps(RETURNS_SAMPLE, indent=2), encoding="utf-8"
    )
    (directory / "natal-upsert.json").write_text(
        json.dumps(NATAL_SAMPLE, indent=2), encoding="utf-8"
    )
    (directory / "interpret-request.json").write_text(
        json.dumps(INTERPRET_SAMPLE, indent=2), encoding="utf-8"
    )


def build_postman(path: Path) -> None:
    collection = {
        "info": {
            "name": "AstroEngine Relationship APIs",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Requests derived from the FastAPI OpenAPI document.",
        },
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000"},
        ],
        "item": [
            {
                "name": "Synastry Aspects",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/v1/synastry/aspects",
                        "host": ["{{baseUrl}}"],
                        "path": ["v1", "synastry", "aspects"],
                    },
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps(SYN_SAMPLE, indent=2),
                    },
                },
            },
            {
                "name": "Transit Scan",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/v1/scan/transits",
                        "host": ["{{baseUrl}}"],
                        "path": ["v1", "scan", "transits"],
                    },
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps(SCAN_SAMPLE, indent=2),
                    },
                },
            },
            {
                "name": "Returns Scan",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/v1/scan/returns",
                        "host": ["{{baseUrl}}"],
                        "path": ["v1", "scan", "returns"],
                    },
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps(RETURNS_SAMPLE, indent=2),
                    },
                },
            },
            {
                "name": "Natal Upsert",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "url": {
                        "raw": "{{baseUrl}}/natals/sample",
                        "host": ["{{baseUrl}}"],
                        "path": ["natals", "sample"],
                    },
                    "body": {
                        "mode": "raw",
                        "raw": json.dumps(NATAL_SAMPLE, indent=2),
                    },
                },
            },
        ],
    }
    path.write_text(json.dumps(collection, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--postman", type=Path, default=DEFAULT_POSTMAN)
    args = parser.parse_args()

    core_client = TestClient(core_app)
    specs_core = build_specs(core_client, args.output, prefix="core-")

    plus_app = FastAPI(
        title="AstroEngine Relationship Plus API",
        default_response_class=ORJSONResponse,
    )
    plus_app.include_router(plus_relationship_router)
    plus_app.include_router(plus_interpret_router)
    plus_client = TestClient(plus_app)
    specs_plus = build_specs(plus_client, args.output, prefix="plus-")

    specs = {**specs_core, **specs_plus}
    build_examples(args.examples)
    build_postman(args.postman)

    summary = {name: str(path.relative_to(Path.cwd())) for name, path in specs.items()}
    print(json.dumps({"written": summary, "examples": str(args.examples), "postman": str(args.postman)}, indent=2))


if __name__ == "__main__":
    main()
