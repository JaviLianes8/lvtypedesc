# lvtypedesc guide

Every example on this page runs as part of the test suite.

## Reading a descriptor

`parse_type_descriptor` takes `bytes`, `bytearray` or `memoryview` and reads the descriptor
at the start. Whatever follows it (usually the flattened data) is left alone.

```pycon
>>> from lvtypedesc import parse_type_descriptor
>>> parse_type_descriptor(bytes.fromhex("0004 000A") + b"flattened data follows")
Scalar(code=10, name='DBL', label=None, flags=0)

```

Each descriptor starts with a 16-bit length (the whole descriptor, header included) and a
16-bit type-code word. The low byte of that word is the type code; the high byte is
reserved by LabVIEW and kept in `flags`. Bit `0x40` of it means a name follows the fields.

## The nodes

| Node | Codes | Fields |
| --- | --- | --- |
| `Scalar` | `0x01` to `0x0E` (I8 to U64, SGL, DBL, EXT, CSG, CDB, CXT) | none |
| `LVEnum` | `0x15`, `0x16`, `0x17` (EnumU8, EnumU16, EnumU32) | `items` |
| `PhysicalQuantity` | `0x19` to `0x1E` (SGLUnit to CXTUnit) | `units` |
| `Boolean` | `0x21`, and `0x20` (the old 16-bit Boolean) | none |
| `LVString` | `0x30` String, `0x32` Path, `0x33` Picture | `size` |
| `Array` | `0x40` | `element`, `dimensions`, `rank` |
| `Cluster` | `0x50` | `fields` |
| `LVVariant` | `0x53` | none |
| `Waveform` | `0x54` (time stamps are subtype 6) | `payload`, `subtype` |
| `FixedPoint` | `0x5F` | `payload` |
| `Refnum` | `0x70` | `payload`, `subtype` |

Every node also has `code`, `name` (the label from `known_codes()`), `label` and `flags`.
Nodes are frozen dataclasses: hashable, comparable and picklable. Equality ignores `flags`,
as NI advises for the reserved byte.

```pycon
>>> from lvtypedesc import VARIABLE
>>> grid = parse_type_descriptor(bytes.fromhex("0012 0040 0002 0000 0003 FFFF FFFF 0004 0021"))
>>> grid.rank, grid.dimensions, grid.dimensions[1] == VARIABLE
(2, (3, -1), True)
>>> enum = parse_type_descriptor(bytes.fromhex("000C 0016 0003 0141 0142 0143"))
>>> enum.items
('A', 'B', 'C')
>>> quantity = parse_type_descriptor(bytes.fromhex("000E 001A 0002 0002 FFFF 0003 0001"))
>>> quantity.units
((2, -1), (3, 1))

```

A size or dimension that the descriptor does not fix is `VARIABLE` (`-1`), which LabVIEW
writes as `0xFFFFFFFF`. Units are `(base index, exponent)` pairs over LabVIEW's nine SI
bases: 0 rad, 1 sr, 2 s, 3 m, 4 kg, 5 A, 6 K, 7 mol, 8 cd.

Fixed-point numbers, refnums and waveform types have layouts that change between LabVIEW
versions, so every byte after their header is kept in `payload`, a name included, and their
`label` stays `None`. `subtype` reads the first word of the payload.

```pycon
>>> stamp = parse_type_descriptor(bytes.fromhex("0012 4054 0006 0B61 6363 6573 7320 7469 6D65"))
>>> stamp.subtype, stamp.label, stamp.payload[2:]
(6, None, b'\x0baccess time')

```

## Names

A name is a Pascal string (a length byte, then the text) at the next even offset after the
fields, padded to a whole word. It is LabVIEW's control or cluster element name. LabVIEW
writes names and enum items in the system code page (Windows-1252 on a Western Windows);
this library maps each byte to one character (Latin-1), so every byte survives a round
trip. To read text such as `€` (byte `0x80`), re-decode it:
`label.encode("latin-1").decode("cp1252")`, and encode the other way before writing.

