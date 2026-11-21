# biosig-zarr Format (pre-beta)

> **Caution. Draft text, proposed and not accepted.**
> This document is the text proposed by the Request for Comments (RFC) RFC-0001, in [nemarOrg/rfcs](https://github.com/nemarOrg/rfcs).
> It specifies `format_version` 3, which no implementation writes or reads yet.
> The accepted text is release `2.0.0`, for `format_version` 2.
> This draft is pre-beta: it can change without notice, and nothing in it is a compatibility promise yet.
> For stores served by the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR),
> the [Store Contract](https://docs.nemar.org/platform/zarr/store-contract/) and the [Format Stability Policy](https://docs.nemar.org/platform/zarr/format-stability/) remain the binding documents.
> Where this document disagrees with them, those pages govern NEMAR's stores until this specification reaches beta.

## Status of this document

This document specifies `format_version` 3 of the format.
The specification defines the format; implementations follow it.
[biosigIO](https://github.com/neuromechanist/biosigio) is one exemplar implementation, and the first:
the version 2 text was written from what its release 1.2.13 produces, so that the stores already in use conform,
and where biosigIO and this document disagree, the disagreement is either a defect in biosigIO or an [open question](#open-questions), never a silent change to the format.
Every statement about existing writer behavior was checked against that release's source,
against stores written with it for this purpose,
and against one public NEMAR store on 2026-11-18.
[Appendix A](#appendix-a-exemplar-implementation-map) lists where biosigIO implements each rule of version 2.

Version 3 runs ahead of every implementation.
It adds a time model (two kinds of channel group, valid intervals, declared missing values, a start time per group),
the resolution of the source,
a record of every lossy step,
and rules that keep a reader of an earlier version from misreading a version 3 store.
No store carries version 3 yet, and [Reading earlier versions](#reading-earlier-versions) says how a version 3 reader reads the stores that exist.

Five parts of this document also run ahead of any implementation, and each is marked **Proposed** where it appears:

- **The name `biosig-zarr`.**
  biosigIO 1.2.13 writes the legacy name `biosigio-zarr`, and its reader accepts only that name.
  The rename lands with the first writer of version 3; no store carries the new name yet.
- **The packaged form (`.bzx`).**
  No tool writes or reads it yet.
- **The `generated_by` attribute.**
  No writer produces it yet.
- **The `zarr_conventions` attribute.**
  No writer produces it yet.
- **The conformance classes.**
  The first schemas and conformance vectors are in this repository, in [`schemas/`](../schemas/) and [`conformance/`](../conformance/); no validator of whole stores exists yet.

RFC-0001 puts parts of this text up for comment.
Each such place is marked **Open for comment** with the number of the RFC question that asks about it.
Anything no implementation does today, and that version 3 does not specify, is listed under [Open questions](#open-questions) and is not specified here.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in RFC 2119 and RFC 8174,
when, and only when, they appear in all capitals.
RFC 2119 and RFC 8174 are documents of the Internet Engineering Task Force (IETF), separate from the Requests for Comments in nemarOrg/rfcs.
In the attribute tables, CONDITIONAL means the attribute MUST be present when its stated condition holds and MUST be absent otherwise.
In formulas, `round(x)` means `floor(x + 0.5)`, evaluated in 64-bit floating point: a value exactly halfway between two integers rounds up.
Many libraries round halves to the even integer instead, so a writer or reader MUST use this definition wherever this document says `round`.

## Scope and non-goals

biosig-zarr stores **one recording** of biosignals as a Zarr version 3 (v3) hierarchy:
electroencephalography (EEG), magnetoencephalography (MEG), intracranial EEG (iEEG), electromyography (EMG), and the channels recorded alongside them.
The recording can be continuous or can have gaps, and a signal in it can be sampled on a uniform grid or at irregular times.
The layout serves three kinds of read from one copy:
interactive viewing, windowed analysis or model inference, and sequential streaming for model training.

A biosig-zarr store is:

- **Derived.**
  It is made from a source recording, and the source stays authoritative.
- **Lossy by default.**
  Signals above a per-modality rate cap are resampled down to it,
  samples are quantized to 16-bit signed integers (`int16`) by default,
  and non-finite samples in an integer store are stored as missing.
  Every step that makes a stored sample differ from the source sample is recorded in the [derivation list](#the-derivation-list).
- **An analysis and serving representation.**
  It is shaped for fast partial reads over a network, not for fidelity to the source file.

The following are non-goals:

- **Not an archival format.**
  A store MUST NOT be treated as the record of what was acquired.
  The source recording, in its own format, is that record.
- **Not a dataset container.**
  A store holds one recording.
  It has no notion of subjects, sessions, a participants table, a dataset description, or an index across recordings.
  A publisher that needs those defines them outside the store.
- **Not a replacement for source metadata.**
  A store carries what a reader needs to interpret its samples and events.
  It does not carry the full sidecar metadata of a Brain Imaging Data Structure (BIDS) dataset.
- **Not a processing record.**
  The format records the steps of its own conversion (resampling, placing timestamps on a grid, unit conversion, quantization, and the handling of non-finite samples), and nothing else.
  It has no place for re-referencing, filtering, artifact removal, or segmentation into trials.
- **Not lossless by guarantee.**
  A store can hold a [bit-exact copy](#exact-copies) of a source's samples, but a writer is not required to make one,
  and even a 32-bit floating point (`float32`) store is resampled when the source rate exceeds the cap.

## Terminology

- **Recording**: one acquisition, with one or more channels, possibly paused and resumed.
- **Source**: the file or files the recording was read from.
- **Store**: one biosig-zarr hierarchy, holding one recording.
- **Directory form**: a store laid out as a directory tree of Zarr v3 objects, conventionally named with the suffix `.zarr`.
- **Packaged form**: a store packed into one ZIP file with the suffix `.bzx`.
- **Recording timeline**: the one time axis of a store, in seconds; see [Recording timeline](#recording-timeline).
- **Channel group**: a Zarr group holding channels of one modality that share one time base.
- **Uniform group**: a channel group whose samples lie on one grid with a fixed rate.
- **Timestamped group**: a channel group with one explicit time per sample.
- **Valid interval**: a range of sample indices of a uniform group where samples were acquired.
- **Missing value**: the stored value that means "no sample here".
- **Level 0**: the full-resolution signal array of a uniform group.
- **View level**: a downsampled minimum and maximum envelope of level 0, for rendering only.
- **Digital value**: a sample as stored in an array.
- **Physical value**: a sample in the channel's unit, recovered from a digital value by [dequantization](#dequantization).
- **Served rate**: the sampling rate of level 0, in hertz (Hz).
- **Source rate**: the sampling rate of the source.
- **Writer**: software that produces a store.
- **Reader**: software that consumes a store.
- **Publisher**: a party that distributes stores.
- **Profile**: a publisher's documented set of restrictions and additions on top of this specification.
  NEMAR's is the only profile that exists today.

## Format identification and versioning

A store identifies itself in the `attributes` of its root `zarr.json`.

### Format name

**Proposed.**
The root attribute `format` MUST be the string `biosig-zarr`.

The legacy name `biosigio-zarr` denotes the same format.
A reader MUST accept both names, permanently, and MUST treat a store identically under either.
A reader MUST NOT infer anything else about a store from which name it carries.
A writer of version 3 MUST write `biosig-zarr`.

A reader MUST refuse a store whose `format` is neither name.

> **Note. Where the rename stands.**
> biosigIO 1.2.13 writes `biosigio-zarr` and refuses to read any other name.
> Until a release that accepts both names is in use, a store carrying `biosig-zarr` is not readable by biosigIO's reader.
> NEMAR's version 2 stores keep the legacy name until they are converted again as version 3 stores;
> NEMAR does not rename a store by editing its metadata (nemar-cli ADR 0131).

### Zarr convention

**Proposed.**
A version 3 store declares itself under the Zarr conventions mechanism as well.

- The root attribute `zarr_conventions` MUST be an array that holds exactly one entry whose `uuid` is `3d7d2fe9-20a5-46d9-a92b-9170cddf6633`, the identifier of the biosig-zarr convention.
- That entry SHOULD have `name` equal to `"biosig-zarr"`, MAY have `spec_url`, `schema_url` and `description`,
  and MUST NOT have other members, as the Zarr conventions specification requires.
- The array MAY hold entries for other conventions.
- A reader identifies a store by `format` and `format_version`.
  A reader MUST NOT refuse a store because `zarr_conventions` holds an entry it does not recognize.
- A version 2 store has no `zarr_conventions`, and a reader MUST NOT require it on one.

The identifier never changes; ADR 0004 of this repository records it.

**Open for comment: RFC-0001 question 5** (the shape of the declaration).

### Format version

The root attribute `format_version` MUST be an integer.
This document specifies version 3.
A writer that implements this document MUST write `format_version` 3 on every store it writes, including a continuous, uniformly sampled recording.

- Version 1 differs from version 2 in one respect:
  `recording_metadata` is a string holding JavaScript Object Notation (JSON) text, where version 2 holds a JSON object.
  This document no longer covers version 1 stores.
- Version 2 differs from version 3 in everything [Reading earlier versions](#reading-earlier-versions) lists.
- A store with no `format_version` attribute is, historically, a version 1 store; a reader of this document MUST refuse it as unsupported.
- A reader SHOULD accept a number with an integral value, such as `3.0`, as that integer.
- A reader MUST refuse a store whose `format_version` is greater than the highest version it implements.
  It MUST NOT attempt to read such a store on the assumption that the layout is unchanged.

### Reading earlier versions

A reader that implements version 3 MUST also read version 2 stores.
This is settled, and not open for comment.
Version 1 stores are no longer covered by this document, so whether a reader reads them is outside it.
A reader reads a version 2 store as a version 3 store with these values:

- Every group named in `channel_groups` is a uniform group, and there is no timestamped group.
- `start_time` is 0, `valid_intervals` is the single interval `{ "start": 0, "stop": n_samples, "source_time": 0 }`, and `time_regularization` is `null`.
- `missing_value` is `null` on every array.
- Every group's storage type is the root `dtype`.
- The `events` group's `onset_source_basis` is `"unknown"`.
- The source fields of [Sample resolution](#sample-resolution) are unknown, and `derivation` is unknown, not empty.

A version 2 store has no field that claims continuity, so these values are what it implies, not what was checked against its source.
A reader SHOULD tell its user that continuity is not recorded in a version 2 store.

A store MUST NOT be changed from one `format_version` to another by editing its metadata.
A version 3 store is written from its source, so that its valid intervals, source fields and derivation describe the source and not an assumption.

### What changes the version

- Adding an attribute does not change `format_version`.
  A reader MUST ignore attributes it does not recognize.
- Chunk and shard sizes are not part of the version.
  A reader MUST take every chunk and shard shape from array metadata, never from a constant.
- A change that makes a reader conforming to this document return wrong data, or no data, MUST increase `format_version`.
- A new kind of channel group MUST increase `format_version`.
- The [packaged form](#the-packaged-form-bzx) shares `format_version` with the store:
  a change to the packing rules that makes a conforming reader fail MUST increase it.
  **Open for comment: RFC-0001 question 13.**

Version 2 grew by addition, so two version 2 stores can differ in which attributes they carry.
A reader of a version 2 store MUST treat each attribute in this table as possibly absent:

| First written by biosigIO | Attributes |
| --- | --- |
| 1.2.1 | `channels[].nonfinite_samples` |
| 1.2.6 | `n_view_levels`, `view_levels`, `chunk_seconds`, `shard_seconds`, `chunk_samples`, `shard_samples`, `source_rate_hz`, `view_chunk_columns` (root and group), `view_downsample` on a group, `chunk_columns` |
| 1.2.7 | root `channels_tsv_units`, `channels[].bids_unit` |
| 1.2.11 | `subject_info_excluded` |

A reader that needs one of these and does not find it SHOULD fall back to array metadata, or refuse with a message that names the missing attribute.

The store's `format_version` is independent of any version number a publisher gives its own documents, such as a dataset index.

## The directory form

### Zarr requirements

- A store MUST be a Zarr v3 hierarchy.
  Every node's metadata is in a `zarr.json` object.
  A store MUST NOT use Zarr version 2 metadata.
- biosigIO's writer writes no consolidated metadata.
  A reader MUST NOT depend on consolidated metadata being present.
- **A store is navigable without listing.**
  Every node path is derivable from attributes:
  the root's `channel_groups` and `timestamped_groups` name the channel groups,
  each uniform group's `view_levels` names its view arrays,
  and the `events` group's `n_events` says whether its arrays exist.
  A writer MUST preserve this property.
  A reader SHOULD navigate by attributes, because a store served over the Hypertext Transfer Protocol (HTTP) usually cannot be listed.
- The root group MUST NOT contain child nodes other than the channel groups named in `channel_groups` and `timestamped_groups` and the `events` group.
  biosigIO's reader treats every root child except `events` as a channel group.
- A store MUST hold at least one channel group.
- A reader MUST take the chunk key encoding and the codec chain of every array from that array's metadata.

### Hierarchy

```
<name>.zarr/                  root group
  zarr.json                   root attributes
  <modality>_<rate>hz/        a uniform group, named in channel_groups
    zarr.json                 group attributes, including channels[]
    0/                        level 0: signal, shape [n_channels, n_samples], sharded
    view/                     group, always present, no attributes
      1/, 2/, ...             view levels: shape [2, n_channels, n_L], not sharded
  <timestamped name>/         a timestamped group, named in timestamped_groups
    zarr.json                 group attributes, including channels[]
    time/                     float64, shape [n_samples], sharded
    values/                   shape [n_channels, n_samples], sharded
    time_index/               float64, shape [n_chunks], one chunk
  events/                     group, always present
    onset/, duration/, code/  one-dimensional arrays, present when n_events > 0
```

### Root attributes

In every attribute table in this document, the Presence column states what a writer conforming to this document writes.
A version 2 store written by an older release can lack the attributes listed under [What changes the version](#what-changes-the-version).

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `format` | string | REQUIRED | See [Format name](#format-name). |
| `format_version` | integer | REQUIRED | `3`. See [Format version](#format-version). |
| `zarr_conventions` | array of objects | REQUIRED (**Proposed**) | See [Zarr convention](#zarr-convention). |
| `channel_groups` | array of strings | REQUIRED | The names of the uniform groups, and only those, in the order they were written. It MAY be empty. |
| `timestamped_groups` | array of strings | REQUIRED | The names of the timestamped groups, in the order they were written. It MAY be empty. |
| `dtype` | string | REQUIRED | The default storage type of the store's signal arrays: `"int16"`, `"int32"`, `"float32"`, or `"float64"`. See [Sample resolution](#sample-resolution). |
| `source_sample_type` | string | REQUIRED | The default type of a decoded source sample. See [Sample resolution](#sample-resolution). |
| `source_adc_bits` | integer or `null` | REQUIRED | The default bit depth of the source's analog-to-digital converter (ADC). See [Sample resolution](#sample-resolution). |
| `origin_source_time` | number or `null` | OPTIONAL | See [Recording timeline](#recording-timeline). |
| `modality_rates` | object | REQUIRED | The rate caps the writer applied, in Hz, keyed by uppercase modality name. |
| `anti_alias_filter` | string | REQUIRED | A free-text description of the resampling filter. |
| `view_downsample` | integer | REQUIRED | The decimation factor between consecutive view levels. |
| `view_chunk_columns` | integer | REQUIRED | The nominal number of time columns per view chunk. |
| `source_format` | string | REQUIRED | The name of the source file format, or `"n/a"` when unknown. |
| `recording_metadata` | object | REQUIRED | Technical metadata about the recording; see [Recording metadata](#recording-metadata). It MAY be empty. |
| `created_utc` | string | REQUIRED | When the store was written, as an International Organization for Standardization (ISO) 8601 timestamp in Coordinated Universal Time (UTC). |
| `subject_info_excluded` | boolean | CONDITIONAL | `true` when the writer's subject-information exclusion ran on this store; see [Security and privacy](#security-and-privacy). |
| `channels_tsv_units` | object | CONDITIONAL | Present when a BIDS `channels.tsv` was applied: a summary of what it did to channel units. |
| `generated_by` | array of objects | REQUIRED (**Proposed**) | The software that produced the store, and its versions; see [Generating software](#generating-software). |
| `biosigio_version` | string | OPTIONAL, deprecated | The release of biosigIO that wrote the store. Superseded by `generated_by`; kept so older readers keep working. |
| `note` | string | OPTIONAL | Free text for a human reader. |

A name MUST NOT appear in both `channel_groups` and `timestamped_groups`.
`channel_groups` keeps its version 2 name and meaning, so a reader that navigates by it reaches only uniform groups.

A reader needs only `format`, `format_version`, `channel_groups`, and `timestamped_groups` from the root to locate the signal.
The remaining REQUIRED attributes record how the store was derived.
A reader MUST NOT require `biosigio_version` or `note`,
and until `generated_by` and `zarr_conventions` leave Proposed, a reader MUST NOT require them either.

`channels_tsv_units` holds the integer counts `converted`, `relabelled`, and `kept_importer_unit`, and the boolean `units_column_present`.
It can also hold `matched_case_insensitive`, a map from a sidecar row name to the channel label it matched only by ignoring case.

**Example (illustrative).**
The root attributes of a store converted from a BioSemi Data Format (BDF) file, with `recording_metadata`, `generated_by` and a profile's additions left out:

```json
{
  "format": "biosig-zarr",
  "format_version": 3,
  "zarr_conventions": [
    { "uuid": "3d7d2fe9-20a5-46d9-a92b-9170cddf6633", "name": "biosig-zarr" }
  ],
  "channel_groups": ["eeg_250hz", "misc_64hz"],
  "timestamped_groups": [],
  "dtype": "int16",
  "source_sample_type": "int24",
  "source_adc_bits": null,
  "modality_rates": { "EEG": 250, "MEG": 250, "IEEG": 1000, "EMG": 1000 },
  "anti_alias_filter": "scipy.signal.resample_poly",
  "view_downsample": 4,
  "view_chunk_columns": 4096,
  "source_format": "BDF",
  "created_utc": "2026-11-20T12:00:00Z"
}
```

### Recording timeline

A store has one recording timeline, in seconds, as 64-bit floating point numbers.
Every time in a store is a time on it:
`start_time` and `source_time` in a uniform group, `time` in a timestamped group, and `onset` in the `events` group.

- Time 0 is the instant the source's own clock calls the start of the recording:
  the start date and time of a European Data Format (EDF) file, the first sample of a BrainVision or Functional Image File Format (FIF) file,
  and for an Extensible Data Format (XDF) file the earliest first-sample timestamp among the streams written, after clock correction.
- A writer MUST place every channel group and every event on this one timeline.
  Gaps count: an event recorded after a 30-second pause has an onset 30 seconds later than its position in the samples without the gap.
- `origin_source_time` is the value of the source's own clock at time 0, in seconds, for a source that has one, such as the Lab Streaming Layer (LSL) clock in XDF.
  With it a reader can restore source timestamps exactly.
  It is absent or `null` when the source has no such clock.

The absolute date and time of time 0 has no defined attribute.
**Open for comment: RFC-0001 question 6** (see [open question](#open-questions) 10).

**Open for comment: RFC-0001 question 37** (one timeline, with a `start_time` per uniform group).

### Channel groups

Every channel group carries the group attribute `kind`, whose value is `"uniform"` or `"timestamped"`.
A uniform group is described here and under [Level-0 array](#level-0-array) and [View pyramid](#view-pyramid);
a timestamped group is described under [Timestamped groups](#timestamped-groups).
What a reader does with `kind` is under [Reader safety](#reader-safety).

A writer puts channels into one uniform group per pair of modality and source rate, with the source rate rounded to the nearest integer.
Every channel in a uniform group therefore has the same served rate, the same `start_time`, the same valid intervals, and the same number of samples.
Channels that were not acquired over the same intervals MUST be in separate groups.

**Naming.**
A group name is opaque.
A writer conventionally names a uniform group `<modality>_<rate>hz`,
with the modality in lowercase and the served rate rounded to the nearest integer, for example `eeg_250hz`.
The name carries the served rate, not the source rate.
biosigIO's version 2 writer, when two source rates of one modality map to the same served rate, appends `_from<source rate>` to the second name.
A group name MUST be unique within the store and MUST appear in exactly one of `channel_groups` and `timestamped_groups`.
A reader MUST NOT parse the modality, the rate or the kind out of a group name; it MUST read them from the group attributes.

**Served rate.**
The served rate of a uniform group is `min(source rate, cap)`,
where the cap is the entry for the group's modality in `modality_rates`.
A modality with no entry keeps its source rate.
A writer MUST NOT upsample.
A writer MUST NOT round `rate`: it is the exact served rate, whatever the group name and the grouping key say.
The caps are a writer parameter and are recorded in the store;
biosigIO's writer's defaults are 250 Hz for `EEG` and `MEG`, and 1000 Hz for `IEEG` and `EMG`.
**Open for comment: RFC-0001 question 2** (rates that are not integers).

**Resampling.**
Continuous channels are resampled with an anti-aliased polyphase filter.
Discrete channels, whose `channel_type` is `TRIG`, `SYSCLOCK`, or `CTRL`, are resampled by taking the nearest source sample, with no filter, so step edges survive.
A writer MUST resample each valid interval on its own:
a filter MUST NOT read source samples from two intervals at once, because those samples were never adjacent.
For interval `k`, with `m_k` source samples, a writer MUST derive its place on the grid as follows:

- `start_k` is 0 for the first interval;
  for a later interval it is `round((source_time_k - start_time) * rate)` when its `source_time` is a number, and the previous interval's `stop` when it is `null`.
- The interval holds `n_k = max(1, round(m_k * rate / channel source rate))` samples, and `stop_k = start_k + n_k`.
- `n_samples` is the last interval's `stop`: the grid points from sample 0 to the last sample of the last interval, gaps included.
  For a recording with one interval it is `round(m * rate / channel source rate)`, as in version 2.

When `start_k` would be less than the previous `stop`, the intervals overlap on the grid, and [Valid intervals](#valid-intervals) says what the writer does.

**Attributes of every group.**

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `kind` | string | REQUIRED | `"uniform"` or `"timestamped"`. |
| `modality` | string | REQUIRED | The modality of the group, in uppercase, such as `EEG`. |
| `n_channels` | integer | REQUIRED | The number of channels. |
| `n_samples` | integer | REQUIRED | The number of samples per channel: of level 0 in a uniform group, gaps included; of `time` in a timestamped group. |
| `channels` | array of objects | REQUIRED | One object per channel; see below. |
| `dtype` | string | OPTIONAL | The storage type of this group's signal arrays, overriding the root `dtype`; see [Sample resolution](#sample-resolution). |

**Attributes of a uniform group.**

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `rate` | number | REQUIRED | The exact served rate, in Hz. |
| `original_rate` | number | REQUIRED | The source rate used as the grouping key: rounded to an integer. |
| `start_time` | number | REQUIRED | The time of sample 0 on the recording timeline, in seconds. It MAY be negative. |
| `valid_intervals` | array of objects | REQUIRED | Where acquired samples exist; see [Valid intervals](#valid-intervals). Never empty. |
| `time_regularization` | object or `null` | REQUIRED | `null` when the source declared uniform sampling; otherwise how per-sample timestamps were placed on the grid; see [Time regularization](#time-regularization). |
| `n_view_levels` | integer | REQUIRED | The number of view arrays in the group. It can be 0. |
| `view_levels` | array of integers | REQUIRED | The view level numbers, contiguous from 1. Empty when `n_view_levels` is 0. |
| `view_downsample` | integer | REQUIRED | The decimation factor between consecutive view levels. |
| `view_chunk_columns` | integer | REQUIRED | The nominal number of time columns per view chunk. |
| `chunk_seconds` | number | REQUIRED | The nominal time span of a level-0 inner chunk, in seconds. |
| `shard_seconds` | number | REQUIRED | The nominal time span of a level-0 shard, in seconds. |

**Channel objects.**
`channels` MUST hold exactly `n_channels` objects.

| Member | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `label` | string | REQUIRED | The channel name. |
| `row_index` | integer | REQUIRED | The channel's index along axis 0 of the level-0 array, or of `values` in a timestamped group. |
| `channel_type` | string | REQUIRED | The channel type, in uppercase, such as `EEG` or `TRIG`. |
| `modality` | string | REQUIRED | The modality of the group. |
| `unit` | string | REQUIRED | The unit of the channel's physical values, or `"n/a"` when unknown. |
| `prefilter` | string | REQUIRED | Free text describing acquisition filtering, or `"n/a"`. |
| `original_rate` | number | CONDITIONAL | Present in a uniform group: the channel's source rate, in Hz. |
| `target_rate` | number | CONDITIONAL | Present in a uniform group: the served rate, in Hz. |
| `anti_aliased` | boolean | CONDITIONAL | Present in a uniform group: `true` when the channel is continuous and was downsampled. |
| `usable_for_inference` | boolean | REQUIRED | `false` for a discrete channel, and for a channel that held non-finite source samples. |
| `scale` | number | REQUIRED | A copy of this channel's entry in the `scale` array of level 0, or of `values`. |
| `offset` | number | REQUIRED | A copy of this channel's entry in the `offset` array of level 0, or of `values`. |
| `source_sample_type` | string | OPTIONAL | Overrides the root value for this channel; see [Sample resolution](#sample-resolution). |
| `source_adc_bits` | integer or `null` | OPTIONAL | Overrides the root value for this channel. |
| `source_step` | number or `null` | REQUIRED | One source digital step, in `unit`. |
| `source_offset` | number or `null` | REQUIRED | The physical value of source digital code 0, in `unit`. |
| `source_digital_range` | array of two integers, or `null` | REQUIRED | The digital minimum and maximum the source declares. |
| `derivation` | array of strings | REQUIRED | Every step that made a stored sample differ from the source sample; see [The derivation list](#the-derivation-list). |
| `nonfinite_samples` | integer | CONDITIONAL | Present when non-finite source samples were stored as missing, or, in a version 2 store, replaced: how many. |
| `bids_unit` | string | CONDITIONAL | Present when a BIDS `channels.tsv` declared a unit that the writer recorded but did not adopt. |

The `row_index` values of a group MUST be the integers 0 to `n_channels - 1`, each used once.
A reader MUST address a channel's samples by `row_index`, not by its position in `channels` and not by `label`.
A writer SHOULD write unique labels within a group.
A reader MUST tolerate repeated labels, which exist in stores written before biosigIO's writer began to suffix them.

`unit` is the unit of the values dequantization returns.
A reader MUST read it per channel and MUST NOT assume a unit from the modality.

`usable_for_inference` says whether a channel is fit to use as input to analysis or machine learning.

### Level-0 array

Each uniform group MUST contain an array named `0`, written as follows.

- **Shape**: the array MUST have shape `[n_channels, n_samples]`.
  Axis 0 is the channel, axis 1 is time.
- **Data type**: the array's data type MUST be the group's storage type (see [Sample resolution](#sample-resolution)).
- **Sharding**: the array MUST use the `sharding_indexed` codec.
  The shard shape, which is the array's chunk grid shape, is `[n_channels, shard_samples]`.
  The inner chunk shape is `[n_channels, chunk_samples]`.
- **Every inner chunk spans every channel.**
  A writer MUST NOT split an inner chunk or a shard along the channel axis.
- **Inner codec chain**: the chain MUST be `bytes` with little-endian byte order, then `blosc` with the `zstd` compressor.
- **Shard index**: the index codecs MUST be `bytes` with little-endian byte order, then `crc32c`.
- **Fill value**: see [Missing values](#missing-values).

biosigIO's version 2 writer uses compression level 5, byte shuffle, a fill value of 0, and an index at the end of each shard.
Those four are its choices, not requirements, and a reader MUST take them from the array metadata.

`shard_samples` MUST be a positive integer multiple of `chunk_samples`.
It can exceed `n_samples`: a recording shorter than one nominal shard is written as a single shard rounded up to a whole number of inner chunks.

This is the array metadata biosigIO's version 2 writer produces for a four-channel, 175000-sample `int16` group, attributes omitted.
A version 3 writer writes the same metadata, except that `fill_value` is `-32768`, the declared missing value:

```json
{
  "zarr_format": 3,
  "node_type": "array",
  "shape": [4, 175000],
  "data_type": "int16",
  "chunk_grid": { "name": "regular", "configuration": { "chunk_shape": [4, 75000] } },
  "chunk_key_encoding": { "name": "default", "configuration": { "separator": "/" } },
  "fill_value": 0,
  "codecs": [
    {
      "name": "sharding_indexed",
      "configuration": {
        "chunk_shape": [4, 1000],
        "codecs": [
          { "name": "bytes", "configuration": { "endian": "little" } },
          { "name": "blosc", "configuration": { "typesize": 2, "cname": "zstd", "clevel": 5, "shuffle": "shuffle", "blocksize": 0 } }
        ],
        "index_codecs": [
          { "name": "bytes", "configuration": { "endian": "little" } },
          { "name": "crc32c" }
        ],
        "index_location": "end"
      }
    }
  ],
  "storage_transformers": []
}
```

**Level-0 attributes.**

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `level` | integer | REQUIRED | `0`. |
| `kind` | string | REQUIRED | `"signal"`. |
| `rate` | number | REQUIRED | The served rate, in Hz. |
| `source_rate_hz` | number | REQUIRED | The source rate the group came from, in Hz. |
| `downsample_factor` | integer | REQUIRED | `1`. |
| `chunk_samples` | integer | REQUIRED | The inner chunk length along time, in samples. |
| `shard_samples` | integer | REQUIRED | The shard length along time, in samples. |
| `anti_aliased` | boolean | REQUIRED | `true` when any channel in the group is `anti_aliased`. |
| `usable_for_inference` | boolean | REQUIRED | `true` when any channel in the group is `usable_for_inference`. |
| `scale` | array of numbers | REQUIRED | One finite, nonzero factor per channel, indexed by `row_index`. |
| `offset` | array of numbers | REQUIRED | One finite offset per channel, indexed by `row_index`. |
| `missing_value` | scalar or `null` | REQUIRED | See [Missing values](#missing-values). |
| `physical_formula` | string | REQUIRED | The literal text `physical = digital * scale + offset`. |

`scale` and `offset` MUST each hold exactly `n_channels` numbers.
`chunk_samples` and `shard_samples` restate the array metadata; where they differ, the array metadata governs.

**Time axis.**
Level 0 of a uniform group is sampled on one grid.
Sample `i` lies at `start_time + i / rate` seconds on the recording timeline.
Only the samples inside a [valid interval](#valid-intervals) were acquired.

### Valid intervals

`valid_intervals` says where a uniform group holds acquired samples.
A continuous recording has exactly one interval, so a store states continuity instead of implying it.
Each entry is an object:

| Member | Type | Meaning |
| --- | --- | --- |
| `start` | integer | The first sample index of the interval. |
| `stop` | integer | One past the last sample index of the interval. |
| `source_time` | number or `null` | The time of the interval's first sample as the source states it, converted to the recording timeline (not a reading of the source's own clock); `null` when the source does not say. |

- An interval is half-open: it holds the samples `start` to `stop - 1`, and the sample `stop` is not in it.
- Intervals MUST be sorted by `start`, non-empty (`start` less than `stop`), and non-overlapping.
- The first interval's `start` MUST be 0, and the last interval's `stop` MUST be `n_samples`.
  Time before the first sample is expressed by `start_time`, not by a leading gap.
- When `source_time` is a number, `start` MUST equal `round((source_time - start_time) * rate)`.
  The placement error, `source_time - (start_time + start / rate)`, is then at most half a sample period, up to floating-point rounding, and a reader can compute it from the two numbers.
- When `source_time` is `null`, the time that elapsed before the interval is unknown,
  as with a BrainVision "New Segment" marker with no date, an EEGLAB `boundary` event, or runs that were concatenated.
  The interval's `start` MUST equal the previous interval's `stop`, or 0 for the first interval.
  Grid times from that interval on are a convention, not a measurement:
  a reader MUST NOT report them as recording times without saying so,
  and the onsets of events in such a store follow the same convention.
  When the first interval's `source_time` is `null`, the source does not say when its first sample was taken,
  and `start_time` itself is a convention.
- Between two intervals whose later `source_time` is a number, the gap lasts `(next.start - prev.stop) / rate` seconds:
  it runs from `start_time + prev.stop / rate` to `start_time + next.start / rate`, and the grid points in it, `prev.stop` to `next.start - 1`, were not acquired.
- A sample outside every interval was not acquired.
  Its stored value has no meaning, and a reader MUST NOT return it as data.
- A reader MUST NOT filter, resample, epoch, or interpolate across an interval boundary, whether a gap separates the two intervals or not.
- Segments that overlap in time, or a source clock that runs backward, cannot be placed on one grid.
  A writer MUST refuse such a source, or write the affected intervals with `source_time` `null`, which keeps their order and declares their timing unknown.
- A writer SHOULD NOT write more than 65,536 intervals in a group;
  a signal more fragmented than that belongs in a timestamped group.
- A gap shorter than one sample period cannot be expressed on the grid, because intervals are counted in grid indices:
  rounding places the two intervals next to each other, and the pause disappears.
  A source with such gaps MUST be written as a timestamped group if the pause is to be kept.
  **Open for comment: RFC-0001 question 40.**

**Storage.**
A writer MUST NOT write a shard or an inner chunk that lies wholly outside the valid intervals.
Zarr reads an absent chunk as the fill value, and the sharding codec marks an absent inner chunk in its index, so a gap of any length costs no storage.
Only the partial chunks at the edges of an interval hold filler.

**Open for comment:**
RFC-0001 question 18 (gaps on the grid as the only expression of discontinuity),
question 19 (an attribute with a cap, or arrays),
question 21 (`source_time` `null` for undated segments and concatenated runs, and whether epoched data is accepted this way),
and question 27 (whether a recording whose time base is unknown at all may be stored).

**Example (illustrative).**
An EDF Plus (EDF+) recording in its discontinuous variant (EDF+D), with 19 EEG channels at 250 Hz, whose recorder ran from 0 to 60 seconds and again from 90 to 240 seconds.
These are the group's attributes, with `channels` and the view attributes left out:

```json
{
  "kind": "uniform",
  "modality": "EEG",
  "rate": 250.0,
  "original_rate": 250.0,
  "n_channels": 19,
  "n_samples": 60000,
  "start_time": 0.0,
  "valid_intervals": [
    { "start": 0, "stop": 15000, "source_time": 0.0 },
    { "start": 22500, "stop": 60000, "source_time": 90.0 }
  ],
  "time_regularization": null,
  "chunk_seconds": 4.0,
  "shard_seconds": 300.0
}
```

With 1,000-sample inner chunks, chunks 15 to 21 are never written, and chunk 22 holds 500 filler samples followed by 500 acquired ones.

### Time regularization

A stream with a nominal rate and a measured timestamp for each sample, such as an LSL stream in XDF or motion capture with a BIDS `LATENCY` channel, has two homes in the format:

1. **As measured**, in a [timestamped group](#timestamped-groups) with `nominal_rate` set.
   Nothing about timing is lost.
2. **Regularized**, in a uniform group whose `time_regularization` is an object that says how the timestamps were placed on the grid.

A writer MUST set `time_regularization` to such an object whenever a uniform group's samples came from a source with per-sample timestamps, and MUST set it to `null` only when the source declared uniform sampling.

| Member | Type | Meaning |
| --- | --- | --- |
| `method` | string | `"index_order"`: samples kept as measured and assigned to consecutive grid points. `"interpolated"`: values computed at grid times. |
| `interpolation` | string | CONDITIONAL: present when `method` is `"interpolated"`, naming the kind, such as `"linear"`. |
| `nominal_rate` | number or `null` | The rate the source declared. |
| `effective_rate` | number or `null` | `(n - 1) / (t_last - t_first)` over the `n` source timestamps, or `null` when `n` is 1. |
| `max_abs_time_error` | number | With `index_order`, the largest distance, in seconds, between a source timestamp and the grid time its sample was given; with `interpolated`, the largest spacing between the source samples used for one output sample. |
| `rms_time_error` | number | The root mean square of the same quantity, in seconds. |
| `timestamp_derivation` | array of strings | What had been done to the source timestamps, from the tokens of the `time` array under [Timestamped groups](#timestamped-groups). |

With `interpolated`, the amplitudes are no longer measured values, so every channel's `derivation` includes `time_interpolated`.
With `index_order`, no sample changes, so it is recorded here and not in a channel's `derivation`.

Which home a publisher uses is a profile choice; [NEMAR's profile](#the-nemar-profile) keeps such streams as measured by default.
**Open for comment: RFC-0001 question 23.**

### Missing values

Every signal array (level 0, every view array, and `values` in a timestamped group) carries the attribute `missing_value`:
the stored value that means "no sample here", encoded as Zarr v3 encodes `fill_value` for the array's data type, or `null` when every stored value is data.

| Data type | `missing_value` when declared | Data codes |
| --- | --- | --- |
| `int16` | `-32768` | `-32767` to `32767` (65,535 codes) |
| `int32` | `-2147483648` | `-2147483647` to `2147483647` |
| `float32`, `float64` | `"NaN"` | Every value that is not NaN |

- A declared `missing_value` MUST be the value this table gives for the array's data type.
- When `missing_value` is not `null`, the array's `fill_value` MUST equal it,
  so an absent chunk decodes to missing, in a gap and anywhere else.
- When `missing_value` is not `null`, a writer MUST NOT store a data sample as that value.
- `missing_value` MAY be `null` only on an integer array that holds an [exact copy](#exact-copies) of source codes,
  and only when the channel's `source_digital_range` includes the type's most negative code or is `null`.
  Such an array cannot mark one missing sample; gaps are still expressed by `valid_intervals`.
- The view arrays of a group MUST declare the same `missing_value` as its level 0.
- A reader MUST return a missing sample as missing (NaN, a mask, or an explicit list of ranges), never as `missing_value * scale + offset`.
- **Non-finite source samples** (NaN or infinity) never enter a resampling filter.
  A writer resamples each run of finite source samples on its own, as it does each valid interval.
  Stored sample `i` of interval `k` corresponds to the source sample `round((i - start_k) * channel source rate / rate)` of that interval, its nearest source sample.
  When that source sample is non-finite, a writer MUST store, in an integer array, the missing value,
  and in a floating point array, the same non-finite value (NaN, which is its missing value, or the infinity).
  Without resampling, stored sample `i` is source sample `i - start_k`, so the rule stores each non-finite source sample in its own place.
- `nonfinite_samples` counts the stored samples of the channel that the previous rule set, so a test can check it against the array.
  A channel with any such sample has `usable_for_inference` `false`,
  and, in an integer array, `nonfinite_to_missing` in its `derivation`.

The two mechanisms have separate jobs, and a reader applies both.
`valid_intervals` is about a whole group and the acquisition: the recorder was off.
`missing_value` is about one channel at one sample: a sensor was off, a packet was dropped, or a value was not finite.

**Open for comment: RFC-0001 question 22** (always reserve the code, or allow `null` for exact copies).

### Dequantization

A reader MUST recover physical values as:

```
physical[c, i] = digital[c, i] * scale[c] + offset[c]
```

where `c` is a channel's `row_index`, and `scale` and `offset` are the attributes of level 0 or of `values`.
The formula applies to samples that are inside a valid interval and are not missing.
The result is in the channel's `unit`.
A reader SHOULD compute it in 64-bit floating point.
A reader MUST NOT evaluate `physical_formula`; it is a description, not an expression to execute.

The formula holds for every data type.
In a floating point array every `scale` is 1 and every `offset` is 0, so the stored values are already physical values.

**How a writer can quantize** (informative).
For an `int16` array with the declared missing value, each channel is mapped separately onto the 65,535 data codes.
With `pmin` and `pmax` the smallest and largest finite samples of the channel after resampling:

```
scale   = (pmax - pmin) / 65534
offset  = pmin + 32767 * scale
digital = clip(round((physical - offset) / scale), -32767, 32767)
```

A constant channel is stored as all zeros with `scale` 1 and `offset` equal to the constant.
The error on a finite sample is at most half of `scale`, up to floating-point rounding.
Another writer MAY choose `scale` and `offset` differently, as long as the dequantization formula holds and no data sample takes the missing value.

> **Note. The version 2 quantization.**
> biosigIO's version 2 writer maps each channel onto all 65,536 `int16` codes,
> with `scale = (pmax - pmin) / 65535`, `offset = pmin + 32768 * scale`, and clipping to `-32768` and `32767`.
> It stores each non-finite sample as the digital value nearest to physical zero, and the store does not record which samples were replaced.
> Version 3 frees the code `-32768` for the missing value,
> so `scale` grows by a factor of 65,535/65,534 and `offset` moves to the middle of the channel's range.

### Sample resolution

**The store side.**
The storage type of a channel group is its own `dtype` when it has one, and the root `dtype` otherwise.
Its name gives the width in bits and whether the type is integer or floating point.

- The storage type MUST be one of `int16`, `int32`, `float32`, and `float64`.
  Zarr v3 has no 24-bit integer type; `int32` holds 24-bit source codes without requantization, and `float64` holds double-precision source samples.
- Every signal array of the group MUST have the storage type as its Zarr `data_type`.
- For an integer type, `scale[c]` is the store's quantization step for channel `c`:
  one digital step, in the channel's `unit`, with an error of at most half a step on a requantized sample.
  For a floating point type, the resolution is that of the type.

**Open for comment: RFC-0001 question 29** (whether `int32` and `float64` belong in the core, and whether a signal reader may refuse them).

**The source side.**
These fields state the resolution of the source, so a reader can tell how much precision a store gave up and an exporter can restore the source's ranges.

| Field | Where | Type | Meaning |
| --- | --- | --- | --- |
| `source_sample_type` | root (REQUIRED), channel (OPTIONAL override) | string | The type of a decoded sample in the source: `int<N>` or `uint<N>` with `N` from 1 to 64, `float32`, `float64`, or `"n/a"` when unknown. A BDF file is `int24`. |
| `source_adc_bits` | root (REQUIRED), channel (OPTIONAL override) | integer or `null` | The bit depth of the analog-to-digital converter, only when the source states it. |
| `source_step` | channel (REQUIRED) | number or `null` | One source digital step in the channel's `unit`, after any unit conversion the writer applied. Nonzero; negative when the source gain is negative. `null` for a floating point source, or when unknown. |
| `source_offset` | channel (REQUIRED) | number or `null` | The physical value of source digital code 0, in the channel's `unit`. `null` when `source_step` is `null`. |
| `source_digital_range` | channel (REQUIRED) | array of two integers, or `null` | The digital minimum and maximum the source declares; `null` when it declares none. |

- A reader takes `source_sample_type` and `source_adc_bits` from the channel object when it has the member, and from the root otherwise.
  The channel's value replaces the root's; it is not multiplied by it.
- A writer SHOULD write only the root value when every channel agrees,
  and SHOULD write `"n/a"` or `null` at the root when channels differ, with every channel stating its own.
- A writer MUST NOT infer `source_adc_bits` from the sample type: a 16-bit converter can sit in a 24-bit file.
- The source's physical range is not stored, because it follows from the per-channel fields:
  `physical_min = digital_min * source_step + source_offset`, and the same for the maximum.

**Open for comment:**
RFC-0001 question 30 (whether `source_adc_bits` should exist),
question 31 (the pattern `int<N>` and `uint<N>`, or a closed list),
question 32 (whether the source fields restore the header of the formats you export to),
and question 39 (whether a store should carry an explicit bit-depth attribute as well).

**Example (illustrative).**
A BDF channel recorded at 1024 Hz, capped to 250 Hz and requantized into an `int16` store, with `"source_sample_type": "int24"` at the root:

```json
{
  "label": "A1",
  "row_index": 0,
  "channel_type": "EEG",
  "modality": "EEG",
  "unit": "uV",
  "prefilter": "n/a",
  "original_rate": 1024.0,
  "target_rate": 250.0,
  "anti_aliased": true,
  "usable_for_inference": true,
  "scale": 0.061037,
  "offset": 0.0,
  "source_step": 0.03125,
  "source_offset": 0.0,
  "source_digital_range": [-8388608, 8388607],
  "derivation": ["resampled", "requantized"]
}
```

A reader that compares `scale` with `source_step` sees which side is coarser: here the store's step is about twice the source's, about one bit coarser.

### Exact copies

When a channel is not resampled, not unit-converted, and the storage type holds the source's codes, a writer MAY copy the codes unchanged.
In an exact copy, `digital` equals the source code, `scale` equals `source_step`, `offset` equals `source_offset`, and `derivation` is empty.
An EDF file at or below the rate cap can then be reproduced bit for bit.
When the channel's `source_digital_range` includes the type's most negative code, or is `null`, the array declares `missing_value` `null`.
Otherwise it declares the missing value, and a writer that finds a source code equal to it, outside the declared range, MUST NOT make an exact copy of that channel with it declared (a source that keeps to its declared digital range never has such a code).

Whether a writer makes exact copies is the writer's choice and a profile's.

### View pyramid

Each uniform group MUST contain a group named `view`.
It holds zero or more arrays named `1`, `2`, and so on, exactly those listed in the group's `view_levels`.

A view level is a minimum and maximum envelope of level 0, for drawing a long recording quickly.
A reader MUST NOT use a view level as signal for analysis or machine learning.

- **Shape**: `[2, n_channels, n_L]`. Along axis 0, index 0 is the minimum and index 1 is the maximum.
- **Data type**: the same as level 0.
- **Values**: digital values on level 0's scale.
  A reader dequantizes them with the level-0 `scale` and `offset` of the same group.
- **Length**: `n_L = floor(n_(L-1) / view_downsample)`, with `n_0 = n_samples`.
- **Content**: with `f` the level's `downsample_factor`, column `j` holds, per channel, the minimum and the maximum of the level-0 samples `j * f` to `(j + 1) * f - 1` that are inside a valid interval and not missing.
  This is the same as taking, at level 1, the minimum and maximum of `view_downsample` level-0 samples, and at a higher level the minimum of the minimums and the maximum of the maximums of `view_downsample` columns of the level below,
  provided that a column of the level below that holds no data is skipped.
  At every level, a writer MUST NOT take the missing value, or the filler of a gap, as a data value.
  Trailing samples that do not fill a whole column are not represented at that level.
- **Empty columns**: a column with no acquired, non-missing sample holds the missing value in both rows,
  or, when the array declares no missing value, the fill value.
- **Mask rule**: column `j` of a level with factor `f` covers acquired samples if and only if some valid interval has `start < (j + 1) * f` and `stop > j * f`.
  A reader MUST treat a column that the mask rule excludes as empty, and MUST treat a column that holds the missing value as empty.
  When `missing_value` is `null`, the mask rule alone identifies empty columns, because the fill value can be a data value.
- **Chunking**: view arrays are not sharded.
  The chunk shape is `[2, n_channels, chunk_columns]`, where `chunk_columns` is `view_chunk_columns` capped by `n_L`.
- **Codec chain**: `bytes` with little-endian byte order, then `blosc` with the `zstd` compressor.

**View array attributes.**

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `level` | integer | REQUIRED | The level number, 1 or greater. |
| `kind` | string | REQUIRED | `"minmax_envelope"`. |
| `axis0` | array of strings | REQUIRED | `["min", "max"]`. |
| `downsample_factor` | integer | REQUIRED | `view_downsample` raised to the power `level`. |
| `rate_effective` | number | REQUIRED | The group's `rate` divided by `downsample_factor`, in Hz. |
| `chunk_columns` | integer | REQUIRED | The chunk length along time, in columns. |
| `missing_value` | scalar or `null` | REQUIRED | The same as level 0's; see [Missing values](#missing-values). |
| `usable_for_inference` | boolean | REQUIRED | `false`. |

biosigIO's writer stops adding levels once the level it just wrote has 512 columns or fewer, or after 12 levels.
The last level can therefore be shorter than 512 columns, and a group of 512 samples or fewer has no view levels.
Those two limits are writer parameters and are not recorded in the store;
a reader MUST rely on `view_levels`.

### Timestamped groups

A timestamped group holds a signal with one explicit time per sample:
an irregularly sampled signal, a sparse signal with a value (a cuff blood pressure, a temperature probe), or a jittered stream kept as measured.
Such timing already exists in sources.
EDF+D (sections 2.1.1, 2.1.2 and 2.2.4 of the EDF+ specification) can encode irregular samples as data records of duration 0, with one sample per ordinary signal in each record and each record carrying its own time-keeping timestamp.
A timestamped group keeps that timing explicit, and streams it, instead of forcing it onto a grid.
A point process with no value, such as a marker, is an event and belongs in the [`events` group](#events-group).

```
<name>/                 group, kind "timestamped"
  zarr.json             group attributes, including channels[]
  time/                 float64, shape [n_samples]
  values/               shape [n_channels, n_samples]
  time_index/           float64, shape [n_chunks]
```

A timestamped group MUST NOT contain an array named `0` or a group named `view`, and MUST NOT carry the attribute `rate`.

**Attributes of a timestamped group,** in addition to the [attributes of every group](#channel-groups):

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `nominal_rate` | number or `null` | REQUIRED | The rate the source declared; `null` for a signal with none. |
| `effective_rate` | number or `null` | REQUIRED | `(n_samples - 1) / (t_last - t_first)`, or `null` when `n_samples` is 1. Informative: a reader MUST NOT compute sample times from it. |
| `time_range` | array of two numbers | REQUIRED | The first and the last value of `time`. |
| `continuity` | string | REQUIRED | `"continuous"` (samples of a continuous process; interpolation is meaningful), `"step"` (a value holds until the next sample), `"instantaneous"` (a value describes only its instant), or `"unknown"`. |
| `chunk_samples` | integer | REQUIRED | The inner chunk length along time, shared by `time` and `values`. |

`n_samples` MUST be at least 1.
Channel objects in a timestamped group have no `original_rate`, `target_rate` or `anti_aliased`.

**The `time` array.**

- `time` holds seconds on the recording timeline, as `float64`.
  Every value MUST be finite, and the values MUST NOT decrease.
- Sample `i` of every channel in the group was taken at `time[i]`.
  Channels that do not share timestamps MUST be in separate groups.
- Its attributes are `kind` (`"time"`), `unit` (`"s"`), and `derivation`, all REQUIRED.
  `derivation` lists what was done to the source timestamps, and is empty when the values are the source's own timestamps shifted to the origin:
  `clock_synchronized` (a clock offset or drift correction was applied, such as the clock offsets of XDF),
  `dejittered` (timestamps were smoothed or regressed),
  `deduced` (some samples carried no timestamp and were given one from the nominal rate),
  and `sorted` (the source order was not time order).
  **Open for comment: RFC-0001 question 28**, which covers this vocabulary as well as the channels'.

**The `values` array.**
Its data type is the group's storage type, and its attributes are `kind` (`"values"`), `scale`, `offset`, `missing_value`, and `physical_formula`, all REQUIRED,
with the meanings they have on level 0.

**The `time_index` array.**
Element `k` is `time[k * chunk_samples]`, the first time of inner chunk `k`.
It is written as a single chunk.

**Chunking.**
`time` is chunked `[chunk_samples]` and `values` `[n_channels, chunk_samples]`, both with the `sharding_indexed` codec, the same shard length, and the inner codec chain and shard index of level 0,
so inner chunk `k` of one matches inner chunk `k` of the other.

**Reading** (informative).
To read the window from `t0` to `t1`, a reader fetches `time_index`, searches it for the range of chunks, fetches those chunks of `time` and `values`, and trims them by `time`.
A sparse signal fits in one chunk, so its read is three small requests.

A reader MUST NOT interpolate or resample a group whose `continuity` is not `"continuous"` without saying so.

**Open for comment:**
RFC-0001 question 24 (one shared `time` array per group),
question 25 (the `continuity` vocabulary, whose names follow Neurodata Without Borders (NWB)),
and question 26 (whether seconds in 64-bit floating point are precise enough).

**Example (illustrative).**
A cuff blood pressure taken about every five minutes during a four-hour EEG recording.
The group's attributes, with `channels` left out:

```json
{
  "kind": "timestamped",
  "modality": "MISC",
  "n_channels": 2,
  "n_samples": 47,
  "nominal_rate": null,
  "effective_rate": 0.0033,
  "time_range": [212.4, 14162.9],
  "continuity": "instantaneous",
  "chunk_samples": 1000
}
```

The root lists `"timestamped_groups": ["bp_cuff"]` beside `"channel_groups": ["eeg_250hz"]`.

### Events group

The events group is deliberately light.
It plays the part that a data file's own annotations play, such as the annotation channel of EDF+ or the markers of a BrainVision file:
when, for how long, and which code, with a label for each code.
It is not an event table.
A store stands in for a data file, so the full description of events stays where the dataset keeps it,
in a BIDS dataset its `events.tsv` and `events.json`, with columns such as `trial_type`, `value`, and Hierarchical Event Descriptors (HED) annotations.
Keeping only the light form also leaves no room for the free text that data-file annotations often carry, which can include information about the person recorded.

The root group MUST contain a group named `events`, whether or not the recording has events.

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `n_events` | integer | REQUIRED | The number of events. It can be 0. |
| `label_map` | object | REQUIRED | A map from an event code, written as a decimal string, to its description. Empty when `n_events` is 0. |
| `onset_source_basis` | string | REQUIRED | How the source counted onsets: `"timeline"`, `"concatenated"`, or `"unknown"`; see below. |

When `n_events` is greater than 0, the group MUST contain three one-dimensional arrays of length `n_events`:

| Array | Data type | Meaning |
| --- | --- | --- |
| `onset` | `float64` | The event onset, in seconds on the recording timeline. |
| `duration` | `float64` | The event duration, in seconds. |
| `code` | `int32` | The event's code, a key of `label_map`. |

Row `k` of the three arrays describes event `k`.
When `n_events` is 0, the arrays MUST be absent, and a reader MUST NOT request them.

A writer MUST write onsets on the [recording timeline](#recording-timeline), whatever the source's own basis.
`onset_source_basis` records that basis:
`"timeline"` when the source gave onsets on the recording timeline, as the annotations of EDF+ do;
`"concatenated"` when the source counted onsets in samples with the gaps removed, and the writer mapped them through `valid_intervals`;
`"unknown"` when the writer cannot tell.
It matters only when a group has more than one valid interval, and there a reader SHOULD warn its user when it is `"unknown"`.

**From an onset to a sample.**
For a uniform group, the sample nearest an onset is `i = round((onset - start_time) * rate)`.
When `i` is outside `[0, n_samples)` or outside every valid interval, the event has no sample in that group,
and a reader MUST say so instead of clamping `i` or moving it to the nearest sample that was acquired.
An event inside a gap therefore keeps its onset and has no sample.
For example, at 10 Hz with `start_time` 0, `n_samples` 40, and the half-open valid intervals `[0, 20)` and `[24, 40)` in sample indices, the gap runs from 2.00 to 2.40 seconds;
an event at 2.02 seconds gives `i = 20`, which no interval holds, so the event has no sample, although sample 19 and sample 24 were acquired.
A gap shorter than one sample cannot be written this way; such data needs a timestamped group ([Valid intervals](#valid-intervals), RFC-0001 question 40).
**Open for comment: RFC-0001 question 38** (`onset_source_basis` and the onset rule).
For a timestamped group, the sample of an onset is the first `i` with `time[i] >= onset`.
The event has a sample only when such an `i` exists and, when `nominal_rate` is a number, `time[i] - onset` is less than `1 / nominal_rate`, or, when `nominal_rate` is `null`, `time[i]` equals `onset`.

biosigIO's version 2 writer copies onsets and durations from the events table it is given without changing or checking them,
so the timeline rule rests on the caller.
It assigns codes from 0 in order of first appearance, and writes each array as a single chunk.
biosigIO's writer does not set a codec chain for these arrays, so it is whatever the Zarr library defaults to;
a reader MUST take it from the array metadata.

Events belong to the recording, not to a channel group.

> **Note. Side note: `events.parquet` is not part of a store.**
> A publisher can also keep a collection-level events table outside the stores.
> NEMAR publishes one per dataset, `events.parquet`, with one row per event and channel group and a precomputed level-0 sample index,
> so events can be queried across recordings without opening any store
> (see [`events.parquet`](https://docs.nemar.org/platform/zarr/index-contract/#eventsparquet)).
> That file is a publisher addition, not part of this format:
> it is not inside any store, it is not packed into a `.bzx`,
> and the `events` group above remains the events of record for a recording.

### Recording metadata

`recording_metadata` is a JSON object of technical facts about the recording and its source,
such as the source file name, the source format, and the number of signals.
Its members depend on the source format and on the importer.
This specification does not define them, and a reader MUST NOT depend on any member being present.

A value that JSON cannot express directly is written as a typed envelope:

```json
{ "__biosigio_type__": "datetime", "value": "2020-01-01T09:30:00" }
```

The two envelope types are `datetime` and `date`, each with an ISO 8601 `value`.
A reader MAY decode envelopes or leave them as they are.
A reader MUST NOT construct any other type from an envelope.

### Extension attributes

A publisher MAY add attributes to the root group, to a channel group, and to the `events` group.

- An extension MUST NOT change the meaning of any attribute or array this document defines.
- An extension MUST NOT be needed to read the signal or the events correctly.
  A reader that ignores every extension still reads a store correctly.
- An extension MUST NOT add nodes to the root group.
- A publisher SHOULD place its additions under one attribute whose name identifies the publisher, to avoid colliding with attributes this specification adds later.

## Provenance

### Core derivation record

A store records how it was derived from its source in attributes this document already defines:
`source_format`, `created_utc`, `dtype`, `modality_rates`, `anti_alias_filter`, `source_sample_type`, `source_adc_bits`, and `origin_source_time` on the root;
`original_rate`, `start_time`, `valid_intervals`, and `time_regularization` on each uniform group, `source_rate_hz` on level 0;
`derivation` on each `time` array;
`missing_value` on each signal array;
and `original_rate`, `target_rate`, `anti_aliased`, `nonfinite_samples`, `bids_unit`, the source fields, and `derivation` on each channel.
A writer MUST write them truthfully for the conversion it performed.

### The derivation list

A writer MUST record, in the channel's `derivation`, every step that makes a stored sample differ from the source sample, in the order the steps were applied.
A stored sample differs from its source sample when either of these holds:

- In an integer array, its digital value is not the source code, or the channel's `scale` and `offset` are not `source_step` and `source_offset`.
- In a floating point array, its value is not the source's physical value:
  the source's own value for a floating point source,
  or `source_code * source_step + source_offset`, evaluated in 64-bit floating point, for an integer source.
  An integer source stored in a floating point type whose stored values cannot all hold that number exactly is `narrowed`.

A stored sample also differs when it stands at a grid time that is not its source sample's own time, which `resampled`, `nearest_sample`, `time_interpolated`, and `gap_filled` record.

Each token is one of these:

| Token | Meaning | Where the size of the change is recorded |
| --- | --- | --- |
| `resampled` | The rate was changed through an anti-alias filter. | `original_rate`, `target_rate`, root `anti_alias_filter` |
| `nearest_sample` | The rate was changed by picking the nearest source sample (discrete channels). | `original_rate`, `target_rate` |
| `time_interpolated` | Values were computed at grid times from timestamped samples. | `time_regularization` |
| `unit_converted` | Values were multiplied by a unit factor. | `unit`, `bids_unit` |
| `requantized` | The stored integer codes lie on a new lattice, not the source's codes. | `scale` against `source_step` |
| `narrowed` | Values are stored at lower precision than the source's values: a floating point source in a narrower floating point type, or an integer source in a floating point type that cannot hold its physical values exactly. | The storage type against `source_sample_type` |
| `nonfinite_to_missing` | Non-finite source samples are stored as the missing value. | `nonfinite_samples` |
| `nonfinite_zeroed` | Non-finite samples were stored as physical zero, as version 2 did. A writer of version 3 MUST NOT do this; the token exists so that a tool describing a version 2 store can use the same list. | `nonfinite_samples` |
| `gap_filled` | Samples at times the source did not record are stored as data. A writer MUST NOT do this when it can locate the gap; the token exists for sources whose reading library fills gaps silently. | none |

- An empty list means that no stored sample differs from its source sample:
  in an integer array the stored codes are the source's codes, and in a floating point array the stored values are the source's physical values exactly.
- A profile MAY add tokens that contain a colon, such as `nemar:sss`.
  A reader MUST treat a token it does not recognize as a step that changed the samples in a way it does not know.

**Open for comment: RFC-0001 question 28** (whether the vocabulary is complete, and whether an empty list is a claim a reader can rely on).

### Generating software

**Proposed.**
No implementation writes this attribute yet.

`generated_by` names every piece of software that took part in producing the store, with its version,
so a store says what made it without naming any one implementation in the format itself.
It follows the shape of the `GeneratedBy` field of a BIDS `dataset_description.json`.

- `generated_by` MUST be a non-empty array of objects.
- The first entry MUST describe the software that wrote the store's Zarr hierarchy, for example biosigIO.
- Further entries MAY describe software that drove or fed the conversion,
  such as a publisher's conversion pipeline or the library that read the source file,
  in order from the writer outward.
- Every entry MUST have `name` (string) and `version` (string),
  and MAY have `code_url` (string, a link to the source code),
  `description` (string), and `container` (object, with `type`, `tag`, and `uri`, as in BIDS).
- A tool that packs a store into a `.bzx` file without changing it MUST NOT add itself to `generated_by`:
  packing changes no byte of the store.
- A reader MUST ignore entries and members it does not recognize.

For example, a store written by biosigIO inside NEMAR's conversion pipeline:

```json
{
  "generated_by": [
    { "name": "biosigio", "version": "1.3.0", "code_url": "https://github.com/neuromechanist/biosigio" },
    { "name": "nemar-zarr-engine", "version": "3", "description": "NEMAR conversion pipeline" }
  ]
}
```

The version numbers above are illustrative.

The core format does not say which dataset a recording belongs to, under which license it is shared, or how to cite it.
Those facts belong to a publisher, in a profile.

### Requirements on a provenance block

A profile that adds provenance does so in a provenance block.
These requirements are modeled on the one profile that exists, and are untested against a second publisher.

- A provenance block MUST be a single root attribute whose value is a JSON object and whose name identifies the profile.
- A provenance block MUST be generated by the publisher's conversion pipeline from the publisher's authoritative records.
  It is a copy made at conversion time, never a place to edit a fact.
- A provenance block SHOULD identify the source well enough to detect that it is stale:
  an identifier for the source collection, and an immutable revision of it.
- A provenance block SHOULD state the license, how to cite the data, and a persistent identifier when one exists.
- A provenance block SHOULD state whether the served signal was processed beyond the conversion steps this document records.
- A member whose value the publisher does not have MUST be `null`, not omitted and not invented.
  A block SHOULD let a reader tell a value that does not exist from a lookup that failed.
- A provenance block MUST NOT hold subject-level information; see [Security and privacy](#security-and-privacy).
- A reader MUST ignore a provenance block it does not recognize.

### The NEMAR profile

NEMAR's profile is documented on the [Store Contract](https://docs.nemar.org/platform/zarr/store-contract/#root-group-attributes) page, which is its authoritative description.
In summary, a NEMAR store is a biosig-zarr store with these restrictions and additions:

- **Restrictions**:
  `dtype` is always `int16`;
  the rate caps are fixed (see [Channel groups and the rate caps](https://docs.nemar.org/platform/zarr/store-contract/#channel-groups-and-the-rate-caps));
  the modality of a recording comes from its BIDS file name suffix;
  subject-information exclusion always runs.
- **Provenance block**: the root attribute `nemar`,
  with the members `dataset_id`, `doi` (a Digital Object Identifier), `license`, `citation`, `source_commit`, `source_tree`, `derived`, `hed_version` (the HED schema version), `engine_version`, `contract_url`, and `provenance_fetch_failed`.
- **Other root additions**:
  `sss` (present when Signal-Space Separation was applied to an MEG recording),
  `power_line_frequency`,
  and the electrode position attributes `electrode_positions`, `electrode_coordinate_system`, `electrode_coordinate_units`, `electrode_positions_source`, `electrode_positions_file`, and `electrode_coordsystem_file`.
- **Events addition**: `value_descriptions` on the `events` group.

These additions predate this document and sit directly on the root, not under one profile attribute.
Their names are reserved: this specification will not define an attribute with any of them.

For version 3, NEMAR's profile is proposed to make these choices; the Store Contract remains authoritative for NEMAR's served stores:

- Uniform groups and the `values` of timestamped groups are stored as `int16`, and every signal array declares its missing value.
- A jittered stream is kept as measured, in a timestamped group, and is regularized only on request, with the timing error recorded.
- An epoched source, which holds only cut trials, is refused for now.
  **Open for comment: RFC-0001 question 21.**
- Whether NEMAR's writer makes [exact copies](#exact-copies) is decided after measuring how many recordings qualify.
- NEMAR's dataset index does not list a timestamped group among a recording's groups until the index schema carries `kind`.
- NEMAR keys no derived result on a version 3 store until a second definition of its store content digest exists (nemar-cli ADR 0123); the digest is NEMAR's machinery, not part of the format.

## The packaged form (`.bzx`)

**Proposed.**
This section states the intended rules.
No tool implements them yet, and details can change before the first implementation.

A directory-form store has thousands of small objects.
The packaged form holds the same store in one file.
The packing rules are this specification's own.
The Open Microscopy Environment (OME) proposal for zipped OME-Zarr, [RFC-9](https://ngff.openmicroscopy.org/rfc/9/), is prior art for them, not a dependency:
later changes to RFC-9 do not change these rules, and a change to them is made through this specification's own process.
RFC-9 was still under review when this text was written, and it phrases most of its rules as recommendations;
the packaged form makes several of them requirements.

- A `.bzx` file MUST be a ZIP archive that holds exactly one biosig-zarr store.
- The root of the archive MUST be the root of the store:
  the store's root metadata is the entry named `zarr.json`.
- The root `zarr.json` MUST be the first entry in the archive and the first entry in its central directory.
- Every entry MUST be stored without ZIP compression.
  Chunks are already compressed by their Zarr codecs.
  **Open for comment (RFC-0001 question 8).**
- Every entry's content MUST be byte-identical to the corresponding object of the directory form.
  **Open for comment (RFC-0001 question 8).**
  Packing and unpacking therefore change no chunk and no metadata document,
  and a byte range inside an entry maps to a byte range of the file.
- A chunk or shard that the directory form does not hold, such as one that lies wholly in a gap, has no entry.
  A packer MUST NOT create an entry for an absent chunk, and an unpacker MUST NOT treat its absence as damage.
- The archive MUST use the ZIP64 format extension, whatever its size.
- The ZIP archive comment MUST carry the format name and the `format_version`.
  **Proposed:** a reader can then identify the file, and refuse a version it does not implement, without opening an entry;
  this depends on the comment's encoding, which is RFC-0001 question 10.
- A `.bzx` file MUST NOT contain another `.bzx` file or any other zipped Zarr hierarchy.
- A `.bzx` file is written once.
  A writer MUST NOT modify one in place; a changed store is packed again.
  **Open for comment (RFC-0001 question 8).**
- The file name SHOULD end with `.bzx`.

**Open for comment:**
RFC-0001 question 8 (requirements stronger than RFC-9's recommendations, stored entries, byte-identical entries, and writing once),
question 9 (split archives, and the order of the `zarr.json` entries),
question 10 (the encoding of the archive comment),
and question 11 (fixed entry order, timestamps and attributes).

A `.bzx` file and the directory form it was packed from are the same store.
Everything in [The directory form](#the-directory-form) applies to the hierarchy inside the archive.
In particular, a `.bzx` file holds the recording's events, in the store's [`events` group](#events-group), like any other store.
It holds nothing from outside the store: a publisher's collection-level files, such as NEMAR's `events.parquet`, are never packed into it.

## Conformance

**Proposed.**
These classes exist so that an implementation can say precisely what it supports.
The first test suite is in this repository: JSON Schemas for the metadata documents in [`schemas/`](../schemas/), and conformance vectors in [`conformance/`](../conformance/),
with at least one failing case for each layer of [Reader safety](#reader-safety),
and with vectors for the `round` ties, the gap example of the [`events` group](#events-group), and the mask rule of the [View pyramid](#view-pyramid).
[`conformance/README.md`](../conformance/README.md) says which vector tests which rule.

### Writers

- A **core writer** produces directory-form stores that satisfy every MUST and MUST NOT that this document places on a writer or on a store,
  including the `zarr_conventions` entry,
  in [Format identification and versioning](#format-identification-and-versioning), [The directory form](#the-directory-form), [Provenance](#provenance), and [Security and privacy](#security-and-privacy).
- A **packaging writer** is a core writer that also satisfies [The packaged form](#the-packaged-form-bzx).

A store conforms to a profile when it conforms to this document and to that profile's own document.

### Readers

- An **identifying reader** recognizes a store.
  It accepts both format names, applies the version rules, refuses a newer `format_version`, and ignores attributes it does not recognize.
  It does not require `zarr_conventions`, and does not refuse a store whose `zarr_conventions` holds an entry it does not recognize.
- A **signal reader** is an identifying reader that also reads level 0 of any uniform group and returns physical values.
  It takes chunk and shard shapes and codec chains from array metadata, addresses channels by `row_index`, applies the dequantization formula with per-channel `scale` and `offset`,
  and applies `start_time`, `valid_intervals`, and `missing_value`.
  It MUST support the `int16` storage type.
  For any other storage type it MUST either read it correctly or refuse it with an error that names the type.
- A **full reader** is a signal reader that also reads view levels through `view_levels`, reads events, and lets its caller choose among several channel groups.

Support for timestamped groups, and support for the packaged form, are separate capabilities, stated alongside the class.

A signal reader SHOULD verify the checksum of each shard index it reads.

### Reader safety

Four layers keep a reader from misreading a store, so that no single omission returns wrong times or wrong values.
The conformance suite has at least one case for each layer, which fails when the check is removed (see [Conformance](#conformance)).
Every reader of a uniform group MUST also pass the gap case of the [`events` group](#events-group):
at 10 Hz, with the valid intervals `[0, 20)` and `[24, 40)`, an event at 2.02 seconds has no sample.
**Open for comment: RFC-0001 question 36** (whether the four layers are enough).

1. **Version.**
   A writer of this document writes `format_version` 3 on every store, and a reader MUST refuse a version above the highest it implements (see [Format version](#format-version)).
   A version 2 reader such as biosigIO 1.2.13 refuses a version 3 store by its version (its version check is listed in [Appendix A](#appendix-a-exemplar-implementation-map)),
   and also by its name, because it accepts only `biosigio-zarr`.
2. **Kind.**
   A reader MUST read a group's `kind` before reading any array of the group.
   A reader MUST refuse a group whose `kind` it does not implement, and MUST refuse a group of a version 3 store that has no `kind`.
   A reader MUST NOT infer a group's kind from its name or from which children it has.
3. **Structure.**
   A timestamped group is not named in `channel_groups`, and has no array `0`, no `view` group, and no attribute `rate` (see [Timestamped groups](#timestamped-groups)).
   A reader that skips the first two layers and navigates by `channel_groups` never reaches one,
   and a reader that opens one as a uniform group gets an error for a missing node or attribute instead of wrong times.
4. **Within a uniform group.**
   A reader that does not implement `start_time`, `valid_intervals`, or `missing_value` MUST refuse a group where that attribute is in effect,
   with an error that names it.
   `start_time` is in effect when it is not 0;
   `valid_intervals` is in effect when it holds more than one interval;
   `missing_value` is in effect when it is not `null` on level 0.

## Security and privacy

### Subject information

A store holds a recording's signal, its events, its channel names, types and units, and technical metadata.
It is not the place for information about the person recorded:
identity, age, sex, a patient code, a birth date, or free text written by an operator.
Such information belongs at dataset scope, where access to it can be governed once.

- A store that a publisher distributes MUST NOT hold subject-level information in any attribute.
  Subject-level information here means identity and phenotype: a name, a patient code, a birth date, age, sex, handedness, and operator or administrative free text.
  A pseudonymous subject label inside a source file name is outside this rule; a publisher decides whether to keep it.
- A writer MUST offer a mode that leaves subject-level members out of `recording_metadata`,
  and MUST set the root attribute `subject_info_excluded` to `true` on a store written in that mode.
- A writer MUST NOT set `subject_info_excluded` on a store written without that mode.

The mark has a narrow meaning, and a reader MUST NOT read more into it.
In biosigIO's writer the mode removes members by name, from a fixed list, at any depth of `recording_metadata`,
and reduces path-valued members to their final component.
It does not inspect values.
The following can still be present in a store that carries the mark:

- a subject label inside a file name, such as the `sub-01` of a BIDS path, in `recording_metadata` or in a provenance block;
- the date and time the recording started;
- anything held under a member name that is not on the list;
- anything written into an event description or a channel label.

The mark says the mode ran.
It does not say the store, or the dataset behind it, is free of identifying information.
In biosigIO's writer the mode is off unless the caller asks for it.

### Reading untrusted stores

A reader that opens stores from sources it does not control SHOULD treat every part of a store as untrusted input.

- **Sizes.**
  Shapes and chunk shapes come from metadata.
  A reader SHOULD bound the memory it allocates from them, and SHOULD bound the decompressed size of a chunk by its declared shape and data type.
  A reader SHOULD bound the number of valid intervals it accepts in a group.
- **Intervals and times.**
  A reader MUST refuse a group whose `valid_intervals` break the rules of [Valid intervals](#valid-intervals) instead of reading it leniently.
  A reader SHOULD refuse a `time` chunk whose values are not finite or decrease.
- **Strings.**
  Channel labels, event descriptions, units, and metadata values are arbitrary text.
  A reader that displays them SHOULD escape them for the context it displays them in.
- **Formulas and envelopes.**
  A reader MUST NOT execute `physical_formula` and MUST NOT construct arbitrary types from typed envelopes.
- **Archives.**
  A reader of the packaged form MUST reject an entry whose name is absolute or that would resolve outside the store,
  and SHOULD refuse an archive that violates [The packaged form](#the-packaged-form-bzx) instead of reading it leniently.
- **Integrity.**
  The `crc32c` checksum covers each shard's index, not its chunk payloads.
  The format has no checksum over a whole store and no signature, so it does not by itself detect a store that was altered.

## Open questions

Each item is a gap between what a general-purpose format needs and what this draft, or the exemplar implementation, provides today.
None of them is specified above, except where an item says it is closed in version 3, and names where.
The numbers are kept from the version 2 text, so that links to them stay valid.

**Identity and versioning**

1. biosigIO's writer still writes the legacy format name and its reader refuses the new one.
2. A writer is identified today only by `biosigio_version`, which names one implementation.
   `generated_by` (**Proposed**, see [Generating software](#generating-software)) is the neutral replacement;
   open are when it becomes REQUIRED, and whether stores written before it are backfilled from `biosigio_version` and a publisher's own records.
3. `format_version` 2 has absorbed four rounds of new attributes.
   A reader learns what a store carries only by probing for each attribute.
   Whether to add a minor revision number, or a list of feature names, is undecided.
4. Whether to declare the format as a registered Zarr convention in root attributes is undecided.
   Direction (2026-11-18): register it as a Zarr convention; the declaration's shape is still to be settled.
   Version 3 writes the identifier (see [Zarr convention](#zarr-convention)); the shape is RFC-0001 question 5.

**Signal**

5. Non-integer sampling rates.
   Group names and the grouping key round the rate to an integer,
   the resampling ratio is formed from rounded rates,
   and the streaming writer also rounds the rates it records in `original_rate` and `source_rate_hz`.
   Version 3 forbids rounding `rate`, and keeps the rounded grouping key and `original_rate`;
   when two source rates round to the same key, the channels of one group need not share one exact rate.
   RFC-0001 question 2.
6. Closed in version 3.
   Replaced non-finite samples were counted but not located, and a `float32` store did not flag a channel that holds NaN values.
   [Missing values](#missing-values) now locates them and flags the channel.
7. The resampling filter is recorded as free text that names one library function.
   Its cutoff frequency and design are not recorded, so a consumer cannot state the low-pass applied without knowing that library's defaults.
8. The two view pyramid limits (512 columns, 12 levels) are not recorded in the store.
9. Closed in version 3.
   A recording that is not continuous had no representation, with one uniform time axis per group and no per-sample timestamps.
   [Valid intervals](#valid-intervals) and [Timestamped groups](#timestamped-groups) now represent it; their details are open for comment.
10. The absolute start time of a recording has no defined attribute.
    It appears, when it does, under importer-specific names in `recording_metadata`.
    RFC-0001 question 6.
11. `unit`, `channel_type`, and `modality` are free-form strings.
    This document defines no vocabulary for them.
    RFC-0001 question 4.
12. Whether a `float32` store belongs in the core, or in a profile, is undecided.
    Thin readers in constrained runtimes support `int16` only.
    Version 3 adds `int32` and `float64` and lets a signal reader refuse a type other than `int16`; RFC-0001 question 29.
13. Arrays carry no dimension names.
    RFC-0001 question 20.
14. Whether level 0 may use codecs other than `blosc` with `zstd` is undecided.
    The restriction keeps thin readers possible, at the cost of codec choice.
    RFC-0001 question 3.

**Events**

15. The codec chain of the event arrays is left to the Zarr library's default.
16. Closed in version 3.
    The time origin of `onset` was inherited from the caller's events table, and there was no rule for converting an onset to a level-0 sample index.
    The [recording timeline](#recording-timeline) and the onset rule of the [`events` group](#events-group) now define both.
17. How a missing duration is represented is undefined.
18. Richer event semantics, such as per-value descriptions or HED annotations, exist only in a profile.
    This is deliberate (see [Events group](#events-group)): the format does not carry full event tables, which stay with the dataset.
    What remains open is only whether a profile should declare where its event table lives.

**Metadata and extensions**

19. `recording_metadata` has no schema, and its typed envelope key names one implementation.
20. Extension attributes have no namespace rule that existing stores follow.
    The NEMAR additions sit directly on the root.
21. biosigIO's reader finds channel groups by listing the root instead of reading `channel_groups`,
    which is why extensions cannot add root nodes.
22. There is no neutral, profile-independent provenance attribute.

**Privacy and integrity**

23. Subject-information exclusion is off by default in biosigIO's writer and works by member name only.
    Direction (2026-11-18): writers exclude subject information by default, and keeping it becomes the explicit choice.
24. There is no whole-store checksum, manifest, or signature.
    Whether a reader must verify the shard index checksum, which this document only recommends, is undecided.
    Direction (2026-11-18): deferred to beta, when `.bzx` files begin to circulate outside the publishers that make them.
    RFC-0001 question 12.

**The packaged form**

25. Nothing implements it.
26. The encoding of the ZIP archive comment is undecided.
    RFC-9 uses a JSON object under one top-level key, in Unicode Transformation Format 8-bit (UTF-8) encoding.
    RFC-0001 question 10.
27. Whether to adopt the remaining RFC-9 rules is undecided:
    no archives split into parts, and all `zarr.json` entries ahead of chunk entries in breadth-first order.
    RFC-0001 question 9.
28. Entry naming, entry order after the root `zarr.json`, and entry timestamps are undefined,
    so two tools packing the same store need not produce the same bytes.
    RFC-0001 question 11.
29. Whether encrypted entries are forbidden is unstated.
30. No media type is registered, and the `.bzx` suffix is not registered anywhere.
    One file-extension listing reports an unrelated use of `.bzx`.
    RFC-0001 question 15.

**Specification machinery**

31. Closed in version 3.
    There was no JSON Schema for any attribute object.
    [`schemas/`](../schemas/) now holds one for each metadata document, for versions 2 and 3.
32. Closed in version 3.
    There were no published example stores, test vectors, or validator.
    [`conformance/`](../conformance/) now holds example stores cut from a recording dedicated to the public domain, with the outcome a reader must reach for each, and [`tools/`](../tools/) the checks that run them.
33. Closed.
    The change process, the license and the home are decided.
    A normative change needs an accepted RFC in nemarOrg/rfcs, as `GOVERNANCE.md` in this repository says.
    The license follows the model of the OME Next-Generation File Format (OME-NGFF) specification,
    with the specification text under the [W3C Software and Document License](https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document)
    and software, schemas, test vectors and sample implementations under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0);
    contributions are signed off under the Developer Certificate of Origin, as `CONTRIBUTING.md` says.
    The text lives in its own public repository, nemarOrg/biosig-zarr, since 2026-11-20,
    and a permanent identifier that does not name its host, `w3id.org/biosig-zarr`, is being registered so that the repository can move later without breaking links.

## Appendix A: exemplar implementation map

This appendix is informative: it shows where one implementation realizes each rule, and does not make that implementation normative.
It maps the rules of version 2; no implementation of version 3 exists yet.
File paths are in [biosigIO at release 1.2.13](https://github.com/neuromechanist/biosigio/tree/v1.2.13).
Line numbers refer to that release.

| Rule in this document | Source |
| --- | --- |
| Format name and version constants | `biosigio/exporters/zarr.py:77-78` |
| Default rate caps | `biosigio/exporters/zarr.py:82-87` |
| Served rate is `min(source, cap)`, never upsampled | `biosigio/exporters/zarr.py:114-119` |
| Polyphase resampling; nearest sample for discrete channels | `biosigio/exporters/zarr.py:122-149` |
| Discrete channel types | `biosigio/core/channel_types.py:25` |
| Quantization, constant channels, non-finite replacement | `biosigio/exporters/zarr.py:152-191` |
| View level construction and stopping rule | `biosigio/exporters/zarr.py:194-218`, `biosigio/exporters/zarr_stream.py:108-136` |
| Chunk and shard lengths | `biosigio/exporters/zarr.py:221-229` |
| View chunk width | `biosigio/exporters/zarr.py:232-245` |
| `dtype` is `int16` or `float32` | `biosigio/exporters/zarr.py:332-333` |
| `.zarr` suffix | `biosigio/exporters/zarr.py:338-339` |
| Blosc codec with `zstd` | `biosigio/exporters/zarr.py:343`, `biosigio/exporters/zarr_stream.py:627` |
| Grouping by modality and rounded source rate | `biosigio/exporters/zarr.py:347-351`, `biosigio/exporters/zarr_stream.py:621-623` |
| `n_samples` | `biosigio/exporters/zarr.py:364`, `biosigio/exporters/zarr_stream.py:654` |
| `scale` 1 and `offset` 0 in a `float32` store | `biosigio/exporters/zarr.py:366-367`, `379-380` |
| Channel objects | `biosigio/exporters/zarr.py:382-409`, `biosigio/exporters/zarr_stream.py:745-767` |
| Group naming and collisions | `biosigio/exporters/zarr.py:411-422`, `biosigio/exporters/zarr_stream.py:655-657` |
| Group attributes | `biosigio/exporters/zarr.py:433-448`, `biosigio/exporters/zarr_stream.py:790-805` |
| Level-0 array and attributes | `biosigio/exporters/zarr.py:450-478`, `biosigio/exporters/zarr_stream.py:661-668`, `806-821` |
| View group, arrays, and attributes | `biosigio/exporters/zarr.py:480-502`, `biosigio/exporters/zarr_stream.py:669-688`, `822-833` |
| Events group, always written | `biosigio/exporters/zarr.py:504-521`, `biosigio/exporters/zarr_stream.py:836-853` |
| Root attributes | `biosigio/exporters/zarr.py:530-555`, `biosigio/exporters/zarr_stream.py:866-888` |
| Typed envelopes in `recording_metadata` | `biosigio/tabular_schema.py:54-76`, `105-124` |
| Subject-information exclusion | `biosigio/exporters/subject_info.py:40-117`, `156-216`; `biosigio/exporters/zarr.py:248-264` |
| Reader: format name check | `biosigio/importers/zarr.py:57-61` |
| Reader: version rules | `biosigio/importers/zarr.py:62-73` |
| Reader: channel groups found by listing the root | `biosigio/importers/zarr.py:75` |
| Reader: dequantization by `row_index` | `biosigio/importers/zarr.py:84-99` |
| Reader: repeated labels tolerated | `biosigio/importers/zarr.py:89-96` |
| Reader: events | `biosigio/importers/zarr.py:144-159` |
| Reader: `recording_metadata` as object or string | `biosigio/importers/zarr.py:114-117` |
| Extension attributes are ignored by the reader | `docs/formats/zarr.md:260-262` |

## References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174): requirement key words.
- [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html).
- [Zarr sharding codec](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/index.html).
- [Zarr conventions specification](https://github.com/zarr-conventions/zarr-conventions-spec): the `zarr_conventions` attribute.
- [OME-Zarr RFC-9: zipped OME-Zarr](https://ngff.openmicroscopy.org/rfc/9/): prior art for the packaged form.
- [biosigIO](https://github.com/neuromechanist/biosigio): biosigIO's writer and reader.
- [NEMAR Store Contract](https://docs.nemar.org/platform/zarr/store-contract/) and [Format Stability Policy](https://docs.nemar.org/platform/zarr/format-stability/): the NEMAR profile.
