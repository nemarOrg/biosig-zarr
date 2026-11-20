# ADR 0001: License and contribution terms

**Status:** accepted
**Date:** 2026-11-20
**Owner:** Seyed Yahya Shirazi

## Context

The Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) decided, in its Architecture Decision Record (ADR) 0128, "The Zarr serving copy is not an NWB container" (nemarOrg/nemar-cli), on 2026-11-18 that biosig-zarr is specified as its own format under a license that follows the Open Microscopy Environment Next-Generation File Format (OME-NGFF) model:
the World Wide Web Consortium (W3C) Software and Document License for the specification text, and the Apache License 2.0 for software, schemas, and test vectors.
Two things were still open when this repository was created.
The text was first published on docs.nemar.org, inside a repository licensed Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0), which forbids derivative works and contradicts the decided license.
And the contribution terms were unsettled: OME-NGFF uses the W3C contributor agreement, which applies only inside a W3C community group.

## Decision

1. The specification text is under the W3C Software and Document License (2023 version, the current one).
2. The JSON Schemas, conformance vectors, tools, and any code are under the Apache License 2.0.
   Recordings used for vectors keep their public-domain dedication (Creative Commons CC0 1.0).
3. The owner relicensed the text from CC BY-NC-ND 4.0 to the licenses above on 2026-11-20; `LICENSE.md` records it, and the format page on docs.nemar.org is replaced by a pointer to this repository.
4. Contributions are licensed under the same license as the part they touch ("inbound equals outbound"), and every commit carries a Developer Certificate of Origin (DCO) sign-off.
   There is no contributor license agreement.

## Consequences

- Anyone may copy, modify, and redistribute the text, including commercially, if the notice travels with the copy.
  That is the intent: other tools must be able to quote and build on the specification.
- Apache 2.0 carries an explicit patent grant, which matters more for a format that others implement than for a tool.
- The 2023 W3C license has no Software Package Data Exchange (SPDX) identifier; the SPDX list carries only the 2015 version.
  `LICENSE.md` names the license in words, and the license file in `LICENSES/` is the 2023 text from w3.org.
- Contributors must sign off each commit; a reviewer checks it, because no bot is installed.
- No agreement needs administering, and a contributor's rights are stated in the commit itself.
- A later change of license for any part needs a new ADR.

## Alternatives considered

- **Creative Commons Attribution 4.0 International (CC BY 4.0) for the text:** the choice of the Brain Imaging Data Structure and better known to researchers.
  Rejected because the owner had already decided the OME-NGFF model, whose neighbor text can then be quoted without a license mismatch.
- **Keep CC BY-NC-ND 4.0:** rejected; no derivative works and no commercial use contradict the purpose of an open specification.
- **A contributor license agreement, or the W3C contributor agreement:** rejected; the first needs administering, the second applies only inside a W3C community group.

## Receipts

- NEMAR ADR 0128 (content: the license model and the decision that biosig-zarr is its own specified format) and neuromechanist/biosigio#179: <https://github.com/neuromechanist/biosigio/issues/179>.
- W3C Software and Document License, 2023 version: <https://www.w3.org/copyright/software-license-2023/>.
- Apache License 2.0: <https://www.apache.org/licenses/LICENSE-2.0>.
- Developer Certificate of Origin: <https://developercertificate.org/>.
