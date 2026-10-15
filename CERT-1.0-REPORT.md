# lvtypedesc 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.0, 1221d48)
- [x] Baseline gates run on 0.2.0
- [x] Real LabVIEW 2026 captures and NI sources (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0 (items 8, 10, 13, 14)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer (item 16)
- [ ] Gates (item 15)
- [ ] PR open and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.2.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 57 passed |
| `pytest --doctest-modules src` | no doctests at all |

## Ground truth (item 7)

Three independent sources, none of them this library's own output:

- **NI's Type Descriptors page** (fetched 2026-10-15 through NI's documentation API by
  `scripts/fetch_sources.py`; the copy stays local and git-ignored, `tests/fixtures/sources/MANIFEST.json`
  records URL, date, size, SHA-256 and licence). It documents the nested form that Variant To
  Flattened String returns: the length and type-code words, the reserved high byte, the name
  appended as a Pascal string rounded to an even length, and the layout of numerics, enums,
  physical quantities, strings, arrays, clusters and variants. 0.2.0's README called the format
  "community reverse-engineering, not an official NI specification"; that was false and is
  corrected. `tests/test_sources_truth.py` checks every code in NI's table is recognised, every
  recognised or refused code is in the LabVIEW Wiki list (fetched the same day), and NI's six
  printed example descriptors read as NI explains them.
- **Descriptors LabVIEW 2026 wrote** (`tests/fixtures/labview2026/*.dat`, LabVIEW 2026 Community
  26.3.1f1 on this PC, 2026-10-15): `scripts/capture-labview-datalogs.ps1` runs fifteen vi.lib VIs
  and the shipped example `Fixed-Point Cast.vi` unmodified through the ActiveX VI Server with
  front-panel logging at finish (every VI hashed before and after, unchanged). The datalog files
  start with LabVIEW's table of the panel's type descriptors. `tests/test_labview_datalogs.py`
  parses every leaf entry (Booleans, I16, I32, U8, I8, strings, paths, enums, variants, refnums,
  time stamps, fixed-point numbers, most with names) and writes each back byte for byte;
  rebuilds every array and cluster in the nested form (the table names elements by index; the
  rebuild is test code, labelled) and checks it parses to its parsed elements and writes back
  exactly; pins the error cluster, 1D and 2D arrays, an EnumU16 and a file refnum. Typedef
  entries are refused by name: their inner length word does not match the bytes they occupy.
