from __future__ import annotations

import argparse
from pathlib import Path

from .generator import generate_bujo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a hyperlinked Bullet Journal PDF."
    )
    parser.add_argument("--year", type=int, default=2027)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("bujo-2027.pdf"),
        help="Output PDF path.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generate_bujo(year=args.year, output=args.output)


if __name__ == "__main__":
    main()
