# Licenses

This repository has three license parts, by kind of file, and [ADR 0001](.context/decisions/0001-license-and-contribution-terms.md) records why.
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

The specification text was first published on docs.nemar.org, the documentation site of the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), in a repository licensed under Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
That license does not allow derivative works or commercial use.
On 2026-11-20 the text's author relicensed it under the W3C Software and Document License, in this repository.
The format page on docs.nemar.org was then replaced by a pointer to this repository, which holds the one canonical copy.

Hosting this repository, which NEMAR provides as a service, gives NEMAR no ownership of the text.

Copyright (c) 2026 the biosig-zarr contributors.
