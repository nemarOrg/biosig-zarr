"""Build the biosig-zarr conformance vectors from one real CC0 recording.

This is a one-purpose builder, not a library: it exports nothing, and nothing
outside ``tools/`` imports it. Run it from the repository root:

    uv run --project tools/vectors python tools/vectors/build.py all --work DIR

Steps, each also a subcommand:

- ``crop``: download the source recording and its channels sidecar, check them
  against the recorded size and SHA-256, and cut the crop into ``DIR/crop``.
- ``write``: run biosigIO 1.2.13 (through ``uvx``) on the crop, and copy its
  output unchanged to ``conformance/stores/v2/v2-legacy-name.zarr``.
- ``derive``: alter that store's root metadata document, one change per vector;
  derive the version 1 vector from it the same way; write the format version 3
  vectors from the crop with zarr-python and NumPy (no writer of version 3
  exists), and alter them, one change per vector; write the goldens and
  ``conformance/manifest.json``; format the JSON this script wrote (not the
  stores) with Biome. It does not run the version 2 writer.

``conformance/SOURCES.md`` records every step and every alteration in prose.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from zarr.codecs import BloscCodec, BytesCodec

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / "conformance"
STORES_V1 = CONFORMANCE / "stores" / "v1"
STORES_V2 = CONFORMANCE / "stores" / "v2"
STORES_V3 = CONFORMANCE / "stores" / "v3"
GOLDENS = CONFORMANCE / "goldens"
MANIFEST = CONFORMANCE / "manifest.json"
SCHEMA_BASE = "https://w3id.org/biosig-zarr/schemas/v2/"

USER_AGENT = "biosig-zarr-conformance-builder/1 (+https://github.com/nemarOrg/biosig-zarr)"
SOURCE_BASE = "https://data.nemar.org/on009081/v1.0.0/sub-01/eeg/"
SOURCE_EDF = "sub-01_task-rest_eeg.edf"
SOURCE_EDF_BYTES = 224464
SOURCE_EDF_SHA256 = "640a891838f31f1f4087098e288439c7a8d820aaa8d92ff185678f2b3b7f11bb"
SOURCE_TSV = "sub-01_task-rest_channels.tsv"
SOURCE_TSV_BYTES = 1270
SOURCE_TSV_SHA256 = "84c135dc9c357331ca9d64c703622c509ac238a5c2880dee55a483d3d8ce9c4e"

# The crop: these channels, in this order, and the first CROP_RECORDS data
# records (one second each in this file).
CROP_CHANNELS = ("Fp1-A1", "Fp2-A2", "O1-A1", "O2-A2", "Add_lead1")
CROP_RECORDS = 10

# The writer, pinned with the libraries it ran with when the vectors were made.
WRITER = [
    "uvx",
    "--python",
    "3.13",
    "--from",
    "biosigio[zarr]==1.2.13",
    "--with",
    "zarr==3.4.2",
    "--with",
    "numcodecs==0.17.1",
    "--with",
    "numpy==2.5.5",
    "--with",
    "pandas==3.1.1",
    "--with",
    "scipy==1.18.1",
    "--with",
    "pyedflib==0.1.42",
    "python",
    "-c",
    "import sys\n"
    "from biosigio import Recording\n"
    "rec = Recording.from_file(sys.argv[1])\n"
    "rec.to_zarr(sys.argv[2], exclude_subject_info=True)\n",
]

LEGACY = "v2-legacy-name"

# What a reader of the version 3 text reads in the version 2 stores: the values of
# "Reading earlier versions" (one interval, start_time 0, missing_value null,
# onset_source_basis unknown), so no attribute of layer 4 is in effect.
V2_GROUP_AS_V3 = {
    "start_time": 0,
    "valid_intervals": [{"start": 0, "stop": 1000, "source_time": 0}],
    "missing_value": None,
    "refuse_without": [],
    "view_empty_columns": {"1": []},
}
V2_READ_AS_V3 = {
    "outcome": "accept",
    "goldens": f"goldens/{LEGACY}.json",
    "uniform_groups": ["eeg_100hz", "misc_100hz"],
    "timestamped_groups": [],
    "groups": {"eeg_100hz": V2_GROUP_AS_V3, "misc_100hz": V2_GROUP_AS_V3},
    "events": {"onset_source_basis": "unknown", "samples": []},
}


# Every vector after the first is the legacy store with one JSON Patch applied
# to its root metadata document, ``zarr.json``.
DERIVED: list[dict[str, Any]] = [
    {
        "id": "v2-new-name",
        "class": "valid",
        "rule": "format-name",
        "patch": [{"op": "replace", "path": "/attributes/format", "value": "biosig-zarr"}],
        "expect": {"outcome": "accept", "goldens": f"goldens/{LEGACY}.json"},
        "layer": None,
        "expect3": V2_READ_AS_V3,
    },
    {
        "id": "v2-unknown-attribute",
        "class": "valid",
        "rule": "what-changes-the-version",
        "patch": [
            {
                "op": "add",
                "path": "/attributes/conformance_unknown_attribute",
                "value": {"note": "An attribute no reader recognizes."},
            }
        ],
        "expect": {"outcome": "accept", "goldens": f"goldens/{LEGACY}.json"},
        "layer": None,
        "expect3": V2_READ_AS_V3,
    },
    {
        "id": "v2-version-3",
        "class": "invalid",
        "description": (
            "Invalid because a version 2 reader MUST refuse a store whose format_version is "
            "greater than the highest version it implements (spec line 126), not because "
            "the store breaks another version 2 rule. A reader of the version 3 text may "
            "refuse it at the root, because it has no timestamped_groups (line 271 of the "
            "draft text), before it reaches "
            "layer 2; its refusal is not unique to layer 2, and v3-no-kind is the layer 2 case."
        ),
        "rule": "format-version",
        "patch": [{"op": "replace", "path": "/attributes/format_version", "value": 3}],
        "expect": {
            "outcome": "refuse",
            "schema_failure": {
                "schema": SCHEMA_BASE + "root.schema.json",
                "document": "zarr.json",
                "instance_path": "/attributes/format_version",
                "keyword": "const",
            },
        },
        "layer": None,
        "expect3": {
            "outcome": "refuse",
            "refusal": {"layer": 2, "rule": "reader-safety", "subject": "eeg_100hz"},
        },
    },
    {
        "id": "v2-unknown-format",
        "class": "invalid",
        "rule": "format-name",
        "patch": [{"op": "replace", "path": "/attributes/format", "value": "example-zarr"}],
        "expect": {
            "outcome": "refuse",
            "schema_failure": {
                "schema": SCHEMA_BASE + "root.schema.json",
                "document": "zarr.json",
                "instance_path": "/attributes/format",
                "keyword": "enum",
            },
        },
        "layer": None,
        "expect3": {
            "outcome": "refuse",
            "refusal": {"layer": None, "rule": "format-name", "subject": "format"},
        },
    },
    {
        "id": "v2-no-channel-groups",
        "class": "invalid",
        "rule": "root-attributes",
        "patch": [{"op": "remove", "path": "/attributes/channel_groups"}],
        "expect": {
            "outcome": "schema-invalid",
            "schema_failure": {
                "schema": SCHEMA_BASE + "root.schema.json",
                "document": "zarr.json",
                "instance_path": "/attributes",
                "keyword": "required",
            },
        },
        "layer": None,
    },
]
# The version 3 reader's outcome for v2-no-channel-groups is the version 2 one: the
# store does not conform, and the text states no reader outcome beyond that.
DERIVED[-1]["expect3"] = DERIVED[-1]["expect"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(name: str, size: int, digest: str, dest: Path) -> Path:
    """Download one source file, read only, and refuse it if it changed."""
    target = dest / name
    if not target.exists():
        request = urllib.request.Request(SOURCE_BASE + name, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
    data = target.read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        sys.exit(f"{name}: {len(data)} bytes, not the recorded source; stopping")
    return target


def crop_edf(source: Path, target: Path) -> None:
    """Keep CROP_CHANNELS and the first CROP_RECORDS records of an EDF file.

    Samples are copied as stored; the header is rewritten only where the crop
    changes it: the header length, the record count, the signal count, and the
    per-signal fields of the signals dropped.
    """
    data = source.read_bytes()
    header_bytes = int(data[184:192])
    n_records = int(data[236:244])
    ns = int(data[252:256])
    widths = [16, 80, 8, 8, 8, 8, 8, 80, 8, 32]
    fields: list[list[bytes]] = []
    offset = 256
    for width in widths:
        fields.append([data[offset + i * width : offset + (i + 1) * width] for i in range(ns)])
        offset += width * ns
    labels = [label.decode("ascii").strip() for label in fields[0]]
    samples = [int(n) for n in fields[8]]
    keep = [labels.index(name) for name in CROP_CHANNELS]
    if n_records < CROP_RECORDS:
        sys.exit("the crop is longer than the source")

    fixed = bytearray(data[:256])
    new_header_bytes = 256 + 256 * len(keep)
    fixed[184:192] = f"{new_header_bytes:<8}".encode("ascii")
    fixed[236:244] = f"{CROP_RECORDS:<8}".encode("ascii")
    fixed[252:256] = f"{len(keep):<4}".encode("ascii")
    signal_header = b"".join(b"".join(column[i] for i in keep) for column in fields)

    record_len = 2 * sum(samples)
    starts = [2 * sum(samples[:i]) for i in range(ns)]
    body = bytearray()
    for record in range(CROP_RECORDS):
        base = header_bytes + record * record_len
        for i in keep:
            body += data[base + starts[i] : base + starts[i] + 2 * samples[i]]
    target.write_bytes(bytes(fixed) + signal_header + bytes(body))


def crop_tsv(source: Path, target: Path) -> None:
    """Keep the header row and the rows of CROP_CHANNELS, in crop order."""
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = {line.split("\t", 1)[0]: line for line in lines[1:]}
    target.write_text(lines[0] + "".join(rows[name] for name in CROP_CHANNELS), "utf-8")


def edf_physical(path: Path) -> dict[str, np.ndarray]:
    """Physical values of every signal of an EDF file, by label, in float64."""
    data = path.read_bytes()
    header_bytes = int(data[184:192])
    n_records = int(data[236:244])
    ns = int(data[252:256])

    def field(offset: int, width: int) -> list[str]:
        start = 256 + offset * ns
        cells = [data[start + i * width : start + (i + 1) * width] for i in range(ns)]
        return [cell.decode().strip() for cell in cells]

    labels = field(0, 16)
    pmin = [float(v) for v in field(16 + 80 + 8, 8)]
    pmax = [float(v) for v in field(16 + 80 + 16, 8)]
    dmin = [float(v) for v in field(16 + 80 + 24, 8)]
    dmax = [float(v) for v in field(16 + 80 + 32, 8)]
    samples = [int(v) for v in field(16 + 80 + 40 + 80, 8)]
    record_len = sum(samples)
    digital = np.frombuffer(data[header_bytes:], dtype="<i2").reshape(n_records, record_len)
    out = {}
    start = 0
    for i, label in enumerate(labels):
        d = digital[:, start : start + samples[i]].reshape(-1).astype(np.float64)
        gain = (pmax[i] - pmin[i]) / (dmax[i] - dmin[i])
        out[label] = (d - dmin[i]) * gain + pmin[i]
        start += samples[i]
    return out


def do_crop(work: Path) -> Path:
    downloads = work / "source"
    crop = work / "crop"
    downloads.mkdir(parents=True, exist_ok=True)
    crop.mkdir(parents=True, exist_ok=True)
    edf = fetch(SOURCE_EDF, SOURCE_EDF_BYTES, SOURCE_EDF_SHA256, downloads)
    tsv = fetch(SOURCE_TSV, SOURCE_TSV_BYTES, SOURCE_TSV_SHA256, downloads)
    crop_edf(edf, crop / SOURCE_EDF)
    crop_tsv(tsv, crop / SOURCE_TSV)
    for path in sorted(crop.iterdir()):
        print(f"{path.name}  {path.stat().st_size} bytes  sha256 {sha256(path)}")
    return crop


def do_write(crop: Path) -> None:
    target = STORES_V2 / f"{LEGACY}.zarr"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{LEGACY}.zarr"
        subprocess.run([*WRITER, str(crop / SOURCE_EDF), str(out)], check=True)
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(out, target)


def store_files(store: Path) -> dict[str, str]:
    """SHA-256 of every file in a store, keyed by its path inside the store."""
    return {
        path.relative_to(store).as_posix(): sha256(path)
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }


def pointer_parts(pointer: str) -> list[str]:
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]


def apply_patch(document: dict, patch: list[dict]) -> dict:
    """Apply the add, replace and remove operations of a JSON Patch (RFC 6902)."""
    result = copy.deepcopy(document)
    for operation in patch:
        *parents, last = pointer_parts(operation["path"])
        node: Any = result
        for part in parents:
            node = node[int(part)] if isinstance(node, list) else node[part]
        op = operation["op"]
        if isinstance(node, list):
            if op == "add":
                node.insert(len(node) if last == "-" else int(last), operation["value"])
            elif op == "replace":
                node[int(last)] = operation["value"]
            elif op == "remove":
                del node[int(last)]
            else:
                raise ValueError(op)
        elif op in ("add", "replace"):
            if op == "replace" and last not in node:
                raise KeyError(operation["path"])
            node[last] = operation["value"]
        elif op == "remove":
            del node[last]
        else:
            raise ValueError(op)
    return result


def zarr_json_bytes(document: dict) -> bytes:
    """Serialize a metadata document the way zarr-python 3.4.2 does."""
    return json.dumps(document, indent=2).encode()


def derive_store(base: Path, target: Path, document: str, patch: list[dict]) -> None:
    """Copy a store and apply one JSON Patch to one of its metadata documents."""
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base, target)
    raw = (base / document).read_bytes()
    parsed = json.loads(raw)
    if zarr_json_bytes(parsed) != raw:
        sys.exit(f"{base.name}/{document} does not round-trip; stopping")
    (target / document).write_bytes(zarr_json_bytes(apply_patch(parsed, patch)))


def derive_vector(spec: dict) -> None:
    source = STORES_V2 / f"{LEGACY}.zarr"
    derive_store(source, STORES_V2 / f"{spec['id']}.zarr", "zarr.json", spec["patch"])


def child(parent: zarr.Group, name: str) -> Any:
    """A child node, found by the name an attribute gives it."""
    return parent[name]


def goldens(store: Path, crop: Path) -> dict:
    """Level-0 physical values of every channel, and the source values they came from."""
    source = edf_physical(crop / SOURCE_EDF)
    root = zarr.open_group(store, mode="r")
    root_attrs: dict[str, Any] = dict(root.attrs)
    groups = {}
    for name in root_attrs["channel_groups"]:
        group = child(root, name)
        attrs: dict[str, Any] = dict(group.attrs)
        level0 = child(group, "0")
        digital = np.asarray(level0[:], dtype=np.float64)
        scale = np.asarray(level0.attrs["scale"], dtype=np.float64)
        offset = np.asarray(level0.attrs["offset"], dtype=np.float64)
        channels = []
        for channel in sorted(attrs["channels"], key=lambda c: c["row_index"]):
            row = channel["row_index"]
            physical = digital[row] * scale[row] + offset[row]
            channels.append(
                {
                    "row_index": row,
                    "label": channel["label"],
                    "unit": channel["unit"],
                    "max_abs_error": abs(float(scale[row])) / 2,
                    "physical": physical.tolist(),
                    "source_physical": source[channel["label"]].tolist(),
                }
            )
        groups[name] = {
            "rate": attrs["rate"],
            "n_samples": attrs["n_samples"],
            "channels": channels,
        }
    events = child(root, "events")
    return {
        "vector": LEGACY,
        "source": f"conformance/SOURCES.md, crop of {SOURCE_EDF}",
        "formula": "physical[c, i] = digital[c, i] * scale[c] + offset[c], in float64",
        "groups": groups,
        "events": {"n_events": events.attrs["n_events"]},
    }


def v2_entries() -> list[dict]:
    """The manifest entries of the version 2 vectors, with the version 3 reader's outcomes."""
    entries = [
        {
            "id": LEGACY,
            "path": f"stores/v2/{LEGACY}.zarr",
            "format_version": 2,
            "class": "valid",
            "layer": None,
            "rule": "format-name",
            "description": "Written by biosigIO 1.2.13 and not changed since.",
            "expect": {
                "2": {"outcome": "accept", "goldens": f"goldens/{LEGACY}.json"},
                "3": V2_READ_AS_V3,
            },
            "files": store_files(STORES_V2 / f"{LEGACY}.zarr"),
        }
    ]
    for spec in DERIVED:
        entries.append(
            {
                "id": spec["id"],
                "path": f"stores/v2/{spec['id']}.zarr",
                "format_version": 2,
                "class": spec["class"],
                "layer": spec["layer"],
                "rule": spec["rule"],
                **({"description": spec["description"]} if "description" in spec else {}),
                "derived_from": LEGACY,
                "alteration": {"document": "zarr.json", "patch": spec["patch"]},
                "expect": {"2": spec["expect"], "3": spec["expect3"]},
                "files": store_files(STORES_V2 / f"{spec['id']}.zarr"),
            }
        )
    return entries


