// Run tools/check-schemas.ts on the real manifest and on copies with one member changed,
// and confirm it passes the first and fails each copy.

import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const SCRIPT = join(ROOT, "tools", "check-schemas.ts");
const MANIFEST = join(ROOT, "conformance", "manifest.json");

type Entry = { id: string; class: string; expect: Record<string, Record<string, unknown>> };

function run(manifest?: unknown): { code: number; stderr: string } {
  const args = ["bun", "run", SCRIPT];
  let dir: string | undefined;
  if (manifest !== undefined) {
    dir = mkdtempSync(join(tmpdir(), "check-schemas-"));
    const path = join(dir, "manifest.json");
    writeFileSync(path, JSON.stringify(manifest));
    args.push(path);
  }
  const result = Bun.spawnSync(args, { cwd: ROOT, stderr: "pipe", stdout: "pipe" });
  if (dir) rmSync(dir, { recursive: true });
  return { code: result.exitCode, stderr: result.stderr.toString() };
}

function altered(id: string, change: (entry: Entry) => void): unknown {
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8")) as { vectors: Entry[] };
  const entry = manifest.vectors.find((vector) => vector.id === id);
  if (!entry) throw new Error(`no vector ${id}`);
  change(entry);
  return manifest;
}

test("the real manifest passes", () => {
  expect(run().code).toBe(0);
});

test("a valid vector flipped to invalid fails", () => {
  const result = run(altered("v2-legacy-name", (entry) => (entry.class = "invalid")));
  expect(result.code).toBe(1);
  expect(result.stderr).toContain("v2-legacy-name: class invalid, but the outcome is accept");
});

test("an invalid vector flipped to valid fails", () => {
  const result = run(altered("v2-version-3", (entry) => (entry.class = "valid")));
  expect(result.code).toBe(1);
  expect(result.stderr).toContain("v2-version-3: class valid, but the outcome is refuse");
  expect(result.stderr).toContain("v2-version-3: class valid, but a schema_failure is cited");
});

test("a schema-invalid vector without a cited failure fails", () => {
  const result = run(
    altered("v2-no-channel-groups", (entry) => delete entry.expect["2"].schema_failure),
  );
  expect(result.code).toBe(1);
  expect(result.stderr).toContain("v2-no-channel-groups: schema-invalid, but no schema_failure");
});

test("a cited failure that the store does not have fails", () => {
  const result = run(
    altered("v2-unknown-format", (entry) => {
      (entry.expect["2"].schema_failure as { instance_path: string }).instance_path = "/node_type";
    }),
  );
  expect(result.code).toBe(1);
  expect(result.stderr).toContain("v2-unknown-format/zarr.json: fails, but not at /node_type");
});
