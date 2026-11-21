"""Check the conformance vectors with stock zarr-python and no other reader code.

Run from the repository root:

    uv run --project tools/vectors pytest tools/vectors -q
"""

from __future__ import annotations

import hashlib
import json
import math
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
        assert str(vector["format_version"]) in vector["expect"]
        assert "3" in vector["expect"], "every vector has an outcome for a version 3 reader"
        outcome = vector["expect"][str(vector["format_version"])]["outcome"]
        assert (outcome == "accept") == (vector["class"] == "valid")
    for layer in (1, 2, 3, 4):
        assert any(vector["layer"] == layer for vector in VECTORS), f"no vector for layer {layer}"


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
        node: Any = result
        for part in parents:
            node = node[int(part)] if isinstance(node, list) else node[part]
        if isinstance(node, list):
            if operation["op"] == "remove":
                del node[int(last)]
            elif operation["op"] == "add":
                node.insert(len(node) if last == "-" else int(last), operation["value"])
            else:
                node[int(last)] = operation["value"]
        elif operation["op"] == "remove":
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


def round_half_up(x: float) -> int:
    """round(x) as the text defines it: floor(x + 0.5), in 64-bit floating point."""
    return math.floor(x + 0.5)


def acquired(intervals: list[dict], n_samples: int) -> np.ndarray:
    mask = np.zeros(n_samples, dtype=bool)
    for interval in intervals:
        mask[interval["start"] : interval["stop"]] = True
    return mask


def read_store(store: Path) -> dict:
    """Open a store with zarr-python as a reader of the version 3 text does: navigate by
    attributes, read version 2 with the defaults of "Reading earlier versions", dequantize
    with the text's formula, and return a missing or not acquired sample as NaN."""
    root = zarr.open_group(store, mode="r")
    root_attrs: dict[str, Any] = dict(root.attrs)
    assert root_attrs["format"] in FORMAT_NAMES
    version = root_attrs["format_version"]
    assert version in (2, 3)
    groups: dict[str, dict] = {}
    for name in root_attrs["channel_groups"]:
        group = child(root, name)
        attrs: dict[str, Any] = dict(group.attrs)
        level0 = child(group, "0")
        n_samples = attrs["n_samples"]
        if version == 3:
            assert attrs["kind"] == "uniform"
            start_time = attrs["start_time"]
            intervals = attrs["valid_intervals"]
            missing = level0.attrs["missing_value"]
        else:
            assert digital_type(level0) == np.dtype(str(root_attrs["dtype"]))
            start_time, missing = 0, None
            intervals = [{"start": 0, "stop": n_samples, "source_time": 0}]
        digital = np.asarray(level0[:])
        scale = np.asarray(level0.attrs["scale"], dtype=np.float64)
        offset = np.asarray(level0.attrs["offset"], dtype=np.float64)
        mask = acquired(intervals, n_samples)
        rows = {}
        for channel in attrs["channels"]:
            row = channel["row_index"]
            physical = digital[row].astype(np.float64) * scale[row] + offset[row]
            present = mask if missing is None else mask & (digital[row] != missing)
            rows[row] = np.where(present, physical, np.nan)
        views = {}
        for level in attrs["view_levels"]:
            view = child(child(group, "view"), str(level))
            assert view.shape[:2] == (2, attrs["n_channels"])
            views[level] = (np.asarray(view[:]), view.attrs["downsample_factor"])
        groups[name] = {
            "kind": "uniform",
            "rate": attrs["rate"],
            "start_time": start_time,
            "n_samples": n_samples,
            "intervals": intervals,
            "missing": missing,
            "digital": digital,
            "rows": rows,
            "views": views,
        }
    for name in root_attrs.get("timestamped_groups", []) if version == 3 else []:
        group = child(root, name)
        attrs = dict(group.attrs)
        assert attrs["kind"] == "timestamped"
        values = child(group, "values")
        digital = np.asarray(values[:])
        scale = np.asarray(values.attrs["scale"], dtype=np.float64)
        offset = np.asarray(values.attrs["offset"], dtype=np.float64)
        missing = values.attrs["missing_value"]
        rows = {}
        for channel in attrs["channels"]:
            row = channel["row_index"]
            physical = digital[row].astype(np.float64) * scale[row] + offset[row]
            rows[row] = (
                physical if missing is None else np.where(digital[row] != missing, physical, np.nan)
            )
        time = np.asarray(child(group, "time")[:])
        time_index = np.asarray(child(group, "time_index")[:])
        np.testing.assert_array_equal(time_index, time[:: attrs["chunk_samples"]])
        groups[name] = {
            "kind": "timestamped",
            "nominal_rate": attrs["nominal_rate"],
            "n_samples": attrs["n_samples"],
            "time": time,
            "rows": rows,
        }
    events = child(root, "events")
    n_events = events.attrs["n_events"]
    if n_events == 0:
        assert list(events.array_keys()) == []
        onsets = durations = codes = []
    else:
        onsets = np.asarray(child(events, "onset")[:]).tolist()
        durations = np.asarray(child(events, "duration")[:]).tolist()
        codes = np.asarray(child(events, "code")[:]).tolist()
    return {
        "groups": groups,
        "events": {"n_events": n_events, "onset": onsets, "duration": durations, "code": codes},
    }


