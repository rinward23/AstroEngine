from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    OrbPolicy, SeverityProfile, Chart, Event, RuleSetVersion,
    AsteroidMeta, ExportJob, ChartKind, EventType, ExportType
)
from app.repo import (
    OrbPolicyRepo, SeverityProfileRepo, ChartRepo, EventRepo,
    RuleSetRepo, AsteroidRepo, ExportJobRepo
)

# In-memory DB for tests
engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base.metadata.create_all(engine)


def test_crud_cycle():
    with TestSession() as db:
        # OrbPolicy
        op = OrbPolicyRepo().create(db, name="classic", per_object={"Sun": 8.0})
        assert op.id is not None

        # SeverityProfile
        sp = SeverityProfileRepo().create(db, name="default", weights={"conjunction": 1.0})
        assert sp.id is not None

        # Chart
        ch = ChartRepo().create(db, kind=ChartKind.natal, dt_utc=datetime.now(timezone.utc), lat=0.0, lon=0.0)
        assert ch.id is not None

        # Event linked to chart
        ev = EventRepo().create(
            db,
            type=EventType.custom,
            start_ts=datetime.now(timezone.utc),
            chart=ch,
            objects={"A": "Mars", "B": "Venus"},
        )
        assert ev.id is not None and ev.chart_id == ch.id

        # Ruleset
        rs = RuleSetRepo().create(db, key="electional_default", version=1, definition_json={})
        assert rs.id is not None

        # Asteroid
        am = AsteroidRepo().create(db, name="Chiron", designation="2060")
        assert am.id is not None

        # Export job
        ex = ExportJobRepo().create(db, type=ExportType.ics, params={"foo": "bar"})
        assert ex.id is not None

        # Update
        ChartRepo().update(db, ch.id, location_name="Greenwich")
        assert ChartRepo().get(db, ch.id).location_name == "Greenwich"

        # Delete
        EventRepo().delete(db, ev.id)
        assert EventRepo().get(db, ev.id) is None
