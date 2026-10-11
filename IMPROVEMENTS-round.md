# Improvements round

Ranked, substantial improvements for this round. Each is additive: the existing
`parse_type_descriptor` / `describe` API keeps working unchanged.

## Provenance note (read first)

The type-descriptor code table this library uses is the community
reverse-engineering published at the LabVIEW wiki
(https://labviewwiki.org/wiki/Type_descriptor). It is consistent with the
scattered fragments NI has published, but it is **not** an official, byte-exact
NI specification. Codes can also differ between LabVIEW versions and between the
in-memory 16-bit-word form and the flattened byte form. So every code and layout
below is treated as the common documented set, not a guarantee, and the parser
reports honest errors rather than guessing. Where a payload cannot be verified
(fixed-point and refnum internals), the raw bytes are preserved instead of being
invented into fields.

## Ranked improvements

1. **Command-line interface.** A real `lvtypedesc` console script (argparse,
   `[project.scripts]`): `decode` a hex descriptor into a readable type, a
   `codes` listing of every code the library knows, `--version`, and a `--help`
   with runnable examples. Errors go to stderr with exit code 1. This is the
   single biggest reach improvement: it makes the library usable without writing
   Python.

2. **Expose the type-code enum.** A public `TypeCode` `IntEnum` so callers can
   refer to `TypeCode.DBL` instead of a bare `0x0A`, plus `known_codes()` that
   returns the full `(code, name, category)` table that backs the CLI listing.

3. **Round-trip emission.** `to_bytes(node)` re-emits the canonical descriptor
   for every node type the library models, so `parse` and `to_bytes` are
   inverses for the supported subset. This is round-trip "where defined": it
   emits the short-form descriptor and refuses (honest error) when the length
   would overflow the 16-bit short-form length word.

4. **Recognise fixed-point and refnum.** FXP (`0x5F`) and Refnum (`0x70`) move
   from "unsupported, raises" to recognised nodes. Because their internal
   payload layout is version-specific and not fully verifiable, the parser keeps
   the raw payload bytes rather than inventing fields. The refnum subtype word is
   surfaced as a best-effort `subtype` and documented as provisional.

5. **Faithful string sizing.** `LVString` now carries the descriptor's 32-bit
   size word (`VARIABLE` for `0xFFFFFFFF`), so fixed-size strings, paths and
   pictures round-trip exactly and the size is inspectable.

6. **Multi-line pretty-print.** `pretty(node)` renders a parsed descriptor as an
   indented tree, complementing the existing one-line `describe`. The CLI uses it
   for `decode --tree`.

7. **Stronger tests.** A contract test that parses representative descriptors for
   every structural family (scalar, string, array of DBL, cluster) and asserts
   the whole typed tree; round-trip property tests; a CLI unit test; and a real
   end-to-end test that pip-installs the package editable and drives the actual
   installed `lvtypedesc` console script through a subprocess.

## Deliberately out of scope

Enums, variants and waveforms stay unsupported with a clear error: their payloads
are not documented well enough to parse honestly. No codes are invented. The
long-form (32-bit length) descriptor variant is not emitted; `to_bytes` reports
when a tree is too large for the short form instead of guessing the long form.
