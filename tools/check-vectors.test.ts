// Run tools/check-vectors.ts on the real manifest with every check on, then with one check
// turned off at a time, and confirm that each check decides at least one outcome: with it
// off, the checker's reading of some vector no longer matches the manifest.

import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { ALL_CHECKS, type Checks, checkVectors } from "./check-vectors.ts";

const MANIFEST = join(new URL("..", import.meta.url).pathname, "conformance", "manifest.json");

/** The ids of the vectors whose outcome changes with these checks. */
function changed(off: Partial<Checks>): string[] {
  const problems = checkVectors({ ...ALL_CHECKS, ...off });
  return [...new Set(problems.map((problem) => problem.id))];
}

test("the real manifest agrees with the reading of the text", () => {
  expect(checkVectors()).toEqual([]);
});

test("layer 1: turned off, an outcome changes", () => {
  const ids = changed({ layer1: false });
  expect(ids.length).toBeGreaterThan(0);
  expect(ids).toContain("v3-version-4");
  expect(ids).toContain("v1-no-format-version");
});

test("layer 2: turned off, an outcome changes", () => {
  const ids = changed({ layer2: false });
  expect(ids.length).toBeGreaterThan(0);
  expect(ids).toContain("v3-no-kind");
});

test("layer 3: turned off, an outcome changes", () => {
  const ids = changed({ layer3: false });
  expect(ids.length).toBeGreaterThan(0);
  expect(ids).toContain("v3-timestamped-listed");
});

test("layer 4: turned off, an outcome changes", () => {
  const ids = changed({ layer4: false });
  expect(ids.length).toBeGreaterThan(0);
  expect(ids).toEqual(expect.arrayContaining(["v3-continuous", "v3-gap-10hz", "v3-start-time"]));
});

test("round ties: turned off, an outcome changes", () => {
  const ids = changed({ roundTies: false });
  expect(ids).toEqual(["v3-gap-10hz"]);
});

test("mask rule: turned off, an outcome changes", () => {
  const ids = changed({ maskRule: false });
  expect(ids).toEqual(["v3-gap-10hz"]);
});

test("a manifest that disagrees with the computation fails", () => {
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const gap = manifest.vectors.find((vector: { id: string }) => vector.id === "v3-gap-10hz");
  // 0.25 s at 10 Hz is the tie 2.5; a reader that rounds halves to even gives 2, not 3.
  gap.expect["3"].events.samples[0].sample = 2;
  const problems = checkVectors(ALL_CHECKS, manifest);
  expect(problems.map((problem) => problem.id)).toEqual(["v3-gap-10hz"]);
  expect(problems[0].message).toContain("event samples");
});
