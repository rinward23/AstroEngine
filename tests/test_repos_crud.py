from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    AsteroidMeta,
    Chart,
    Event,
    ExportJob,
    OrbPolicy,
    RuleSetVersion,
    SeverityProfile,
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
        op = OrbPolicyRepo().create(
            db,
            profile_key="default",
            body="Sun",
            aspect="sextile",
            orb_degrees=4.0,
        )
        assert op.id is not None

        # SeverityProfile
        sp = SeverityProfileRepo().create(
            db,
            profile_key="default",
            weights={"sextile": 0.5},
        )
        assert sp.id is not None

        # Chart
        ch = ChartRepo().create(
            db,
            chart_key="chart-1",
            profile_key="default",
            data={"kind": "natal"},
        )
        assert ch.id is not None

        # Ruleset
        rs = RuleSetRepo().create(
            db,
            ruleset_key="electional_default",
            version="1.0",
            checksum="abc123",
            definition={"rules": []},
        )
        assert rs.id is not None
        assert isinstance(rs, RuleSetVersion)

        # Event linked to chart and ruleset
        ev = EventRepo().create(
            db,
            event_key="event-1",
            chart_id=ch.id,
            ruleset_version_id=rs.id,
            event_time=datetime.now(timezone.utc),
            event_type="custom",
            payload={"objects": {"A": "Mars", "B": "Venus"}},
        )
        assert ev.id is not None and ev.chart_id == ch.id

        # Asteroid
        am = AsteroidRepo().create(
            db,
            asteroid_id="2060",
            designation="2060",
            common_name="Chiron",
            attributes={"alias": "Chiron"},
        )
        assert am.id is not None

        # Export job
        ex = ExportJobRepo().create(
            db,
            job_key="job-1",
            job_type="ics",
            payload={"foo": "bar"},
        )
        assert ex.id is not None

        # Update
        ChartRepo().update(db, ch.id, source="Greenwich")
        assert ChartRepo().get(db, ch.id).source == "Greenwich"

        # Tag editor
        repo = ChartRepo()
        repo.update_tags(db, ch.id, ["Natal", "Client", "natal"])
        assert repo.get(db, ch.id).tags == ["natal", "client"]

        # Soft delete and restore
        repo.soft_delete(db, ch.id)
        assert repo.get(db, ch.id) is None
        assert repo.list_deleted(db)
        repo.restore(db, ch.id)
        assert repo.get(db, ch.id) is not None

        # Delete
        EventRepo().delete(db, ev.id)
        assert EventRepo().get(db, ev.id) is None
