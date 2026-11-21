# Version history

This page records what changed in the format, by `format_version` and by specification release.
It is informative: the normative text is [`index.md`](index.md), and the changes of each release are in [`CHANGELOG.md`](../CHANGELOG.md).
The release scheme is in [`GOVERNANCE.md`](../GOVERNANCE.md): the major number of a release equals `format_version`.

## By `format_version`

| `format_version` | What it is | Where it is defined |
| --- | --- | --- |
| 1 | `recording_metadata` is a string holding JavaScript Object Notation (JSON) text; a store with no `format_version` attribute is a version 1 store | [Format version](index.md#format-version) |
| 2 | `recording_metadata` is a JSON object; the format that [`index.md`](index.md) specifies | [Format version](index.md#format-version) |

Version 2 has grown by addition without changing the number, so two version 2 stores can differ in which attributes they carry.
The attributes that older stores can lack, and the release of biosigIO that first wrote each, are listed under [What changes the version](index.md#what-changes-the-version).

## By specification release

| Release | `format_version` | Summary |
| --- | --- | --- |
| 2.0.0 | 2 | The pre-beta text moved from docs.nemar.org, with no normative change. Four parts the text marks Proposed are not yet implemented in stores served by the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR): the `biosig-zarr` tag inside stores, `.bzx`, `generated_by`, and the conformance classes. |
| 2.0.1 | 2 | Editorial, no change to what conforms: the JSON Schemas for format version 2, in `schemas/v2/`, and the first conformance vectors, in `conformance/`, cut from one recording dedicated to the public domain. |
| 2.0.2 | 2 | Editorial, no change to what conforms: the specification is independent of NEMAR, its first implementer, and the copyright holder of its text is the biosig-zarr contributors ([Architecture Decision Record 0005](../.context/decisions/0005-the-specification-is-independent-of-nemar.md)). |

Later releases are added here when they are tagged.
A release that proposes a change lives on a draft branch and is tagged with a `-draft.N` suffix until its Request for Comments is accepted; see [`GOVERNANCE.md`](../GOVERNANCE.md).
