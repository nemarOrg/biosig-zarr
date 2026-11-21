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
| `class` | `valid` when the store conforms to the text, `invalid` when it does not. |
| `layer` | The reader-safety layer, 1 to 4, that the vector tests for the newest reader the manifest has outcomes for, or `null`. A version 2 reader has no layers, so every entry is `null` at `2.0.1`. |
| `rule` | The anchor of the heading in `spec/index.md` whose rule the vector tests, such as `format-name`. |
| `description` | Optional free text. |
| `derived_from`, `alteration` | For a vector made by altering another: the base vector, the document changed, and the change as a JSON Patch (Request for Comments (RFC) 6902). Every other file is byte-identical to the base. |
| `expect` | The outcome for a reader, keyed by the format version that reader implements, as a string (`"2"`). |
| `files` | The SHA-256 of every file of the store, keyed by its path inside the store. |

An outcome in `expect` has the member `outcome`:

- `accept`: a conforming reader opens the store, and `goldens` names the file of values it must return.
- `refuse`: a conforming reader refuses the store, for the rule in `rule`.
- `schema-invalid`: the store does not conform, and a schema shows it; the text states no reader outcome beyond that.

When a schema rejects the store, `schema_failure` names the schema's `$id`, the `document` inside the store, the `instance_path` (a JSON Pointer) where validation fails, and the failing `keyword`.
Every other metadata document of the store validates.

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
uv run --project tools/vectors pytest tools/vectors -q   # the vectors against the manifest and goldens
```

`check:schemas` compiles every schema under JSON Schema draft 2020-12 in strict mode, checks that each `$id` matches its path,
validates every metadata document of every vector, and confirms that each cited schema failure happens where the manifest says.
The tests open every valid vector with stock zarr-python and no other reader code, dequantize with the text's formula, compare the values with the goldens,
recompute every digest in the manifest, and confirm each derived vector differs from its base by exactly its recorded alteration.

## Adding a vector

A vector is cut from a real recording dedicated to the public domain, never generated, and its source and every step go in `SOURCES.md`.
An invalid vector is a valid one altered in one controlled, recorded way, so that a failure points to one rule.
Add it through `tools/vectors/build.py`, so it can be made again, and keep the whole of `conformance/` small.
