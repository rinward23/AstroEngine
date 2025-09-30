"""Encrypted note storage and search helpers."""
from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from .crdt import CRDTDocument


def _blake2b_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    import hashlib

    blocks: List[bytes] = []
    counter = 0
    while len(b"".join(blocks)) < length:
        counter_bytes = counter.to_bytes(8, "big")
        digest = hashlib.blake2b(nonce + counter_bytes, key=key, digest_size=32)
        blocks.append(digest.digest())
        counter += 1
    return b"".join(blocks)[:length]


class NotesCipher:
    """Simple authenticated encryption based on Blake2b and XOR."""

    def __init__(self, key: bytes) -> None:
        if len(key) < 16:
            raise ValueError("Encryption key must be at least 16 bytes")
        self._key = key

    @property
    def key(self) -> bytes:
        return self._key

    def encrypt(self, plaintext: bytes) -> str:
        nonce = secrets.token_bytes(16)
        keystream_len = max(len(plaintext), 32)
        keystream = _blake2b_keystream(self._key, nonce, keystream_len)
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
        mac = _blake2b_keystream(self._key, nonce, 32)
        tag = bytes(a ^ b for a, b in zip(mac, keystream[:32]))
        payload = base64.b64encode(nonce + tag + ciphertext)
        return payload.decode("ascii")

    def decrypt(self, payload: str) -> bytes:
        raw = base64.b64decode(payload)
        nonce, tag, ciphertext = raw[:16], raw[16:48], raw[48:]
        keystream_len = max(len(ciphertext), 32)
        keystream = _blake2b_keystream(self._key, nonce, keystream_len)
        expected_tag = bytes(a ^ b for a, b in zip(_blake2b_keystream(self._key, nonce, 32), keystream[:32]))
        if expected_tag != tag:
            raise ValueError("Ciphertext integrity validation failed")
        return bytes(c ^ k for c, k in zip(ciphertext, keystream))


@dataclass
class NoteRecord:
    note_id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    local_created_at: datetime
    title: str
    body_enc: str
    tags: Sequence[str]
    tzid: Optional[str] = None
    location: Optional[str] = None
    visibility: str = "private"
    crdt_state: Dict[str, object] = field(default_factory=dict)
    meta: Dict[str, object] = field(default_factory=dict)

    def decrypted_body(self, cipher: NotesCipher) -> str:
        return cipher.decrypt(self.body_enc).decode("utf-8")


class NotesStore:
    """In-memory representation of the diary store used for tests."""

    def __init__(self, cipher: NotesCipher) -> None:
        self._cipher = cipher
        self._notes: Dict[str, NoteRecord] = {}

    @property
    def cipher(self) -> NotesCipher:
        return self._cipher

    def upsert_from_crdt(self, note_id: str, owner_id: str, document: CRDTDocument) -> NoteRecord:
        payload = document.to_note_dict()
        now = datetime.now(timezone.utc)
        title = payload.get("title", "")
        body = payload.get("body", "")
        tags = tuple(sorted(payload.get("tags", [])))
        enc = self._cipher.encrypt(body.encode("utf-8"))
        record = self._notes.get(note_id)
        if record:
            created_at = record.created_at
            local_created_at = record.local_created_at
        else:
            created_at = now
            local_created_at = payload.get("local_created_at", now)
        new_record = NoteRecord(
            note_id=note_id,
            owner_id=owner_id,
            created_at=created_at,
            updated_at=now,
            local_created_at=local_created_at,
            title=title,
            body_enc=enc,
            tags=tags,
            tzid=payload.get("tzid"),
            location=payload.get("location"),
            visibility=payload.get("visibility", "private"),
            crdt_state=document.to_payload(),
            meta=payload.get("meta", {}),
        )
        self._notes[note_id] = new_record
        return new_record

    def get(self, note_id: str) -> Optional[NoteRecord]:
        return self._notes.get(note_id)

    def search(self, owner_id: str, query: str = "", tags: Optional[Iterable[str]] = None) -> List[NoteRecord]:
        required_tags = set(tags or [])
        results: List[NoteRecord] = []
        for record in self._notes.values():
            if record.owner_id != owner_id:
                continue
            if required_tags and not required_tags.issubset(set(record.tags)):
                continue
            if query:
                haystack = f"{record.title}\n{self._cipher.decrypt(record.body_enc).decode('utf-8')}"
                if query.lower() not in haystack.lower():
                    continue
            results.append(record)
        results.sort(key=lambda r: r.updated_at, reverse=True)
        return results

    def export_owner_notes(self, owner_id: str) -> str:
        data = [
            {
                "note_id": record.note_id,
                "title": record.title,
                "body": record.decrypted_body(self._cipher),
                "tags": list(record.tags),
                "meta": record.meta,
            }
            for record in self._notes.values()
            if record.owner_id == owner_id
        ]
        return json.dumps({"notes": data}, indent=2, sort_keys=True)

    def erase_owner_notes(self, owner_id: str) -> int:
        to_delete = [note_id for note_id, record in self._notes.items() if record.owner_id == owner_id]
        for note_id in to_delete:
            del self._notes[note_id]
        return len(to_delete)
