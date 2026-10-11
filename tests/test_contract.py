import importlib.resources

import lvtypedesc

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "VARIABLE",
    "Array",
    "Boolean",
    "Category",
    "Cluster",
    "LVString",
    "Scalar",
    "TypeDesc",
    "TypeDescError",
    "describe",
    "parse_type_descriptor",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvtypedesc.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvtypedesc.__all__:
        assert hasattr(lvtypedesc, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvtypedesc.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvtypedesc").joinpath("py.typed").is_file()
