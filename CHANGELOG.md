# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `parse_type_descriptor` reads a LabVIEW type-descriptor byte string into a
  typed tree of frozen dataclasses, and `describe` renders it as a readable line.
- Supported subset: numeric scalars (I8 to U64, SGL, DBL, EXT, complex),
  booleans, strings, paths, pictures, n-dimensional arrays and nested clusters.
- Out-of-scope codes (enums, variants, waveforms, refnums) and truncated input
  raise `TypeDescError`. Fills the gap left by VI-file parsers, which do not
  decode the runtime type-descriptor byte string.
