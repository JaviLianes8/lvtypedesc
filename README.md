# lvtypedesc

Parse LabVIEW type-descriptor byte strings into a readable, typed schema

## Install

```
pip install lvtypedesc
```

A LabVIEW type descriptor is the small, length-prefixed block of type codes that
precedes flattened LabVIEW data. This library turns that block into a typed tree
you can inspect, which is the schema a generic unflatten needs.

## Usage

```python
from lvtypedesc import parse_type_descriptor, describe, pretty, to_bytes

# A 1D array of clusters, each holding an I32 and a string.
data = bytes.fromhex(
    "001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF".replace(" ", "")
)

node = parse_type_descriptor(data)
print(describe(node))  # 1D Array of Cluster { I32, String }
print(node.rank)  # 1
print(node.element.fields[0].name)  # I32
print(to_bytes(node) == data)  # True, round-trips exactly
print(pretty(node))
# Array (rank 1, dims [variable])
#   Cluster (2 fields)
#     [0] I32
#     [1] String (size variable)
```

The tree is built from frozen dataclasses: `Scalar`, `Boolean`, `LVString` (with
`size`), `Array` (with `element` and `dimensions`), `Cluster` (with `fields`),
`FixedPoint` and `Refnum`. A dimension or string whose size is not fixed in the
descriptor uses the sentinel `VARIABLE`. Trailing bytes, such as the flattened
data after the descriptor, are ignored. Truncated, unknown or out-of-scope input
raises `TypeDescError`.

`to_bytes` re-emits the canonical short-form descriptor for any node the library
models, so `parse_type_descriptor` and `to_bytes` are inverses for the supported
subset. `TypeCode` exposes the recognised codes by name and `known_codes()`
returns the full table.

## Command line

Installing the package also installs a `lvtypedesc` console script:

```
$ lvtypedesc decode 00040003
I32
$ lvtypedesc decode 000E00400001FFFFFFFF0004000A
1D Array of DBL
$ lvtypedesc decode --tree 000E00500002000400030004000A
Cluster (2 fields)
  [0] I32
  [1] DBL
$ lvtypedesc codes          # list every recognised type code
$ lvtypedesc --version
```

Whitespace in the hex is ignored. Errors go to stderr with exit code 1. Run
`lvtypedesc --help` for the full list of examples.

## Supported subset

Fully parsed: the numeric scalars (`I8` to `U64`, `SGL`, `DBL`, `EXT` and the
complex variants), booleans, strings, paths, pictures, n-dimensional arrays and
clusters, nested to any depth. Fixed-point (`FXP`) and refnum descriptors are
recognised and their type-specific bytes preserved, but their internal layout is
not interpreted (see provenance below).

Not covered, and reported with a clear error: enums, variants and waveforms,
whose payloads are not documented well enough to parse honestly.

## Provenance (please read)

The type-descriptor code table used here is **community reverse-engineering**,
documented at the [LabVIEW wiki](https://labviewwiki.org/wiki/Type_descriptor).
It is consistent with the fragments NI has published but it is **not** an
official, byte-exact NI specification. Two further caveats:

- Codes can change between LabVIEW versions, so treat them as the common
  documented set rather than a guarantee for every build.
- The in-memory 16-bit-word form and the flattened byte form can differ. This
  library parses the flattened byte form.

Because of this, anything that cannot be verified is treated as provisional:
unknown codes raise an honest error instead of a guess, and the fixed-point and
refnum payloads are kept as raw bytes rather than invented into fields. The
refnum `subtype` word is surfaced best-effort and is itself provisional.

## Why

LabVIEW ships flattened data with a leading type descriptor, and decoding it in
Python needs that descriptor parsed into a schema first. OpenG's Variant Data
Library parses descriptors inside LabVIEW, but it is LabVIEW VIs, not Python. The
existing PyPI packages read LabVIEW source files instead: `pylabview` and `lvkit`
parse the `.vi` binary, `pylavi` validates VI files. None of them exposes a parser
for the raw runtime type-descriptor byte string that precedes flattened data or
sits inside a variant. This library fills that gap with a zero-dependency, fully
typed reader for the common documented types.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
