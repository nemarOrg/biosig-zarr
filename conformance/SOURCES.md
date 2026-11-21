# Sources of the conformance vectors

Every conformance vector is cut from a real recording that its source dedicated to the public domain,
and this file records where each one came from and every step applied to it.
The recording's samples keep their public-domain dedication;
the other files in `conformance/` are under the Apache License 2.0 (see [`LICENSE.md`](../LICENSE.md)).

## The recording

| Field | Value |
| --- | --- |
| Archive | Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) |
| Dataset | `on009081`, "EEG during Balinese dance movements and balance tasks in expert dancers and non-dancers" (EEG is electroencephalography) |
| Dataset version | `v1.0.0`; NEMAR Digital Object Identifier (DOI) `10.82901/nemar.on009081` |
| Upstream | OpenNeuro `ds009081`, version `1.0.0`, DOI `10.18112/openneuro.ds009081.v1.0.0` |
| License | CC0 (Creative Commons Zero, the public-domain dedication), as the dataset's `dataset_description.json` states (`"License": "CC0"`) |
| Recording | `sub-01/eeg/sub-01_task-rest_eeg.edf`, a resting recording of about 61 seconds, in European Data Format (EDF) |
| Size and digest | 224,464 bytes; SHA-256 (Secure Hash Algorithm, 256-bit) `640a891838f31f1f4087098e288439c7a8d820aaa8d92ff185678f2b3b7f11bb` |
| Content | 18 signals at 100 hertz (Hz), 61 data records of one second each |
| Sidecar | `sub-01/eeg/sub-01_task-rest_channels.tsv`, the Brain Imaging Data Structure (BIDS) channels table: 1,270 bytes; SHA-256 `84c135dc9c357331ca9d64c703622c509ac238a5c2880dee55a483d3d8ce9c4e` |

Both files were read on 2026-11-20, read only, from `https://data.nemar.org/on009081/v1.0.0/sub-01/eeg/`,
with the User-Agent `biosig-zarr-conformance-builder/1`.
The build script refuses either file if its size or digest differs from the values above.

## What was kept

- **Channels**: `Fp1-A1`, `Fp2-A2`, `O1-A1`, and `O2-A2` (type `EEG` in the channels table), and `Add_lead1` (type `MISC`), in that order.
- **Time**: the first 10 data records, which are the first 10 seconds, so 1,000 samples per channel.

## Steps

Every step is in [`tools/vectors/build.py`](../tools/vectors/build.py), and it runs again with
`uv run --project tools/vectors python tools/vectors/build.py all --work <scratch directory>`.

1. **Download** both files and check their sizes and digests.
2. **Crop the EDF file.**
   The samples of the kept channels in the kept records are copied as stored, with no rescaling.
   The header is copied except where the crop changes it:
   the header length, the number of data records, the number of signals,
   and the per-signal fields, which keep only the kept channels.
   The start date and time, the patient and recording fields, and the reserved field are unchanged.
   The crop is 11,536 bytes, SHA-256 `5e34a9cd9436f51049959f068e4a0b32b098e11b7769e76299841d5345be96d8`.
3. **Crop the channels table** to its header row and the rows of the kept channels, in the kept order, unchanged.
   The crop is 445 bytes, SHA-256 `d3504694edd025e40a1d9f3d575e3e06b3c19a6b73c6754323eb2899ad2adcd4`.
   It sits beside the cropped EDF file, so the writer applies it.
4. **Write the store with biosigIO 1.2.13**,
   run as `uvx --from "biosigio[zarr]==1.2.13"` with Python 3.13 and zarr 3.4.2, numcodecs 0.17.1, NumPy 2.5.5, pandas 3.1.1, SciPy 1.18.1, and pyEDFlib 0.1.42,
   calling `Recording.from_file(<crop>)` and then `to_zarr(<store>, exclude_subject_info=True)`, with every other option at its default.
   The channels table sets the types, so the store has two channel groups, `eeg_100hz` and `misc_100hz`,
   and the writer records what the table did to the units in `channels_tsv_units`.
   The recording has no annotations, so the store has zero events.
   Its output is `stores/v2/v2-legacy-name.zarr`, byte for byte.
   Running the writer again reproduces every file except the root `zarr.json`, whose `created_utc` records the time of writing.
5. **Alter the store** to make each other vector (next section).
6. **Write the goldens and the manifest** (see [`README.md`](README.md)).

## Alterations

Each derived vector is `v2-legacy-name` with one change to its root `zarr.json`, and every other file byte-identical.
The change is a JavaScript Object Notation (JSON) Patch, recorded in the vector's `alteration` member of `manifest.json`.
The document is written again the way zarr-python 3.4.2 writes it (`json.dumps` with an indent of 2), which reproduces the writer's bytes exactly before the change.

| Vector | Change to the root attributes |
| --- | --- |
| `v2-new-name` | `format` replaced by `"biosig-zarr"` |
| `v2-unknown-attribute` | `conformance_unknown_attribute` added, an object no reader recognizes |
| `v2-version-3` | `format_version` replaced by `3` |
| `v2-unknown-format` | `format` replaced by `"example-zarr"` |
| `v2-no-channel-groups` | `channel_groups` removed |
