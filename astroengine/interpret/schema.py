"""JSON Schema definition for interpretation rulepacks."""

from __future__ import annotations

RULEPACK_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["rulepack", "version", "profiles", "rules"],
    "properties": {
        "rulepack": {"type": "string"},
        "version": {"type": "integer", "minimum": 1},
        "meta": {"type": "object"},
        "profiles": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {
                "type": "object",
                "required": ["tags"],
                "properties": {
                    "tags": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                    }
                },
            },
        },
        "archetypes": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "rules": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/definitions/rule"},
        },
    },
    "definitions": {
        "rule": {
            "type": "object",
            "required": ["id", "scope", "when", "then"],
            "properties": {
                "id": {"type": "string"},
                "scope": {
                    "enum": ["synastry", "composite", "davison"],
                    "default": "synastry",
                },
                "when": {"$ref": "#/definitions/when"},
                "then": {"$ref": "#/definitions/then"},
            },
            "additionalProperties": False,
        },
        "when": {
            "type": "object",
            "required": ["bodiesA", "bodiesB", "aspects"],
            "properties": {
                "bodiesA": {
                    "oneOf": [
                        {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        {"const": "*"},
                    ]
                },
                "bodiesB": {
                    "oneOf": [
                        {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        {"const": "*"},
                    ]
                },
                "aspects": {
                    "oneOf": [
                        {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 1,
                        },
                        {"const": "*"},
                    ]
                },
                "min_severity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "additionalProperties": False,
        },
        "then": {
            "type": "object",
            "required": ["title", "tags"],
            "properties": {
                "title": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "base_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5,
                },
                "score_fn": {"type": "string", "default": "cosine^1.0"},
                "markdown_template": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

__all__ = ["RULEPACK_SCHEMA"]
