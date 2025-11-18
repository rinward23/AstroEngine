"""Registry wiring for developer platform artefacts (SDKs, CLI, portal)."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_developer_platform_module"]

DEV_DOC = "docs/module/developer_platform.md"


def register_developer_platform_module(registry: AstroRegistry) -> None:
    """Expose developer platform deliverables and documentation."""

    module = registry.register_module(
        "developer_platform",
        metadata={
            "description": "SDKs, CLI workflows, and portal assets generated from OpenAPI specs.",
            "documentation": DEV_DOC,
            "status": "available",
        },
    )

    sdks = module.register_submodule(
        "sdks",
        metadata={
            "description": "Typed SDK plans for interacting with AstroEngine services.",
            "docs": ["docs/module/developer_platform/sdks.md"],
        },
    )
    sdks.register_channel(
        "languages",
        metadata={"description": "Client SDK targets driven by frozen OpenAPI schemas."},
    ).register_subchannel(
        "typescript",
        metadata={
            "description": "TypeScript SDK generated via docs/module/developer_platform/sdks.md",
            "status": "available",
        },
        payload={
            "generator": "docs/module/developer_platform/sdks.md#typescript",
            "schemas": ["openapi/"],
        },
    )
    sdks.get_channel("languages").register_subchannel(
        "python",
        metadata={
            "description": "Python SDK outline referencing OpenAPI generator workflows.",
            "status": "available",
        },
        payload={
            "generator": "docs/module/developer_platform/sdks.md#python",
            "schemas": ["openapi/"],
        },
    )

    agents = module.register_submodule(
        "agents",
        metadata={
            "description": "Automation toolkit for embedding AstroEngine data inside agents.",
            "docs": ["docs/module/developer_platform/agents.md"],
            "status": "beta",
        },
    )
    agent_toolkits = agents.register_channel(
        "toolkits",
        metadata={
            "description": "SDK surfaces designed for orchestration agents and LLM pipelines.",
        },
    )
    agent_toolkits.register_subchannel(
        "python",
        metadata={
            "description": "Python helper exposing registry discovery and transit scanning for agents.",
            "status": "available",
        },
        payload={
            "module": "astroengine.agents.AgentSDK",
            "datasets": [
                "docs-site/docs/fixtures/timeline_events.json",
                "qa/artifacts/solarfire/2025-10-02/cross_engine.json",
            ],
            "documentation": "docs/module/developer_platform/agents.md#python",
        },
    )

    cli = module.register_submodule(
        "cli",
        metadata={
            "description": "Command line tooling aligned with runtime modules.",
            "docs": ["docs/module/developer_platform/cli.md"],
        },
    )
    cli.register_channel(
        "workflows",
        metadata={
            "description": "Planned CLI entrypoints that mirror scan/event/election workflows.",
        },
    ).register_subchannel(
        "transit_scan",
        metadata={
            "description": "Placeholder CLI for scan/election orchestration.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/developer_platform/cli.md",
            "commands": ["astroengine scan", "astroengine returns"],
        },
    )

    codex = module.register_submodule(
        "codex",
        metadata={
            "description": "Developer codex surfaces for inspecting registry assets.",
            "docs": ["docs/module/developer_platform/codex.md"],
            "status": "beta",
        },
    )
    access = codex.register_channel(
        "access",
        metadata={
            "description": "Entry points that expose the registry hierarchy to developers.",
        },
    )
    access.register_subchannel(
        "cli",
        metadata={
            "description": "Command line interface for browsing codex metadata.",
            "status": "available",
        },
        payload={
            "command": "astroengine codex",
            "documentation": "docs/module/developer_platform/codex.md#cli",
        },
    )
    access.register_subchannel(
        "python",
        metadata={
            "description": "Python helpers for programmatic codex exploration.",
            "status": "available",
        },
        payload={
            "module": "astroengine.codex",
            "functions": [
                "astroengine.codex.describe_path",
                "astroengine.codex.resolved_files",
            ],
            "documentation": "docs/module/developer_platform/codex.md#python",
        },
    )
    access.register_subchannel(
        "mcp",
        metadata={
            "description": "Model Context Protocol manifest for codex registry helpers.",
            "status": "available",
        },
        payload={
            "manifest": "astroengine.codex.codex_mcp_server",
            "recommendedServers": "astroengine.codex.common_mcp_servers",
            "documentation": "docs/module/developer_platform/codex.md#mcp",
        },
    )

    devportal = module.register_submodule(
        "devportal",
        metadata={
            "description": "Developer portal assets (docs, playground, collection exports).",
            "docs": ["docs/module/developer_platform/devportal.md"],
        },
    )
    portals = devportal.register_channel(
        "surfaces",
        metadata={
            "description": "Static site and playground deliverables documented under devportal.md.",
        },
    )
    portals.register_subchannel(
        "docs",
        metadata={
            "description": "Documentation site plan (Docusaurus) for the developer portal.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/developer_platform/devportal.md#documentation",
        },
    )
    portals.register_subchannel(
        "playground",
        metadata={
            "description": "API playground referencing frozen OpenAPI schemas.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/developer_platform/devportal.md#playground",
        },
    )
    portals.register_subchannel(
        "collections",
        metadata={
            "description": "Postman/Insomnia collection exports derived from openapi specs.",
            "status": "planned",
        },
        payload={
            "documentation": "docs/module/developer_platform/devportal.md#collections",
        },
    )

    webhooks = module.register_submodule(
        "webhooks",
        metadata={
            "description": "Webhook delivery contracts and verification helpers.",
            "docs": ["docs/module/developer_platform/webhooks.md"],
        },
    )
    webhooks.register_channel(
        "contracts",
        metadata={
            "description": "Webhook delivery jobs and signature verification flows.",
        },
    ).register_subchannel(
        "jobs",
        metadata={
            "description": "Webhook job processing pipelines backed by recorded payloads.",
            "status": "beta",
        },
        payload={
            "documentation": "docs/module/developer_platform/webhooks.md#jobs",
        },
    )
    webhooks.get_channel("contracts").register_subchannel(
        "verification",
        metadata={
            "description": "Signature verification helpers shared by SDK/CLI implementations.",
            "status": "beta",
        },
        payload={
            "documentation": "docs/module/developer_platform/webhooks.md#verification",
        },
    )
