from __future__ import annotations

from astroengine.engine.notes.crdt import CRDTDocument
from astroengine.engine.notes.store import NotesCipher, NotesStore
from astroengine.engine.privacy import PrivacyController


def build_store():
    cipher = NotesCipher(b"0123456789abcdef0123456789abcdef")
    store = NotesStore(cipher)
    return cipher, store


def seed_note(store: NotesStore, cipher: NotesCipher):
    document = CRDTDocument(device_id="user")
    document.apply_patch({"title": "Entry", "body": "All data is real", "tags": ["journal"]})
    store.upsert_from_crdt("note1", "user", document)


def test_local_only_blocks_network():
    cipher, store = build_store()
    seed_note(store, cipher)
    controller = PrivacyController(owner_id="user", cipher=cipher, store=store)
    controller.set_local_only(True, actor="user")
    assert not controller.allow_network_calls()
    controller.set_local_only(False, actor="user")
    assert controller.allow_network_calls()


def test_export_and_erase_flow():
    cipher, store = build_store()
    seed_note(store, cipher)
    controller = PrivacyController(owner_id="user", cipher=cipher, store=store)
    export = controller.export_notes(actor="user")
    assert "Entry" in export
    erased = controller.erase_notes(actor="user")
    assert erased == 1


def test_key_rotation_changes_identifier():
    cipher, store = build_store()
    controller = PrivacyController(owner_id="user", cipher=cipher, store=store)
    before = controller.keys.current_key_id
    controller.rotate_key(actor="user")
    after = controller.keys.current_key_id
    assert before != after
