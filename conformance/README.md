# Conformance vectors

This directory holds the conformance vectors of the biosig-zarr specification:
small stores cut from one real recording, each with the outcome a reader of the text must reach.
The specification text, [`spec/index.md`](../spec/index.md), is the definition;
the vectors and the JavaScript Object Notation (JSON) Schemas in [`schemas/`](../schemas/) transcribe it and add nothing.

## Status

### Format version 2: editorial, by the editor's ruling

`GOVERNANCE.md` makes any change to a JSON Schema normative, and lets the editor decide whether a change is normative or editorial.
On 2026-11-20 the editor ruled that the first format version 2 schemas and vectors are editorial:
they transcribe the `2.0.0` text and add no requirement to it,
so they are on `main` and are released with the text as `2.0.1`.
Where a schema or a vector and the text disagree, the text governs, and the disagreement is a defect in the schema or the vector.
`GOVERNANCE.md` is deliberately unchanged:
the ruling applies to release `2.0.1` only, and any later change to a schema is normative, as `GOVERNANCE.md` says.

### Format version 3: proposed with the text

The format version 3 schemas, in `schemas/v3/`, and vectors, in `stores/v3/` and `stores/v1/`, are on the branch `draft/3.0.0`,
with the text that the Request for Comments (RFC) RFC-0001 in nemarOrg/rfcs proposes.
They are part of that proposal, not accepted, and they reach `main` only if RFC-0001 is accepted.
The text still governs: a disagreement between the draft text and a version 3 schema or vector is a defect in the schema or the vector.

## Layout

| Path | What it is |
| --- | --- |
| `manifest.json` | Every vector, its expected outcomes, and the SHA-256 (Secure Hash Algorithm, 256-bit) digest of every file in it |
| `stores/v1/` | The version 1 vector: a store with no `format_version`, which a reader of the version 3 text refuses |
| `stores/v2/` | The vectors for format version 2, each a directory-form store named `<id>.zarr` |
| `stores/v3/` | The vectors for format version 3 |
| `goldens/` | The values a reader must return from each store it accepts |
| `SOURCES.md` | The recording the vectors come from, its license, and every step and alteration applied |

The tools that build and check the vectors are in [`tools/vectors/`](../tools/vectors/), [`tools/check-schemas.ts`](../tools/check-schemas.ts), and [`tools/check-vectors.ts`](../tools/check-vectors.ts).

## The manifest

`manifest.json` is the contract.
A copy of the vectors elsewhere pins the digest of `manifest.json`, and the manifest pins the digest of every file.

Its member `vectors` is an array, with one object per vector:

| Member | Meaning |
| --- | --- |
| `id` | The vector's name, unique in the manifest. |
| `path` | The store, relative to this directory. Its directory, `stores/v<N>/`, is the version the store was written for before any alteration, and `check:schemas` checks it against `schemas/v<N>/` when that directory exists. |
| `format_version` | The major version of the text whose rule the vector was made for. It is not necessarily the `format_version` the store claims: `v2-version-3` was made for the version 2 text, and `v1-no-format-version` for the version 3 text, which requires a reader to refuse it. |
| `class` | For a reader of the version in `format_version`: `valid`, the store conforms to the text, and a reader of that version accepts it; `invalid`, the store does not conform, or a reader of that version must refuse it. `v2-version-3` is invalid because a version 2 reader refuses it ("Format version"), not because it breaks another version 2 rule. |
| `layer` | The reader-safety layer, 1 to 4, that the vector tests for the newest reader the manifest has outcomes for, a reader of the version 3 text, or `null`. Every entry was `null` at `2.0.1`, for a version 2 reader, which has no layers; `v2-version-3` now has `2`, because a version 3 reader refuses it at layer 2. |
| `rule` | The anchor of the heading in `spec/index.md` whose rule the vector tests, such as `format-name`. |
| `description` | Optional free text for a human reader, such as why a vector has its class. |
| `derived_from` | For a vector made by altering another: the `id` of the base vector. |
| `alteration` | For the same vectors: `document`, the path inside the store of the one document changed, and `patch`, the change as a JSON Patch (RFC 6902 of the Internet Engineering Task Force). Every other file is byte-identical to the base. |
| `expect` | The outcome for a reader, keyed by the format version that reader implements, as a string (`"2"`, `"3"`). Every vector has an outcome for a reader of the version 3 text. |
| `files` | The SHA-256 of every file of the store, keyed by its path inside the store. |

An outcome in `expect` has the member `outcome`:

