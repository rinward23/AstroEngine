"""Tests for the astroengine.codex helper module."""

from __future__ import annotations

from pathlib import Path

from astroengine import codex


def test_describe_root_contains_developer_platform() -> None:
    node = codex.describe_path()
    assert node.kind == "registry"
    assert "developer_platform" in node.children


def test_codex_cli_entry_metadata_and_payload() -> None:
    node = codex.describe_path(["developer_platform", "codex", "access", "cli"])
    assert node.kind == "subchannel"
    assert node.metadata.get("status") == "available"
    assert node.payload and node.payload.get("command") == "astroengine codex"


def test_resolved_files_for_python_helpers_points_to_docs() -> None:
    paths = codex.resolved_files(["developer_platform", "codex", "access", "python"])
    filenames = {Path(p).name for p in paths}
    assert "codex.md" in filenames
    for path in paths:
        assert Path(path).exists()


def test_codex_mcp_manifest_includes_registry_resource() -> None:
    manifest = codex.codex_mcp_server()
    payload = manifest.as_dict()
    assert payload["name"] == "astroengine-codex"
    assert "registry" in payload["resources"]
    registry_resource = payload["resources"]["registry"]
    assert isinstance(registry_resource.get("data"), dict)
    assert payload["tools"], "Expected codex MCP manifest to expose tools"


def test_common_mcp_servers_expose_dataset_root() -> None:
    servers = codex.common_mcp_servers()
    dataset_server = next(server for server in servers if server.name == "astroengine-datasets")
    root_path = Path(dataset_server.configuration["root"])  # type: ignore[index]
    assert root_path.exists()
    assert root_path.name == "datasets"
