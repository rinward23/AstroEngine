"""Export subcommand for AstroEngine CLI."""


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "export", help="Export computed data to a file"
    )
    parser.add_argument("-o", "--out", required=True, help="Output file path")
    parser.set_defaults(cmd="export")


def run(args):
    print(f"[export] writing to {args.out}")
