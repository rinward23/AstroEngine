"""Privacy configuration helpers."""
from __future__ import annotations

from astroengine.engine.privacy import PrivacyController


def toggle_local_only(controller: PrivacyController, enabled: bool, actor: str) -> None:
    controller.set_local_only(enabled, actor)


def export_notes(controller: PrivacyController, actor: str) -> str:
    return controller.export_notes(actor)


def erase_notes(controller: PrivacyController, actor: str) -> int:
    return controller.erase_notes(actor)
