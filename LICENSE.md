# Licenses

The Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) decided on 2026-11-18, and confirmed on 2026-11-20, that this repository has three license parts, by kind of file.
The full license texts are in [`LICENSES/`](LICENSES/).

## 1. Specification text

The specification text is under the World Wide Web Consortium (W3C) Software and Document License, 2023 version.
The text is `spec/` and the other Markdown documentation: `README.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, and the Architecture Decision Records in `.context/decisions/`.
The license text is [`LICENSES/W3C-SOFTWARE-DOC-20230101.txt`](LICENSES/W3C-SOFTWARE-DOC-20230101.txt).
It lets anyone copy, modify, and distribute the text for any purpose, provided the notice travels with every copy and every change is noted.

## 2. Software, schemas, and conformance vectors

The following are under the Apache License 2.0 (`Apache-2.0`): the JSON Schemas in `schemas/`, the conformance vectors in `conformance/`, tools, any code, the continuous integration workflows, and the configuration files (`package.json`, `bun.lock`, `biome.json`, `_typos.toml`).
The license text is [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt).

A conformance vector is cut from a real recording that its source dedicated to the public domain (Creative Commons CC0 1.0).
The vector's own files, such as manifests and expected results, are Apache-2.0.
The recording's data keeps its CC0 dedication, and the source of each recording is recorded beside it.

## 3. Contributions

By contributing, you license your contribution under the same license as the part it touches: the W3C Software and Document License for text, and Apache-2.0 for schemas, vectors, tools, and code ("inbound equals outbound").
Every commit carries a Developer Certificate of Origin (DCO) sign-off, which is how a contributor states the right to do so.
No contributor license agreement is used.
[`CONTRIBUTING.md`](CONTRIBUTING.md) explains how to sign off.

## Record of the text's earlier license

The specification text was first published on docs.nemar.org, in a repository licensed under Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
That license does not allow derivative works or commercial use, and it contradicts the license NEMAR decided for the text on 2026-11-18.
On 2026-11-20 the owner of the text relicensed it to the W3C Software and Document License in this repository.
Once the text has moved, the format page on docs.nemar.org is removed and replaced by a pointer to this repository, so this repository holds the one canonical copy.

Copyright (c) 2026 NEMAR contributors.
