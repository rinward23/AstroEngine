from datetime import datetime, timezone

from app.db.models import (
    OrbPolicy,
    SeverityProfile,
    Chart,
    Event,
    RuleSetVersion,
    AsteroidMeta,
    ExportJob,
    ChartKind,
    EventType,
    ExportType,
)


def test_model_instantiation():
    op = OrbPolicy(name="classic")
    sp = SeverityProfile(name="default")
    ch = Chart(kind=ChartKind.natal, dt_utc=datetime.now(timezone.utc), lat=0.0, lon=0.0)
    rs = RuleSetVersion(key="electional_default")
    ev = Event(type=EventType.custom, start_ts=datetime.now(timezone.utc), chart=ch)
    am = AsteroidMeta(name="Chiron", designation="2060")
    ex = ExportJob(type=ExportType.ics)

    assert op.name == "classic"
    assert ch.kind == ChartKind.natal
    assert ev.chart is ch
