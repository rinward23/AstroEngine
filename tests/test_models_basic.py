from datetime import datetime, timezone

from app.db.models import (
    AsteroidMeta,
    Chart,
    Event,
    ExportJob,
    OrbPolicy,
    RuleSetVersion,
    RulesetVersion,
    SeverityProfile,
)


def test_model_instantiation():
    op = OrbPolicy(profile_key="default", body="Sun", aspect="sextile", orb_degrees=4.0)
    sp = SeverityProfile(profile_key="default", weights={"sextile": 0.5})
    ch = Chart(chart_key="chart-1", profile_key="default", data={"kind": "natal"})
    assert ch.tags == []
    assert ch.deleted_at is None
    rs = RulesetVersion(
        ruleset_key="electional_default",
        version="1.0",
        checksum="abc123",
        definition={"rules": []},
    )
    ev = Event(
        event_key="event-1",
        chart=ch,
        ruleset_version=rs,
        event_time=datetime.now(timezone.utc),
        event_type="custom",
        payload={"objects": {"A": "Mars", "B": "Venus"}},
    )
    am = AsteroidMeta(
        asteroid_id="2060",
        designation="2060",
        common_name="Chiron",
        attributes={"alias": "Chiron"},
    )
    ex = ExportJob(job_key="job-1", job_type="ics")

    assert op.profile_key == "default"
    assert ch.events == [ev]
    assert ev.chart is ch
    assert isinstance(rs, RuleSetVersion)
    assert am.common_name == "Chiron"
    assert ex.job_type == "ics"
