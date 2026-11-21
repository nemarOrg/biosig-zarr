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
  write the goldens and ``conformance/manifest.json``; format the JSON this
  script wrote (not the stores) with Biome.

``conformance/SOURCES.md`` records every step and every alteration in prose.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import zarr

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / "conformance"
STORES_V2 = CONFORMANCE / "stores" / "v2"
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


# Every vector after the first is the legacy store with one JSON Patch applied
# to its root metadata document, ``zarr.json``.
DERIVED = [
    {
        "id": "v2-new-name",
        "class": "valid",
        "rule": "format-name",
        "patch": [{"op": "replace", "path": "/attributes/format", "value": "biosig-zarr"}],
        "expect": {"outcome": "accept", "goldens": f"goldens/{LEGACY}.json"},
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
    },
    {
        "id": "v2-version-3",
        "class": "invalid",
        "description": (
            "Invalid because a version 2 reader MUST refuse a store whose format_version is "
            "greater than the highest version it implements (spec line 126), not because "
            "the store breaks another version 2 rule."
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
    },
]


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
        node = result
        for part in parents:
            node = node[part]
        if operation["op"] in ("add", "replace"):
            if operation["op"] == "replace" and last not in node:
                raise KeyError(operation["path"])
            node[last] = operation["value"]
        elif operation["op"] == "remove":
            del node[last]
        else:
            raise ValueError(operation["op"])
    return result


def zarr_json_bytes(document: dict) -> bytes:
    """Serialize a metadata document the way zarr-python 3.4.2 does."""
    return json.dumps(document, indent=2).encode()


def derive_vector(spec: dict) -> None:
    source = STORES_V2 / f"{LEGACY}.zarr"
    target = STORES_V2 / f"{spec['id']}.zarr"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    raw = (source / "zarr.json").read_bytes()
    document = json.loads(raw)
    if zarr_json_bytes(document) != raw:
        sys.exit("the writer's root zarr.json does not round-trip; stopping")
    (target / "zarr.json").write_bytes(zarr_json_bytes(apply_patch(document, spec["patch"])))


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


def do_derive(crop: Path) -> None:
    for spec in DERIVED:
        derive_vector(spec)
    GOLDENS.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDENS / f"{LEGACY}.json"
    golden_path.write_text(json.dumps(goldens(STORES_V2 / f"{LEGACY}.zarr", crop), indent=2))

    entries = [
        {
            "id": LEGACY,
            "path": f"stores/v2/{LEGACY}.zarr",
            "format_version": 2,
            "class": "valid",
            "layer": None,
            "rule": "format-name",
            "description": "Written by biosigIO 1.2.13 and not changed since.",
            "expect": {"2": {"outcome": "accept", "goldens": f"goldens/{LEGACY}.json"}},
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
                "layer": None,
                "rule": spec["rule"],
                **({"description": spec["description"]} if "description" in spec else {}),
                "derived_from": LEGACY,
                "alteration": {"document": "zarr.json", "patch": spec["patch"]},
                "expect": {"2": spec["expect"]},
                "files": store_files(STORES_V2 / f"{spec['id']}.zarr"),
            }
        )
    manifest = {
        "$comment": "The conformance contract; see conformance/README.md.",
        "spec": "spec/index.md",
        "vectors": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run(
        ["bun", "x", "biome", "format", "--write", str(MANIFEST), str(golden_path)],
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
