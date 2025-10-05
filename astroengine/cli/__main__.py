import argparse

from . import diagnose, export, scan  # noqa: F401


def main() -> int:
    parser = argparse.ArgumentParser(prog="astroengine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan.add_subparser(sub)
    export.add_subparser(sub)
    diagnose.add_subparser(sub)

    args = parser.parse_args()

    handlers = {
        "scan": scan.run,
        "export": export.run,
        "diagnose": diagnose.run,
    }
    return int(handlers[args.cmd](args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
