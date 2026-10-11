"""Command-line interface for lvtypedesc.

Decode a hex type descriptor into a readable type, or list the codes the library
knows. Errors are written to stderr and the process exits with status 1.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from ._codes import known_codes
from ._errors import TypeDescError
from ._model import describe
from ._parser import parse_type_descriptor
from ._pretty import pretty

_EXAMPLES = """\
examples:
  lvtypedesc decode 00040003                          -> I32
  lvtypedesc decode "0004 000A"                       -> DBL (spaces are ignored)
  lvtypedesc decode 000E00400001FFFFFFFF0004000A      -> 1D Array of DBL
  lvtypedesc decode --tree 000E00500002000400030004000A
  lvtypedesc codes                                    -> list every known type code
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvtypedesc",
        description="Parse LabVIEW type-descriptor byte strings into a readable type.",
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvtypedesc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    decode = sub.add_parser(
        "decode",
        help="decode a hex type descriptor into a readable type",
        description="Decode a hex type descriptor. Whitespace in the hex is ignored.",
    )
    decode.add_argument("hex", help="the type descriptor as hex, for example 00040003")
    decode.add_argument(
        "--tree",
        action="store_true",
        help="print an indented tree instead of a one-line summary",
    )

    sub.add_parser(
        "codes",
        help="list every type code the library recognises",
        description="List every recognised type code, with its name and category.",
    )
    return parser


def _run_decode(hex_text: str, tree: bool) -> int:
    try:
        data = bytes.fromhex(hex_text)
    except ValueError as exc:
        print(f"error: not valid hex: {exc}", file=sys.stderr)
        return 1
    try:
        node = parse_type_descriptor(data)
    except TypeDescError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(pretty(node) if tree else describe(node))
    return 0


def _run_codes() -> int:
    for code, name, category in known_codes():
        print(f"0x{code:02X}  {name:<10} {category.value}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvtypedesc`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "decode":
        return _run_decode(args.hex, args.tree)
    return _run_codes()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
