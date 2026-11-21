# Conformance vectors

This directory holds the conformance vectors of the biosig-zarr specification:
small stores cut from one real recording, each with the outcome a reader of the text must reach.
The specification text, [`spec/index.md`](../spec/index.md), is the definition;
the vectors and the JavaScript Object Notation (JSON) Schemas in [`schemas/`](../schemas/) transcribe it and add nothing.

## Status: editorial, by the editor's ruling

`GOVERNANCE.md` makes any change to a JSON Schema normative, and lets the editor decide whether a change is normative or editorial.
On 2026-11-20 the editor ruled that the first format version 2 schemas and vectors are editorial:
they transcribe the `2.0.0` text and add no requirement to it,
so they are on `main` and are released with the text as `2.0.1`.
Where a schema or a vector and the text disagree, the text governs, and the disagreement is a defect in the schema or the vector.
`GOVERNANCE.md` is deliberately unchanged:
the ruling applies to release `2.0.1` only, and any later change to a schema is normative, as `GOVERNANCE.md` says.

## Layout

| Path | What it is |
| --- | --- |
| `manifest.json` | Every vector, its expected outcomes, and the SHA-256 (Secure Hash Algorithm, 256-bit) digest of every file in it |
| `stores/v2/` | The vectors for format version 2, each a directory-form store named `<id>.zarr` |
| `goldens/` | The values a reader must return from each valid vector |
| `SOURCES.md` | The recording the vectors come from, its license, and every step and alteration applied |

The tools that build and check the vectors are in [`tools/vectors/`](../tools/vectors/) and [`tools/check-schemas.ts`](../tools/check-schemas.ts).

## The manifest

`manifest.json` is the contract.
A copy of the vectors elsewhere pins the digest of `manifest.json`, and the manifest pins the digest of every file.

Its member `vectors` is an array, with one object per vector:

| Member | Meaning |
| --- | --- |
| `id` | The vector's name, unique in the manifest. |
| `path` | The store, relative to this directory. |
| `format_version` | The major version of the text whose rule the vector was made for: the `v2` of `stores/v2/`. It is not necessarily the `format_version` the store claims. |
| `class` | `valid`: the store conforms to the text, and a reader of that version accepts it. `invalid`: the store does not conform, or a reader of that version must refuse it. `v2-version-3` is invalid because a version 2 reader refuses it ("Format version"), not because it breaks another version 2 rule. |
| `layer` | The reader-safety layer, 1 to 4, that the vector tests for the newest reader the manifest has outcomes for, or `null`. A version 2 reader has no layers, so every entry is `null` at `2.0.1`. |
| `rule` | The anchor of the heading in `spec/index.md` whose rule the vector tests, such as `format-name`. |
| `description` | Optional free text for a human reader, such as why a vector has its class. |
| `derived_from` | For a vector made by altering another: the `id` of the base vector. |
| `alteration` | For the same vectors: `document`, the path inside the store of the one document changed, and `patch`, the change as a JSON Patch (Request for Comments (RFC) 6902). Every other file is byte-identical to the base. |
| `expect` | The outcome for a reader, keyed by the format version that reader implements, as a string (`"2"`). |
| `files` | The SHA-256 of every file of the store, keyed by its path inside the store. |

An outcome in `expect` has the member `outcome`:

- `accept`: a conforming reader opens the store, and `goldens` names the file of values it must return.
- `refuse`: a conforming reader refuses the store, for the rule in `rule`.
- `schema-invalid`: the store does not conform, and a schema shows it; the text states no reader outcome beyond that.

When a schema rejects the store, `schema_failure` names the schema's `$id`, the `document` inside the store, the `instance_path` (a JSON Pointer) where validation fails, and the failing `keyword`.
Every other metadata document of the store validates.

`check:schemas` checks that `class` and `expect` agree:
a `valid` vector has the outcome `accept` and cites no schema failure;
an `invalid` vector has the outcome `refuse` or `schema-invalid`, a `schema-invalid` one cites a schema failure, and every cited failure must happen.

## What the schemas do not check

A JSON Schema checks one document at a time, so the rules of the text that relate two values are not in the schemas:
group names unique and listed in `channel_groups` (line 227 of `spec/index.md` at `2.0.0`),
`view_levels` contiguous from 1 and `n_view_levels` long (line 254),
`channels` holding exactly `n_channels` objects (line 261),
`row_index` values covering 0 to `n_channels - 1` once each (line 280),
the level-0 data type equal to the root `dtype` (line 296),
and `scale` and `offset` holding exactly `n_channels` numbers (line 360).
Shapes, chunk shapes, and counts that must agree with attributes are not checked either.

## Goldens

A goldens file lists, for each channel group and each channel by `row_index`,
the physical values of level 0 that dequantization returns (`physical = digital * scale + offset`, in 64-bit floating point),
and, beside them, the values of the source recording the channel came from, with `max_abs_error`, half the channel's `scale`.
A reader's values must equal `physical` exactly;
`physical` lies within `max_abs_error` of `source_physical`, which shows the goldens trace to the real recording.

## Running the checks

From the repository root:

```bash
bun install
bun run check:schemas                              # the schemas against the vectors
bun test tools                                     # the schema check fails when it should
uv run --project tools/vectors pytest tools/vectors -q   # the vectors against the manifest and goldens
```

`check:schemas` compiles every schema under JSON Schema draft 2020-12 in strict mode, checks that each `$id` matches its path,
validates every metadata document of every vector, and confirms that each cited schema failure happens where the manifest says.
The tests open every valid vector with stock zarr-python and no other reader code, dequantize with the text's formula, compare the values with the goldens,
recompute every digest in the manifest, and confirm each derived vector differs from its base by exactly its recorded alteration.

## Rebuilding the vectors

`uv run --project tools/vectors python tools/vectors/build.py all --work <scratch directory>` rebuilds every vector.
It needs the network, to download the source recording, and a scratch directory, given with `--work`, for the download and the crop.
Each rebuild changes `created_utc` in the six root `zarr.json` files, which the writer sets to the time of writing,
and so the digests of those six files in `manifest.json`.
The chunks, every other metadata document, and the goldens come out byte-identical.
A rebuild diff confined to those lines is expected, and is not corruption.
`build.py derive --work <scratch directory>` remakes the derived vectors, the goldens, and the manifest from the committed `v2-legacy-name` without running the writer, and changes nothing.

## Adding a vector

A vector is cut from a real recording dedicated to the public domain, never generated, and its source and every step go in `SOURCES.md`.
An invalid vector is a valid one altered in one controlled, recorded way, so that a failure points to one rule.
Add it through `tools/vectors/build.py`, so it can be made again, and keep the whole of `conformance/` small.
