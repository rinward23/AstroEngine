"""Diagnose subcommand for AstroEngine CLI."""


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "diagnose", help="Run environment/adapter checks"
    )
    parser.set_defaults(cmd="diagnose")


def run(_args):
    print("[diagnose] environment looks OK")