def digital_type(array: Any) -> np.dtype:
    return np.dtype(str(array.dtype))


def as_array(values: list) -> np.ndarray:
    return np.asarray([np.nan if v is None else v for v in values], dtype=np.float64)


READS = [
    (vector, key)
    for vector in VECTORS
    for key in sorted(vector["expect"])
    if "goldens" in vector["expect"][key]
]


@pytest.mark.parametrize(
    ("vector", "key"), READS, ids=[f"{vector['id']}-reader-{key}" for vector, key in READS]
)
def test_read_matches_goldens(vector: dict, key: str) -> None:
    """Every store a reader accepts reads as its goldens, missing samples as missing."""
    golden = json.loads((CONFORMANCE / vector["expect"][key]["goldens"]).read_text("utf-8"))
    read = read_store(store_path(vector))
    assert read["events"]["n_events"] == golden["events"]["n_events"]
    for member in ("onset", "duration", "code"):
        if member in golden["events"]:
            assert read["events"][member] == golden["events"][member]
    uniform = {n for n, g in read["groups"].items() if g["kind"] == "uniform"}
    assert uniform == {
        n for n, g in golden["groups"].items() if g.get("kind", "uniform") == "uniform"
    }
    assert set(read["groups"]) == set(golden["groups"])
    for name, group in golden["groups"].items():
        assert set(read["groups"][name]["rows"]) == {c["row_index"] for c in group["channels"]}
        if "time" in group:
            np.testing.assert_array_equal(read["groups"][name]["time"], np.asarray(group["time"]))
        for channel in group["channels"]:
            physical = read["groups"][name]["rows"][channel["row_index"]]
            assert physical.shape == (group["n_samples"],)
            np.testing.assert_array_equal(physical, as_array(channel["physical"]))


def test_goldens_trace_to_the_source() -> None:
    """The golden values lie within half a quantization step of the values that were
    quantized: the source recording, or for a resampled channel the filter's output."""
    for path in sorted((CONFORMANCE / "goldens").glob("*.json")):
        golden = json.loads(path.read_text("utf-8"))
        for group in golden["groups"].values():
            for channel in group["channels"]:
                physical = as_array(channel["physical"])
                reference = as_array(channel.get("unquantized", channel["source_physical"]))
                assert np.array_equal(np.isnan(physical), np.isnan(reference))
                error = np.abs(physical - reference)[~np.isnan(physical)]
                assert error.max() <= channel["max_abs_error"] * (1 + 1e-9)
                if "resampled" not in channel.get("derivation", []):
                    source = as_array(channel["source_physical"])
                    np.testing.assert_array_equal(reference, source)


V3_READ = [
    vector
    for vector in VECTORS
    if vector["expect"]["3"].get("goldens") and vector["path"].startswith("stores/v3/")
]


