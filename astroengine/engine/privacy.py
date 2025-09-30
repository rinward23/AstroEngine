"""Privacy controls covering local-only mode and exports."""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .notes.store import NotesCipher, NotesStore


@dataclass
class AuditLogEntry:
    timestamp: datetime
    actor: str
    action: str
    details: Dict[str, object]


@dataclass
class WorkspaceKeys:
    current_key_id: str
    secret: bytes


class PrivacyController:
    """Manage privacy policies for a diary workspace."""

    def __init__(self, owner_id: str, cipher: NotesCipher, store: NotesStore) -> None:
        self.owner_id = owner_id
        self.cipher = cipher
        self.store = store
        self.local_only = False
        self.audit_log: List[AuditLogEntry] = []
        self.keys = WorkspaceKeys(current_key_id=self._new_key_id(), secret=cipher.key)

    def _new_key_id(self) -> str:
        return secrets.token_hex(8)

    def set_local_only(self, enabled: bool, actor: str) -> None:
        self.local_only = enabled
        self._log(actor, "local_only", {"enabled": enabled})

    def allow_network_calls(self) -> bool:
        return not self.local_only

    def export_notes(self, actor: str) -> str:
        export = self.store.export_owner_notes(self.owner_id)
        self._log(actor, "export", {"size": len(export)})
        return export

    def erase_notes(self, actor: str) -> int:
        count = self.store.erase_owner_notes(self.owner_id)
        self._log(actor, "erase", {"count": count})
        return count

    def rotate_key(self, actor: str, new_secret: Optional[bytes] = None) -> None:
        self.keys = WorkspaceKeys(current_key_id=self._new_key_id(), secret=new_secret or secrets.token_bytes(32))
        self._log(actor, "rotate_key", {"key_id": self.keys.current_key_id})

    def _log(self, actor: str, action: str, details: Dict[str, object]) -> None:
        self.audit_log.append(
            AuditLogEntry(timestamp=datetime.now(timezone.utc), actor=actor, action=action, details=details)
        )