# ---------------------------------------------------------------------------
# Format version 3, and the version 1 vector, which belongs to the version 3 suite.
#
# No writer of version 3 exists, so these stores are written here from the crop
# with zarr-python and NumPy: the metadata documents the text specifies, and the
# arrays with the codec chains it names. Every resampling, quantization and
# alteration is recorded in the store's derivation lists and in SOURCES.md.
# ---------------------------------------------------------------------------

SCHEMA_V3 = "https://w3id.org/biosig-zarr/schemas/v3/"
CONVENTION_UUID = "3d7d2fe9-20a5-46d9-a92b-9170cddf6633"
# An identifier minted for v3-timestamped with uuidgen on 2026-11-20; it names no convention.
UNKNOWN_CONVENTION_UUID = "7172d401-2def-4e11-b5b7-db7f6673c195"
# The time the version 3 vectors were first written. A rebuild keeps it, so that a
# rebuild reproduces every file byte for byte.
CREATED_UTC = "2026-11-21T02:11:15Z"
MISSING_INT16 = -32768
EEG_CHANNELS = CROP_CHANNELS[:4]
MISC_CHANNEL = CROP_CHANNELS[4]
DEFAULT_CAPS = {"EEG": 250, "MEG": 250, "IEEG": 1000, "EMG": 1000}
FIR_TAPS = 41
ANTI_ALIAS_FILTER = (
    "windowed-sinc low-pass finite impulse response filter, 41 taps, Hamming window, "
    "cutoff at half the served rate, applied with NumPy to each run of finite source "
    "samples of each valid interval with reflected edges; each grid point takes the "
    "filtered value at its nearest source sample"
)
VIEW_DOWNSAMPLE = 4
VIEW_CHUNK_COLUMNS = 1024
PHYSICAL_FORMULA = "physical = digital * scale + offset"
GENERATED_BY = [
    {
        "name": "biosig-zarr-conformance-builder",
        "version": "1",
        "code_url": "https://github.com/nemarOrg/biosig-zarr/tree/draft/3.0.0/tools/vectors",
        "description": "tools/vectors/build.py: writes the conformance vectors; not a library",
    },
    {"name": "zarr-python", "version": zarr.__version__},
    {"name": "numpy", "version": np.__version__},
]
# The codec chain of "Level-0 array" and "View pyramid": bytes, little-endian, then blosc
# with zstd (level 5 and byte shuffle are this builder's choice, as they are biosigIO's).
BLOSC_ZSTD = BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")
BYTES_LITTLE = BytesCodec(endian="little")
KEY_ENCODING: dict[str, Any] = {"name": "default", "separator": "/"}

