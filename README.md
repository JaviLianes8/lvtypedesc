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
from lvtypedesc import parse_type_descriptor, describe

# A 1D array of clusters, each holding an I32 and a string.
data = bytes.fromhex("001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF".replace(" ", ""))

node = parse_type_descriptor(data)
print(describe(node))        # 1D Array of Cluster { I32, String }
print(node.rank)             # 1
print(node.element.fields)   # (Scalar(code=3, name='I32'), LVString(code=48, name='String'))
```

The tree is built from frozen dataclasses: `Scalar`, `Boolean`, `LVString`,
`Array` (with `element` and `dimensions`) and `Cluster` (with `fields`). A
dimension or string whose size is not fixed in the descriptor uses the sentinel
`VARIABLE`. Trailing bytes, such as the flattened data after the descriptor, are
ignored. Truncated, unknown or out-of-scope input raises `TypeDescError`.

### Supported subset

Fully parsed: the numeric scalars (`I8` to `U64`, `SGL`, `DBL`, `EXT` and the
complex variants), booleans, strings, paths, pictures, n-dimensional arrays and
clusters, nested to any depth.

Not covered, and reported with a clear error: enums, variants, waveforms,
refnums and other exotic or partly undocumented variants. NI also notes that
type codes can change between LabVIEW versions, so treat the codes as the common,
documented set rather than a guarantee for every build.

## Why

LabVIEW ships flattened data with a leading type descriptor, and decoding it in
Python needs that descriptor parsed into a schema first. OpenG's Variant Data
Library parses descriptors inside LabVIEW, but it is LabVIEW VIs, not Python. The
existing PyPI packages read LabVIEW source files instead: `pylabview` and `lvkit`
parse the `.vi` binary, `pylavi` validates VI files. None of them exposes a parser
for the raw runtime type-descriptor byte string that precedes flattened data or
sits inside a variant. The format is NI-documented and version-sensitive, so the
value here is a maintained Python decoder, not a new format: this library fills
that gap with a zero-dependency, fully typed reader for the common documented types.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
