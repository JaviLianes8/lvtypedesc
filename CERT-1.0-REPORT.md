# lvtypedesc 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.0, 1221d48)
- [x] Baseline gates run on 0.2.0
- [x] Real LabVIEW 2026 captures and NI sources (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0 (items 8, 10, 13, 14)
- [x] Five QA lenses report PASS (item 19)
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

Kept: every 0.2.0 name; signatures unchanged except `Refnum` (its `subtype` field became a
property read from `payload`, and `payload` is keyword-only). Changed for 1.0.0 (CHANGELOG
1.0.0 and the GUIDE's "Upgrading from 0.2"): `label` and `flags` on every node (keyword-only,
`flags` out of equality as NI advises, `label` compared), new `LVEnum`, `PhysicalQuantity`,
`LVVariant`, `Waveform` and `MAX_DEPTH`, stricter reading (at most 65535 bytes, through the
buffer protocol), `TypeError` for non-bytes input and malformed trees, one set of checks for
`to_bytes`, `describe` and `pretty` (exact built-in field types, a node's `name` must be its
code's name, values that fit their fields, a lower bound of the encoded size at most 65535
bytes), `pretty` with names, a bounded command line with `python -m`. Public classes carry
`__module__` `lvtypedesc`.
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

## Packaging and end-to-end (items 8, 10, 13, 14), lens d at d3eeed9

- `python -m build` and `twine check --strict`: both PASSED. Wheel: the package, `py.typed`,
  LICENSE, the console entry point. Sdist: `src`, `tests` with the sixteen LabVIEW 2026 datalogs,
  `gettype.json` and their manifest, the sources manifest only (the fetched NI and wiki copies
  are excluded even when present), README, GUIDE, CHANGELOG, CONTRIBUTING, LICENSE, pyproject.
- The wheel in a fresh venv on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, the suite
  run from the extracted sdist with `src` removed against the installed wheel: green on every
  interpreter (9 source tests skip without the fetched copies; on 3.10 one more, tomllib).
- The console script, `python -m lvtypedesc`, every `--help` example, exit codes 0/1/2 by
  subprocess; a `mypy --strict` consumer of all 22 public names against the installed wheel.
- PyPI 0.2.0 installed, then upgraded in place: `pip check` clean, no stale files; 101 behaviour
  differences over about 120 probes, every one stated in CHANGELOG 1.0.0 or the GUIDE's upgrade
  section after the round-2 fixes.

## Independent QA lenses (item 19)

Each lens was a fresh, independent review that read the certification checklist first, ran
things rather than reading them, and reported back only.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | c9c85ee | FAIL (2 medium, 6 low, 2 info) | a node's `name` could contradict its code and break the round-trip promise; equality now compares `label` (undocumented); `pretty` changed the refnum text; wording of the 0.2 echo; huge ints gave `ValueError` in rendering; bare `TypeDesc` inconsistent; positional `Refnum` payload failed late; parsing copied all input; docs named private `main`; module paths in pickles. Fixed in 1a523db |
| a | 2 | 1a523db | PASS (3 info) | all ten fixed; error wording and a bare assert polished in 85dd115; `FixedPoint.payload` stays positional (0.2 compatibility) |
| b. Correctness and ground truth | 1 | ac9f4a5 | PASS (2 low, 1 info) | NI's six examples, 172 leaves from 17 more shipped VIs (U8 to CDB, units, enums, analog and digital waveforms, queue and notifier refnums) and GetType.llb answers on new descriptors all agree, byte for byte; the repo's capture scripts reproduce the fixtures. Low: names are the system code page, not Latin-1 text; bytes left after the fields are dropped silently. Documented and pinned by contracts in 3f0f037 |
| c. Adversarial and robustness | 1 | 3f0f037 | FAIL (2 medium, 6 low) | 3.06 million fuzz cases, only `TypeDescError`; shared subtrees took exponential time; the command line failed silently on an ASCII console; lying `int`/`tuple`/`bytes` subclasses leaked `ValueError`/`OverflowError` or wrote wrong bytes; control characters in usage errors; memoryview read bound. Fixed in d484425 |
| c | 2 | d484425, 78926fc, 03e390a | FAIL, then PASS | the node cap did not bound wide nodes (65535 units per node, minutes of work); replaced by a lower bound of the encoded size counted from lengths (78926fc), then enum items counted at full length (03e390a). 1.4 million more fuzz cases, closed pipes, hostile sweep: PASS |
| d. Packaging and real e2e | 1 | d3eeed9 | PASS (4 low) | above; low: 0.2 nesting wording, bare `TypeDesc` error change missing from the upgrade notes, `release.ps1` ignored exit codes, CRLF working tree. Fixed in ae77b7f and 0c74c77 |
| d | 2 | ae77b7f | PASS | fixes confirmed |
| e. Contract strength (blind) | 1 | 0c74c77 | FAIL | 139 mutations: 115 killed (2 only by a timeout), 6 equivalent, 18 survived (exact limits, closed-output exit codes, message wording, the size bound, positional API). Contracts in `tests/test_contract_strength.py` (28256a0) |
| e | 2 | 28256a0 | PASS | all 18 survivors and the 2 timeout kills re-applied and killed in about 2 s each; the costly hostile tests now check the size bound first (231d235) |

Equivalent mutations argued by lens e: `sorted()` over a table written in code order; the range
guard before `dict.get`; masking a size already checked; an unreachable `SystemExit` fallback;
the 300-character cut on CLI data errors (every reachable message is under 80 characters); the
`_print_message` stream choice (no path reaches it with stderr).

## Independent reviewer (item 16)

| Review | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- |
| 1 | 42a89db | FAIL (items 6, 17, 18) | gates alone, docs, packaging, upgrade from 0.2.0, hygiene of tree and history all clean; 8 report mutations re-applied (7 killed as recorded, one variant survived); 40 new mutations: 31 killed, 1 equivalent (enum sum guard at twice the limit), 8 survived (enum and array counts above 255, unit pairs of the wrong length, the second dimension unchecked, dimensions and units counted at 2 bytes, size 0 shown as variable, names aligned on absolute offsets, the 300-character cut raised tenfold). One report line named the factory's rules file and blocked the trace guard. Fixed: report reworded (guard CLEAN), contracts in `tests/test_contract_strength.py` (0744209; all 9 re-applied and killed), name alignment stated in the GUIDE and a notice added to the capture manifest (55a6592) |

## Decisions for the maintainer

- Typedefs (`0xF1`) are refused: in LabVIEW 2026's datalogs the inner length word of a typedef
  does not match the bytes it occupies (two reviewers confirmed), so no layout is guessed.
- Fixed-point, refnum and waveform descriptors keep their bytes (an appended name included) in
  `payload`; their layout is version-specific and unpublished.
- Names and enum items map one byte to one character (Latin-1) so every byte round-trips;
  LabVIEW writes the system code page, and the GUIDE shows how to re-decode.
- Bytes left inside a descriptor after its fields and name are ignored, not written back.
- `FixedPoint.payload` stays positional (as in 0.2.0); `Refnum` and `Waveform` take it by keyword.
- LabVIEW 2026 is the only version captured; NI says codes may change between versions.
- The LabVIEW captures (sixteen datalogs, about 15 KB, and the GetType answers) ship in the
  sdist as test fixtures with their manifest; the fetched NI and wiki pages stay local.
- GUIDE.md and this report are longer than 200 lines; the rule applies to source and test files,
  and `tests/test_packaging.py` enforces it for them.