# The events every version 3 vector of the continuous recording carries, on the
# recording timeline: (onset, duration, code). The source has no annotations.
CONTINUOUS_EVENTS = [(1.0, 0.0, 0), (2.0, 0.0, 0), (9.5, 0.0, 0), (11.0, 0.0, 0)]
# The events of the gap vector: the example of the text, and three exact ties.
GAP_EVENTS = [(0.25, 0.0, 0), (1.25, 0.0, 0), (2.02, 0.0, 0), (3.25, 0.0, 0)]
EVENT_LABELS = {"0": "conformance marker"}

# The gap vector: 10 Hz from the 100 Hz crop, the first 4 seconds, with source samples
# 200 to 239 cut out as a pause of the recorder, and one source sample made non-finite.
GAP_RATE = 10.0
GAP_SEGMENTS = [(0, 200, 0.0), (240, 400, 2.4)]  # source samples [a, b), and source_time
GAP_NONFINITE = ("O1-A1", 300)  # channel, source sample

# The exact-copy gap vector: the first 4 seconds at the source rate, the codes copied
# unchanged, so no missing value is declared and the fill value 0 is a possible data code.
# The group starts 5 ms into the timeline, and the second segment is dated 2.4 s, so that
# its place on the grid, (2.4 - 0.005) * 100 = 239.5, and the onset 0.0, at
# (0.0 - 0.005) * 100 = -0.5, are exact ties of round.
EXACT_START_TIME = 0.005
EXACT_SEGMENTS = [(0, 200, 0.005), (240, 400, 2.4)]
EXACT_EVENTS = [(0.0, 0.0, 0), (1.0, 0.0, 0), (2.2, 0.0, 0), (3.0, 0.0, 0)]


def round_half_up(x: float) -> int:
    """round(x) as the text defines it: floor(x + 0.5), in 64-bit floating point."""
    return math.floor(x + 0.5)


def edf_signals(path: Path) -> dict[str, dict[str, Any]]:
    """Every signal of an EDF file, by label: its digital codes and header fields."""
    data = path.read_bytes()
    header_bytes = int(data[184:192])
    n_records = int(data[236:244])
    duration = float(data[244:252])
    ns = int(data[252:256])

    def field(offset: int, width: int) -> list[str]:
        start = 256 + offset * ns
        cells = [data[start + i * width : start + (i + 1) * width] for i in range(ns)]
        return [cell.decode("ascii").strip() for cell in cells]

    labels = field(0, 16)
    units = field(96, 8)
    pmin = [float(v) for v in field(104, 8)]
    pmax = [float(v) for v in field(112, 8)]
    dmin = [int(v) for v in field(120, 8)]
    dmax = [int(v) for v in field(128, 8)]
    prefilter = field(136, 80)
    samples = [int(v) for v in field(216, 8)]
    digital = np.frombuffer(data[header_bytes:], dtype="<i2").reshape(n_records, sum(samples))
    out = {}
    start = 0
    for i, label in enumerate(labels):
        step = (pmax[i] - pmin[i]) / (dmax[i] - dmin[i])
        codes = digital[:, start : start + samples[i]].reshape(-1).astype(np.int64)
        out[label] = {
            "codes": codes,
            "rate": samples[i] / duration,
            "record_duration": duration,
            "samples_per_record": samples[i],
            "edf_unit": units[i],
            "prefilter": prefilter[i] or "n/a",
            "step": step,
            "offset": pmin[i] - dmin[i] * step,
            "digital_range": [dmin[i], dmax[i]],
        }
        start += samples[i]
    return out


