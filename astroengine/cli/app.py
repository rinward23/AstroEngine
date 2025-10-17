"""Primary Typer application for the AstroEngine CLI."""

from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path
import json
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

import typer

from astroengine.app_api import run_sign_ingress_detector
from astroengine.boot import configure_logging
from astroengine.ephe import DEFAULT_INSTALL_ROOT, available_sets
from astroengine.chinese import compute_four_pillars, compute_zi_wei_chart

from . import diagnose
from ._compat import cli_legacy_missing_reason, try_import_cli_legacy
from .channels.transit.common import canonical_events_to_dicts


app = typer.Typer(help="AstroEngine command line interface.")
chinese_app = typer.Typer(help="Chinese astrology chart calculators.")
transits_app = typer.Typer(help="Transit scanning utilities.")
transit_app = typer.Typer(help="Transit event utilities.")
ruleset_app = typer.Typer(help="Ruleset authoring utilities.")
_EPHEMERIS_SET_LABEL = ", ".join(available_sets())


def _parse_local_options(values: List[str]) -> Dict[str, str]:
    options: Dict[str, str] = {}
    for value in values:
        key, sep, raw = value.partition("=")
        if not sep:
            raise typer.BadParameter(f"Invalid option '{value}'. Expected KEY=VALUE.")
        options[key.strip()] = raw.strip()
    return options


