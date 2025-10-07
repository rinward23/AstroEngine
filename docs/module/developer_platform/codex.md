# Developer Platform Codex

The codex surfaces the module → submodule → channel → subchannel registry
used throughout AstroEngine. It exists to help developers discover the
available datasets, rulepacks, and workflows without needing to read every
Python file manually.

## Capabilities

* Provides a structured API (`astroengine.codex`) for programmatic access to
  the registry tree.
* Ships a terminal command (`astroengine codex`) so engineers can browse the
  hierarchy, inspect metadata, and jump to the underlying documentation.
* Resolves metadata references to concrete files, ensuring that every run is
  backed by the real sources in the repository.

## CLI {#cli}

The CLI exposes three primary actions:

* `astroengine codex tree` renders the full hierarchy. Add `--json` to obtain
  the raw snapshot emitted by `AstroRegistry.as_dict()`.
* `astroengine codex show MODULE[/SUBMODULE[/CHANNEL[/SUBCHANNEL]]]` prints
  metadata for a specific node. Use `--json` to emit the underlying payload as
  JSON for scripting.
* `astroengine codex files MODULE/...` resolves documentation or dataset
  references to absolute filesystem paths, allowing you to open the referenced
  material in your editor.

Examples:

```bash
# Summarise the developer platform module
astroengine codex show developer_platform --json

# Locate all documentation files linked from the codex CLI entries
astroengine codex files developer_platform codex cli
```

## Python helpers {#python}

The `astroengine.codex` package mirrors the CLI functionality for use inside
Python:

```python
from astroengine import codex

node = codex.describe_path(["developer_platform", "codex", "access", "cli"])
print(node.metadata["description"])  # -> Command line interface for browsing codex metadata.

paths = codex.resolved_files(["developer_platform", "codex", "access", "python"])
for path in paths:
    print(path)
```

Calling `codex.registry_snapshot()` returns the same structure that powers the
`tree` command, while `codex.get_registry(refresh=True)` rebuilds the registry
for integration tests. All metadata returned by these functions originates
from the SolarFire-aligned registry definitions shipped in the repository—no
synthetic values are introduced.

## Model Context Protocol integration {#mcp}

The codex helpers can be surfaced to a Model Context Protocol (MCP) host so
external tools can query the same registry data that powers the CLI and
Python APIs. Two key entry points are provided:

* `astroengine codex mcp` emits a JSON manifest describing the available MCP
  tools (`registry_snapshot`, `describe_path`, and `resolved_files`) alongside
  curated filesystem servers that expose datasets and documentation.
* `astroengine.codex.codex_mcp_server()` returns the same manifest for direct
  programmatic use, while `astroengine.codex.common_mcp_servers()` lists the
  complementary servers used by the CLI output.

Each manifest is backed by the live registry snapshot and documentation paths
tracked in this repository so that MCP orchestrators never reference synthetic
or placeholder data.