- **LabVIEW's own type-descriptor VIs** (`vi.lib/Utility/GetType.llb`, LabVIEW 2026):
  `scripts/capture-labview-gettype.ps1` calls `TD_Get Array/Cluster/Enum/Unit/StringLike
  Information`, `TD_Get Ref Info`, `TD_Create Cluster` and `TD_Create Array` on 25 hand-written
  descriptors (`scripts/make_gettype_jobs.py`, labelled hand-written; NI's examples among them).
  `tests/test_labview_gettype.py`: LabVIEW's reading of ranks, dimensions, element offsets,
  element counts, enum items, units, string sizes and refnum kinds equals this library's, and
  the clusters and arrays LabVIEW builds (named and unnamed) are exactly what `to_bytes` writes.

Defects of 0.2.0 found against this truth: names were dropped, so `to_bytes(parse(x)) != x` for
every named descriptor LabVIEW wrote (almost all of them) although the README promised
inverses; a child descriptor could run past its parent; enums, units, variants and time stamps
were refused; deep nesting raised `RecursionError`; `to_bytes` raised `OverflowError` or wrote
invalid bytes for out-of-range values.

## API review (items 1 to 5)

Kept: every 0.2.0 name with its signature. Changed for 1.0.0 (CHANGELOG 1.0.0 and the GUIDE's
"Upgrading from 0.2"): `label` and `flags` on every node (keyword-only, `flags` out of equality
as NI advises), `Refnum.subtype` now a property, new `LVEnum`, `PhysicalQuantity`, `LVVariant`,
`Waveform` and `MAX_DEPTH`, stricter reading, `TypeError` for non-bytes input and malformed
trees, checked writing, `pretty` with names, a bounded command line with `python -m`.
`TypeDescError` (a `ValueError`, `__module__` `lvtypedesc`) covers data; messages name offsets,
codes and limits, type names cut to 40 characters. Every public name has a runnable example;
`tests/test_docs.py` runs every module's doctests, the README and GUIDE `pycon` blocks and the
five command transcripts. `mypy --strict src tests scripts` is clean; no `Any` in the public API.

## Author mutation round (item 18)

Each mutation was applied alone to a fresh copy of the branch at a35133f on Elena's PC
(Python 3.14.2), the suite run with `-x`, no bytecode, the end-to-end module excluded (the
command line is also covered in process); the suite was green before. 40 mutations: 38 killed
at once; P06 and D03 survived and were killed by contracts added afterwards (re-applied and
confirmed killed).

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| P01 | length read little-endian | `_readers.py` | killed | `tests/test_cli.py::test_decode_prints_the_readable_type` |
| P02 | length below the header accepted | `_readers.py` | killed | `tests/test_parse.py::test_length_word_below_header_raises` |
| P03 | child may run past its parent | `_readers.py` | killed | `tests/test_promises_parse.py::test_a_child_may_not_run_past_its_parent` |
| P04 | code and flags swapped | `_readers.py` | killed | `tests/test_cli.py::test_decode_prints_the_readable_type` |
| P05 | name alignment inverted | `_readers.py` | killed | `tests/test_cli.py::test_decode_tree_matches_pretty` |
| P06 | name overrun check off by one | `_readers.py` | survived, then killed | `tests/test_promises_parse.py::test_a_name_running_past_its_descriptor_raises[0008 4003 0461 6263]` |
| P07 | Pascal string loses its first character | `_readers.py` | killed | `tests/test_cli.py::test_decode_tree_matches_pretty` |
| P08 | large sizes read as variable | `_readers.py` | killed | `tests/test_promises_emit.py::test_parsing_the_written_bytes_gives_the_tree_back` |
| P09 | unit exponent read unsigned | `_readers.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._nodes]` |
| P10 | name read without the flag | `_parser.py` | killed | `tests/test_promises_parse.py::test_without_bit_0x40_trailing_bytes_are_not_a_name` |
| P11 | depth limit one level late | `_parser.py` | killed | `tests/test_promises_parse.py::test_nesting_deeper_than_max_depth_raises` |
| P12 | opaque payload loses its last byte | `_parser.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._describe]` |
| P13 | unit pair swapped | `_parser.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._nodes]` |
| P14 | dimensions reversed | `_parser.py` | killed | `tests/test_docs.py::test_pycon_examples_run_and_print_what_they_show[GUIDE.md]` |
| P15 | memoryview refused | `_parser.py` | killed | `tests/test_promises_parse.py::test_accepts_every_bytes_like_input[memoryview]` |
| C01 | Boolean16 read as a scalar | `_codes.py` | killed | `tests/test_promises_emit.py::test_parsing_the_written_bytes_gives_the_tree_back` |
| C02 | EnumU32 dropped | `_codes.py` | killed | `tests/test_docs.py::test_pycon_examples_run_and_print_what_they_show[GUIDE.md]` |
| C03 | Set no longer refused by name | `_codes.py` | killed | `tests/test_promises_parse.py::test_known_but_unsupported_codes_are_refused_by_name[115-Set]` |
| E01 | wrong name flag written | `_emit.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._emit]` |
| E02 | name not aligned | `_emit.py` | killed | `tests/test_promises_emit.py::test_parsing_the_written_bytes_gives_the_tree_back` |
| E03 | opaque payload padded | `_emit.py` | killed | `tests/test_fuzz.py::test_mutated_real_descriptors_only_raise_type_desc_error[2]` |
| E04 | length limit off by one | `_emit.py` | killed | `tests/test_promises_emit.py::test_values_that_do_not_fit_raise[tree19-65536 bytes does not fit]` |
| E05 | size 0xFFFFFFFF accepted | `_emit.py` | killed | `tests/test_promises_emit.py::test_values_that_do_not_fit_raise[tree3-size must be VARIABLE]` |
| E06 | 256-byte text accepted | `_emit.py` | killed | `tests/test_promises_emit.py::test_values_that_do_not_fit_raise[tree8-item of 256 bytes is longer than 255]` |
| E07 | unit written swapped | `_emit.py` | killed | `tests/test_fuzz.py::test_mutated_real_descriptors_only_raise_type_desc_error[4]` |
| E08 | code and class check dropped | `_emit.py` | killed | `tests/test_promises_emit.py::test_a_code_must_fit_the_class` |
| E09 | count limit off by one | `_emit.py` | killed | `tests/test_promises_emit.py::test_values_that_do_not_fit_raise[tree5-65536 dimensions do not]` |
| K01 | tree depth limit one level late | `_check.py` | killed | `tests/test_promises_render.py::test_every_function_takes_max_depth_and_refuses_more[describe]` |
| K02 | bool accepted as an int | `_check.py` | killed | `tests/test_promises_render.py::test_malformed_trees_raise_type_error` |
| K03 | type names not cut | `_check.py` | killed | `tests/test_promises_render.py::test_long_type_names_are_cut_in_messages` |
| D01 | exponent 1 printed | `_describe.py` | killed | `tests/test_docs.py::test_pycon_examples_run_and_print_what_they_show[GUIDE.md]` |
| D02 | time stamp subtype wrong | `_describe.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._describe]` |
| D03 | rank 0 shown as 1D | `_describe.py` | survived, then killed | `tests/test_promises_render.py::test_a_rank_zero_array_reads_as_such` |
| R01 | names not quoted | `_pretty.py` | killed | `tests/test_cli.py::test_decode_tree_matches_pretty` |
| R02 | field positions counted from 1 | `_pretty.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._pretty]` |
| N01 | subtype read little-endian | `_nodes.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._describe]` |
| N02 | flags compared | `_model.py` | killed | `tests/test_docs.py::test_module_doctests_pass[lvtypedesc._model]` |
| L01 | data errors exit 0 | `_cli.py` | killed | `tests/test_cli.py::test_bad_hex_is_a_data_error_that_never_echoes_it` |
| L02 | messages not cut | `_cli_io.py` | killed | `tests/test_cli.py::test_usage_errors_do_not_echo_huge_arguments` |
| L03 | --tree ignored | `_cli.py` | killed | `tests/test_cli.py::test_decode_tree_matches_pretty` |
