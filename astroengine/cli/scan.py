"""Scan subcommand for AstroEngine CLI."""


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "scan", help="Scan a time window and list events"
    )
    parser.add_argument("--from", dest="start", required=True, help="Start ISO datetime")
    parser.add_argument("--to", dest="end", required=True, help="End ISO datetime")
    parser.set_defaults(cmd="scan")


def run(args):
    print(f"[scan] start={args.start} end={args.end}")
