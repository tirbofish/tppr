"""Command-line entry point: convert Mistral OCR JSON files into tppr paper JSON.

Usage examples:
    python -m tppr_paper_extractor samples/mistral/BaulkhamHills.json
    python -m tppr_paper_extractor samples/mistral -o samples/tppr
    python -m tppr_paper_extractor one.json two.json -o out/ --validate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .extractor import extract_paper, validate_paper


def _iter_inputs(paths: list[str]) -> list[Path]:
    """Expand directories into their .json files; keep files as-is."""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(f"Input not found: {raw}")
    return out


def _resolve_output(input_path: Path, output: Path | None, many: bool) -> Path | None:
    """Decide where to write a single input's result.

    Returns None to signal "write to stdout".
    """
    if output is None:
        return None if not many else input_path.with_suffix(".tppr.json")
    if output.is_dir() or many:
        return output / input_path.with_suffix(".tppr.json").name
    return output


def _process_one(
    input_path: Path,
    output: Path | None,
    *,
    indent: int,
    do_validate: bool,
    quiet: bool,
) -> int:
    with input_path.open("r", encoding="utf-8") as fh:
        mistral = json.load(fh)
    paper = extract_paper(mistral)
    payload = json.dumps(paper, indent=indent, ensure_ascii=False)

    if output is None:
        sys.stdout.write(payload + "\n")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
        if not quiet:
            print(
                f"{input_path.name} -> {output} "
                f"({len(paper['questions'])} questions, "
                f"{paper['total_marks']} marks)",
                file=sys.stderr,
            )

    if do_validate:
        errs = validate_paper(paper)
        if errs:
            label = str(output or input_path)
            for e in errs:
                print(f"VALIDATION ERROR [{label}]: {e}", file=sys.stderr)
            return 1
        if not quiet:
            print(f"validated: {output or input_path}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tppr-paper-extractor",
        description="Convert Mistral OCR JSON into tppr paper JSON.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Mistral OCR .json file(s) or a directory containing them.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file (single input) or directory (multiple/dir input). "
        "Omit to write a single result to stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent width (default: 2). Use -1 for compact output.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate each output against the tppr content schema and exit "
        "non-zero on any failure.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logs.")
    args = parser.parse_args(argv)

    inputs = _iter_inputs(args.inputs)
    if not inputs:
        print("No .json inputs found.", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else None
    if output and not output.exists():
        # Treat a path ending with a separator or supplied for multiple inputs
        # as a directory; create it. A single-file input keeps it as a file.
        if len(inputs) > 1 or Path(args.inputs[0]).is_dir() or args.output.endswith(("/", "\\")):
            output.mkdir(parents=True, exist_ok=True)
    many = len(inputs) > 1 or any(Path(p).is_dir() for p in args.inputs)

    indent = args.indent if args.indent >= 0 else None
    failures = 0
    for inp in inputs:
        out_path = _resolve_output(inp, output, many)
        try:
            failures += _process_one(
                inp,
                out_path,
                indent=indent,
                do_validate=args.validate,
                quiet=args.quiet,
            )
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"ERROR processing {inp}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())