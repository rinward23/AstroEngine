"""Command line interface for AstroEngine."""

from __future__ import annotations




def cmd_env(_: argparse.Namespace) -> int:
    providers = ", ".join(list_providers()) or "(none)"
    print("Registered providers:", providers)
    return 0



    events = scan_contacts(
        start_iso=args.start,
        end_iso=args.end,
        moving=args.moving,
        target=args.target,
        provider_name=args.provider,
        decl_parallel_orb=args.decl_orb,
        decl_contra_orb=args.decl_orb,
        antiscia_orb=args.mirror_orb,
        contra_antiscia_orb=args.mirror_orb,
        step_minutes=args.step,
        aspects_policy_path=args.aspects_policy,
    )

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                "start_timestamp": args.start,
                "end_timestamp": args.end,
                "moving": args.moving,
                "target": args.target,
                "provider": args.provider,
                "target_longitude": args.target_longitude,
            },
            "events": events_to_dicts(events),
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(events)} events to {args.json}")

    if args.sqlite:
        SQLiteExporter(args.sqlite).write(events)
        print(f"SQLite export complete: {args.sqlite}")

    if args.parquet:
        ParquetExporter(args.parquet).write(events)
        print(f"Parquet export complete: {args.parquet}")

    if not any((args.json, args.sqlite, args.parquet)):
        print(serialize_events_to_json(events))

    return 0




    try:
        validate_payload(args.schema, payload)
    except SchemaValidationError as exc:
        print("Validation failed:", file=sys.stderr)
        for message in exc.errors:
            print("  -", message, file=sys.stderr)
        return 1

    print(f"Payload validated against {args.schema}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    env_parser = sub.add_parser("env", help="List registered providers")
    env_parser.set_defaults(func=cmd_env)

    transits = sub.add_parser("transits", help="Scan for transit contacts")
    transits.add_argument("--start", required=True)
    transits.add_argument("--end", required=True)
    transits.add_argument("--moving", default="sun")
    transits.add_argument("--target", default="moon")
    transits.add_argument("--provider", default="swiss")
    transits.add_argument("--decl-orb", type=float, default=0.5)
    transits.add_argument("--mirror-orb", type=float, default=2.0)
    transits.add_argument("--step", type=int, default=60)
    transits.add_argument("--aspects-policy")
    transits.add_argument("--target-longitude", type=float)
    transits.add_argument("--json")
    transits.add_argument("--sqlite")
    transits.add_argument("--parquet")
    transits.set_defaults(func=cmd_transits)

    validate = sub.add_parser("validate", help="Validate a JSON payload against a schema")
    validate.add_argument("schema", choices=list(available_schema_keys("jsonschema")))
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    return namespace.func(namespace)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