def tsv_rows(path: Path) -> dict[str, dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return {
        row[0]: dict(zip(header, row, strict=True)) for row in (x.split("\t") for x in lines[1:])
    }


def source_physical(signal: dict[str, Any]) -> np.ndarray:
    """source_code * source_step + source_offset, in float64 (The derivation list)."""
    return signal["codes"].astype(np.float64) * signal["step"] + signal["offset"]


def quantize(physical: np.ndarray) -> tuple[np.ndarray, float, float]:
    """The text's informative int16 quantization ("Dequantization"); NaN becomes missing."""
    finite = np.isfinite(physical)
    pmin, pmax = float(physical[finite].min()), float(physical[finite].max())
    digital = np.full(physical.shape, MISSING_INT16, dtype=np.int16)
    if pmax == pmin:
        scale, offset = 1.0, pmin
        digital[finite] = 0
    else:
        scale = (pmax - pmin) / 65534
        offset = pmin + 32767 * scale
        codes = np.floor((physical[finite] - offset) / scale + 0.5)
        digital[finite] = np.clip(codes, -32767, 32767).astype(np.int16)
    return digital, scale, offset


def lowpass(run: np.ndarray, factor: int) -> np.ndarray:
    """The anti-alias filter of ANTI_ALIAS_FILTER, on one run of finite samples."""
    half = FIR_TAPS // 2
    if len(run) <= half:
        sys.exit("a run of finite samples is too short for the filter; stopping")
    n = np.arange(FIR_TAPS) - half
    cutoff = 0.5 / factor
    taps = 2 * cutoff * np.sinc(2 * cutoff * n) * np.hamming(FIR_TAPS)
    taps /= taps.sum()
    return np.convolve(np.pad(run, half, mode="reflect"), taps, mode="valid")


def resample_interval(x: np.ndarray, source_rate: float, rate: float) -> np.ndarray:
    """One valid interval of one channel, on the grid ("Channel groups", "Missing values").

    Each run of finite source samples is filtered on its own; grid point j takes the
    filtered value at its nearest source sample, round(j * source_rate / rate), and is
    NaN (missing) when that source sample is non-finite.
    """
    factor = round(source_rate / rate)
    if factor * rate != source_rate:
        sys.exit("the builder resamples by an integer factor only; stopping")
    filtered = np.full(x.shape, np.nan)
    finite = np.isfinite(x)
    i = 0
    while i < len(x):
        if not finite[i]:
            i += 1
            continue
        j = i
        while j < len(x) and finite[j]:
            j += 1
        filtered[i:j] = lowpass(x[i:j], factor)
        i = j
    n = max(1, round_half_up(len(x) * rate / source_rate))
    return filtered[[round_half_up(j * source_rate / rate) for j in range(n)]]


def place_intervals(
    segments: list[tuple[np.ndarray, float | None]],
    source_rate: float,
    rate: float,
    start_time: float,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Place source segments on one grid ("Channel groups", "Valid intervals").

    Each segment is a [channels, m] array of source physical values (NaN for a
    non-finite sample) with its source_time. Returns the values on the grid (NaN
    outside every interval and where missing), the nearest source values, and
    valid_intervals.
    """
    placed: list[tuple[int, np.ndarray, np.ndarray]] = []
    intervals: list[dict] = []
    stop = 0
    for k, (segment, source_time) in enumerate(segments):
        if k == 0:
            start = 0
        elif source_time is None:
            start = stop
        else:
            start = round_half_up((source_time - start_time) * rate)
        if start < stop:
            sys.exit("two intervals overlap on the grid; stopping")
        if rate == source_rate:
            values = segment.copy()
            nearest = segment.copy()
        else:
            values = np.stack([resample_interval(row, source_rate, rate) for row in segment])
            index = [round_half_up(j * source_rate / rate) for j in range(values.shape[1])]
            nearest = segment[:, index]
        stop = start + values.shape[1]
        placed.append((start, values, nearest))
        intervals.append({"start": start, "stop": stop, "source_time": source_time})
    n_channels = segments[0][0].shape[0]
    grid = np.full((n_channels, stop), np.nan)
    near = np.full((n_channels, stop), np.nan)
    for start, values, nearest in placed:
        grid[:, start : start + values.shape[1]] = values
        near[:, start : start + values.shape[1]] = nearest
    return grid, near, intervals


def acquired_mask(intervals: list[dict], n_samples: int) -> np.ndarray:
    mask = np.zeros(n_samples, dtype=bool)
    for interval in intervals:
        mask[interval["start"] : interval["stop"]] = True
    return mask


def view_levels(n_samples: int, stop_columns: int) -> list[int]:
    """Levels while a level has columns, stopping after one with at most stop_columns."""
    levels = []
    level = 1
    while n_samples // VIEW_DOWNSAMPLE**level > 0:
        levels.append(level)
        if n_samples // VIEW_DOWNSAMPLE**level <= stop_columns:
            break
        level += 1
    return levels


def view_envelope(
    digital: np.ndarray, acquired: np.ndarray, factor: int, missing: int | None, fill: int
) -> np.ndarray:
    """Column j holds the minimum and maximum of the acquired, non-missing level-0
    samples j * f to (j + 1) * f - 1, or, when there are none, the missing value, or the
    fill value when the array declares no missing value ("View pyramid")."""
    n_channels, n_samples = digital.shape
    columns = n_samples // factor
    out = np.full((2, n_channels, columns), fill, dtype=np.int16)
    for j in range(columns):
        window = slice(j * factor, (j + 1) * factor)
        for c in range(n_channels):
            values = digital[c, window]
            keep = acquired[window]
            if missing is not None:
                keep = keep & (values != missing)
            values = values[keep]
            if values.size:
                out[0, c, j] = values.min()
                out[1, c, j] = values.max()
    return out


def channel_object(
    label: str,
    row: int,
    signal: dict[str, Any],
    tsv: dict[str, str],
    *,
    uniform: dict[str, Any] | None,
    scale: float,
    offset: float,
    derivation: list[str],
    nonfinite: int,
) -> dict[str, Any]:
    """A channel object of "Channel groups", in the order of its table."""
    out: dict[str, Any] = {
        "label": label,
        "row_index": row,
        "channel_type": tsv["type"],
        "modality": tsv["type"],
        "unit": tsv["units"],
        "prefilter": signal["prefilter"],
    }
    if uniform is not None:
        out.update(uniform)
    out.update(
        {
            "usable_for_inference": nonfinite == 0,
            "scale": scale,
            "offset": offset,
            "source_step": signal["step"],
            "source_offset": signal["offset"],
            "source_digital_range": signal["digital_range"],
            "derivation": derivation,
        }
    )
    if nonfinite:
        out["nonfinite_samples"] = nonfinite
    return out


def write_uniform_group(
    root: zarr.Group,
    name: str,
    labels: tuple[str, ...],
    signals: dict[str, dict[str, Any]],
    tsv: dict[str, dict[str, str]],
    *,
    segments: list[tuple[int, int, float]],
    rate: float,
    nonfinite: tuple[str, int] | None,
    chunk: int,
    shard: int,
    stop_columns: int,
    start_time: float = 0.0,
    exact: bool = False,
) -> dict[str, Any]:
    """Write one uniform group; return its values for the goldens.

    With ``exact``, the group is an exact copy of the source codes ("Exact copies"): no
    resampling, scale and offset are the source's, the derivation list is empty, and the
    arrays declare no missing value, so their fill value 0 is a possible data value.
    """
    source_rate = signals[labels[0]]["rate"]
    source = np.stack([source_physical(signals[label]) for label in labels])
    if nonfinite is not None:
        source[labels.index(nonfinite[0]), nonfinite[1]] = np.nan
    grid, near, intervals = place_intervals(
        [(source[:, a:b], t) for a, b, t in segments], source_rate, rate, start_time
    )
    n_samples = grid.shape[1]
    acquired = acquired_mask(intervals, n_samples)
    missing_value: int | None = None if exact else MISSING_INT16
    fill = 0 if exact else MISSING_INT16
    if exact:
        if rate != source_rate or nonfinite is not None:
            sys.exit("an exact copy is neither resampled nor altered in value; stopping")
        codes_source = np.stack([signals[label]["codes"] for label in labels]).astype(np.float64)
        code_grid, _, _ = place_intervals(
            [(codes_source[:, a:b], t) for a, b, t in segments], source_rate, rate, start_time
        )
    digital = np.full(grid.shape, fill, dtype=np.int16)
    scales, offsets, channels = [], [], []
    resampled = rate != source_rate
    for row, label in enumerate(labels):
        if exact:
            digital[row, acquired] = code_grid[row, acquired].astype(np.int16)
            scale, offset = signals[label]["step"], signals[label]["offset"]
        else:
            codes, scale, offset = quantize(np.where(acquired, grid[row], np.nan))
            digital[row] = codes
        scales.append(scale)
        offsets.append(offset)
        missing = int(np.sum(acquired & ~np.isfinite(grid[row])))
        derivation = ["resampled"] if resampled else []
        if missing:
            derivation.append("nonfinite_to_missing")
        if not exact:
            derivation.append("requantized")
        uniform = {
            "original_rate": source_rate,
            "target_rate": rate,
            "anti_aliased": resampled,
        }
        channels.append(
            channel_object(
                label,
                row,
                signals[label],
                tsv[label],
                uniform=uniform,
                scale=scale,
                offset=offset,
                derivation=derivation,
                nonfinite=missing,
            )
        )
    levels = view_levels(n_samples, stop_columns)
    group = root.create_group(
        name,
        attributes={
            "kind": "uniform",
            "modality": channels[0]["modality"],
            "n_channels": len(labels),
            "n_samples": n_samples,
            "channels": channels,
            "rate": rate,
            "original_rate": float(round(source_rate)),
            "start_time": start_time,
            "valid_intervals": intervals,
            "time_regularization": None,
            "n_view_levels": len(levels),
            "view_levels": levels,
            "view_downsample": VIEW_DOWNSAMPLE,
            "view_chunk_columns": VIEW_CHUNK_COLUMNS,
            "chunk_seconds": chunk / rate,
            "shard_seconds": shard / rate,
        },
    )
    level0 = group.create_array(
        "0",
        shape=digital.shape,
        dtype="int16",
        chunks=(len(labels), chunk),
        shards=(len(labels), shard),
        fill_value=fill,
        attributes={
            "level": 0,
            "kind": "signal",
            "rate": rate,
            "source_rate_hz": source_rate,
            "downsample_factor": 1,
            "chunk_samples": chunk,
            "shard_samples": shard,
            "anti_aliased": resampled,
            "usable_for_inference": any(c["usable_for_inference"] for c in channels),
            "scale": scales,
            "offset": offsets,
            "missing_value": missing_value,
            "physical_formula": PHYSICAL_FORMULA,
        },
        compressors=BLOSC_ZSTD,
        serializer=BYTES_LITTLE,
        chunk_key_encoding=KEY_ENCODING,
    )
    level0[:] = digital
    view = group.create_group("view")
    for level in levels:
        factor = VIEW_DOWNSAMPLE**level
        envelope = view_envelope(digital, acquired, factor, missing_value, fill)
        columns = min(VIEW_CHUNK_COLUMNS, envelope.shape[2])
        array = view.create_array(
            str(level),
            shape=envelope.shape,
            dtype="int16",
            chunks=(2, len(labels), columns),
            fill_value=fill,
            compressors=BLOSC_ZSTD,
            serializer=BYTES_LITTLE,
            chunk_key_encoding=KEY_ENCODING,
            attributes={
                "level": level,
                "kind": "minmax_envelope",
                "axis0": ["min", "max"],
                "downsample_factor": factor,
                "rate_effective": rate / factor,
                "chunk_columns": columns,
                "missing_value": missing_value,
                "usable_for_inference": False,
            },
        )
        array[:] = envelope
    return {
        "kind": "uniform",
        "rate": rate,
        "start_time": start_time,
        "n_samples": n_samples,
        "channels": [
            golden_channel(
                channels[row],
                digital[row],
                scales[row],
                offsets[row],
                grid[row],
                near[row],
                acquired if exact else acquired & (digital[row] != MISSING_INT16),
            )
            for row in range(len(labels))
        ],
    }


def write_timestamped_group(
    root: zarr.Group,
    name: str,
    label: str,
    signals: dict[str, dict[str, Any]],
    tsv: dict[str, dict[str, str]],
    *,
    chunk: int,
    shard: int,
) -> dict[str, Any]:
    """Write one timestamped group of one channel, whose time holds the source's own
    sample times: the record onset plus the sample's place in the record."""
    signal = signals[label]
    per_record = signal["samples_per_record"]
    n = len(signal["codes"])
    time = np.array(
        [
            (i // per_record) * signal["record_duration"]
            + (i % per_record) * signal["record_duration"] / per_record
            for i in range(n)
        ],
        dtype=np.float64,
    )
    physical = source_physical(signal)
    digital, scale, offset = quantize(physical)
    channel = channel_object(
        label,
        0,
        signal,
        tsv[label],
        uniform=None,
        scale=scale,
        offset=offset,
        derivation=["requantized"],
        nonfinite=0,
    )
    group = root.create_group(
        name,
        attributes={
            "kind": "timestamped",
            "modality": channel["modality"],
            "n_channels": 1,
            "n_samples": n,
            "channels": [channel],
            "nominal_rate": signal["rate"],
            "effective_rate": (n - 1) / (float(time[-1]) - float(time[0])),
            "time_range": [float(time[0]), float(time[-1])],
            "continuity": "continuous",
            "chunk_samples": chunk,
        },
    )
    time_array = group.create_array(
        "time",
        shape=(n,),
        dtype="float64",
        chunks=(chunk,),
        shards=(shard,),
        attributes={"kind": "time", "unit": "s", "derivation": []},
        compressors=BLOSC_ZSTD,
        serializer=BYTES_LITTLE,
        chunk_key_encoding=KEY_ENCODING,
    )
    time_array[:] = time
    values = group.create_array(
        "values",
        shape=(1, n),
        dtype="int16",
        chunks=(1, chunk),
        shards=(1, shard),
        fill_value=MISSING_INT16,
        attributes={
            "kind": "values",
            "scale": [scale],
            "offset": [offset],
            "missing_value": MISSING_INT16,
            "physical_formula": PHYSICAL_FORMULA,
        },
        compressors=BLOSC_ZSTD,
        serializer=BYTES_LITTLE,
        chunk_key_encoding=KEY_ENCODING,
    )
    values[:] = digital[np.newaxis, :]
    index = time[::chunk].copy()
    time_index = group.create_array(
        "time_index", shape=index.shape, dtype="float64", chunks=index.shape
    )
    time_index[:] = index
    return {
        "kind": "timestamped",
        "n_samples": n,
        "time": time.tolist(),
        "channels": [
            golden_channel(
                channel, digital, scale, offset, physical, physical, digital != MISSING_INT16
            )
        ],
    }


def golden_channel(
    channel: dict[str, Any],
    digital: np.ndarray,
    scale: float,
    offset: float,
    unquantized: np.ndarray,
    nearest: np.ndarray,
    present: np.ndarray,
) -> dict[str, Any]:
    """The values a reader returns for one channel; null where there is no sample."""
    physical = digital.astype(np.float64) * scale + offset

    def listed(values: np.ndarray) -> list[float | None]:
        return [float(v) if ok else None for v, ok in zip(values, present, strict=True)]

    return {
        "row_index": channel["row_index"],
        "label": channel["label"],
        "unit": channel["unit"],
        "derivation": channel["derivation"],
        "max_abs_error": abs(scale) / 2,
        "physical": listed(physical),
        "unquantized": listed(unquantized),
        "source_physical": listed(nearest),
    }


def write_events(root: zarr.Group, events: list[tuple[float, float, int]]) -> dict[str, Any]:
    group = root.create_group(
        "events",
        attributes={
            "n_events": len(events),
            "label_map": EVENT_LABELS if events else {},
            "onset_source_basis": "timeline",
        },
    )
    columns = {
        "onset": ("float64", [e[0] for e in events]),
        "duration": ("float64", [e[1] for e in events]),
        "code": ("int32", [e[2] for e in events]),
    }
    for name, (dtype, values) in columns.items():
        array = group.create_array(name, shape=(len(events),), dtype=dtype, chunks=(len(events),))
        array[:] = np.asarray(values, dtype=dtype)
    return {
        "n_events": len(events),
        "onset": [e[0] for e in events],
        "duration": [e[1] for e in events],
        "code": [e[2] for e in events],
    }


def root_attributes(
    channel_groups: list[str],
    timestamped_groups: list[str],
    caps: dict[str, int],
    n_channels: int,
    conventions: list[dict[str, str]],
) -> dict[str, Any]:
    """The root attributes of "Root attributes", in the order of its table."""
    return {
        "format": "biosig-zarr",
        "format_version": 3,
        "zarr_conventions": conventions,
        "channel_groups": channel_groups,
        "timestamped_groups": timestamped_groups,
        "dtype": "int16",
        "source_sample_type": "int16",
        "source_adc_bits": None,
        "modality_rates": caps,
        "anti_alias_filter": ANTI_ALIAS_FILTER,
        "view_downsample": VIEW_DOWNSAMPLE,
        "view_chunk_columns": VIEW_CHUNK_COLUMNS,
        "source_format": "EDF",
        "recording_metadata": {"source_file": SOURCE_EDF, "number_of_signals": n_channels},
        "created_utc": CREATED_UTC,
        "channels_tsv_units": {
            "converted": 0,
            "relabelled": n_channels,
            "kept_importer_unit": 0,
            "units_column_present": True,
        },
        "generated_by": GENERATED_BY,
    }


BIOSIG_CONVENTION = {"uuid": CONVENTION_UUID, "name": "biosig-zarr"}


def write_v3_store(vector_id: str, crop: Path) -> dict:
    """Write one version 3 vector that is not derived from another; return its goldens."""
    signals = edf_signals(crop / SOURCE_EDF)
    tsv = tsv_rows(crop / SOURCE_TSV)
    target = STORES_V3 / f"{vector_id}.zarr"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    n_source = len(signals[EEG_CHANNELS[0]]["codes"])
    groups: dict[str, Any] = {}
    if vector_id == "v3-continuous":
        root = zarr.create_group(
            target,
            zarr_format=3,
            attributes=root_attributes(
                ["eeg_100hz"], [], DEFAULT_CAPS, len(EEG_CHANNELS), [BIOSIG_CONVENTION]
            ),
        )
        groups["eeg_100hz"] = write_uniform_group(
            root, "eeg_100hz", EEG_CHANNELS, signals, tsv,
            segments=[(0, n_source, 0.0)], rate=100.0, nonfinite=None,
            chunk=400, shard=1200, stop_columns=512,
        )  # fmt: skip
        events = write_events(root, CONTINUOUS_EVENTS)
    elif vector_id == "v3-gap-10hz":
        root = zarr.create_group(
            target,
            zarr_format=3,
            attributes=root_attributes(
                ["eeg_10hz"], [], {**DEFAULT_CAPS, "EEG": 10}, len(EEG_CHANNELS),
                [BIOSIG_CONVENTION],
            ),
        )  # fmt: skip
        segments = [(a, b, a / signals[EEG_CHANNELS[0]]["rate"]) for a, b, _ in GAP_SEGMENTS]
        if [t for _, _, t in segments] != [t for _, _, t in GAP_SEGMENTS]:
            sys.exit("a source_time is not the time of its first source sample; stopping")
        groups["eeg_10hz"] = write_uniform_group(
            root, "eeg_10hz", EEG_CHANNELS, signals, tsv,
            segments=segments, rate=GAP_RATE, nonfinite=GAP_NONFINITE,
            chunk=4, shard=16, stop_columns=2,
        )  # fmt: skip
        events = write_events(root, GAP_EVENTS)
    elif vector_id == "v3-gap-exact-copy":
        root = zarr.create_group(
            target,
            zarr_format=3,
            attributes=root_attributes(
                ["eeg_100hz"], [], DEFAULT_CAPS, len(EEG_CHANNELS), [BIOSIG_CONVENTION]
            ),
        )
        groups["eeg_100hz"] = write_uniform_group(
            root, "eeg_100hz", EEG_CHANNELS, signals, tsv,
            segments=EXACT_SEGMENTS, rate=100.0, nonfinite=None,
            chunk=40, shard=160, stop_columns=25, start_time=EXACT_START_TIME, exact=True,
        )  # fmt: skip
        events = write_events(root, EXACT_EVENTS)
    elif vector_id == "v3-timestamped":
        root = zarr.create_group(
            target,
            zarr_format=3,
            attributes=root_attributes(
                ["eeg_100hz"], ["misc_timestamped"], DEFAULT_CAPS, len(CROP_CHANNELS),
                [
                    BIOSIG_CONVENTION,
                    {"uuid": UNKNOWN_CONVENTION_UUID, "name": "conformance-unknown-convention"},
                ],
            ),
        )  # fmt: skip
        groups["eeg_100hz"] = write_uniform_group(
            root, "eeg_100hz", EEG_CHANNELS, signals, tsv,
            segments=[(0, n_source, 0.0)], rate=100.0, nonfinite=None,
            chunk=400, shard=1200, stop_columns=512,
        )  # fmt: skip
        groups["misc_timestamped"] = write_timestamped_group(
            root, "misc_timestamped", MISC_CHANNEL, signals, tsv, chunk=400, shard=1200
        )
        events = write_events(root, CONTINUOUS_EVENTS)
    else:
        raise ValueError(vector_id)
    return {
        "vector": vector_id,
        "source": f"conformance/SOURCES.md, crop of {SOURCE_EDF}",
        "formula": "physical[c, i] = digital[c, i] * scale[c] + offset[c], in float64",
        "missing": "null: no sample (outside every valid interval, or the missing value)",
        "groups": groups,
        "events": events,
    }


def continuous_group(start_time: float) -> dict[str, Any]:
    """What a version 3 reader reads in eeg_100hz of the continuous vectors."""
    return {
        "start_time": start_time,
        "valid_intervals": [{"start": 0, "stop": 1000, "source_time": start_time}],
        "missing_value": MISSING_INT16,
        "refuse_without": (["start_time"] if start_time else []) + ["missing_value"],
        "view_empty_columns": {"1": []},
    }


def event_samples(group: str, samples: list[int | None], events: list) -> list[dict]:
    return [
        {"group": group, "onset": onset, "sample": sample}
        for (onset, _, _), sample in zip(events, samples, strict=True)
    ]


CONTINUOUS_READ = {
    "outcome": "accept",
    "goldens": "goldens/v3-continuous.json",
    "uniform_groups": ["eeg_100hz"],
    "timestamped_groups": [],
    "groups": {"eeg_100hz": continuous_group(0.0)},
    "events": {
        "onset_source_basis": "timeline",
        "samples": event_samples("eeg_100hz", [100, 200, 950, None], CONTINUOUS_EVENTS),
    },
}


def schema_failure(schema: str, document: str, instance_path: str, keyword: str) -> dict:
    return {
        "schema": SCHEMA_V3 + schema,
        "document": document,
        "instance_path": instance_path,
        "keyword": keyword,
    }


def refusal(layer: int | None, rule: str, subject: str) -> dict:
    return {"layer": layer, "rule": rule, "subject": subject}


# Every version 3 vector, and the version 1 vector. A vector with "derived_from" is its
# base with one JSON Patch applied to one metadata document; the others are written.
# Each "expect" is the outcome for a reader of the version 3 text, derived from the text
# by hand; tools/check-vectors.ts recomputes it from the store's metadata.
V3_VECTORS: list[dict[str, Any]] = [
    {
        "id": "v1-no-format-version",
        "dir": "v1",
        "class": "invalid",
        "layer": 1,
        "rule": "format-version",
        "description": (
            "A version 1 store: no format_version, and recording_metadata as a string "
            "holding JSON text. A reader of the version 3 text MUST refuse it as unsupported."
        ),
        "derived_from": LEGACY,
        "document": "zarr.json",
        "patch": [
            {"op": "remove", "path": "/attributes/format_version"},
            {"op": "replace", "path": "/attributes/recording_metadata", "value": None},
        ],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(1, "format-version", "format_version"),
        },
    },
    {
        "id": "v3-continuous",
        "dir": "v3",
        "class": "valid",
        "layer": 4,
        "rule": "missing-values",
        "description": (
            "One uniform int16 group of four EEG channels at their source rate, one valid "
            "interval, the declared missing value, and the zarr_conventions entry. A reader "
            "that does not implement missing_value MUST refuse it, naming missing_value."
        ),
        "expect": CONTINUOUS_READ,
    },
    {
        "id": "v3-gap-10hz",
        "dir": "v3",
        "class": "valid",
        "layer": 4,
        "rule": "events-group",
        "description": (
            "The gap case of the text: 10 Hz, valid intervals [0, 20) and [24, 40), an event "
            "at 2.02 s with no sample, three onsets that are exact ties of round, one sample "
            "missing inside an interval, and view levels with factors 4 and 16."
        ),
        "expect": {
            "outcome": "accept",
            "goldens": "goldens/v3-gap-10hz.json",
            "uniform_groups": ["eeg_10hz"],
            "timestamped_groups": [],
            "groups": {
                "eeg_10hz": {
                    "start_time": 0.0,
                    "valid_intervals": [
                        {"start": 0, "stop": 20, "source_time": 0.0},
                        {"start": 24, "stop": 40, "source_time": 2.4},
                    ],
                    "missing_value": MISSING_INT16,
                    "refuse_without": ["valid_intervals", "missing_value"],
                    "view_empty_columns": {"1": [5], "2": []},
                }
            },
            "events": {
                "onset_source_basis": "timeline",
                "samples": event_samples("eeg_10hz", [3, 13, None, 33], GAP_EVENTS),
            },
        },
    },
    {
        "id": "v3-gap-exact-copy",
        "dir": "v3",
        "class": "valid",
        "layer": 4,
        "rule": "view-pyramid",
        "description": (
            "An exact copy of the source codes at 100 Hz, with no missing value declared, so "
            "the fill value 0 of the gap and of the empty view columns is a possible data "
            "value and only the mask rule finds the empty columns. start_time is 0.005; the "
            "second interval's place on the grid, 239.5, and the onset 0.0, at -0.5, are exact "
            "ties of round. A reader that implements neither start_time nor valid_intervals "
            "MUST refuse it, naming each."
        ),
        "expect": {
            "outcome": "accept",
            "goldens": "goldens/v3-gap-exact-copy.json",
            "uniform_groups": ["eeg_100hz"],
            "timestamped_groups": [],
            "groups": {
                "eeg_100hz": {
                    "start_time": EXACT_START_TIME,
                    "valid_intervals": [
                        {"start": 0, "stop": 200, "source_time": 0.005},
                        {"start": 240, "stop": 400, "source_time": 2.4},
                    ],
                    "missing_value": None,
                    "refuse_without": ["start_time", "valid_intervals"],
                    "view_empty_columns": {"1": list(range(50, 60)), "2": [13, 14]},
                }
            },
            "events": {
                "onset_source_basis": "timeline",
                "samples": event_samples("eeg_100hz", [0, 100, None, 300], EXACT_EVENTS),
            },
        },
    },
    {
        "id": "v3-start-time",
        "dir": "v3",
        "class": "valid",
        "layer": 4,
        "rule": "recording-timeline",
        "description": (
            "v3-continuous with the group starting 1.5 s into the recording timeline. A "
            "reader that does not implement start_time MUST refuse it, naming start_time."
        ),
        "derived_from": "v3-continuous",
        "document": "eeg_100hz/zarr.json",
        "patch": [
            {"op": "replace", "path": "/attributes/start_time", "value": 1.5},
            {"op": "replace", "path": "/attributes/valid_intervals/0/source_time", "value": 1.5},
        ],
        "expect": {
            **CONTINUOUS_READ,
            "groups": {"eeg_100hz": continuous_group(1.5)},
            "events": {
                "onset_source_basis": "timeline",
                "samples": event_samples("eeg_100hz", [None, 50, 800, 950], CONTINUOUS_EVENTS),
            },
        },
    },
    {
        "id": "v3-timestamped",
        "dir": "v3",
        "class": "valid",
        "layer": 3,
        "rule": "reader-safety",
        "description": (
            "A uniform group and a timestamped group whose time holds the source's own "
            "sample times. A reader navigating by channel_groups reaches only the uniform "
            "group. zarr_conventions also holds an entry for a convention no reader knows."
        ),
        "expect": {
            **CONTINUOUS_READ,
            "goldens": "goldens/v3-timestamped.json",
            "timestamped_groups": ["misc_timestamped"],
            "events": {
                "onset_source_basis": "timeline",
                "samples": event_samples("eeg_100hz", [100, 200, 950, None], CONTINUOUS_EVENTS)
                + event_samples("misc_timestamped", [100, 200, 950, None], CONTINUOUS_EVENTS),
            },
        },
    },
    {
        "id": "v3-version-4",
        "dir": "v3",
        "class": "invalid",
        "layer": 1,
        "rule": "format-version",
        "derived_from": "v3-continuous",
        "document": "zarr.json",
        "patch": [{"op": "replace", "path": "/attributes/format_version", "value": 4}],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(1, "format-version", "format_version"),
            "schema_failure": schema_failure(
                "root.schema.json", "zarr.json", "/attributes/format_version", "const"
            ),
        },
    },
    {
        "id": "v3-unknown-format",
        "dir": "v3",
        "class": "invalid",
        "layer": None,
        "rule": "format-name",
        "derived_from": "v3-continuous",
        "document": "zarr.json",
        "patch": [{"op": "replace", "path": "/attributes/format", "value": "example-zarr"}],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(None, "format-name", "format"),
            "schema_failure": schema_failure(
                "root.schema.json", "zarr.json", "/attributes/format", "const"
            ),
        },
    },
    {
        "id": "v3-no-kind",
        "dir": "v3",
        "class": "invalid",
        "layer": 2,
        "rule": "reader-safety",
        "derived_from": "v3-continuous",
        "document": "eeg_100hz/zarr.json",
        "patch": [{"op": "remove", "path": "/attributes/kind"}],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(2, "reader-safety", "eeg_100hz"),
            "schema_failure": schema_failure(
                "uniform-group.schema.json", "eeg_100hz/zarr.json", "/attributes", "required"
            ),
        },
    },
    {
        "id": "v3-unknown-kind",
        "dir": "v3",
        "class": "invalid",
        "layer": 2,
        "rule": "reader-safety",
        "derived_from": "v3-continuous",
        "document": "eeg_100hz/zarr.json",
        "patch": [{"op": "replace", "path": "/attributes/kind", "value": "sparse"}],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(2, "reader-safety", "eeg_100hz"),
            "schema_failure": schema_failure(
                "uniform-group.schema.json", "eeg_100hz/zarr.json", "/attributes/kind", "const"
            ),
        },
    },
    {
        "id": "v3-timestamped-listed",
        "dir": "v3",
        "class": "invalid",
        "layer": 3,
        "rule": "reader-safety",
        "description": (
            "Invalid because a name MUST NOT appear in both channel_groups and "
            "timestamped_groups, and channel_groups names only uniform groups; a JSON Schema "
            "cannot express a rule between two arrays, so no schema failure is cited."
        ),
        "derived_from": "v3-timestamped",
        "document": "zarr.json",
        "patch": [
            {
                "op": "replace",
                "path": "/attributes/channel_groups",
                "value": ["eeg_100hz", "misc_timestamped"],
            }
        ],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(3, "reader-safety", "misc_timestamped"),
        },
    },
    {
        "id": "v3-bad-intervals",
        "dir": "v3",
        "class": "invalid",
        "layer": None,
        "rule": "reading-untrusted-stores",
        "description": (
            "v3-gap-10hz with overlapping valid intervals, [0, 30) and [24, 40). A JSON "
            "Schema cannot compare two intervals, so no schema failure is cited."
        ),
        "derived_from": "v3-gap-10hz",
        "document": "eeg_10hz/zarr.json",
        "patch": [{"op": "replace", "path": "/attributes/valid_intervals/0/stop", "value": 30}],
        "expect": {
            "outcome": "refuse",
            "refusal": refusal(None, "reading-untrusted-stores", "eeg_10hz"),
        },
    },
    {
        "id": "v3-no-conventions",
        "dir": "v3",
        "class": "invalid",
        "layer": None,
        "rule": "zarr-convention",
        "description": (
            "Fails writer conformance: zarr_conventions is REQUIRED (Proposed). A reader "
            "MUST NOT require it, so a reader reads the store."
        ),
        "derived_from": "v3-continuous",
        "document": "zarr.json",
        "patch": [{"op": "remove", "path": "/attributes/zarr_conventions"}],
        "expect": {
            **CONTINUOUS_READ,
            "outcome": "schema-invalid",
            "reader": "accept",
            "schema_failure": schema_failure(
                "root.schema.json", "zarr.json", "/attributes", "required"
            ),
        },
    },
    {
        "id": "v3-conventions-extra-member",
        "dir": "v3",
        "class": "invalid",
        "layer": None,
        "rule": "zarr-convention",
        "description": (
            "Fails writer conformance: the biosig-zarr entry of zarr_conventions MUST NOT have "
            "members other than uuid, name, spec_url, schema_url and description. A reader "
            "identifies a store by format and format_version, so a reader reads the store."
        ),
        "derived_from": "v3-continuous",
        "document": "zarr.json",
        "patch": [{"op": "add", "path": "/attributes/zarr_conventions/0/version", "value": "3"}],
        "expect": {
            **CONTINUOUS_READ,
            "outcome": "schema-invalid",
            "reader": "accept",
            "schema_failure": schema_failure(
                "root.schema.json",
                "zarr.json",
                "/attributes/zarr_conventions/0",
                "additionalProperties",
            ),
        },  # fmt: skip
    },
]


