# biosig-zarr Format (pre-beta)

> **Caution. Pre-beta: not stable.**
> This page is a pre-beta specification.
> It can change without notice, and nothing on it is a compatibility promise yet.
> For stores served by the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR),
> the [Store Contract](https://docs.nemar.org/platform/zarr/store-contract/) and the [Format Stability Policy](https://docs.nemar.org/platform/zarr/format-stability/) remain the binding documents.
> Where this page disagrees with them, those pages govern NEMAR's stores until this specification reaches beta.

## Status of this document

This page specifies `format_version` 2 of the format.
The specification defines the format; implementations follow it.
[biosigIO](https://github.com/neuromechanist/biosigio) is one exemplar implementation, and the first:
this draft was written from what its release 1.2.13 produces, so that the stores already in use conform,
and where biosigIO and this page disagree, the disagreement is either a defect in biosigIO or an [open question](#open-questions), never a silent change to the format.
Every statement about existing writer behavior was checked against that release's source,
against stores written with it for this purpose,
and against one public NEMAR store on 2026-11-18.
[Appendix A](#appendix-a-exemplar-implementation-map) lists where biosigIO implements each rule.

Three parts of this page run ahead of any implementation, and each is marked **Proposed** where it appears:

- **The name `biosig-zarr`.**
  biosigIO 1.2.13 writes the legacy name `biosigio-zarr`, and its reader accepts only that name.
  The rename is planned; no store carries the new name yet.
- **The packaged form (`.bzx`).**
  No tool writes or reads it yet.
- **The `generated_by` attribute.**
  No writer produces it yet.
- **The conformance classes.**
  No test suite or validator exists yet.

Anything no implementation does today is listed under [Open questions](#open-questions) and is not specified here.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in Request for Comments (RFC) 2119 and RFC 8174,
when, and only when, they appear in all capitals.
In the attribute tables, CONDITIONAL means the attribute MUST be present when its stated condition holds and MUST be absent otherwise.

## Scope and non-goals

biosig-zarr stores **one continuous recording** of biosignals as a Zarr version 3 (v3) hierarchy:
electroencephalography (EEG), magnetoencephalography (MEG), intracranial EEG (iEEG), electromyography (EMG), and the channels recorded alongside them.
The layout serves three kinds of read from one copy:
interactive viewing, windowed analysis or model inference, and sequential streaming for model training.

A biosig-zarr store is:

- **Derived.**
  It is made from a source recording, and the source stays authoritative.
- **Lossy by default.**
  Signals above a per-modality rate cap are resampled down to it,
  samples are quantized to 16-bit signed integers (`int16`) by default,
  and non-finite samples in an `int16` store are replaced.
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
  The format describes resampling, unit conversion, and quantization, and nothing else.
  It has no place for re-referencing, filtering, artifact removal, or segmentation into trials.
- **Not lossless.**
  Even a 32-bit floating point (`float32`) store is resampled when the source rate exceeds the cap,
  and holds values at `float32` precision.

## Terminology

- **Recording**: one continuous acquisition, with one or more channels.
- **Source**: the file or files the recording was read from.
- **Store**: one biosig-zarr hierarchy, holding one recording.
- **Directory form**: a store laid out as a directory tree of Zarr v3 objects, conventionally named with the suffix `.zarr`.
- **Packaged form**: a store packed into one ZIP file with the suffix `.bzx`.
- **Channel group**: a Zarr group holding the channels of one modality that share one sampling rate.
- **Level 0**: the full-resolution signal array of a channel group.
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
Once a writer has adopted the new name, it MUST NOT write the legacy one.

A reader MUST refuse a store whose `format` is neither name.

> **Note. Where the rename stands.**
> biosigIO 1.2.13 writes `biosigio-zarr` and refuses to read any other name.
> Until a release that accepts both names is in use, a store carrying `biosig-zarr` is not readable by biosigIO's reader.

### Format version

The root attribute `format_version` MUST be an integer.
This page specifies version 2.

- Version 1 differs from version 2 in one respect:
  `recording_metadata` is a string holding JavaScript Object Notation (JSON) text, where version 2 holds a JSON object.
- A store with no `format_version` attribute is a version 1 store.
- A reader SHOULD accept a number with an integral value, such as `2.0`, as that integer.
- A reader MUST refuse a store whose `format_version` is greater than the highest version it implements.
  It MUST NOT attempt to read such a store on the assumption that the layout is unchanged.

### What changes the version

- Adding an attribute does not change `format_version`.
  A reader MUST ignore attributes it does not recognize.
- Chunk and shard sizes are not part of the version.
  A reader MUST take every chunk and shard shape from array metadata, never from a constant.
- A change that makes a reader conforming to this page return wrong data, or no data, MUST increase `format_version`.

Version 2 has grown by addition, so two version 2 stores can differ in which attributes they carry.
A reader MUST treat each attribute in this table as possibly absent:

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
  the root's `channel_groups` names the channel groups,
  each group's `view_levels` names its view arrays,
  and the `events` group's `n_events` says whether its arrays exist.
  A writer MUST preserve this property.
  A reader SHOULD navigate by attributes, because a store served over the Hypertext Transfer Protocol (HTTP) usually cannot be listed.
- The root group MUST NOT contain child nodes other than the channel groups named in `channel_groups` and the `events` group.
  biosigIO's reader treats every root child except `events` as a channel group.
- A reader MUST take the chunk key encoding and the codec chain of every array from that array's metadata.

### Hierarchy

```
<name>.zarr/                  root group
  zarr.json                   root attributes
  <modality>_<rate>hz/        one channel group per (modality, source rate) pair
    zarr.json                 group attributes, including channels[]
    0/                        level 0: signal, shape [n_channels, n_samples], sharded
    view/                     group, always present, no attributes
      1/, 2/, ...             view levels: shape [2, n_channels, n_L], not sharded
  events/                     group, always present
    onset/, duration/, code/  one-dimensional arrays, present when n_events > 0
```

### Root attributes

In every attribute table on this page, the Presence column states what a writer conforming to this page writes.
A version 2 store written by an older release can lack the attributes listed under [What changes the version](#what-changes-the-version).

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `format` | string | REQUIRED | See [Format name](#format-name). |
| `format_version` | integer | REQUIRED | See [Format version](#format-version). |
| `channel_groups` | array of strings | REQUIRED | The names of the channel groups, in the order they were written. |
| `dtype` | string | REQUIRED | `"int16"` or `"float32"`: the data type of every level-0 and view array in the store. |
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

A reader needs only `format`, `format_version`, and `channel_groups` from the root to locate the signal.
The remaining REQUIRED attributes record how the store was derived.
A reader MUST NOT require `biosigio_version` or `note`,
and until `generated_by` leaves Proposed, a reader MUST NOT require it either.

`channels_tsv_units` holds the integer counts `converted`, `relabelled`, and `kept_importer_unit`, and the boolean `units_column_present`.
It can also hold `matched_case_insensitive`, a map from a sidecar row name to the channel label it matched only by ignoring case.

### Channel groups

A writer puts channels into one group per pair of modality and source rate, with the source rate rounded to the nearest integer.
Every channel in a group therefore has the same served rate and the same number of samples.

**Naming.**
biosigIO's writer names a group `<modality>_<rate>hz`,
with the modality in lowercase and the served rate rounded to the nearest integer, for example `eeg_250hz`.
The name carries the served rate, not the source rate.
When two source rates of one modality map to the same served rate, the in-memory writer appends `_from<source rate>` to the second name.
A group name MUST be unique within the store and MUST appear in `channel_groups`.
A reader MUST NOT parse the modality or the rate out of a group name; it MUST read them from the group attributes.

**Served rate.**
The served rate of a group is `min(source rate, cap)`,
where the cap is the entry for the group's modality in `modality_rates`.
A modality with no entry keeps its source rate.
A writer MUST NOT upsample.
The caps are a writer parameter and are recorded in the store;
biosigIO's writer's defaults are 250 Hz for `EEG` and `MEG`, and 1000 Hz for `IEEG` and `EMG`.

**Resampling.**
Continuous channels are resampled with an anti-aliased polyphase filter.
Discrete channels, whose `channel_type` is `TRIG`, `SYSCLOCK`, or `CTRL`, are resampled by taking the nearest source sample, with no filter, so step edges survive.
`n_samples` is the source sample count multiplied by `rate / original_rate`, rounded to the nearest integer.

**Group attributes.**

| Attribute | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `modality` | string | REQUIRED | The modality of the group, in uppercase, such as `EEG`. |
| `rate` | number | REQUIRED | The served rate, in Hz. |
| `original_rate` | number | REQUIRED | The source rate used as the grouping key: rounded to an integer. |
| `n_channels` | integer | REQUIRED | The number of channels. |
| `n_samples` | integer | REQUIRED | The number of level-0 samples per channel. |
| `channels` | array of objects | REQUIRED | One object per channel; see below. |
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
| `row_index` | integer | REQUIRED | The channel's index along axis 0 of the level-0 array. |
| `channel_type` | string | REQUIRED | The channel type, in uppercase, such as `EEG` or `TRIG`. |
| `modality` | string | REQUIRED | The modality of the group. |
| `unit` | string | REQUIRED | The unit of the channel's physical values, or `"n/a"` when unknown. |
| `prefilter` | string | REQUIRED | Free text describing acquisition filtering, or `"n/a"`. |
| `original_rate` | number | REQUIRED | The channel's source rate, in Hz. |
| `target_rate` | number | REQUIRED | The served rate, in Hz. |
| `anti_aliased` | boolean | REQUIRED | `true` when the channel is continuous and was downsampled. |
| `usable_for_inference` | boolean | REQUIRED | `false` for a discrete channel, and for a channel with replaced non-finite samples. |
| `scale` | number | REQUIRED | A copy of this channel's entry in the level-0 `scale` array. |
| `offset` | number | REQUIRED | A copy of this channel's entry in the level-0 `offset` array. |
| `nonfinite_samples` | integer | CONDITIONAL | Present when non-finite samples were replaced in an `int16` store: how many. |
| `bids_unit` | string | CONDITIONAL | Present when a BIDS `channels.tsv` declared a unit that the writer recorded but did not adopt. |

The `row_index` values of a group MUST be the integers 0 to `n_channels - 1`, each used once.
A reader MUST address a channel's samples by `row_index`, not by its position in `channels` and not by `label`.
A writer SHOULD write unique labels within a group.
A reader MUST tolerate repeated labels, which exist in stores written before biosigIO's writer began to suffix them.

`unit` is the unit of the values dequantization returns.
A reader MUST read it per channel and MUST NOT assume a unit from the modality.

`usable_for_inference` says whether a channel is fit to use as input to analysis or machine learning.

### Level-0 array

Each channel group MUST contain an array named `0`, written as follows.

- **Shape**: the array MUST have shape `[n_channels, n_samples]`.
  Axis 0 is the channel, axis 1 is time.
- **Data type**: the array MUST be `int16` or `float32`, equal to the root `dtype`.
- **Sharding**: the array MUST use the `sharding_indexed` codec.
  The shard shape, which is the array's chunk grid shape, is `[n_channels, shard_samples]`.
  The inner chunk shape is `[n_channels, chunk_samples]`.
- **Every inner chunk spans every channel.**
  A writer MUST NOT split an inner chunk or a shard along the channel axis.
- **Inner codec chain**: the chain MUST be `bytes` with little-endian byte order, then `blosc` with the `zstd` compressor.
- **Shard index**: the index codecs MUST be `bytes` with little-endian byte order, then `crc32c`.

biosigIO's writer uses compression level 5, byte shuffle, a fill value of 0, and an index at the end of each shard.
Those four are its choices, not requirements, and a reader MUST take them from the array metadata.

`shard_samples` MUST be a positive integer multiple of `chunk_samples`.
It can exceed `n_samples`: a recording shorter than one nominal shard is written as a single shard rounded up to a whole number of inner chunks.

This is the array metadata biosigIO's writer produces for a four-channel, 175000-sample `int16` group, attributes omitted:

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
| `physical_formula` | string | REQUIRED | The literal text `physical = digital * scale + offset`. |

`scale` and `offset` MUST each hold exactly `n_channels` numbers.
`chunk_samples` and `shard_samples` restate the array metadata; where they differ, the array metadata governs.

**Time axis.**
Level 0 is uniformly sampled.
Sample `i` of a group lies `i / rate` seconds after the start of the recording.

### Dequantization

A reader MUST recover physical values as:

```
physical[c, i] = digital[c, i] * scale[c] + offset[c]
```

where `c` is a channel's `row_index`, and `scale` and `offset` are the level-0 array attributes.
The result is in the channel's `unit`.
A reader SHOULD compute it in 64-bit floating point.
A reader MUST NOT evaluate `physical_formula`; it is a description, not an expression to execute.

The formula holds for both data types.
In a `float32` store every `scale` is 1 and every `offset` is 0, so the stored values are already physical values.

**How biosigIO's writer quantizes** (informative).
For an `int16` store, each channel is mapped separately.
With `pmin` and `pmax` the smallest and largest finite samples of the channel after resampling:

```
scale   = (pmax - pmin) / 65535
offset  = pmin + 32768 * scale
digital = clip(round((physical - offset) / scale), -32768, 32767)
```

A constant channel is stored as all zeros with `scale` 1 and `offset` equal to the constant.
The error on a finite sample is at most half of `scale`, up to floating-point rounding.
Another writer MAY choose `scale` and `offset` differently, as long as the dequantization formula holds.

**Non-finite samples.**
`int16` cannot represent not-a-number (NaN) or infinite values.
In an `int16` store biosigIO's writer computes `scale` and `offset` from the finite samples only,
then stores each non-finite sample as the digital value nearest to physical zero, clipped to the `int16` range.
The channel gains `nonfinite_samples` with the count, and its `usable_for_inference` is `false`.
A store does not record which samples were replaced.
A `float32` store keeps NaN values as they are and does not flag the channel.

### View pyramid

Each channel group MUST contain a group named `view`.
It holds zero or more arrays named `1`, `2`, and so on, exactly those listed in the group's `view_levels`.

A view level is a minimum and maximum envelope of level 0, for drawing a long recording quickly.
A reader MUST NOT use a view level as signal for analysis or machine learning.

- **Shape**: `[2, n_channels, n_L]`. Along axis 0, index 0 is the minimum and index 1 is the maximum.
- **Data type**: the same as level 0.
- **Values**: digital values on level 0's scale.
  A reader dequantizes them with the level-0 `scale` and `offset` of the same group.
- **Length**: `n_L = floor(n_(L-1) / view_downsample)`, with `n_0 = n_samples`.
- **Content**: column `j` of level 1 holds, per channel, the minimum and the maximum of the `view_downsample` level-0 samples starting at `j * view_downsample`.
  Column `j` of a higher level holds the minimum of the minimums and the maximum of the maximums of the `view_downsample` columns of the level below, starting at `j * view_downsample`.
  Trailing samples that do not fill a whole column are not represented at that level.
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
| `usable_for_inference` | boolean | REQUIRED | `false`. |

biosigIO's writer stops adding levels once the level it just wrote has 512 columns or fewer, or after 12 levels.
The last level can therefore be shorter than 512 columns, and a group of 512 samples or fewer has no view levels.
Those two limits are writer parameters and are not recorded in the store;
a reader MUST rely on `view_levels`.

### Events group

The events group is deliberately light.
It plays the part that a data file's own annotations play, such as the annotation channel of European Data Format Plus (EDF+) or the markers of a BrainVision file:
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

When `n_events` is greater than 0, the group MUST contain three one-dimensional arrays of length `n_events`:

| Array | Data type | Meaning |
| --- | --- | --- |
| `onset` | `float64` | The event onset, in seconds. |
| `duration` | `float64` | The event duration, in seconds. |
| `code` | `int32` | The event's code, a key of `label_map`. |

Row `k` of the three arrays describes event `k`.
When `n_events` is 0, the arrays MUST be absent, and a reader MUST NOT request them.

A writer MUST write onsets on the time axis of the recording, where level-0 sample 0 is at 0 seconds.
biosigIO's writer copies onsets and durations from the events table it is given without changing or checking them,
so this rule rests on the caller.
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

- An extension MUST NOT change the meaning of any attribute or array this page defines.
- An extension MUST NOT be needed to read the signal or the events correctly.
  A reader that ignores every extension still reads a store correctly.
- An extension MUST NOT add nodes to the root group.
- A publisher SHOULD place its additions under one attribute whose name identifies the publisher, to avoid colliding with attributes this specification adds later.

## Provenance

### Core derivation record

A store records how it was derived from its source in attributes this page already defines:
`source_format`, `created_utc`, `dtype`, `modality_rates`, and `anti_alias_filter` on the root;
`original_rate` on each group, `source_rate_hz` on level 0;
and `original_rate`, `target_rate`, `anti_aliased`, `nonfinite_samples`, and `bids_unit` on each channel.
A writer MUST write them truthfully for the conversion it performed.

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
"generated_by": [
  { "name": "biosigio", "version": "1.3.0", "code_url": "https://github.com/neuromechanist/biosigio" },
  { "name": "nemar-zarr-engine", "version": "3", "description": "NEMAR conversion pipeline" }
]
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
- A provenance block SHOULD state whether the served signal was processed beyond the resampling, unit conversion, and quantization this page describes.
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

These additions predate this page and sit directly on the root, not under one profile attribute.
Their names are reserved: this specification will not define an attribute with any of them.

## The packaged form (`.bzx`)

**Proposed.**
This section states the intended rules.
No tool implements them yet, and details can change before the first implementation.

A directory-form store has thousands of small objects.
The packaged form holds the same store in one file,
following the approach of the Open Microscopy Environment (OME) proposal for zipped OME-Zarr, [RFC-9](https://ngff.openmicroscopy.org/rfc/9/).
RFC-9 was still under review when this page was written, and it phrases most of its rules as recommendations;
the packaged form makes several of them requirements.

- A `.bzx` file MUST be a ZIP archive that holds exactly one biosig-zarr store.
- The root of the archive MUST be the root of the store:
  the store's root metadata is the entry named `zarr.json`.
- The root `zarr.json` MUST be the first entry in the archive and the first entry in its central directory.
- Every entry MUST be stored without ZIP compression.
  Chunks are already compressed by their Zarr codecs.
- Every entry's content MUST be byte-identical to the corresponding object of the directory form.
  Packing and unpacking therefore change no chunk and no metadata document,
  and a byte range inside an entry maps to a byte range of the file.
- The archive MUST use the ZIP64 format extension, whatever its size.
- The ZIP archive comment MUST carry the format name and the `format_version`,
  so a reader can identify the file without opening an entry.
- A `.bzx` file MUST NOT contain another `.bzx` file or any other zipped Zarr hierarchy.
- A `.bzx` file is written once.
  A writer MUST NOT modify one in place; a changed store is packed again.
- The file name SHOULD end with `.bzx`.

A `.bzx` file and the directory form it was packed from are the same store.
Everything in [The directory form](#the-directory-form) applies to the hierarchy inside the archive.
In particular, a `.bzx` file holds the recording's events, in the store's [`events` group](#events-group), like any other store.
It holds nothing from outside the store: a publisher's collection-level files, such as NEMAR's `events.parquet`, are never packed into it.

## Conformance

**Proposed.**
These classes exist so that an implementation can say precisely what it supports.
There is no test suite yet.

### Writers

- A **core writer** produces directory-form stores that satisfy every MUST and MUST NOT that this page places on a writer or on a store,
  in [Format identification and versioning](#format-identification-and-versioning), [The directory form](#the-directory-form), [Provenance](#provenance), and [Security and privacy](#security-and-privacy).
- A **packaging writer** is a core writer that also satisfies [The packaged form](#the-packaged-form-bzx).

A store conforms to a profile when it conforms to this page and to that profile's own document.

### Readers

- An **identifying reader** recognizes a store.
  It accepts both format names, applies the version rules, refuses a newer `format_version`, and ignores attributes it does not recognize.
- A **signal reader** is an identifying reader that also reads level 0 of any channel group and returns physical values.
  It takes chunk and shard shapes and codec chains from array metadata, addresses channels by `row_index`, and applies the dequantization formula with per-channel `scale` and `offset`.
  It MUST support `int16` stores.
  For a `float32` store it MUST either read it correctly or refuse it with a clear error.
- A **full reader** is a signal reader that also reads view levels through `view_levels`, reads events, and lets its caller choose among several channel groups.

Support for the packaged form is a separate capability, stated alongside the class.

A signal reader SHOULD verify the checksum of each shard index it reads.

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
None of them is specified above.

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

**Signal**

5. Non-integer sampling rates.
   Group names and the grouping key round the rate to an integer,
   the resampling ratio is formed from rounded rates,
   and the streaming writer also rounds the rates it records in `original_rate` and `source_rate_hz`.
6. Replaced non-finite samples are counted but not located, and a `float32` store does not flag a channel that holds NaN values.
7. The resampling filter is recorded as free text that names one library function.
   Its cutoff frequency and design are not recorded, so a consumer cannot state the low-pass applied without knowing that library's defaults.
8. The two view pyramid limits (512 columns, 12 levels) are not recorded in the store.
9. A recording that is not continuous has no representation.
   There is one uniform time axis per group, and no per-sample timestamps.
10. The absolute start time of a recording has no defined attribute.
    It appears, when it does, under importer-specific names in `recording_metadata`.
11. `unit`, `channel_type`, and `modality` are free-form strings.
    This page defines no vocabulary for them.
12. Whether a `float32` store belongs in the core, or in a profile, is undecided.
    Thin readers in constrained runtimes support `int16` only.
13. Arrays carry no dimension names.
14. Whether level 0 may use codecs other than `blosc` with `zstd` is undecided.
    The restriction keeps thin readers possible, at the cost of codec choice.

**Events**

15. The codec chain of the event arrays is left to the Zarr library's default.
16. The time origin of `onset` is inherited from the caller's events table, not enforced.
    There is no defined rule for converting an onset to a level-0 sample index.
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
    Whether a reader must verify the shard index checksum, which this page only recommends, is undecided.
    Direction (2026-11-18): deferred to beta, when `.bzx` files begin to circulate outside the publishers that make them.

**The packaged form**

25. Nothing implements it.
26. The encoding of the ZIP archive comment is undecided.
    RFC-9 uses a JSON object under one top-level key, in Unicode Transformation Format 8-bit (UTF-8) encoding.
27. Whether to adopt the remaining RFC-9 rules is undecided:
    no archives split into parts, and all `zarr.json` entries ahead of chunk entries in breadth-first order.
28. Entry naming, entry order after the root `zarr.json`, and entry timestamps are undefined,
    so two tools packing the same store need not produce the same bytes.
29. Whether encrypted entries are forbidden is unstated.
30. No media type is registered, and the `.bzx` suffix is not registered anywhere.
    One file-extension listing reports an unrelated use of `.bzx`.

**Specification machinery**

31. There is no JSON Schema for any attribute object.
32. There are no published example stores, test vectors, or validator.
33. The change process is undecided.
    Direction (2026-11-18) on license and home:
    the license follows the model of the OME Next-Generation File Format (OME-NGFF) specification,
    with the specification text under the [W3C Software and Document License](https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document)
    and software, schemas, test vectors and sample implementations under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
    OME-NGFF takes contributions to its specification under the W3C contributor license agreement, which applies only within a W3C community group;
    the equivalent for this format is still to be chosen.
    The specification stays on this page while it is pre-beta,
    moves to its own public repository at beta,
    and gets a permanent identifier that does not name its host, so that repository can move later without breaking links.

## Appendix A: exemplar implementation map

This appendix is informative: it shows where one implementation realizes each rule, and does not make that implementation normative.
File paths are in [biosigIO at release 1.2.13](https://github.com/neuromechanist/biosigio/tree/v1.2.13).
Line numbers refer to that release.

| Rule on this page | Source |
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
- [OME-Zarr RFC-9: zipped OME-Zarr](https://ngff.openmicroscopy.org/rfc/9/).
- [biosigIO](https://github.com/neuromechanist/biosigio): biosigIO's writer and reader.
- [NEMAR Store Contract](https://docs.nemar.org/platform/zarr/store-contract/) and [Format Stability Policy](https://docs.nemar.org/platform/zarr/format-stability/): the NEMAR profile.
