# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-15

The public API is now stable: `parse_type_descriptor`, `to_bytes`, `describe`, `pretty`,
`known_codes`, the node classes, `TypeCode`, `Category`, `TypeDescError`, `VARIABLE` and
`MAX_DEPTH` keep their names, signatures and behaviour across 1.x.

- Checked against LabVIEW 2026: the descriptors of sixteen shipped VIs, read from the
  front-panel datalog files LabVIEW wrote, parse and are written back byte for byte, and
  LabVIEW's own type-descriptor VIs read every test descriptor the way this library does.
- Names: bit `0x40` of the type-code word announces an appended name, now read into the
  new `label` field and written back by `to_bytes`. The reserved high byte is kept in the
  new `flags` field, written back and left out of equality. Equality compares `label`, so
  a named descriptor no longer equals an unnamed template.
- New nodes: `LVEnum` (EnumU8, EnumU16, EnumU32, with `items`), `PhysicalQuantity`
  (numbers with units, with `units`), `LVVariant` and `Waveform` (time stamps and other
  waveform types, bytes kept verbatim). `TypeCode`, `Category` and `known_codes()` grow
  with them. Void, ComplexFXP, Set, Map and Typedef are refused by name.
- `Refnum.subtype` is now a property read from `payload` instead of a constructor field;
  `payload` of `Refnum` and `Waveform` is keyword-only.
- Stricter reading: a descriptor that runs past its parent, a string descriptor without its
  size word, or a name that runs past its descriptor raises `TypeDescError`. Nesting is
  limited to `MAX_DEPTH` (64) levels instead of failing with `RecursionError`. Input that is
  not bytes-like raises `TypeError`; `memoryview` is accepted.
- `to_bytes`, `describe` and `pretty` run the same checks first: `TypeError` for a malformed
  tree or a bare `TypeDesc`, `TypeDescError` for a code that does not fit the node's class,
  a `name` that is not the code's name, or a value that does not fit its field. Structured
  descriptors are padded to whole 16-bit words. Fields must hold exactly `int`, `str`,
  `bytes` or `tuple`, and a tree that certainly needs more than 65535 bytes is refused
  before any other work (shared subtrees counted each time). Parsing reads at most 65535 bytes through the buffer protocol.
- `pretty` shows names and enum items; `describe` spells enums, units and time stamps.
- Command line: `python -m lvtypedesc`; data errors are prefixed `lvtypedesc: error:`,
  bounded, and never echo the input; usage errors are cut to 300 characters (0.2.0 echoed a
  whole unknown argument) and control characters in them escaped; characters the console
  cannot show are escaped; a closed output exits 1 without a traceback.
- README rewritten: the format is NI's published Type Descriptors page, not only
  community notes as 0.2.0 said. New GUIDE with an upgrade section.

## [0.2.0] - 2026-10-12

- Command-line interface: a `lvtypedesc` console script with `decode` (optional
  `--tree`), `codes`, `--version` and runnable `--help` examples. Errors go to
  stderr with exit code 1.
- `to_bytes` re-emits the canonical short-form descriptor for every modelled
  node, so parsing and emission are inverses for the supported subset.
- New public API: `TypeCode` enum, `known_codes()`, `pretty()`, `to_bytes()`,
  and the `FixedPoint` and `Refnum` node types.
- Fixed-point (`FXP`) and refnum descriptors are now recognised. Their
  type-specific bytes are preserved verbatim rather than interpreted, because
  their internal layout is version-specific and not fully documented.
- `LVString` now carries the descriptor's 32-bit `size` word (`VARIABLE` when not
  fixed), so fixed-size strings round-trip exactly.
- README now states the provenance plainly: the code table is community
  reverse-engineering from the LabVIEW wiki, not an official NI byte spec.

## [0.1.0] - 2026-10-11 (not published on PyPI)

- First release.
- `parse_type_descriptor` reads a LabVIEW type-descriptor byte string into a
  typed tree of frozen dataclasses, and `describe` renders it as a readable line.
- Supported subset: numeric scalars (I8 to U64, SGL, DBL, EXT, complex),
  booleans, strings, paths, pictures, n-dimensional arrays and nested clusters.
- Out-of-scope codes (enums, variants, waveforms, refnums) and truncated input
  raise `TypeDescError`. Fills the gap left by VI-file parsers, which do not
  decode the runtime type-descriptor byte string.