- `accept`: a conforming reader opens the store, and `goldens` names the file of values it must return.
- `refuse`: a conforming reader refuses the store.
- `schema-invalid`: the store does not conform, and a schema shows it.
  `reader`, when present, is what a reader does with the store, `accept` or `refuse`, as the text says;
  when it is absent, the text states no reader outcome beyond that.

When a schema rejects the store, `schema_failure` names the schema's `$id`, the `document` inside the store, the `instance_path` (a JSON Pointer) where validation fails, and the failing `keyword`.
Every other metadata document of the store validates.

An outcome for a reader of the version 3 text also has:

- with `refuse`, `refusal`: the reader-safety `layer` (or `null`), the `rule` (a heading anchor), and the `subject`, the attribute or group the refusal names;
- with `accept`, or with `reader` `accept`:
  `uniform_groups`, the groups a reader reaches through `channel_groups` and reads as uniform groups;
  `timestamped_groups`, the timestamped groups;
  `groups`, for each uniform group, the `start_time`, `valid_intervals` and `missing_value` a reader reads, with the defaults of "Reading earlier versions" for a version 2 store,
  `refuse_without`, the attributes of layer 4 in effect, which a reader that does not implement them must refuse, naming each,
  and `view_empty_columns`, by view level, the columns the mask rule excludes;
  and `events`, with the `onset_source_basis` a reader reads and, in `samples`, the sample of each event onset in each group, or `null` for an event with no sample.

`check:schemas` checks that `class` and the outcome for the version in `format_version` agree:
a `valid` vector has the outcome `accept` and cites no schema failure;
an `invalid` vector has the outcome `refuse` or `schema-invalid`, a `schema-invalid` one cites a schema failure, and every cited failure must happen.

## Which uses of `round` the vectors cover

The text uses `round` in four places, and only the onset rule ("From an onset to a sample") is a computation a reader makes on its own to return a result, so the onset ties of `v3-gap-10hz` are the vectors for the `round` ties:
the quantization formula ("Dequantization") is informative guidance that another writer may replace,
and the start of an interval ("Valid intervals") and the stored-to-source sample mapping ("Missing values") are writer obligations whose results a reader reads from the store rather than recomputes.

## The version 3 suite

A reader of the version 3 text reads version 2 stores, so the version 2 vectors belong to its suite too, with their outcomes under `"3"`.

| Vector | What a reader of the version 3 text must do |
| --- | --- |
| `v1-no-format-version` | Refuse a store with no `format_version` as unsupported (layer 1). |
| `v2-legacy-name`, `v2-new-name`, `v2-unknown-attribute` | Read a version 2 store, with one valid interval, `start_time` 0, `missing_value` `null`, and `onset_source_basis` `unknown`. |
| `v2-version-3` | Refuse a store that claims version 3 and whose groups have no `kind` (layer 2). |
| `v2-unknown-format`, `v2-no-channel-groups` | As a version 2 reader does. |
| `v3-continuous` | Read one uniform `int16` group with its declared missing value; without support for `missing_value`, refuse it and name it (layer 4). |
| `v3-gap-10hz` | The gap case: at 10 hertz (Hz), with valid intervals `[0, 20)` and `[24, 40)`, the event at 2.02 seconds has no sample, and the ties at 0.25, 1.25 and 3.25 seconds give samples 3, 13 and 33 (a reader that rounds halves to even gives 2, 12 and 32); column 5 of the view level with factor 4 is empty by the mask rule, and column 1 of factor 16 is not; one sample inside an interval is missing; without support for `valid_intervals`, refuse it and name it (layer 4). |
| `v3-start-time` | Map onsets with `start_time` 1.5, so an event before the group starts has no sample; without support for `start_time`, refuse it and name it (layer 4). |
| `v3-timestamped` | Reach only the uniform group through `channel_groups` (layer 3), and read the timestamped group's own sample times; do not refuse an unknown entry of `zarr_conventions`. |
| `v3-version-4` | Refuse `format_version` 4 (layer 1). |
| `v3-unknown-format` | Refuse an unknown format name. |
| `v3-no-kind`, `v3-unknown-kind` | Refuse a group with no `kind`, or with a `kind` it does not implement (layer 2). |
| `v3-timestamped-listed` | Refuse a store that names a timestamped group in `channel_groups` (layer 3). |
| `v3-bad-intervals` | Refuse a group whose valid intervals overlap ("Reading untrusted stores"). |
| `v3-no-conventions`, `v3-conventions-extra-member` | Fail writer conformance (`schemas/v3/root`), and still be read: a reader does not require `zarr_conventions`, and identifies a store by `format` and `format_version`. |