Bytes left inside a descriptor after its fields and name (other than the padding byte)
are ignored and are not written back; `to_bytes` always writes the canonical form.

```pycon
>>> error_out = parse_type_descriptor(
...     bytes.fromhex(
...         "0036 4050 0003 000C 4021 0673 7461 7475 7300 000A 4003 0463 6F64 6500"
...         " 0010 4030 FFFF FFFF 0673 6F75 7263 6500 0965 7272 6F72 206F 7574"
...     )
... )
>>> error_out.label, [field.label for field in error_out.fields]
('error out', ['status', 'code', 'source'])

```

## Writing a descriptor

`to_bytes` is the inverse of parsing: `parse_type_descriptor(to_bytes(node)) == node` for
every valid tree, and every descriptor LabVIEW 2026 wrote in the test captures comes back
byte for byte. A node with a `label` gets bit `0x40` set; other `flags` bits are kept.

```pycon
>>> from lvtypedesc import Cluster, LVString, Scalar, to_bytes
>>> tree = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label="n"), LVString(0x30, "String")))
>>> to_bytes(tree).hex(" ", -2)
'0014 0050 0002 0006 4003 016e 0008 0030 ffff ffff'
>>> parse_type_descriptor(to_bytes(tree)) == tree
True

```

The `name` field is not written: the code decides it when the bytes are read back. The code
must belong to the node's class (a `Scalar` with code `0x30` is refused).

## One line or a tree

```pycon
>>> from lvtypedesc import describe, pretty
>>> describe(error_out)
'Cluster { Boolean, I32, String }'
>>> print(pretty(error_out))
Cluster (3 fields) 'error out'
  [0] Boolean 'status'
  [1] I32 'code'
  [2] String (size variable) 'source'
>>> describe(quantity), describe(stamp), describe(enum)
('DBLUnit [s^-1 m]', 'Timestamp', 'EnumU16 (3 items)')

```

`describe` leaves names out; `pretty` shows names and enum items as Python string literals,
so a control character in them cannot break the layout.

## Type codes

```pycon
>>> from lvtypedesc import Category, TypeCode, known_codes
>>> TypeCode.ENUM_U16, len(known_codes())
(<TypeCode.ENUM_U16: 22>, 34)
>>> [row for row in known_codes() if row[2] is Category.STRING]
[(48, 'String', <Category.STRING: 'string'>), (50, 'Path', <Category.STRING: 'string'>), (51, 'Picture', <Category.STRING: 'string'>)]

```

## Command line

```
$ lvtypedesc decode 00040003
I32
$ lvtypedesc decode "0004 000A"
DBL
$ lvtypedesc decode 000E00400001FFFFFFFF0004000A
1D Array of DBL
$ lvtypedesc decode --tree 00140050000200064003016E00080030FFFFFFFF
Cluster (2 fields)
  [0] I32 'n'
  [1] String (size variable)
```

`lvtypedesc codes` lists every recognised code, `lvtypedesc --version` prints the version,
and `python -m lvtypedesc` works the same way. Whitespace in the hex is ignored. Exit codes:
0 done, 1 bad data (the message goes to stderr, prefixed `lvtypedesc: error:`, cut to 300
characters, never echoing the input), 2 bad usage (the usage message is cut to 300
characters). When the reader of the output goes away
(`lvtypedesc codes | head -1`), the command exits 1 without a traceback. Characters the
console cannot show are written as escapes, and control characters in usage errors are
escaped, so every message is one line.

## Errors

