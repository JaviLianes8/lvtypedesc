# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

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

## [0.1.0]

- First release.
- `parse_type_descriptor` reads a LabVIEW type-descriptor byte string into a
  typed tree of frozen dataclasses, and `describe` renders it as a readable line.
- Supported subset: numeric scalars (I8 to U64, SGL, DBL, EXT, complex),
  booleans, strings, paths, pictures, n-dimensional arrays and nested clusters.
- Out-of-scope codes (enums, variants, waveforms, refnums) and truncated input
  raise `TypeDescError`. Fills the gap left by VI-file parsers, which do not
  decode the runtime type-descriptor byte string.