## What the schemas do not check

A JSON Schema checks one document at a time, so the rules of the text that relate two values are not in the schemas.
For format version 2, citing the lines of `spec/index.md` at `2.0.0`:
group names unique and listed in `channel_groups` (line 227),
`view_levels` contiguous from 1 and `n_view_levels` long (line 254),
`channels` holding exactly `n_channels` objects (line 261),
`row_index` values covering 0 to `n_channels - 1` once each (line 280),
the level-0 data type equal to the root `dtype` (line 296),
and `scale` and `offset` holding exactly `n_channels` numbers (line 360).
For format version 3, citing headings of the draft text, the same rules and also:
a name in only one of `channel_groups` and `timestamped_groups` ("Root attributes");
the storage type of a group's signal arrays ("Sample resolution");
valid intervals sorted, non-empty and non-overlapping, the first `start` 0, the last `stop` equal to `n_samples`, and each `start` placed from its `source_time` ("Valid intervals");
the view arrays declaring the missing value of level 0, and `downsample_factor` equal to `view_downsample` raised to the power `level` ("View pyramid", "Missing values");
and `time_range` against the values of `time`, and `time_index` ("Timestamped groups").
Shapes, chunk shapes, and counts that must agree with attributes are not checked either.
`tools/check-vectors.ts` checks the rules of valid intervals that a reader must check, on every store it reads.

## Goldens

A goldens file lists, for each channel group and each channel by `row_index`,
the physical values that dequantization returns (`physical = digital * scale + offset`, in 64-bit floating point).
A reader's values must equal `physical` exactly.

- For format version 2, beside them are the values of the source recording, `source_physical`, with `max_abs_error`, half the channel's `scale`;
  `physical` lies within `max_abs_error` of `source_physical`, which shows the goldens trace to the real recording.
- For format version 3, a sample with no value, outside every valid interval or missing, is `null`.
  Beside `physical` are `unquantized`, the values that were quantized, within `max_abs_error` of `physical`,
  and `source_physical`, the value of each stored sample's nearest source sample;
  for a channel that was not resampled the two are equal.
  A timestamped group also lists its `time`, and the file lists the event arrays.

## Running the checks

From the repository root:

```bash
bun install
bun run check:schemas                              # the schemas against the vectors
bun run tools/check-vectors.ts                     # the outcomes against a reading of the version 3 text
bun test tools                                     # both checks fail when they should
uv run --project tools/vectors pytest tools/vectors -q   # the vectors against the manifest and goldens
```

`check:schemas` compiles every schema under JSON Schema draft 2020-12 in strict mode, checks that each `$id` matches its path,
checks that every constraint of a version 3 schema carries a `$comment` naming the heading of the text it comes from,
validates every metadata document of every vector, and confirms that each cited schema failure happens where the manifest says.
`check-vectors` reads the metadata of every store, and no chunk, the way a reader of the version 3 text does:
the version rules, the four reader-safety layers, the rules of valid intervals, the onset rule, and the mask rule;
its tests turn each check off in turn and confirm that an outcome then changes.
The Python tests open every store a reader accepts with stock zarr-python and no other reader code, dequantize with the text's formula, and compare the values with the goldens, missing samples as missing;
they check every view column and every event onset against the level-0 values and the manifest, check that no inner chunk lies wholly in a gap,
recompute every digest in the manifest, and confirm each derived vector differs from its base by exactly its recorded alteration.

## Rebuilding the vectors

`uv run --project tools/vectors python tools/vectors/build.py all --work <scratch directory>` rebuilds every vector.
It needs the network, to download the source recording, and a scratch directory, given with `--work`, for the download and the crop.
Each rebuild runs the version 2 writer again,
which changes `created_utc` in the root `zarr.json` of the six version 2 vectors and of `v1-no-format-version`, because the writer sets it to the time of writing,
and so the digests of those seven files in `manifest.json`.
The chunks, every other metadata document, the version 3 vectors, and the goldens come out byte-identical.
A rebuild diff confined to those lines is expected, and is not corruption.
`build.py derive --work <scratch directory>` remakes the derived vectors, the version 3 vectors, the goldens, and the manifest from the committed `v2-legacy-name` without running the version 2 writer, and changes nothing.

## Adding a vector

A vector is cut from a real recording dedicated to the public domain, never generated, and its source and every step go in `SOURCES.md`.
An invalid vector is a valid one altered in one controlled, recorded way, so that a failure points to one rule.
Add it through `tools/vectors/build.py`, so it can be made again, and keep the whole of `conformance/` small.