def _ingress_table(events: Sequence[Mapping[str, object] | object]) -> str:
    headers = ["Timestamp", "Body", "From", "To", "Motion", "Longitude"]
    rows: list[list[str]] = []

    for event in events:
        mapping: Mapping[str, object] | None = None
        if isinstance(event, Mapping):
            mapping = event
        elif hasattr(event, "model_dump"):
            try:
                dumped = event.model_dump()
                if isinstance(dumped, Mapping):
                    mapping = dumped  # type: ignore[assignment]
            except Exception:  # pragma: no cover - defensive
                mapping = None

        def _lookup(attr: str) -> object | None:
            if mapping is not None:
                value = mapping.get(attr)
                if value is not None:
                    return value
            return getattr(event, attr, None)

        ts = _lookup("ts") or _lookup("timestamp") or ""
        body = _lookup("body") or ""
        sign_from = _lookup("from_sign") or _lookup("sign_from") or ""
        sign_to = _lookup("to_sign") or _lookup("sign_to") or ""
        motion = _lookup("motion") or ""
        lon_value = _lookup("longitude")
        try:
            longitude = float(lon_value) % 360.0 if lon_value is not None else 0.0
        except (TypeError, ValueError):  # pragma: no cover - defensive
            longitude = 0.0

        rows.append(
            [
                str(ts),
                str(body),
                str(sign_from),
                str(sign_to),
                str(motion),
                f"{longitude:07.3f}",
            ]
        )

    if not rows:
        return ""

    widths = [len(column) for column in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    header_line = " | ".join(
        header.ljust(widths[idx]) for idx, header in enumerate(headers)
    )
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body_lines = [
        " | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, divider, *body_lines])


@transit_app.command("ingresses")
def transit_ingresses(
    start: str = typer.Option(
        ..., "--start", "--start-utc", help="Start time (ISO-8601, UTC)."
    ),
    end: str = typer.Option(
        ..., "--end", "--end-utc", help="End time (ISO-8601, UTC)."
    ),
    bodies: Optional[List[str]] = typer.Option(
        None,
        "--body",
        "--bodies",
        help="Moving bodies to evaluate (repeatable).",
    ),
    include_moon: Optional[bool] = typer.Option(
        None,
        "--include-moon/--no-include-moon",
        help="Override the profile toggle controlling Moon ingresses.",
    ),
    inner_mode: Optional[str] = typer.Option(
        None,
        "--inner-mode",
        case_sensitive=False,
        help="Ingress policy for Mercury/Venus (always or angles_only).",
    ),
    profile_id: Optional[str] = typer.Option(
        None,
        "--profile",
        help="Profile identifier providing ingress feature toggles.",
    ),
    step_hours: float = typer.Option(
        6.0,
        "--step-hours",
        min=0.25,
        help="Sampling cadence in hours when scanning the ephemeris.",
    ),
    json_output: Optional[Path] = typer.Option(
        None,
        "--json",
        help="Write ingress events to this JSON file.",
    ),
    table: bool = typer.Option(
        True,
        "--table/--no-table",
        help="Display a table summary in the terminal.",
    ),
) -> None:
    """Detect sign ingress events within the supplied UTC window."""

    body_selection: Optional[list[str]] = None
    if bodies:
        tokens: list[str] = []
        for entry in bodies:
            for token in str(entry).replace(",", " ").split():
                cleaned = token.strip()
                if cleaned:
                    tokens.append(cleaned)
        if tokens:
            body_selection = list(dict.fromkeys(tokens))

    inner_mode_value: Optional[str] = None
    if inner_mode is not None:
        normalized = inner_mode.strip().replace("-", "_").lower()
        inner_mode_value = normalized

    try:
        events = run_sign_ingress_detector(
            start,
            end,
            bodies=body_selection,
            include_moon=include_moon,
            inner_mode=inner_mode_value,
            profile_id=profile_id,
            step_hours=step_hours,
        )
    except (RuntimeError, ValueError) as exc:
        typer.secho(f"Ingress detection failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    canonical = canonical_events_to_dicts(events)

    if json_output is not None:
        try:
            json_output.write_text(
                json.dumps(canonical, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            typer.secho(
                f"Wrote {len(canonical)} ingresses to {json_output}",
                fg=typer.colors.GREEN,
                err=False,
            )
        except OSError as exc:  # pragma: no cover - filesystem errors reported at runtime
            typer.secho(
                f"Unable to write JSON output: {exc}", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(1) from exc

    if table:
        summary = _ingress_table(canonical if canonical else events)
        if summary:
            typer.echo(summary)
        else:
            typer.echo("No ingresses detected.")
    elif not canonical:
        typer.echo("No ingresses detected.")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Configure logging before executing subcommands."""

    configure_logging()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Emit diagnostics as JSON."),
    strict: bool = typer.Option(
        False, "--strict", help="Treat warnings as failures when computing the exit status."
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Include environment metadata."),
    smoketest: Optional[str] = typer.Option(
        None,
        "--smoketest",
        metavar="ISO_UTC",
        help="Run a Swiss Ephemeris smoketest for the provided timestamp (or 'now').",
    ),
) -> None:
    """Run the diagnostics suite to validate the local environment."""

    exit_code = diagnose.run(
        SimpleNamespace(
            json=json_output,
            strict=strict,
            verbose=verbose,
            smoketest=smoketest,
        )
    )
    raise typer.Exit(exit_code)


@ruleset_app.command("lint")
def ruleset_lint(
    target: Path = typer.Argument(
        Path("rulesets"),
        metavar="PATH",
        help="Ruleset Markdown file or directory to lint.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit lint findings as JSON."),
) -> None:
    """Validate Markdown rulesets against DSL invariants."""

    from astroengine.core.ruleset_dsl import lint_ruleset_path

    try:
        issues = lint_ruleset_path(target)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if json_output:
        payload = [
            {"path": str(issue.path), "code": issue.code, "message": issue.message}
            for issue in issues
        ]
        typer.echo(json.dumps(payload, indent=2))
    else:
        if issues:
            for issue in issues:
                typer.secho(
                    f"{issue.path}: {issue.code}: {issue.message}",
                    fg=typer.colors.RED,
                    err=True,
                )
        else:
            typer.secho("All rulesets passed lint checks.", fg=typer.colors.GREEN)

    if issues:
        raise typer.Exit(1)


@app.command("serve-api")
def serve_api(
    host: str = typer.Option("127.0.0.1", "--host", help="Interface to bind."),
    port: int = typer.Option(8000, "--port", help="Port to listen on."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (development only)."),
    workers: Optional[int] = typer.Option(
        None, "--workers", help="Number of worker processes to spawn (defaults to CPU count)."
    ),
    log_level: str = typer.Option("info", "--log-level", help="Log level for uvicorn."),
    timeout_keep_alive: int = typer.Option(
        10, "--timeout-keep-alive", help="Seconds to keep idle HTTP connections alive."
    ),
    app_import: str = typer.Option(
        "astroengine.api_server:app",
        "--app-import",
        help="Import string for the ASGI application.",
    ),
) -> None:
    """Run the FastAPI service using uvicorn."""

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional dependency
        typer.secho(
            "uvicorn is not installed. Install astroengine[api] or add uvicorn to your environment.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc

    kwargs: dict[str, object] = {
        "host": host,
        "port": port,
        "log_level": log_level,
        "timeout_keep_alive": timeout_keep_alive,
    }
    if reload:
        kwargs["reload"] = True
    if workers is not None:
        kwargs["workers"] = workers

    try:
        uvicorn.run(app_import, **kwargs)
    except Exception as exc:  # pragma: no cover - runtime server failure
        typer.secho(f"uvicorn exited with an error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.command("serve-ui")
def serve_ui(
    app_path: Optional[str] = typer.Option(
        None,
        "--app",
        help="Override the Streamlit application path (defaults to bundled Aspect Search UI).",
    ),
    streamlit_args: Optional[List[str]] = typer.Argument(
        None,
        metavar="STREAMLIT_ARGS...",
        help="Additional arguments forwarded to Streamlit.",
    ),
) -> None:
    """Launch the bundled Streamlit dashboards."""

    try:
        from astroengine.ux.streamlit import cli as streamlit_cli
    except ImportError as exc:  # pragma: no cover - optional dependency guard
        typer.secho(
            "Streamlit is not installed. Install astroengine[streamlit] or add streamlit to your environment.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc

    args: list[str] = []
    if app_path:
        args.append(app_path)
    if streamlit_args:
        args.extend(streamlit_args)

    exit_code = streamlit_cli.main(args)
    raise typer.Exit(exit_code)


@app.command("chatbot")
def chatbot(
    prompt: Optional[str] = typer.Argument(
        None,
        metavar="PROMPT",
        help="Prompt to send to the narrative assistant (defaults to interactive input).",
    ),
    local_backend: Optional[str] = typer.Option(
        None,
        "--local-backend",
        help="Use the specified local backend registered via astroengine.narrative.local_model.",
    ),
    use_local_env: bool = typer.Option(
        False,
        "--local",
        help="Use the ASTROENGINE_LOCAL_MODEL configuration for local inference.",
    ),
    remote_model: Optional[str] = typer.Option(
        None,
        "--remote-model",
        help="Override the remote GPT model identifier.",
    ),
    temperature: float = typer.Option(
        0.2,
        "--temperature",
        help="Sampling temperature for the selected backend.",
    ),
    include_journal: int = typer.Option(
        0,
        "--include-journal",
        min=0,
        help="Prepend this many recent journal entries to the prompt context.",
    ),
    journal_entry: bool = typer.Option(
        True,
        "--journal/--no-journal",
        help="Persist the prompt and response to the AstroEngine journal.",
    ),
    journal_tag: List[str] = typer.Option(
        [],
        "--tag",
        help="Tag(s) to attach to the saved journal entry.",
    ),
    local_option: List[str] = typer.Option(
        [],
        "--local-option",
        metavar="KEY=VALUE",
        help="Override local backend options (repeatable).",
    ),
) -> None:
    """Send prompts to remote or local narrative engines and log the exchange."""

    prompt_text = prompt or typer.prompt("Prompt")
    metadata: Dict[str, object] = {
        "temperature": temperature,
        "tags": list(journal_tag),
    }

    ux_plugins.setup_cli(None)
    context_entries = []
    context_lines: List[str] = []
    if include_journal > 0:
        context_entries = latest_entries(include_journal)
        if context_entries:
            context_lines = journal_prompt_lines(context_entries)
            metadata["journal_context"] = [entry.entry_id for entry in context_entries]

    combined_prompt = prompt_text
    if context_lines:
        combined_prompt = "\n".join(context_lines + ["", combined_prompt])

    combined_prompt, metadata = ux_plugins.prepare_chat_prompt(combined_prompt, metadata)

    backend_label = "remote"
    response: str
    local_options = _parse_local_options(local_option)
    if local_backend or use_local_env:
        if not local_backend:
            env_client = LocalNarrativeClient.from_env(allow_stub=False)
            backend_name = env_client.backend
            if not backend_name:
                raise typer.BadParameter(
                    "ASTROENGINE_LOCAL_MODEL is not configured for --local mode."
                )
            base_options = dict(env_client.options or {})
            base_options.update(local_options)
            local_client = LocalNarrativeClient(
                backend=backend_name,
                options=base_options,
                allow_stub=False,
            )
        else:
            local_client = LocalNarrativeClient(
                backend=local_backend,
                options=local_options,
                allow_stub=False,
            )
            backend_name = local_backend
        try:
            response = local_client.summarize(combined_prompt, temperature=temperature)
        except Exception as exc:  # pragma: no cover - backend failure
            typer.secho(f"Local backend error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from exc
        backend_label = f"local:{backend_name}"
    else:
        client = GPTNarrativeClient.from_env(model=remote_model or "gpt-3.5-turbo")
        if not client.available:
            typer.secho(
                "Remote GPT backend is unavailable. Provide an API key or use --local.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)
        try:
            response = client.summarize(combined_prompt, temperature=temperature)
        except Exception as exc:  # pragma: no cover - network failure
            typer.secho(f"Remote backend error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1) from exc
        backend_label = f"remote:{client.model}"

    typer.echo(response)

    metadata["backend"] = backend_label
    metadata["prompt"] = prompt_text
    metadata["combined_prompt"] = combined_prompt
    ux_plugins.handle_chat_response(combined_prompt, response, metadata)

    if journal_entry:
        entry = log_entry(
            prompt=prompt_text,
            response=response,
            model=backend_label,
            tags=journal_tag,
            metadata=metadata,
        )
        typer.secho(
            f"Journal entry saved: {entry.entry_id}",
            fg=typer.colors.GREEN,
            err=True,
        )

ephe_app = typer.Typer(help="Swiss Ephemeris utilities.")


@ephe_app.command("install")
def ephe_install(
    url: str = typer.Argument(..., metavar="URL", help="Swiss Ephemeris archive URL to download."),
    agree_license: bool = typer.Option(
        False,
        "--agree-license",
        help="Confirm acceptance of the Swiss Ephemeris license terms.",
    ),
    target: Path = typer.Option(
        DEFAULT_INSTALL_ROOT,
        "--target",
        help="Directory where the archive (and extracted files) will be stored.",
    ),
    filename: Optional[str] = typer.Option(
        None, "--filename", help="Override the destination filename for the download."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
    skip_extract: bool = typer.Option(
        False, "--skip-extract", help="Skip automatic extraction after download."
    ),
    timeout: int = typer.Option(60, "--timeout", help="HTTP timeout in seconds."),
) -> None:
    """Download and optionally extract Swiss Ephemeris data packages."""

    from astroengine.ephe import install as ephe_install_mod

    if not agree_license:
        typer.secho(
            "Swiss Ephemeris downloads require --agree-license acknowledgement.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    try:
        archive_path = ephe_install_mod.install_archive(
            url,
            agree_license=agree_license,
            target=target,
            filename=filename,
            force=force,
            skip_extract=skip_extract,
            timeout=timeout,
        )
    except ephe_install_mod.DownloadError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except OSError as exc:  # pragma: no cover - filesystem errors share message path
        typer.secho(f"Filesystem error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo("Swiss Ephemeris package installed.")
    typer.echo(f"Files located under: {archive_path.parent}")


@ephe_app.command("pull")
def ephe_pull(
    set_name: str = typer.Option(
        "de440s",
        "--set",
        "-s",
        help=f"Ephemeris set to download (available: {_EPHEMERIS_SET_LABEL}).",
    ),
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        help="Destination directory for the ephemeris files (defaults to the cache location for the selected set).",
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        help="Override the base URL or local directory containing the ephemeris files.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files if present."),
    timeout: int = typer.Option(60, "--timeout", help="HTTP timeout in seconds."),
    skip_verify: bool = typer.Option(
        False,
        "--skip-verify",
        help="Skip checksum validation for downloaded files.",
    ),
) -> None:
    """Fetch curated ephemeris datasets into the local cache."""

    from astroengine.ephe import pull as ephe_pull_mod

    try:
        result = ephe_pull_mod.pull_set(
            set_name,
            target=target,
            source=source,
            force=force,
            timeout=timeout,
            verify=not skip_verify,
        )
    except ephe_pull_mod.PullError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if result.downloaded:
        typer.echo(
            f"Downloaded {len(result.downloaded)} file(s) to {result.target_dir}."
        )
    else:
        typer.echo("Ephemeris files already present; nothing downloaded.")
    typer.echo(f"Manifest written to: {result.manifest_path}")


@transits_app.command("scan")
def transits_scan(
    start_utc: str = typer.Option(
        ..., "--start-utc", "--start", help="Start time (ISO-8601, UTC)."
    ),
    end_utc: str = typer.Option(..., "--end-utc", "--end", help="End time (ISO-8601, UTC)."),
    moving: Optional[List[str]] = typer.Option(
        None,
        "--moving",
        "--bodies",
        help="Transiting bodies to scan (repeatable).",
    ),
    targets: Optional[List[str]] = typer.Option(
        None,
        "--target",
        "--targets",
        help="Target bodies or qualified identifiers (repeatable).",
    ),
    target_frames: Optional[List[str]] = typer.Option(
        None,
        "--target-frame",
        "--frame",
        help="Frame(s) to prefix targets (repeatable).",
    ),
    detectors: Optional[List[str]] = typer.Option(
        None,
        "--detector",
        "--detectors",
        help="Enable optional detectors (repeatable; use 'all' for every toggle).",
    ),
    entrypoints: Optional[List[str]] = typer.Option(
        None,
        "--entrypoint",
        help="Explicit scan entrypoint module:function (repeatable).",
    ),
    provider: str = typer.Option(
        "auto", "--provider", help="Ephemeris provider (auto, swiss, pymeeus, skyfield)."
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Profile identifier to annotate export metadata."
    ),
    step_minutes: int = typer.Option(
        60, "--step-minutes", min=1, help="Sampling cadence in minutes."
    ),
    accuracy_budget: Optional[str] = typer.Option(
        None,
        "--accuracy-budget",
        help="Preset cadence (fast=120m, default=60m, high=15m).",
    ),
    json_path: Optional[Path] = typer.Option(
        None, "--json", help="Write scan payload to this JSON file."
    ),
    export_json: Optional[Path] = typer.Option(
        None, "--export-json", help="Write canonical events to a JSON file."
    ),
    export_sqlite: Optional[Path] = typer.Option(
        None, "--export-sqlite", help="Write canonical events to a SQLite file."
    ),
    export_parquet: Optional[Path] = typer.Option(
        None, "--export-parquet", help="Write canonical events to a Parquet dataset."
    ),
    export_ics: Optional[Path] = typer.Option(
        None, "--export-ics", help="Write canonical events to an ICS calendar file."
    ),
    ics_title: str = typer.Option(
        "AstroEngine Events", "--ics-title", help="Calendar title when exporting ICS."
    ),
    cache: bool = typer.Option(
        False, "--cache", help="Enable Swiss longitude caching when available."
    ),
    sidereal: Optional[bool] = typer.Option(
        None,
        "--sidereal/--tropical",
        help="Use sidereal zodiac settings for this scan (default inherits profile).",
    ),
    ayanamsha: Optional[str] = typer.Option(
        None, "--ayanamsha", help="Sidereal ayanāṁśa to apply when sidereal mode is enabled."
    ),
    sqlite_path: Optional[Path] = typer.Option(
        None, "--sqlite", help="Path to SQLite DB; writes into table transits_events."
    ),
    parquet_path: Optional[Path] = typer.Option(
        None, "--parquet", help="Path to Parquet file or dataset directory."
    ),
    parquet_compression: str = typer.Option(
        "snappy",
        "--parquet-compression",
        help="Compression codec for Parquet exports (snappy, gzip, brotli, ...).",
    ),
) -> None:
    """Run the canonical AstroEngine transit scanner."""

    from .channels.transit import scan as transit_scan

    args = Namespace(
        start_utc=start_utc,
        end_utc=end_utc,
        moving=list(moving) if moving else None,
        targets=list(targets) if targets else None,
        target_frames=list(target_frames) if target_frames else None,
        detectors=list(detectors) if detectors else None,
        entrypoint=list(entrypoints) if entrypoints else None,
        provider=provider,
        profile=profile,
        step_minutes=step_minutes,
        accuracy_budget=accuracy_budget,
        json=str(json_path) if json_path else None,
        export_json=str(export_json) if export_json else None,
        export_sqlite=str(export_sqlite) if export_sqlite else None,
        export_parquet=str(export_parquet) if export_parquet else None,
        export_ics=str(export_ics) if export_ics else None,
        ics_title=ics_title,
        cache=cache,
        sidereal=sidereal,
        ayanamsha=ayanamsha,
        sqlite=str(sqlite_path) if sqlite_path else None,
        parquet=str(parquet_path) if parquet_path else None,
        parquet_compression=parquet_compression,
    )
    exit_code = transit_scan.run(args)
    raise typer.Exit(exit_code)


app.add_typer(transits_app, name="transits")
app.add_typer(ephe_app, name="ephe")
app.add_typer(chinese_app, name="chinese")
app.add_typer(transit_app, name="transit")


def _resolve_datetime(moment: str, tz_name: Optional[str]) -> datetime:
    try:
        dt = datetime.fromisoformat(moment)
    except ValueError as exc:  # pragma: no cover - input validation
        raise typer.BadParameter("Use ISO-8601 formatted datetimes (YYYY-MM-DDTHH:MM)") from exc

    if tz_name:
        zone = ZoneInfo(tz_name)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=zone)
        else:
            dt = dt.astimezone(zone)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def _format_star_list(stars) -> str:
    names = ", ".join(star.name for star in stars)
    return names or "-"


@chinese_app.command("four-pillars")
def cli_four_pillars(
    moment: str = typer.Argument(..., metavar="ISO_LOCAL", help="Local datetime in ISO format."),
    tz_name: Optional[str] = typer.Option(
        None,
        "--tz",
        help="IANA timezone (defaults to Asia/Shanghai when the datetime is naive).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit Four Pillars data as JSON."),
) -> None:
    """Compute the Four Pillars for the supplied moment."""

    if tz_name is None and "+" not in moment and moment[-1:].upper() != "Z":
        tz_name = "Asia/Shanghai"

    dt = _resolve_datetime(moment, tz_name)
    chart = compute_four_pillars(dt)
    payload = {
        name: {
            "stem": pillar.stem.name,
            "branch": pillar.branch.name,
            "label": pillar.label(),
        }
        for name, pillar in chart.pillars.items()
    }
    payload["provenance"] = dict(chart.provenance)

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for pillar_name in ("year", "month", "day", "hour"):
        pillar = chart.pillars[pillar_name]
        typer.echo(
            f"{pillar_name.title():<5}: {pillar.stem.name}-{pillar.branch.name}"
        )


@chinese_app.command("zi-wei")
def cli_zi_wei(
    moment: str = typer.Argument(..., metavar="ISO_LOCAL", help="Local datetime in ISO format."),
    tz_name: Optional[str] = typer.Option(
        None,
        "--tz",
        help="IANA timezone (defaults to Asia/Shanghai when the datetime is naive).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit Zi Wei palace data as JSON."),
) -> None:
    """Compute a Zi Wei Dou Shu palace map for the supplied moment."""

    if tz_name is None and "+" not in moment and moment[-1:].upper() != "Z":
        tz_name = "Asia/Shanghai"

    dt = _resolve_datetime(moment, tz_name)
    chart = compute_zi_wei_chart(dt)

    payload = {
        "life_palace": chart.life_palace_index,
        "body_palace": chart.body_palace_index,
        "palaces": [
            {
                "name": palace.name,
                "branch": palace.branch.name,
                "stars": [star.name for star in palace.stars],
            }
            for palace in chart.palaces
        ],
        "provenance": dict(chart.provenance),
    }

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    life = chart.palaces[chart.life_palace_index]
    body = chart.palaces[chart.body_palace_index]
    typer.echo(
        f"Life Palace: {life.name} ({life.branch.name}) | Stars: "
        f"{_format_star_list(life.stars)}"
    )
    typer.echo(
        f"Body Palace: {body.name} ({body.branch.name}) | Stars: "
        f"{_format_star_list(body.stars)}"
    )
    typer.echo("")
    for palace in chart.palaces:
        typer.echo(
            f"{palace.name:<10} ({palace.branch.name}): "
            f"{_format_star_list(palace.stars)}"
        )


database_app = typer.Typer(help="Database migration utilities.")


def _alembic_ini_path() -> Path:
    return Path(__file__).resolve().parents[2] / "alembic.ini"


def _require_alembic():
    try:
        from alembic import command  # type: ignore
        from alembic.util import CommandError  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency guard
        typer.secho(
            "Alembic is not installed. Install astroengine[tools] or add alembic to your environment.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc
    return command, CommandError


def _configure_alembic(database_url: Optional[str]) -> "Config":
    from alembic.config import Config

    config = Config(str(_alembic_ini_path()))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
        os.environ["DATABASE_URL"] = database_url
    return config


@database_app.command("upgrade")
def database_upgrade(
    revision: str = typer.Argument("head", metavar="REVISION", help="Revision identifier to upgrade to."),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="SQLAlchemy database URL (defaults to DATABASE_URL environment variable).",
    ),
) -> None:
    """Apply migrations up to the specified revision."""

    command, CommandError = _require_alembic()
    config = _configure_alembic(database_url)
    try:
        command.upgrade(config, revision)
    except CommandError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@database_app.command("downgrade")
def database_downgrade(
    revision: str = typer.Argument("-1", metavar="REVISION", help="Revision identifier to downgrade to."),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="SQLAlchemy database URL (defaults to DATABASE_URL environment variable).",
    ),
) -> None:
    """Revert migrations down to the specified revision."""

    command, CommandError = _require_alembic()
    config = _configure_alembic(database_url)
    try:
        command.downgrade(config, revision)
    except CommandError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@database_app.command("current")
def database_current(
    verbose: bool = typer.Option(False, "--verbose", help="Show full revision identifiers."),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="SQLAlchemy database URL (defaults to DATABASE_URL environment variable).",
    ),
) -> None:
    """Display the current migration revision."""

    command, CommandError = _require_alembic()
    config = _configure_alembic(database_url)
    try:
        command.current(config, verbose=verbose)
    except CommandError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@database_app.command("history")
def database_history(
    verbose: bool = typer.Option(False, "--verbose", help="Show full revision details."),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="SQLAlchemy database URL (defaults to DATABASE_URL environment variable).",
    ),
) -> None:
    """Display the migration history."""

    command, CommandError = _require_alembic()
    config = _configure_alembic(database_url)
    try:
        command.history(config, verbose=verbose)
    except CommandError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@database_app.command("stamp")
def database_stamp(
    revision: str = typer.Argument("head", metavar="REVISION", help="Revision identifier to stamp."),
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        envvar="DATABASE_URL",
        help="SQLAlchemy database URL (defaults to DATABASE_URL environment variable).",
    ),
) -> None:
    """Set the database revision without running migrations."""

    command, CommandError = _require_alembic()
    config = _configure_alembic(database_url)
    try:
        command.stamp(config, revision)
    except CommandError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


app.add_typer(database_app, name="database")


@app.command("legacy")
def legacy(args: Optional[List[str]] = typer.Argument(None, metavar="ARGS...")) -> None:
    """Invoke the historical monolithic CLI for backward compatibility."""

    module = try_import_cli_legacy()
    if module is None:
        reason = cli_legacy_missing_reason() or "Legacy CLI unavailable"
        typer.secho(reason, fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    legacy_args = list(args or [])
    if legacy_args and legacy_args[0] == "--":
        legacy_args = legacy_args[1:]

    from astroengine import cli_legacy

    exit_code = cli_legacy.main(legacy_args if legacy_args else None)
    raise typer.Exit(exit_code)


__all__ = [
    "app",
]