def v1_patch() -> list[dict]:
    """The version 1 patch: the legacy store's recording_metadata as a JSON string."""
    document = json.loads((STORES_V2 / f"{LEGACY}.zarr" / "zarr.json").read_text("utf-8"))
    text = json.dumps(document["attributes"]["recording_metadata"])
    patch = copy.deepcopy(V3_VECTORS[0]["patch"])
    patch[1]["value"] = text
    return patch


def store_dir(vector_id: str) -> Path:
    for spec in V3_VECTORS:
        if spec["id"] == vector_id:
            return CONFORMANCE / "stores" / spec["dir"] / f"{vector_id}.zarr"
    return STORES_V2 / f"{vector_id}.zarr"


def check_ties() -> None:
    """Every onset a vector relies on as a tie of round is an exact tie in float64."""
    for onset, _, _ in GAP_EVENTS:
        x = (onset - 0.0) * GAP_RATE
        if onset != 2.02 and x - math.floor(x) != 0.5:
            sys.exit(f"{onset} * {GAP_RATE} = {x!r} is not an exact tie; stopping")
    for x in ((0.0 - EXACT_START_TIME) * 100.0, (2.4 - EXACT_START_TIME) * 100.0):
        if x - math.floor(x) != 0.5:
            sys.exit(f"{x!r} is not an exact tie; stopping")


