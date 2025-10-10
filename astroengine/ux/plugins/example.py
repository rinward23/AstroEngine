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

    @hookimpl
    def prepare_chat_prompt(
        self, prompt: str, metadata: dict[str, object]
    ) -> tuple[str, dict[str, object]] | None:
        """Illustrate prompt mutation by appending an opt-in footer."""

        if not metadata.get("plugin_example_enabled"):
            return None
        footer = "\n\n[example plugin footer enabled]"
        return prompt + footer, {"example_footer": True}

    @hookimpl
    def handle_chat_response(
        self, prompt: str, response: str, metadata: dict[str, object]
    ) -> None:
        """Print a debug message when the example flag is active."""

        if metadata.get("example_footer"):
            print("ExamplePlugin observed response:", response[:60], flush=True)
