"""CLI integration for exploring the AstroEngine codex."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, Mapping, Sequence

from ..codex import (
    UnknownCodexPath,
    describe_path,
    get_registry,
    registry_snapshot,
    resolved_files,
)
from ..modules import AstroRegistry

__all__ = ["add_subparser"]


def add_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``codex`` CLI command."""

    parser = sub.add_parser(
        "codex",
        help="Explore module/submodule metadata registered with the codex",
        description=(
            "Inspect the module → submodule → channel → subchannel registry"
            " hierarchy used by the AstroEngine developer codex."
        ),
    )
    codex_sub = parser.add_subparsers(dest="codex_command", required=True)

    tree_parser = codex_sub.add_parser(
        "tree",
        help="Render the codex hierarchy as text or JSON",
        description=(
            "Display the full registry tree so developers can discover which"
            " modules, channels, and subchannels are available."
        ),
    )
    tree_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the hierarchy as JSON instead of a formatted tree",
    )
    tree_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the registry snapshot before rendering the tree",
    )
    tree_parser.set_defaults(handler=_render_tree)

    show_parser = codex_sub.add_parser(
        "show",
        help="Describe metadata for a specific registry path",
        description=(
            "Look up metadata and payload references for a module,"
            " submodule, channel, or subchannel."
        ),
    )
    show_parser.add_argument(
        "path",
        nargs="*",
        help="Path expressed as module[/submodule[/channel[/subchannel]]] or dot separated",
    )
    show_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit metadata as JSON",
    )
    show_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the registry snapshot before resolving the path",
    )
    show_parser.set_defaults(handler=_show_node)

    files_parser = codex_sub.add_parser(
        "files",
        help="List filesystem assets referenced by codex metadata",
        description=(
            "Resolve metadata and payload entries to concrete files so"
            " that they can be opened in the editor."
        ),
    )
    files_parser.add_argument(
        "path",
        nargs="*",
        help="Path expressed as module[/submodule[/channel[/subchannel]]] or dot separated",
    )
    files_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the resolved paths as JSON",
    )
    files_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the registry snapshot before resolving the path",
    )
    files_parser.set_defaults(handler=_list_files)

    parser.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> int:
    try:
        handler = getattr(args, "handler")
    except AttributeError:  # pragma: no cover - argparse guards this
        parser = args.__dict__.get("_parser")
        if parser is not None:
            parser.print_help()
        return 2

    try:
        return handler(args)
    except UnknownCodexPath as exc:
        path = " / ".join(_normalise_segments(getattr(args, "path", [])))
        print(f"Unknown codex path: {path or exc.args}", file=sys.stderr)
        return 2


def _normalise_segments(values: Sequence[str]) -> list[str]:
    segments: list[str] = []
    for value in values:
        if not value:
            continue
        chunk = value.replace("/", ".")
        segments.extend([part for part in chunk.split(".") if part])
    return segments


def _render_tree(args: argparse.Namespace) -> int:
    snapshot = registry_snapshot(refresh=args.refresh)
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0

    for line in _format_tree(snapshot):
        print(line)
    return 0


def _format_tree(snapshot: Mapping[str, Mapping[str, object]]) -> Iterable[str]:
    modules = sorted(snapshot.items())
    for module_name, module_payload in modules:
        yield module_name
        submodules = module_payload.get("submodules", {})
        for submodule_name, sub_payload in sorted(submodules.items()):
            yield f"  {submodule_name}"
            channels = sub_payload.get("channels", {})
            for channel_name, channel_payload in sorted(channels.items()):
                yield f"    {channel_name}"
                subchannels = channel_payload.get("subchannels", {})
                for subchannel_name in sorted(subchannels):
                    yield f"      {subchannel_name}"


def _registry_for(args: argparse.Namespace) -> AstroRegistry:
    return get_registry(refresh=args.refresh)


def _show_node(args: argparse.Namespace) -> int:
    registry = _registry_for(args)
    segments = _normalise_segments(args.path)
    node = describe_path(segments, registry=registry)
    if args.json:
        print(json.dumps(node.as_dict(), indent=2, sort_keys=True))
    else:
        _print_node(node)
    return 0


def _print_node(node) -> None:
    header = node.name if node.name is not None else "<registry>"
    print(f"{node.kind}: {header}")

    if node.metadata:
        print("Metadata:")
        for key in sorted(node.metadata):
            value = node.metadata[key]
            print(f"  {key}: {value}")

    if node.payload:
        print("Payload:")
        for key in sorted(node.payload):
            value = node.payload[key]
            print(f"  {key}: {value}")

    if node.children:
        print("Children:")
        for child in node.children:
            print(f"  - {child}")


def _list_files(args: argparse.Namespace) -> int:
    registry = _registry_for(args)
    segments = _normalise_segments(args.path)
    paths = [str(p) for p in resolved_files(segments, registry=registry)]
    if args.json:
        print(json.dumps(paths, indent=2))
    else:
        for path in paths:
            print(path)
    return 0
