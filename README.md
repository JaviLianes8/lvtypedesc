# lvtypedesc

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse LabVIEW type descriptors into a typed tree, render them, and write them back.

A LabVIEW type descriptor is the short, length-prefixed block of words that says what a
piece of flattened data is: an I32, a 2D array of Booleans, a cluster of named fields.
LabVIEW's Variant To Flattened String returns one as its "type string", and you need it
parsed before you can decode the data that goes with it. `lvtypedesc` reads that block into
frozen dataclasses you can inspect, prints it as one line or as a tree, and writes a tree
back to the exact bytes. Pure Python, no dependencies, fully typed.

## Install

```
pip install lvtypedesc
```

## Quick start

```pycon
>>> from lvtypedesc import describe, parse_type_descriptor, pretty, to_bytes
>>> data = bytes.fromhex(
...     "002A 4040 0001 FFFFFFFF 001A 0050 0002 0006 4003 016E"
...     " 000E 4030 FFFFFFFF 046E 616D 6500 0472 6F77 7300"
... )
>>> node = parse_type_descriptor(data)
>>> describe(node)
'1D Array of Cluster { I32, String }'
>>> print(pretty(node))
Array (rank 1, dims [variable]) 'rows'
  Cluster (2 fields)
    [0] I32 'n'
    [1] String (size variable) 'name'
>>> node.element.fields[1].label
'name'
>>> to_bytes(node) == data
True

```

The tree is made of `Scalar`, `Boolean`, `LVString`, `Array`, `Cluster`, `LVEnum`,
`PhysicalQuantity`, `LVVariant`, `FixedPoint`, `Refnum` and `Waveform` nodes. Element and
control names travel in `label`. The command line does the same from a shell:

```
$ lvtypedesc decode 000E00400001FFFFFFFF0004000A
1D Array of DBL
```

The [guide](https://github.com/JaviLianes8/lvtypedesc/blob/main/GUIDE.md) covers every
node, the command line, errors and limits; the
[changelog](https://github.com/JaviLianes8/lvtypedesc/blob/main/CHANGELOG.md) lists what
changed in 1.0.0.

## What it reads, and how it was checked

The format is the one NI documents on its
[Type Descriptors](https://www.ni.com/docs/en-US/bundle/labview/page/type-descriptors.html)
page for Variant To Flattened String: a 16-bit length, a 16-bit type-code word whose low
byte is the type, type-specific fields, and an optional name. Supported: every numeric
type, enums, numbers with units, Booleans, strings, paths, pictures, arrays and clusters
nested to 64 levels, variants, and element names. Fixed-point numbers, refnums and
waveform types (time stamps among them) are recognised and their bytes kept verbatim,
because their layout is version-specific. Typedefs, sets, maps and void are refused with a
named error.

The parser is tested against what LabVIEW 2026 itself wrote and read on a real machine:
the descriptors in front-panel datalog files of sixteen shipped VIs (error clusters,
paths, enums, refnums, time stamps, fixed-point numbers, 1D and 2D arrays, variants),
whose single-type entries it reads and writes back byte for byte (arrays and clusters are
rebuilt in the nested form for the tests), and the answers of LabVIEW's own
type-descriptor VIs (`vi.lib/Utility/GetType.llb`) on arrays, clusters, enums, units,
strings and refnums, and the nested descriptors those VIs build.

LabVIEW also stores types as a flat list where arrays and clusters point at their elements
by index (datalog files, flattened variants with attributes, VI files). This library reads
the nested form; NI's page describes both.

## Why

The LabVIEW packages on PyPI work on LabVIEW source files: `pylabview` and `pylavi`
describe themselves as LabVIEW file parsers and `lvkit` converts VIs to Python (as listed
on PyPI on 2026-10-15). None offers a small reader and writer for the type string itself.
OpenG's LabVIEW Data Tools parse it inside LabVIEW, as VIs. `lvtypedesc` is that reader
for Python: one function in, one function out, a tree you can type-check against.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvtypedesc/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
