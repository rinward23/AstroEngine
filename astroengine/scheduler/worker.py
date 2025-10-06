
from __future__ import annotations

import json
import time
import traceback
from collections.abc import Callable
from threading import Event
from typing import Any

from app.devmode.backups import run_backup_job

from ..detectors.directed_aspects import solar_arc_natal_aspects
from ..detectors.progressed_aspects import progressed_natal_aspects
from .queue import claim_one, done, fail, heartbeat

HANDLERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "scan:progressions": lambda payload: progressed_natal_aspects(**payload),
    "scan:directions": lambda payload: solar_arc_natal_aspects(**payload),
    "backup:zip": run_backup_job,
}


def _summarize_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "__len__"):
        try:
            return {"count": len(result)}  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - very defensive
            pass
    return {"ok": True}


def run_worker(
    sleep_sec: float = 1.0,
    heartbeat_sec: float = 10.0,
    *,
    stop_event: Event | None = None,
    max_iterations: int | None = None,
) -> None:
    iterations = 0

    while True:
        if stop_event is not None and stop_event.is_set():
            break
        if max_iterations is not None and iterations >= max_iterations:
            break

        job = claim_one()
        iterations += 1

        if job is None:
            time.sleep(sleep_sec)
            continue

        jid = str(job["id"])
        jtype = str(job["type"])
        payload = json.loads(str(job["payload"]))
        claimed_at = time.time()

        try:
            handler = HANDLERS.get(jtype)
            if handler is None:
                raise RuntimeError(f"No handler for {jtype}")
            result = handler(payload)
            if heartbeat_sec > 0 and time.time() - claimed_at >= heartbeat_sec:
                heartbeat(jid)
            done(jid, {"summary": _summarize_result(result)})
        except Exception as exc:  # pragma: no cover - defensive
            fail(
                jid,
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            )


__all__ = ["HANDLERS", "run_worker"]