@pytest.mark.parametrize("vector", V3_READ, ids=ids(V3_READ))
def test_views_and_the_mask_rule(vector: dict) -> None:
    """Each view column holds the minimum and maximum of the acquired, non-missing level-0
    samples it covers; a column the mask rule excludes holds the missing value in both rows;
    and the columns the mask rule excludes are those the manifest names."""
    expected = vector["expect"]["3"]["groups"]
    for name, group in read_store(store_path(vector))["groups"].items():
        if group["kind"] != "uniform":
            continue
        mask = acquired(group["intervals"], group["n_samples"])
        digital, missing = group["digital"], group["missing"]
        for level, (view, factor) in group["views"].items():
            empty = []
            for j in range(view.shape[2]):
                window = slice(j * factor, (j + 1) * factor)
                covered = any(
                    i["start"] < (j + 1) * factor and i["stop"] > j * factor
                    for i in group["intervals"]
                )
                if not covered:
                    empty.append(j)
                    assert (view[:, :, j] == missing).all()
                for c in range(digital.shape[0]):
                    values = digital[c, window]
                    values = values[mask[window] & (values != missing)]
                    if values.size:
                        assert (view[0, c, j], view[1, c, j]) == (values.min(), values.max())
                    else:
                        assert (view[:, c, j] == missing).all()
            assert empty == expected[name]["view_empty_columns"][str(level)]


@pytest.mark.parametrize("vector", V3_READ, ids=ids(V3_READ))
def test_onsets_to_samples(vector: dict) -> None:
    """The manifest's onsets are the store's, and each maps to the manifest's sample by the
    text's rules: round((onset - start_time) * rate) inside a valid interval for a uniform
    group; the first time at or after the onset, within 1 / nominal_rate, for a
    timestamped group."""
    read = read_store(store_path(vector))
    samples = vector["expect"]["3"]["events"]["samples"]
    for name in {s["group"] for s in samples}:
        assert [s["onset"] for s in samples if s["group"] == name] == read["events"]["onset"]
    for entry in samples:
        group = read["groups"][entry["group"]]
        onset = entry["onset"]
        if group["kind"] == "uniform":
            i = round_half_up((onset - group["start_time"]) * group["rate"])
            inside = 0 <= i < group["n_samples"] and any(
                v["start"] <= i < v["stop"] for v in group["intervals"]
            )
            assert entry["sample"] == (i if inside else None)
        else:
            later = np.nonzero(group["time"] >= onset)[0]
            sample = int(later[0]) if later.size else None
            rate = group["nominal_rate"]
            if (
                sample is not None
                and rate is not None
                and group["time"][sample] - onset >= 1 / rate
            ):
                sample = None
            assert entry["sample"] == sample


def test_the_ties_are_exact() -> None:
    """The onsets that test the ties of round are exact halves in 64-bit floating point."""
    gap = BY_ID["v3-gap-10hz"]
    rate = gap["expect"]["3"]["groups"]["eeg_10hz"]
    assert rate["start_time"] == 0.0
    ties = [s["onset"] for s in gap["expect"]["3"]["events"]["samples"] if s["onset"] != 2.02]
    for onset in ties:
        x = (onset - 0.0) * 10.0
        assert x - math.floor(x) == 0.5
        assert round(x) != round_half_up(x), "a round-half-to-even reader must differ"


def shard_index(path: Path, chunks_per_shard: int) -> np.ndarray:
    """The (offset, length) pairs at the end of a shard: index_location end, bytes and crc32c."""
    data = path.read_bytes()
    size = chunks_per_shard * 16
    return np.frombuffer(data[-(size + 4) : -4], dtype="<u8").reshape(chunks_per_shard, 2)


@pytest.mark.parametrize("vector", V3_READ, ids=ids(V3_READ))
def test_no_chunk_wholly_in_a_gap(vector: dict) -> None:
    """A writer MUST NOT write a shard or an inner chunk that lies wholly outside the
    valid intervals; the sharding codec marks an absent inner chunk in its index."""
    store = store_path(vector)
    for name, group in read_store(store)["groups"].items():
        if group["kind"] != "uniform":
            continue
        metadata = json.loads((store / name / "0" / "zarr.json").read_text("utf-8"))
        sharding = metadata["codecs"][0]["configuration"]
        assert sharding["index_location"] == "end"
        shard = metadata["chunk_grid"]["configuration"]["chunk_shape"][1]
        chunk = sharding["chunk_shape"][1]
        mask = acquired(group["intervals"], group["n_samples"])
        for s in range(math.ceil(group["n_samples"] / shard)):
            path = store / name / "0" / "c" / "0" / str(s)
            if not mask[s * shard : (s + 1) * shard].any():
                assert not path.exists()
                continue
            index = shard_index(path, shard // chunk)
            for k in range(shard // chunk):
                start = s * shard + k * chunk
                if not mask[start : start + chunk].any():
                    assert (index[k] == np.iinfo(np.uint64).max).all()
