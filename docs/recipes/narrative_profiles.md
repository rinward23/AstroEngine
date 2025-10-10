# Narrative profiles, time-lords, and mundane timelines

AstroEngine's narrative layer now understands several profile contexts and
can blend in active time-lord stacks. The same offline templates power the
CLI and Python APIs, ensuring deterministic output that references real
event data.

## Offline / local narrative models

Remote GPT access remains optional. The
``astroengine.narrative.local_model.LocalNarrativeClient`` adapter loads
registered backends (for example a ``llama.cpp`` binding) and exposes the
same ``summarize(prompt, temperature=...)`` interface used by
``GPTNarrativeClient``. Register backends at import time and toggle them via
``ASTROENGINE_LOCAL_MODEL``:

```python
from astroengine.narrative.local_model import LocalNarrativeClient, register_backend


def llama_factory(options: dict[str, object]):
    from llama_cpp import Llama

    llm = Llama(model_path=options["model_path"])

    def adapter(prompt: str, *, temperature: float = 0.2, **_: object) -> str:
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response["choices"][0]["message"]["content"]

    return adapter


register_backend("llama.cpp", llama_factory, replace=True)

client = LocalNarrativeClient(backend="llama.cpp", options={"model_path": "./ggml-model.bin"})
print(client.summarize("List three key themes from today's transits."))
```

The CLI mirrors this via ``astroengine chatbot``. Use ``--local-backend`` (or
``--local`` to defer to ``ASTROENGINE_LOCAL_MODEL``) together with optional
``--local-option KEY=VALUE`` overrides. Without any local parameters the
command falls back to the configured remote GPT client.

```bash
# Remote GPT invocation (requires ASTROENGINE_OPENAI_KEY)
astroengine chatbot "Summarise the leading transit themes for today"

# Local inference with a registered backend
astroengine chatbot --local-backend llama.cpp --local-option model_path=./ggml-model.bin \
  "Summarise the leading transit themes for today"
```

Responses default to being journalled for later review (see below). Disable
that behaviour per-invocation via ``--no-journal`` when working with
ephemeral prompts.

## High-level narrative overlays

The ``astroengine.config`` module now exposes a dedicated narrative profile
registry. Built-ins such as ``data_minimal``, ``traditional_classical``,
``modern_psychological``, ``vedic_parashari``, ``jungian_archetypal`` and the
opt-in esoteric overlays adjust only the ``settings.narrative`` section while
preserving the rest of the configuration. Use the FastAPI endpoints under
``/v1/narrative-profiles`` to list, preview, and apply them, or persist new
overlays by POSTing a ``NarrativeCfg`` payload. Profiles are stored beneath
``~/.astroengine/profiles/narrative`` so they can be versioned or synced like
other project assets.

When running the Streamlit dashboard, open the **Narrative Profiles** page to
toggle which data sources, frameworks, and esoteric layers a persona may draw
from. Saving through the UI writes an identical YAML overlay that the API and
CLI can reuse.

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

## Journaling context in narratives

The ``astroengine.narrative.journaling`` module persists chatbot prompts and
responses under ``~/.astroengine/journal``. Each entry stores timestamps,
tags, backend metadata, and the raw exchange. Recent entries can be threaded
into prompts, offline templates, and ``summarize_top_events`` calls. A typical
workflow:

```python
from astroengine.narrative.journaling import (
    latest_entries,
    log_entry,
    journal_prompt_lines,
)
from astroengine.narrative import summarize_top_events

# Persist the most recent conversation
log_entry(prompt="What did Mars activate today?", response="Mars square Venus...", model="remote:gpt-4o")

# Reuse journal context when building a new summary
entries = latest_entries(3)
summary = summarize_top_events(
    events,
    profile="transits",
    journal_entries=entries,
    prefer_template=True,
)
print(summary)
```

The CLI equivalent supplies ``--include-journal N`` so the last *N* entries
are prepended to the prompt before the selected backend runs. Journal files
are portable JSON blobs and can be inspected manually or synced across
devices to maintain continuity between offline and online sessions.
