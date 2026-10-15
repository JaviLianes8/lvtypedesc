"""Leaf nodes beyond plain scalars: enums, physical quantities and the opaque types."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._model import TypeDesc


def first_word(payload: bytes) -> int:
    return int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 0


@dataclass(frozen=True)
class LVEnum(TypeDesc):
    """An enumerated integer (EnumU8, EnumU16 or EnumU32) and its item names.

    >>> from lvtypedesc import LVEnum, parse_type_descriptor
    >>> data = bytes.fromhex("0016 0015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F")
    >>> parse_type_descriptor(data) == LVEnum(0x15, "EnumU8", items=("am", "fm", "fm stereo"))
    True
    """

    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalQuantity(TypeDesc):
    """A floating-point number with a unit, as ``(base index, exponent)`` pairs.

    The base indexes are LabVIEW's nine SI bases: 0 rad, 1 sr, 2 s, 3 m, 4 kg, 5 A,
    6 K, 7 mol, 8 cd.

    >>> from lvtypedesc import PhysicalQuantity, parse_type_descriptor
    >>> node = parse_type_descriptor(bytes.fromhex("000E 001A 0002 0002 FFFF 0003 0001"))
    >>> isinstance(node, PhysicalQuantity), node.units
    (True, ((2, -1), (3, 1)))
    """

    units: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class LVVariant(TypeDesc):
    """A LabVIEW variant. The descriptor says nothing about the value it will hold.

    >>> from lvtypedesc import LVVariant, parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("000C 4053 0756 6172 6961 6E74"))
    LVVariant(code=83, name='Variant', label='Variant', flags=64)
    """


@dataclass(frozen=True)
class FixedPoint(TypeDesc):
    """A LabVIEW fixed-point number (FXP).

    Its layout is version-specific and not published, so every byte after the header
    (an appended name included) is kept verbatim in ``payload``; ``label`` stays None.

    >>> from lvtypedesc import FixedPoint, parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("0008005F41424344"))
    FixedPoint(code=95, name='FXP', label=None, flags=0, payload=b'ABCD')
    """

    payload: bytes = b""


@dataclass(frozen=True)
class Refnum(TypeDesc):
    """A refnum (a handle to a file, queue, VI Server object and so on).

    Every byte after the header is kept verbatim in ``payload``, an appended name
    included; ``label`` stays None. ``subtype`` reads the refnum kind word from it.
    ``payload`` is keyword-only.

    >>> from lvtypedesc import parse_type_descriptor
    >>> node = parse_type_descriptor(bytes.fromhex("000E 4070 0002 0672 6566 6E75 6D00"))
    >>> node.subtype, node.payload[2:9]
    (2, b'\\x06refnum')
    """

    payload: bytes = field(default=b"", kw_only=True)

    @property
    def subtype(self) -> int:
        """The first word of ``payload`` (the refnum kind), or 0 when it is shorter.

        >>> from lvtypedesc import Refnum
        >>> Refnum(0x70, "Refnum", payload=b"\\x00\\x02").subtype
        2
        """
        return first_word(self.payload)


@dataclass(frozen=True)
class Waveform(TypeDesc):
    """A waveform-family type (code ``0x54``), such as a time stamp (subtype 6).

    Every byte after the header is kept verbatim in ``payload``, an appended name
    included; ``label`` stays None. ``subtype`` reads the first word of it. ``payload``
    is keyword-only.

    >>> from lvtypedesc import parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("000600540006")).subtype
    6
    """

    payload: bytes = field(default=b"", kw_only=True)

    @property
    def subtype(self) -> int:
        """The first word of ``payload`` (the waveform kind), or 0 when it is shorter.

        >>> from lvtypedesc import Waveform
        >>> Waveform(0x54, "Waveform", payload=b"\\x00\\x06").subtype
        6
        """
        return first_word(self.payload)
