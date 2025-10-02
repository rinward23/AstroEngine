"""Registry wiring for schema interoperability artefacts."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_interop_module"]

INTEROP_DOC = "docs/module/interop.md"


def register_interop_module(registry: AstroRegistry) -> None:
    """Expose JSON schema catalogue for export validation."""

    module = registry.register_module(
        "interop",
        metadata={
            "description": "Schema catalogue for export payloads and contact gating.",
            "documentation": INTEROP_DOC,
            "datasets": [
                "schemas/result_schema_v1.json",
                "schemas/result_schema_v1_with_domains.json",
                "schemas/contact_gate_schema_v2.json",
                "schemas/natal_input_v1_ext.json",
                "schemas/orbs_policy.json",
            ],
        },
    )

    schemas = module.register_submodule(
        "schemas",
        metadata={
            "description": "JSON schemas validated by astroengine.validation helpers.",
        },
    )
    validation_channel = schemas.register_channel(
        "json_schema",
        metadata={
            "description": "Schemas referenced by validate_payload and related helpers.",
        },
    )
    validation_channel.register_subchannel(
        "result_v1",
        metadata={
            "description": "Baseline result schema covering transit runs.",
            "tests": ["tests/test_result_schema.py"],
        },
        payload={
            "path": "schemas/result_schema_v1.json",
            "schema_id": "result_v1",
        },
    )
    validation_channel.register_subchannel(
        "result_v1_with_domains",
        metadata={
            "description": "Result schema variant with domain annotations.",
            "tests": ["tests/test_result_schema.py"],
        },
        payload={
            "path": "schemas/result_schema_v1_with_domains.json",
            "schema_id": "result_v1_with_domains",
        },
    )
    validation_channel.register_subchannel(
        "contact_gate_v2",
        metadata={
            "description": "Contact gate schema capturing audit trails for UI gating decisions.",
            "tests": ["tests/test_contact_gate_schema.py"],
        },
        payload={
            "path": "schemas/contact_gate_schema_v2.json",
            "schema_id": "contact_gate_v2",
        },
    )
    validation_channel.register_subchannel(
        "natal_input_v1_ext",
        metadata={
            "description": "Extended natal input metadata accepted during Solar Fire imports.",
            "tests": ["tests/test_result_schema.py"],
        },
        payload={
            "path": "schemas/natal_input_v1_ext.json",
            "schema_id": "natal_input_v1_ext",
        },
    )

    data_channel = schemas.register_channel(
        "json_data",
        metadata={
            "description": "Non-schema JSON documents distributed for interoperability.",
        },
    )
    data_channel.register_subchannel(
        "orbs_policy",
        metadata={
            "description": "Aspect orb definitions used by external clients.",
            "tests": ["tests/test_orbs_policy.py"],
        },
        payload={
            "path": "schemas/orbs_policy.json",
            "loader": "astroengine.data.schemas.load_schema_document",
        },
    )
