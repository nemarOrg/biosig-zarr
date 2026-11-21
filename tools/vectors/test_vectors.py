"""Check the conformance vectors with stock zarr-python and no other reader code.

Run from the repository root:

    uv run --project tools/vectors pytest tools/vectors -q
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import zarr

CONFORMANCE = Path(__file__).resolve().parents[2] / "conformance"
MANIFEST = json.loads((CONFORMANCE / "manifest.json").read_text(encoding="utf-8"))
VECTORS = MANIFEST["vectors"]
BY_ID = {vector["id"]: vector for vector in VECTORS}
VALID = [vector for vector in VECTORS if vector["class"] == "valid"]
DERIVED = [vector for vector in VECTORS if "derived_from" in vector]
FORMAT_NAMES = {"biosig-zarr", "biosigio-zarr"}


def ids(vectors: list[dict]) -> list[str]:
    return [vector["id"] for vector in vectors]


def store_path(vector: dict) -> Path:
    return CONFORMANCE / vector["path"]


def test_manifest_shape() -> None:
    assert isinstance(VECTORS, list)
    assert len(BY_ID) == len(VECTORS), "vector ids must be unique"
    for vector in VECTORS:
        assert vector["class"] in {"valid", "invalid"}
        assert vector["layer"] is None or vector["layer"] in {1, 2, 3, 4}
        assert "2" in vector["expect"]
        outcome = vector["expect"]["2"]["outcome"]
        assert (outcome == "accept") == (vector["class"] == "valid")


@pytest.mark.parametrize("vector", VECTORS, ids=ids(VECTORS))
def test_digests(vector: dict) -> None:
    """Every file of a vector is listed, and its SHA-256 matches the manifest."""
    store = store_path(vector)
    found = {
        path.relative_to(store).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in store.rglob("*")
        if path.is_file()
    }
    assert found == vector["files"]


def pointer_parts(pointer: str) -> list[str]:
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]


def apply_patch(document: dict, patch: list[dict]) -> dict:
    result = json.loads(json.dumps(document))
    for operation in patch:
        *parents, last = pointer_parts(operation["path"])
        node = result
        for part in parents:
            node = node[part]
        if operation["op"] == "remove":
            del node[last]
        else:
            node[last] = operation["value"]
    return result


@pytest.mark.parametrize("vector", DERIVED, ids=ids(DERIVED))
def test_one_recorded_alteration(vector: dict) -> None:
    """A derived vector is its base store with exactly the recorded patch applied."""
    base = BY_ID[vector["derived_from"]]
    document = vector["alteration"]["document"]
    changed = {name for name in vector["files"] if vector["files"][name] != base["files"].get(name)}
    assert set(vector["files"]) == set(base["files"])
    assert changed == {document}
    before = json.loads((store_path(base) / document).read_text(encoding="utf-8"))
    after = json.loads((store_path(vector) / document).read_text(encoding="utf-8"))
    assert after == apply_patch(before, vector["alteration"]["patch"])


def child(parent: zarr.Group, name: str) -> Any:
    """A child node, found by the name an attribute gives it."""
    return parent[name]


def read_physical(store: Path) -> dict:
    """Open a store with zarr-python, navigate by attributes, and dequantize level 0."""
    root = zarr.open_group(store, mode="r")
    root_attrs: dict[str, Any] = dict(root.attrs)
    assert root_attrs["format"] in FORMAT_NAMES
    assert root_attrs["format_version"] == 2
    groups = {}
    for name in root_attrs["channel_groups"]:
        group = child(root, name)
        attrs: dict[str, Any] = dict(group.attrs)
        level0 = child(group, "0")
        digital = np.asarray(level0[:])
        assert digital.dtype == np.dtype(str(root_attrs["dtype"]))
        scale = np.asarray(level0.attrs["scale"], dtype=np.float64)
        offset = np.asarray(level0.attrs["offset"], dtype=np.float64)
        rows = {}
        for channel in attrs["channels"]:
            row = channel["row_index"]
            rows[row] = digital[row].astype(np.float64) * scale[row] + offset[row]
        for level in attrs["view_levels"]:
            view = child(child(group, "view"), str(level))
            assert view.shape[:2] == (2, attrs["n_channels"])
        groups[name] = rows
    events = child(root, "events")
    n_events = events.attrs["n_events"]
    if n_events == 0:
        assert list(events.array_keys()) == []
    return {"groups": groups, "n_events": n_events}


@pytest.mark.parametrize("vector", VALID, ids=ids(VALID))
def test_valid_vector_matches_goldens(vector: dict) -> None:
    golden = json.loads((CONFORMANCE / vector["expect"]["2"]["goldens"]).read_text("utf-8"))
    read = read_physical(store_path(vector))
    assert read["n_events"] == golden["events"]["n_events"]
    assert set(read["groups"]) == set(golden["groups"])
    for name, group in golden["groups"].items():
        assert set(read["groups"][name]) == {c["row_index"] for c in group["channels"]}
        for channel in group["channels"]:
            physical = read["groups"][name][channel["row_index"]]
            expected = np.asarray(channel["physical"], dtype=np.float64)
            assert physical.shape == (group["n_samples"],)
            np.testing.assert_array_equal(physical, expected)


def test_goldens_trace_to_the_source() -> None:
    """The golden values lie within half a quantization step of the source recording."""
    for vector in VALID:
        golden = json.loads((CONFORMANCE / vector["expect"]["2"]["goldens"]).read_text("utf-8"))
        for group in golden["groups"].values():
            for channel in group["channels"]:
                error = np.abs(
                    np.asarray(channel["physical"]) - np.asarray(channel["source_physical"])
                )
                assert error.max() <= channel["max_abs_error"] * (1 + 1e-9)
