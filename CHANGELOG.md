# Changelog

All notable changes to the specification are recorded here, newest first.
The versioning scheme is in [`GOVERNANCE.md`](GOVERNANCE.md).
A release is a Git tag made by the owner.

## Unreleased: 3.0.0-draft.1

The text that RFC-0001 in nemarOrg/rfcs proposes, on the branch `draft/3.0.0`.
It is not accepted; it becomes `3.0.0` only if RFC-0001 is accepted.
It specifies `format_version` 3.

Normative changes, all proposed:

- `format_version` 3: a writer writes 3 on every store, and a reader that implements version 3 also reads version 2 stores, with stated default values; a store is never moved to another version by editing its metadata.
- Every channel group carries a required `kind`, `uniform` or `timestamped`; the root lists timestamped groups in a new `timestamped_groups`, and `channel_groups` names only uniform groups.
- A uniform group carries `start_time`, `valid_intervals` (with a nullable `source_time`), and `time_regularization`; `rate` is never rounded; gaps are never written to storage; each valid interval is resampled on its own.
- A timestamped group holds `time`, `values` and `time_index` arrays, with `nominal_rate`, `effective_rate`, `time_range`, `continuity` and `chunk_samples`.
- Every signal array declares `missing_value`, and its `fill_value` equals it; an `int16` array reserves `-32768`, so data codes run from `-32767` to `32767`; `null` is allowed only for an exact copy of full-range source codes.
- Non-finite source samples in an integer array are stored as the missing value, replacing the version 2 replacement by the code nearest physical zero.
- One recording timeline per store, with an optional root `origin_source_time`; event onsets are on it, the `events` group carries a required `onset_source_basis`, and the rule from an onset to a sample is defined.
- Storage types `int32` and `float64` join `int16` and `float32`, with a per-group `dtype` that overrides the root; a signal reader must support `int16` and may refuse the others with an error.
- Source resolution fields: `source_sample_type` and `source_adc_bits` (root default, channel override), and `source_step`, `source_offset` and `source_digital_range` per channel.
- Exact copies of source codes are allowed.
- A required per-channel `derivation` list, from a closed vocabulary that a profile may extend with tokens containing a colon.
- The four reader-safety layers (version, kind, structure, and refusal inside a uniform group), each with a conformance case.
- A version 3 writer writes the format name `biosig-zarr`, and the root attribute `zarr_conventions` carries the convention identifier of ADR 0004.
- The packing rules of `.bzx` are NEMAR's own, with OME-Zarr RFC-9 as prior art; an absent chunk has no entry; the packing rules share `format_version`.
- A reader refuses a group whose valid intervals break their rules.
- The NEMAR profile section lists the choices NEMAR proposes for version 3.

Changes after the first review (round 1), all proposed:

- `round(x)` is defined once as `floor(x + 0.5)` in 64-bit floating point, with halves rounding up, and used for interval placement, interval lengths, `n_samples`, and the onset rule.
- A version 3 reader must read version 2 stores (settled, not open for comment); version 1 stores are no longer covered, and the earlier SHOULD for them is removed.
- A version 2 store's default `onset_source_basis` is `"unknown"`, not `"timeline"`.
- The grouping key and `original_rate` keep the rounding of version 2; only `rate` must not be rounded, and open question 5 says so.
- Multi-interval resampling is specified: each interval's start, sample count `max(1, round(m * rate / source rate))`, and stop, so two writers derive the same `n_samples`.
- Valid intervals are half-open in sample indices; a gap lasts `(next.start - prev.stop) / rate` seconds; a gap shorter than one sample cannot be expressed on the grid and needs a timestamped group (RFC-0001 question 40); a `null` `source_time` on the first interval makes `start_time` a convention; `source_time` is on the recording timeline, not the source clock.
- The onset rule: an event inside a gap keeps its onset and has no sample, never the nearest acquired one, with the 10 Hz example (intervals `[0, 20)` and `[24, 40)`, an event at 2.02 seconds) as a required reader case; the timestamped onset rule gains an upper bound.
- Non-finite source samples never enter a resampling filter; a stored sample is missing when its nearest source sample is non-finite; `nonfinite_samples` counts those stored samples.
- `missing_value` `null` and exact copies depend on the declared `source_digital_range`, not on observed codes.
- View levels exclude missing columns at every level, and the mask rule for a view column is defined, including for `missing_value` `null`.
- The derivation list defines when a stored sample differs from its source sample, for integer and floating point storage, including an integer source stored as floating point (`narrowed`); the meaning of an empty list is stated for both.
- `effective_rate` in `time_regularization` is `null` when there is one source timestamp, as in a timestamped group.
- Reader safety: a single interval with a `null` `source_time` no longer counts as `valid_intervals` in effect; layer 1 cites the version check of biosigIO 1.2.13 and the name check, instead of an unverified range of releases; the conformance suite is described as arriving before RFC-0001 opens, with at least one failing case per layer.
- `zarr_conventions` is part of the writer and identifying-reader conformance classes.
- The NEMAR profile also stores the `values` of timestamped groups as `int16`, and names the Store Contract as authoritative for NEMAR's served stores.
- The timestamped group's motivation cites EDF+D records of duration 0 (EDF+ sections 2.1.1, 2.1.2 and 2.2.4).
- In the packaged form, stored entries, byte-identical entries and writing once are marked open under RFC-0001 question 8, and refusing a version from the archive comment is marked as depending on question 10.
- New open-for-comment markers: RFC-0001 questions 36 (reader safety), 37 (recording timeline), 38 (onset rule), 39 (an explicit bit-depth attribute), 40 (sub-sample gaps), and question 28 on the `time` array's vocabulary.
- The BDF channel example uses `scale` 0.061037 and `offset` 0.0, matching RFC-0001.

Changes after the second review (round 2), proposed:

- A store with no `format_version` is called a version 1 store only historically, and a reader of this document refuses it as unsupported.
- The exact-copy rule about a source code equal to the missing value now says that such a code lies outside the declared digital range and cannot arise when the source keeps to that range.

Editorial corrections:

- The status section said "Three parts" run ahead of any implementation and listed four; the count now matches the list, which gains the new `zarr_conventions` attribute as a fifth.
- "This page" is now "this document" throughout, because the text lives in this repository and not on docs.nemar.org.
- Open question 33 now records that the change process, the license and the home are decided, and closed questions 6, 9 and 16 say where version 3 specifies them; the numbering of the open questions is kept.
- Open questions 4, 5 and 12 say what version 3 does about them and point to RFC-0001 questions 5, 2 and 29; other open questions name their RFC-0001 question.
- The `generated_by` example is now a valid JSON object.
- Places that RFC-0001 puts up for comment are marked with their question number.

## Unreleased

- The repository is initialized: licenses, governance, contribution terms, decision records, and checks on the text.
- A check, `tools/check-moved-text.ts`, compares the word sequence of the specification text with its earlier copy on docs.nemar.org.
- ADR 0004 records the identifier of the biosig-zarr Zarr convention.

## 2.0.0

Format version 2, moved from docs.nemar.org with no normative change.
Four parts the text marks Proposed are not yet implemented in NEMAR's stores: the `biosig-zarr` tag inside stores, `.bzx`, `generated_by`, and the conformance classes.
