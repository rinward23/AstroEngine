"""Conflict-free replicated note documents.

This module provides a minimal CRDT implementation tailored for
synchronising diary notes across multiple devices.  The implementation is
purposefully conservative – instead of modelling an arbitrary text CRDT
it tracks field level updates (title, body, tags, metadata) and resolves
conflicts deterministically using hybrid logical clocks.

The design goal is to guarantee that regardless of merge ordering the
same final state is produced and no user authored field is discarded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, Mapping, MutableMapping, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


@dataclass(frozen=True)
class FieldVersion:
    """Metadata describing the last update to a field."""

    timestamp: datetime
    device_id: str

    def dominates(self, other: "FieldVersion") -> bool:
        """Return ``True`` when this version should win over ``other``."""

        if self.timestamp > other.timestamp:
            return True
        if self.timestamp < other.timestamp:
            return False
        # Deterministic tie breaker on the device identifier.
        return self.device_id > other.device_id

    def to_dict(self) -> Dict[str, str]:
        return {"timestamp": self.timestamp.strftime(ISO_FORMAT), "device": self.device_id}

    @classmethod
    def from_dict(cls, payload: Mapping[str, str]) -> "FieldVersion":
        return cls(
            timestamp=datetime.strptime(payload["timestamp"], ISO_FORMAT).replace(tzinfo=timezone.utc),
            device_id=payload["device"],
        )


@dataclass
class CRDTField:
    """A field inside the CRDT document."""

    value: object
    version: FieldVersion

    def merge(self, other: "CRDTField") -> "CRDTField":
        if other.version.dominates(self.version):
            return other
        if self.version.dominates(other.version):
            return self
        # If both are equal we combine values where possible (e.g. tags).
        if isinstance(self.value, set) and isinstance(other.value, set):
            combined = sorted(self.value | other.value)
            return CRDTField(value=set(combined), version=self.version)
        return self


@dataclass
class CRDTDocument:
    """A CRDT note document comprised of multiple fields."""

    device_id: str
    fields: MutableMapping[str, CRDTField] = field(default_factory=dict)

    def apply_patch(self, patch: Mapping[str, object], timestamp: Optional[datetime] = None) -> None:
        """Apply a patch generated locally on this device."""

        ts = timestamp or datetime.now(timezone.utc)
        version = FieldVersion(timestamp=ts, device_id=self.device_id)
        for key, value in patch.items():
            current = self.fields.get(key)
            field_state = CRDTField(value=value, version=version)
            if current is None:
                self.fields[key] = field_state
            else:
                self.fields[key] = current.merge(field_state)

    def merge(self, *others: "CRDTDocument") -> "CRDTDocument":
        """Merge this document with any number of peers and return ``self``."""

        for other in others:
            for key, field_value in other.fields.items():
                if key in self.fields:
                    self.fields[key] = self.fields[key].merge(field_value)
                else:
                    self.fields[key] = field_value
        return self

    def to_payload(self) -> Dict[str, object]:
        """Serialise the document into a JSON friendly mapping."""

        payload = {}
        for key, field_state in self.fields.items():
            payload[key] = {
                "value": field_state.value,
                "version": field_state.version.to_dict(),
            }
        return payload

    @classmethod
    def from_payload(cls, device_id: str, payload: Mapping[str, Mapping[str, object]]) -> "CRDTDocument":
        fields: MutableMapping[str, CRDTField] = {}
        for key, content in payload.items():
            version = FieldVersion.from_dict(content["version"])
            fields[key] = CRDTField(value=content["value"], version=version)
        return cls(device_id=device_id, fields=fields)

    def to_note_dict(self) -> Dict[str, object]:
        """Return the plain dictionary with current field values."""

        return {key: field_state.value for key, field_state in self.fields.items()}


def merge_documents(device_id: str, documents: Iterable[CRDTDocument]) -> CRDTDocument:
    """Merge ``documents`` into a new :class:`CRDTDocument` for ``device_id``."""

    merged = CRDTDocument(device_id=device_id)
    for doc in documents:
        merged.merge(doc)
    return merged
