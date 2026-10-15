"""Command-line interface: decode a hex type descriptor, or list the known type codes.

Exit codes: 0 done, 1 bad data (or the reader of the output went away), 2 bad usage.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__
from ._cli_io import MESSAGE_LIMIT, Parser, finish, write
from ._codes import known_codes
from ._describe import describe
from ._errors import TypeDescError
from ._parser import parse_type_descriptor
from ._pretty import pretty

_EXAMPLES = """\
examples:
  lvtypedesc decode 00040003                          -> I32
  lvtypedesc decode "0004 000A"                       -> DBL (whitespace is ignored)
  lvtypedesc decode 000E00400001FFFFFFFF0004000A      -> 1D Array of DBL
  lvtypedesc decode --tree 000E00500002000400030004000A
  lvtypedesc codes                                    -> list every known type code

Data errors print to stderr and exit 1; usage errors exit 2.
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = Parser(
        prog="lvtypedesc",
        description="Parse LabVIEW type descriptors into a readable type.",
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
        "--tree", action="store_true", help="print an indented tree with element names"
    )
    sub.add_parser(
        "codes",
        help="list every type code the library recognises",
        description="List every recognised type code, with its name and category.",
    )
    return parser


def _decode(hex_text: str, tree: bool) -> str:
    try:
        data = bytes.fromhex(hex_text)
    except ValueError:
        raise TypeDescError("not valid hex (digits 0-9 and A-F in pairs, spaces allowed)") from None
    node = parse_type_descriptor(data)
    return pretty(node) if tree else describe(node)


def _codes() -> str:
    return "\n".join(f"0x{code:02X}  {name:<10} {cat.value}" for code, name, cat in known_codes())


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvtypedesc`` console script and ``python -m lvtypedesc``.

    >>> from lvtypedesc._cli import main
    >>> main(["decode", "00040003"])
    I32
    0
    """
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else 2
    try:
        output = _decode(args.hex, args.tree) if args.command == "decode" else _codes()
    except TypeDescError as exc:
        write("stderr", f"lvtypedesc: error: {str(exc)[:MESSAGE_LIMIT]}\n")
        return finish(1)
    return finish(0 if write("stdout", output + "\n") else 1)
