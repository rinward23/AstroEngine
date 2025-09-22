"""Built-in example plugin demonstrating CLI hooks."""

from __future__ import annotations

from argparse import ArgumentParser

from . import hookimpl

__all__ = ["ExamplePlugin"]


class ExamplePlugin:
    """Simple plugin that adds a demo CLI flag."""

    @hookimpl
    def setup_cli(self, parser: ArgumentParser) -> None:
        group = parser.add_argument_group("Plugins")
        group.add_argument(
            "--plugin-example",
            action="store_true",
            help="Enable the AstroEngine example plugin output",
        )