def do_v3(crop: Path) -> list[Path]:
    """Write and derive the version 1 and version 3 vectors; return the goldens written."""
    check_ties()
    written = []
    for spec in V3_VECTORS:
        target = store_dir(spec["id"])
        if "derived_from" in spec:
            patch = v1_patch() if spec["id"] == "v1-no-format-version" else spec["patch"]
            spec["patch"] = patch
            derive_store(store_dir(spec["derived_from"]), target, spec["document"], patch)
            continue
        golden = write_v3_store(spec["id"], crop)
        path = GOLDENS / f"{spec['id']}.json"
        path.write_text(json.dumps(golden, indent=2))
        written.append(path)
    return written


def v3_entries() -> list[dict]:
    entries = []
    for spec in V3_VECTORS:
        entry = {
            "id": spec["id"],
            "path": f"stores/{spec['dir']}/{spec['id']}.zarr",
            "format_version": 3,
            "class": spec["class"],
            "layer": spec["layer"],
            "rule": spec["rule"],
            **({"description": spec["description"]} if "description" in spec else {}),
        }
        if "derived_from" in spec:
            entry["derived_from"] = spec["derived_from"]
            entry["alteration"] = {"document": spec["document"], "patch": spec["patch"]}
        entry["expect"] = {"3": spec["expect"]}
        entry["files"] = store_files(store_dir(spec["id"]))
        entries.append(entry)
    return entries


def do_derive(crop: Path) -> None:
    for spec in DERIVED:
        derive_vector(spec)
    GOLDENS.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDENS / f"{LEGACY}.json"
    golden_path.write_text(json.dumps(goldens(STORES_V2 / f"{LEGACY}.zarr", crop), indent=2))
    written = do_v3(crop)
    manifest = {
        "$comment": "The conformance contract; see conformance/README.md.",
        "spec": "spec/index.md",
        "vectors": v2_entries() + v3_entries(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run(
        ["bun", "x", "biome", "format", "--write", str(MANIFEST), str(golden_path)]
        + [str(path) for path in written],
        check=True,
        cwd=ROOT,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("step", choices=["crop", "write", "derive", "all"])
    parser.add_argument("--work", type=Path, required=True, help="scratch directory")
    args = parser.parse_args()
    crop = do_crop(args.work)
    if args.step in ("write", "all"):
        do_write(crop)
    if args.step in ("derive", "all"):
        do_derive(crop)


if __name__ == "__main__":
    main()