| Exception | When |
| --- | --- |
| `TypeDescError` | the bytes are not a descriptor this library reads: truncated input, a length below 4, a descriptor running past its parent or the input, fields or a name running past their descriptor, an unknown code, a refused code (Void, ComplexFXP, Set, Map, Typedef), nesting deeper than `MAX_DEPTH` |
| `TypeDescError` | a tree holds a value no descriptor can hold (`to_bytes`, `describe` and `pretty` alike): a code that does not fit the class, a `name` that is not the code's name, flags outside a byte, a size or dimension outside 32 bits, a count above 65535, text with a character above U+00FF or longer than 255 bytes, a unit outside 16 bits, a label on a node that keeps its name in `payload`, more than 16384 nodes; and, for `to_bytes` only, more than 65535 bytes in all |
| `TypeError` | the argument is not bytes-like (`parse_type_descriptor`) or the tree is malformed: a field that is not exactly `int`, `str`, `bytes` or `tuple` (subclasses are refused; a `TypeCode` member is accepted as a code), or a bare `TypeDesc` instead of a node class (`to_bytes`, `describe`, `pretty`); a released `memoryview` (`parse_type_descriptor`) |

`TypeDescError` is a `ValueError`. Messages name offsets, codes and limits, never the input;
type names in messages are cut to 40 characters.

## Limits

- Nesting: arrays and clusters up to `MAX_DEPTH` (64) levels, for reading and for every
  function that takes a tree, so a hostile descriptor cannot exhaust the stack.
- Size: the 16-bit length word caps a descriptor at 65535 bytes, so parsing reads at most
  that many bytes (through the buffer protocol; a non-contiguous `memoryview` is copied
  first) and is linear and bounded whatever follows the descriptor.
- Nodes: a tree may hold at most 16384 nodes, counting a shared subtree once for every
  place it appears; no descriptor can hold more. This bounds `describe` and `pretty` too.
- Trees must not contain cycles (frozen nodes cannot form one without bypassing the
  dataclass); the nesting limit refuses them, but equality and hashing would recurse.
- `to_bytes` writes descriptors in their canonical, word-padded form, so a parsed
  descriptor near the 65535-byte limit that held odd-length children may come out longer
  than that and be refused.

## Not covered

- Typedefs (`0xF1`): in the datalogs LabVIEW 2026 wrote, the length word of the type inside
  a typedef does not match the bytes it occupies, so it is refused rather than guessed.
- The flat list form (datalog files, flattened variants with attributes, VI files), where
  arrays and clusters name their elements by index.
- The layout inside fixed-point, refnum and waveform payloads.
- Descriptors from LabVIEW versions other than 2026 were not captured; NI notes the codes may
  change between versions.

## Upgrading from 0.2

- Names are read into `label` and written back; 0.2 dropped them, so a named descriptor did
  not survive `to_bytes`. Each node has `flags`, the reserved byte, kept on writing and left
  out of equality. Equality compares `label`, so a named descriptor no longer equals an
  unnamed template such as `Scalar(0x03, "I32")`; compare `dataclasses.replace(node,
  label=None)` to ignore names.
- Enums, physical quantities, variants and waveform types are now read (0.2 refused them).
  Void, ComplexFXP, Set, Map and Typedef are refused by name.
- `Refnum.subtype` is a property read from `payload`, no longer a constructor argument, and
  `payload` is keyword-only (`Refnum(0x70, "Refnum", payload=...)`).
  Payloads of fixed-point numbers and refnums include an appended name, as before.
- A descriptor that runs past its parent, or a string descriptor without its size word, now
  raises `TypeDescError` (0.2 read on into the next bytes, or assumed a variable size).
- Input that is not bytes-like raises `TypeError` (0.2: `TypeDescError`); `memoryview` is
  accepted. Nesting deeper than 64 levels raises `TypeDescError` (0.2: `RecursionError`).
- `to_bytes` checks the tree first and pads structured descriptors to whole words;
  `describe` and `pretty` run the same checks, so all three accept the same trees. A node's
  `name` must be the name of its code (`Scalar(0x03, "Bogus")` is refused). `pretty`
  shows names and enum items.
- The command line prefixes data errors with `lvtypedesc: error:`, cuts usage errors to
  300 characters (0.2 echoed a whole unknown argument), exits 1 quietly when its output is
  closed, and runs as `python -m lvtypedesc`.
