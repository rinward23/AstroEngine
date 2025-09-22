# Narrative profiles, time-lords, and mundane timelines

AstroEngine's narrative layer now understands several profile contexts and
can blend in active time-lord stacks. The same offline templates power the
CLI and Python APIs, ensuring deterministic output that references real
event data.

## Sidereal / ayanāṁśa summaries

Use the ``sidereal`` profile to highlight ayanāṁśa-specific context when
calling :func:`astroengine.narrative.summarize_top_events`:

```python
from astroengine.narrative import summarize_top_events

summary = summarize_top_events(
    events,  # canonical transit records or dict-like payloads
    profile="sidereal",
    profile_context={"ayanamsha": "lahiri"},
    prefer_template=True,
)
print(summary)
```

The output begins with "Sidereal Emphasis" and lists the leading events
alongside corridor widths. Passing ``prefer_template=True`` skips GPT calls
and relies on the deterministic offline template.

## Time-lord overlays

Offline narratives can weave in an active time-lord stack. Build a
``TimelordStack`` (or pass the serialised payload embedded in transit
metadata) and supply it via the ``timelords`` keyword:

```python
from datetime import UTC, datetime
from astroengine.narrative import summarize_top_events
from astroengine.timelords.models import TimelordPeriod, TimelordStack

stack = TimelordStack(
    moment=datetime(2024, 3, 20, tzinfo=UTC),
    periods=(
        TimelordPeriod(
            system="profections",
            level="annual",
            ruler="Mars",
            start=datetime(2023, 3, 21, tzinfo=UTC),
            end=datetime(2024, 3, 20, tzinfo=UTC),
        ),
    ),
)

print(
    summarize_top_events(
        events,
        profile="timelords",
        timelords=stack,
        prefer_template=True,
    )
)
```

The generated paragraph lists each ruler and emphasises the primary period
(``profections annual — Mars`` in the example).

## Mundane outer-cycle timelines

Outer-planet windows can now be generated for charts and dashboards via the
``timeline`` CLI:

```bash
astroengine timeline outer-cycles \
  --start 2020-01-01T00:00:00Z \
  --end 2021-01-01T00:00:00Z \
  --bodies jupiter,saturn \
  --json
```

The JSON payload contains :class:`astroengine.timeline.TransitWindow`
descriptions with metadata (aspect labels, speed differentials, etc.) ready
for Gantt-style visualisations.

## Electional narratives from the CLI

``astroengine query`` can render offline narratives directly from exported
SQLite datasets. Choose a profile tailored to the task:

```bash
astroengine query --sqlite events.db --limit 5 \
  --narrative --narrative-profile electional \
  --context intent=launch --context locale=NYC
```

The command prints the top events and a second block describing the
electional window, incorporating any time-lord metadata stored in the
``meta_json`` column.
