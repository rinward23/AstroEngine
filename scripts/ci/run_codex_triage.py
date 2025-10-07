"""Utility for invoking GPT-5-Codex triage on CI artifacts.

This script is referenced from GitHub Actions to forward compressed
artifact bundles to the OpenAI Responses API with the Code Interpreter
tool enabled.  The model unpacks the archive, inspects CI outputs,
and produces a Markdown summary with remediation guidance and unified
diff patches.  The resulting triage report is printed to stdout and
persisted to disk for later upload as a workflow artifact.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path
from textwrap import dedent

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="Path to the gzipped tarball containing CI artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination file for the Markdown triage report.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL", "gpt-5-codex"),
        help="Override the OpenAI model identifier.",
    )
    return parser.parse_args()


def ensure_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set; unable to contact the OpenAI API."
        )


def build_prompt(archive_name: str) -> str:
    return dedent(
        f"""
        You are the CI sherpa for the AstroEngine monorepo.  A gzip-compressed
        tarball named {archive_name} is attached.  It contains:

        * Lint logs from Ruff, Black, Isort, and Bandit.
        * Static analysis output from mypy and pip-audit.
        * Pytest coverage XML, JUnit XML, and human-readable test logs.

        Responsibilities:
        1. Extract the archive into a working directory inside the code interpreter.
        2. Inspect every file to understand which checks failed and why.
        3. Summarise failures with root-cause analysis that references filenames,
           stack traces, or rule identifiers as appropriate.
        4. When a fix is obvious, propose the minimal patch using fenced unified diffs
           ("```diff" blocks) scoped to the correct repository paths.
        5. If everything passed, confirm the healthy state and highlight which suites ran.
        6. Always end with a concise checklist of developer actions (each item with a
           leading "- [ ]").

        Keep the tone crisp and actionable.  Prefer Markdown headings for readability.
        """
    ).strip()


def request_triage(model: str, archive_path: Path) -> str:
    client = OpenAI()
    payload = base64.b64encode(archive_path.read_bytes()).decode()
    prompt = build_prompt(archive_path.name)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_file",
                        "file_data": {
                            "name": archive_path.name,
                            "data": payload,
                        },
                    },
                ],
            }
        ],
        tools=[{"type": "code_interpreter"}],
    )
    return response.output_text


def main() -> int:
    args = parse_args()

    try:
        ensure_api_key()
    except RuntimeError as exc:  # pragma: no cover - defensive, deterministic branch
        print(str(exc), file=sys.stderr)
        return 1

    if not args.artifacts.exists():
        print(f"Artifact bundle not found: {args.artifacts}", file=sys.stderr)
        return 1

    report = request_triage(args.model, args.artifacts)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
