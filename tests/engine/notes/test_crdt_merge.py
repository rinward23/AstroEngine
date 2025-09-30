from __future__ import annotations

from datetime import datetime, timedelta, timezone

from astroengine.engine.notes.crdt import CRDTDocument, merge_documents


def test_three_way_merge_is_deterministic():
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    device_a = CRDTDocument(device_id="A")
    device_b = CRDTDocument(device_id="B")
    device_c = CRDTDocument(device_id="C")

    device_a.apply_patch({"title": "Launch"}, timestamp=base_time)
    device_b.apply_patch({"body": "Great day"}, timestamp=base_time + timedelta(seconds=5))
    device_c.apply_patch({"tags": ["launch", "diary"]}, timestamp=base_time + timedelta(seconds=3))

    merged_one = merge_documents("server", [device_a, device_b, device_c])
    merged_two = merge_documents("server", [device_c, device_b, device_a])

    assert merged_one.to_note_dict() == merged_two.to_note_dict()
    assert merged_one.to_note_dict()["body"] == "Great day"
