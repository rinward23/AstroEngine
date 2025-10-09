"""CLI helpers for downloading licensed Swiss Ephemeris data packages."""

from __future__ import annotations

import argparse
import shutil
import sys
from contextlib import closing
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests

from . import DEFAULT_INSTALL_ROOT

CHUNK_SIZE = 64 * 1024
TIMEOUT = 60


class DownloadError(RuntimeError):
    """Raised when a download attempt fails."""


def _default_filename(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if name:
        return name
    raise DownloadError("Unable to determine filename from URL; pass --filename explicitly.")


def _download(url: str, destination: Path, *, chunk_size: int = CHUNK_SIZE, timeout: int = TIMEOUT) -> None:
    try:
        response = requests.get(url, stream=True, timeout=timeout)
    except requests.RequestException as exc:  # pragma: no cover - network errors share path with HTTP errors
        raise DownloadError(f"Failed to start download: {exc}") from exc

    with closing(response) as resp:
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - HTTP errors share message path
            raise DownloadError(f"Download failed with status {resp.status_code}.") from exc

        total = int(resp.headers.get("content-length") or 0)
        downloaded = 0
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = destination.with_suffix(destination.suffix + ".part")
        with tmp_path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                fh.write(chunk)
                downloaded += len(chunk)
                _render_progress(downloaded, total)
        tmp_path.replace(destination)
    if total:
        print(f"\nDownloaded {total / (1024 * 1024):.1f} MiB to {destination}")
    else:
        print(f"\nDownloaded file to {destination}")


def _render_progress(downloaded: int, total: int) -> None:
    if not total:
        print(f"\rDownloaded {downloaded / (1024 * 1024):.1f} MiB", end="", file=sys.stderr)
        return
    percent = (downloaded / total) * 100 if total else 0
    msg = f"\rDownloading… {downloaded / (1024 * 1024):.1f} / {total / (1024 * 1024):.1f} MiB ({percent:3.0f}%)"
    print(msg, end="", file=sys.stderr)


def _extract_if_needed(archive_path: Path, target_dir: Path, *, force: bool) -> None:
    suffixes = "".join(archive_path.suffixes)
    if suffixes.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2")):
        print(f"Extracting {archive_path.name} to {target_dir}")
        if force and target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.unpack_archive(str(archive_path), str(target_dir))
        except (shutil.ReadError, ValueError) as exc:
            raise DownloadError(f"Failed to extract archive: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    description = (
        "Download Swiss Ephemeris data into a local cache. You must already have permission "
        "to access the files and explicitly agree to the Swiss Ephemeris license terms."
    )
    epilog = (
        "The Swiss Ephemeris data is proprietary. This helper never bypasses Astrodienst's licensing. "
        "Provide the official download URL or a local mirror that you are allowed to access, and "
        "confirm acceptance of the license with --agree-license before continuing."
    )
    parser = argparse.ArgumentParser(
        prog="astroengine-ephe",
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--install",
        metavar="URL",
        help="Download the Swiss Ephemeris archive from URL into the target directory.",
    )
    parser.add_argument(
        "--agree-license",
        action="store_true",
        help="Confirm that you have read and accepted the Swiss Ephemeris license.",
    )
    parser.add_argument(
        "--target",
        default=str(DEFAULT_INSTALL_ROOT),
        help=f"Directory where the archive (and extracted files) will be stored. [default: {DEFAULT_INSTALL_ROOT}]",
    )
    parser.add_argument(
        "--filename",
        help="Override the destination filename. Defaults to the final segment of the download URL.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in the target directory.",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip automatic extraction even if the download is an archive format.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT,
        help="HTTP timeout in seconds. [default: %(default)s]",
    )
    return parser


def _resolve_destination(args: argparse.Namespace) -> tuple[Path, Path]:
    target_dir = Path(args.target).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = args.filename or _default_filename(args.install)
    file_path = target_dir / filename
    if file_path.exists() and not args.force:
        raise DownloadError(
            f"Destination {file_path} already exists. Use --force to overwrite or choose a different --filename."
        )
    return target_dir, file_path


def install_archive(
    url: str,
    *,
    agree_license: bool,
    target: Path | str = DEFAULT_INSTALL_ROOT,
    filename: str | None = None,
    force: bool = False,
    skip_extract: bool = False,
    timeout: int = TIMEOUT,
) -> Path:
    """Download (and optionally extract) a Swiss Ephemeris archive."""

    if not agree_license:
        raise DownloadError("Swiss Ephemeris downloads require license acceptance.")

    target_dir = Path(target).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / (filename or _default_filename(url))
    if archive_path.exists() and not force:
        raise DownloadError(
            f"Destination {archive_path} already exists. Use force=True to overwrite or choose a different filename."
        )

    _download(url, archive_path, timeout=timeout)
    if not skip_extract:
        _extract_if_needed(archive_path, target_dir, force=force)
    return archive_path


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.install:
        parser.print_help(sys.stderr)
        return 0

    if not args.agree_license:
        parser.error("Swiss Ephemeris downloads require --agree-license acknowledgement.")

    try:
        archive_path = install_archive(
            args.install,
            agree_license=args.agree_license,
            target=args.target,
            filename=args.filename,
            force=args.force,
            skip_extract=args.skip_extract,
            timeout=args.timeout,
        )
    except DownloadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:  # pragma: no cover - filesystem errors share message path
        print(f"Filesystem error: {exc}", file=sys.stderr)
        return 1

    print("Swiss Ephemeris package installed.")
    print(f"Files located under: {archive_path.parent}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
