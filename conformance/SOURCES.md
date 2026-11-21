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

## The version 1 vector

`v1-no-format-version` is `v2-legacy-name` with one change to its root `zarr.json`, in `stores/v1/`:
`format_version` removed, and `recording_metadata` replaced by a string holding its JSON text, written by `json.dumps` with its default separators.
That is the one way a version 1 store differs from a version 2 store ("Format version").
It is made the same way as the other derived vectors, and its patch is in `manifest.json`.

## Format version 3

No writer of format version 3 exists, so [`tools/vectors/build.py`](../tools/vectors/build.py) writes these stores itself, from the same crop,
with zarr-python 3.4.2 and NumPy 2.5.5, and no other library.
It writes the metadata documents the text specifies, and the arrays with the codec chains it names,
and it names itself first in each store's `generated_by`, as the software that wrote the hierarchy, followed by zarr-python and NumPy.
It is a one-purpose vector builder, not a writer: it exports nothing, and nothing outside `tools/` imports it.

### What was kept

- **Channels**: the four EEG channels in uniform groups, and `Add_lead1` in the timestamped group of `v3-timestamped`.
  The channel types and units come from the cropped channels table; its unit `µV` replaces the EDF file's `uV`, which is the same unit, so `channels_tsv_units` counts every channel as relabelled and none as converted.
- **The source fields**: `source_sample_type` `int16`, the type of an EDF sample;
  `source_adc_bits` `null`, because EDF does not state the converter's bit depth;
  and for each channel, from its EDF header, `source_step` `(physical maximum - physical minimum) / (digital maximum - digital minimum)`,
  `source_offset` `physical minimum - digital minimum * source_step`,
  and `source_digital_range` `[digital minimum, digital maximum]`, which is `[-32768, 32767]` for every channel here.

### Steps

1. **Source values.**
   Each source sample's physical value is `source_code * source_step + source_offset`, in 64-bit floating point, as "The derivation list" defines it.
2. **Resampling**, in `v3-gap-10hz` only:
   a windowed-sinc low-pass finite impulse response filter of 41 taps, with a Hamming window and its cutoff at half the served rate, in NumPy,
   is applied to each run of finite source samples of each valid interval on its own, with reflected edges;
   stored sample `i` of interval `k` then takes the filtered value at its nearest source sample, `round((i - start_k) * source rate / rate)`,
   and is missing when that source sample is not finite ("Missing values").
   The root `anti_alias_filter` says the same.
3. **Placing the intervals** on the grid by the rules of "Channel groups" and "Valid intervals", with `start_time` 0.
4. **Quantization**: each channel separately, with the text's informative formula ("Dequantization"), over its acquired, finite samples, onto the codes `-32767` to `32767`;
   every sample outside a valid interval, and every missing sample, is stored as the missing value `-32768`, which is also each signal array's fill value.
   The step is not the source's, so every channel's `derivation` includes `requantized`.
5. **View levels**: `view_downsample` 4, adding levels until one has at most 512 columns (2 in `v3-gap-10hz`, so that it has levels with factors 4 and 16), a parameter of the builder, as of any writer;
   each column holds the minimum and maximum of the acquired, non-missing level-0 samples it covers, and the missing value when there are none.
6. **Chunks**: inner chunks of 400 samples in shards of 1200 in `v3-continuous` and `v3-timestamped`, and of 4 in shards of 16 in `v3-gap-10hz`.
   zarr-python writes no chunk that holds only the fill value, so the inner chunk of samples 20 to 23 of `v3-gap-10hz`, which lies wholly in the gap, is absent from its shard's index,
   and so are the chunks of the `duration` and `code` event arrays, whose values all equal the fill value 0.
7. **Events**: the recording has no annotations, so each vector carries events the builder adds at chosen onsets, an alteration recorded here:
   duration 0 and code 0, labeled `conformance marker`, with `onset_source_basis` `timeline`.
   `v3-continuous` and `v3-timestamped` have onsets 1.0, 2.0, 9.5 and 11.0 seconds; `v3-gap-10hz` has 0.25, 1.25, 2.02 and 3.25 seconds.
   0.25, 1.25 and 3.25 seconds at 10 Hz are 2.5, 12.5 and 32.5 exactly in 64-bit floating point, which the builder and the tests check.
8. **Time of writing**: `created_utc` is `2026-11-21T02:11:15Z`, when the vectors were first written; a rebuild keeps it, so a rebuild reproduces every file byte for byte.

### The vectors written

- **`v3-continuous`**: the group `eeg_100hz`, the four EEG channels at their source rate of 100 Hz for the 10 seconds of the crop, 1,000 samples, in one valid interval with `source_time` 0.0; nothing is resampled.
- **`v3-gap-10hz`**: the group `eeg_10hz`, from the first 4 seconds of the four EEG channels, 400 source samples, altered in two recorded ways:
  - source samples 200 to 239 are removed, as if the recorder had paused for 0.4 seconds, so the source has two segments, starting at 0.0 and 2.4 seconds;
  - source sample 300 of `O1-A1` is replaced by not a number (NaN), as if one sample had been dropped.

  The rate cap for `EEG` in `modality_rates` is 10 Hz, so each segment is resampled to 10 Hz, giving the valid intervals `[0, 20)` with `source_time` 0.0 and `[24, 40)` with `source_time` 2.4, and `n_samples` 40.
  Stored sample 30 of `O1-A1` has the non-finite value as its nearest source sample, so it is missing:
  that channel has `nonfinite_samples` 1, `usable_for_inference` `false`, and `derivation` `["resampled", "nonfinite_to_missing", "requantized"]`;
  the other channels have `["resampled", "requantized"]`.
- **`v3-timestamped`**: `eeg_100hz` as in `v3-continuous`, and the timestamped group `misc_timestamped`, which holds `Add_lead1` at the source's own sample times:
  the sample `s` of data record `r` is at `r * duration + s * duration / n`, with the record duration and the number of samples per record `n` from the EDF header, so its `time` has an empty `derivation`.
  Its `nominal_rate` is the source rate, 100 Hz, and its `continuity` is `continuous`.
  `zarr_conventions` also holds an entry with the `uuid` `7172d401-2def-4e11-b5b7-db7f6673c195`, minted for this vector, which names no convention.

### Alterations

Each derived version 3 vector is its base with one JSON Patch applied to one metadata document, and every other file byte-identical, as for version 2.

| Vector | Base | Document | Change to the attributes |
| --- | --- | --- | --- |
| `v3-start-time` | `v3-continuous` | `eeg_100hz/zarr.json` | `start_time` replaced by `1.5`, and the interval's `source_time` with it |
| `v3-version-4` | `v3-continuous` | `zarr.json` | `format_version` replaced by `4` |
| `v3-unknown-format` | `v3-continuous` | `zarr.json` | `format` replaced by `"example-zarr"` |
| `v3-no-kind` | `v3-continuous` | `eeg_100hz/zarr.json` | `kind` removed |
| `v3-unknown-kind` | `v3-continuous` | `eeg_100hz/zarr.json` | `kind` replaced by `"sparse"` |
| `v3-timestamped-listed` | `v3-timestamped` | `zarr.json` | `misc_timestamped` added to `channel_groups` |
| `v3-bad-intervals` | `v3-gap-10hz` | `eeg_10hz/zarr.json` | the first interval's `stop` replaced by `30`, so it overlaps the second |
| `v3-no-conventions` | `v3-continuous` | `zarr.json` | `zarr_conventions` removed |
| `v3-conventions-extra-member` | `v3-continuous` | `zarr.json` | the member `version` added to the biosig-zarr entry of `zarr_conventions` |
