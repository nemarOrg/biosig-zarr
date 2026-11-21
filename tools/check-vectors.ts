// Check the conformance vectors' expected outcomes for a reader of the version 3 text.
//
// For every vector, read the store's metadata documents the way the text says a reader of
// format version 3 reads them, and compare the result with the manifest's expect["3"]:
//
// - the version rules and layer 1 (Format version, Reading earlier versions);
// - layer 2, the kind of every group, read before any of its arrays;
// - layer 3, the structure: a name in only one of channel_groups and timestamped_groups,
//   only uniform groups in channel_groups, and the nodes and attributes of each kind;
// - layer 4, the attributes in effect in a uniform group (start_time, valid_intervals,
//   missing_value), which a reader that does not implement one of them MUST refuse;
// - the rules of valid intervals that a reader MUST check ("Reading untrusted stores");
// - the onset rule ("From an onset to a sample"), with round(x) = floor(x + 0.5);
// - the mask rule of the view pyramid.
//
// It reads only metadata (zarr.json) and decodes no chunk. The onsets of the events are
// chunk data, so they come from the manifest, and tools/vectors/test_vectors.py checks
// them against the arrays; so does the sample of an onset in a timestamped group, which
// needs the time array.
//
// Each check can be turned off through `Checks`, which tools/check-vectors.test.ts uses to
// prove that each one decides at least one outcome.
//
// Usage: bun run tools/check-vectors.ts [manifest.json]

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const CONFORMANCE = join(ROOT, "conformance");
const SPEC = join(ROOT, "spec", "index.md");
const HIGHEST_VERSION = 3;
const FORMAT_NAMES = new Set(["biosig-zarr", "biosigio-zarr"]);
const KINDS = new Set(["uniform", "timestamped"]);

export type Checks = {
  layer1: boolean;
  layer2: boolean;
  layer3: boolean;
  layer4: boolean;
  /** true: round(x) = floor(x + 0.5), as the text defines it; false: halves to even. */
  roundTies: boolean;
  maskRule: boolean;
};

export const ALL_CHECKS: Checks = {
  layer1: true,
  layer2: true,
  layer3: true,
  layer4: true,
  roundTies: true,
  maskRule: true,
};

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Attributes = Record<string, Json>;
type Interval = { start: number; stop: number; source_time: number | null };
type Refusal = { layer: number | null; rule: string; subject: string };
type Sample = { group: string; onset: number; sample: number | null };
type GroupRead = {
  start_time: number;
  valid_intervals: Interval[];
  missing_value: Json;
  refuse_without: string[];
  view_empty_columns: Record<string, number[]>;
};
type Read =
  | { outcome: "refuse"; refusal: Refusal }
  | {
      outcome: "accept";
      uniform_groups: string[];
      timestamped_groups: string[];
      groups: Record<string, GroupRead>;
      events: { onset_source_basis: Json; samples: Sample[] };
    };
type Expected = {
  outcome: "accept" | "refuse" | "schema-invalid";
  reader?: "accept" | "refuse";
  refusal?: Refusal;
  uniform_groups?: string[];
  timestamped_groups?: string[];
  groups?: Record<string, GroupRead>;
  events?: { onset_source_basis: Json; samples: Sample[] };
};
type Vector = {
  id: string;
  path: string;
  layer: unknown;
  rule: string;
  expect: Record<string, Expected>;
};
export type Problem = { id: string; message: string };

class Refused extends Error {
  constructor(readonly refusal: Refusal) {
    super(`${refusal.rule}: ${refusal.subject}`);
  }
}

function refuse(layer: number | null, rule: string, subject: string): never {
  throw new Refused({ layer, rule, subject });
}

/** The attributes of the metadata document at `path` inside a store, or null if it is absent. */
function attributes(store: string, path: string): Attributes | null {
  const file = join(store, path, "zarr.json");
  if (!existsSync(file)) return null;
  const document = JSON.parse(readFileSync(file, "utf8")) as { attributes?: Attributes };
  return document.attributes ?? {};
}

function shapeOf(store: string, path: string): number[] | null {
  const file = join(store, path, "zarr.json");
  if (!existsSync(file)) return null;
  return (JSON.parse(readFileSync(file, "utf8")) as { shape?: number[] }).shape ?? null;
}

/** round(x) as the text defines it, floor(x + 0.5); or, turned off, halves to even. */
function rounder(checks: Checks): (x: number) => number {
  if (checks.roundTies) return (x) => Math.floor(x + 0.5);
  return (x) => {
    const floor = Math.floor(x);
    const fraction = x - floor;
    if (fraction !== 0.5) return fraction < 0.5 ? floor : floor + 1;
    return floor % 2 === 0 ? floor : floor + 1;
  };
}

function isNumber(value: Json | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** The rules of "Valid intervals" that a reader MUST check ("Reading untrusted stores"). */
function checkIntervals(
  name: string,
  intervals: Json | undefined,
  attrs: { n_samples: number; rate: number; start_time: number },
  round: (x: number) => number,
): Interval[] {
  const bad = () => refuse(null, "reading-untrusted-stores", name);
  if (!Array.isArray(intervals) || intervals.length === 0) return bad();
  const out: Interval[] = [];
  for (const [k, entry] of intervals.entries()) {
    if (entry === null || typeof entry !== "object" || Array.isArray(entry)) return bad();
    const { start, stop, source_time } = entry;
    if (!Number.isInteger(start) || !Number.isInteger(stop)) return bad();
    if (source_time !== null && !isNumber(source_time)) return bad();
    const interval = { start, stop, source_time } as Interval;
    const previous = out[k - 1];
    if (interval.start >= interval.stop) return bad();
    if (k === 0 && interval.start !== 0) return bad();
    if (previous && interval.start < previous.stop) return bad();
    if (interval.source_time === null) {
      if (interval.start !== (previous ? previous.stop : 0)) return bad();
    } else if (interval.start !== round((interval.source_time - attrs.start_time) * attrs.rate)) {
      return bad();
    }
    out.push(interval);
  }
  if (out[out.length - 1].stop !== attrs.n_samples) return bad();
  return out;
}

function readUniform(
  store: string,
  name: string,
  attrs: Attributes,
  version: number,
  checks: Checks,
): GroupRead & { n_samples: number; rate: number } {
  const level0 = attributes(store, `${name}/0`);
  const { n_samples, rate } = attrs;
  // Layer 3: a group that is not uniform has no array 0 and no attribute rate, so a reader
  // that opens it as a uniform group gets an error, not wrong times.
  if (level0 === null || !isNumber(n_samples) || !isNumber(rate)) {
    return refuse(3, "reader-safety", name);
  }
  let start_time = 0;
  let valid_intervals: Interval[] = [{ start: 0, stop: n_samples, source_time: 0 }];
  let missing_value: Json = null;
  if (version >= 3) {
    if (!isNumber(attrs.start_time) || !("missing_value" in level0)) {
      return refuse(3, "reader-safety", name);
    }
    start_time = attrs.start_time;
    missing_value = level0.missing_value;
    valid_intervals = checkIntervals(
      name,
      attrs.valid_intervals,
      { n_samples, rate, start_time },
      rounder(checks),
    );
  }
  // Layer 4: what a reader that does not implement the attribute MUST refuse.
  const inEffect = [
    ...(start_time !== 0 ? ["start_time"] : []),
    ...(valid_intervals.length > 1 ? ["valid_intervals"] : []),
    ...(missing_value !== null ? ["missing_value"] : []),
  ];
  const view_empty_columns: Record<string, number[]> = {};
  const levels = Array.isArray(attrs.view_levels) ? attrs.view_levels : [];
  for (const level of levels) {
    const view = attributes(store, `${name}/view/${level}`);
    const shape = shapeOf(store, `${name}/view/${level}`);
    if (view === null || shape === null || !isNumber(view.downsample_factor)) {
      return refuse(3, "reader-safety", `${name}/view/${level}`);
    }
    const factor = view.downsample_factor;
    const empty: number[] = [];
    // The mask rule: column j covers acquired samples if and only if some valid interval
    // has start < (j + 1) * f and stop > j * f.
    for (let j = 0; checks.maskRule && j < shape[2]; j += 1) {
      const covered = valid_intervals.some(
        (i) => i.start < (j + 1) * factor && i.stop > j * factor,
      );
      if (!covered) empty.push(j);
    }
    view_empty_columns[String(level)] = empty;
  }
  return {
    n_samples,
    rate,
    start_time,
    valid_intervals,
    missing_value,
    refuse_without: checks.layer4 ? inEffect : [],
    view_empty_columns,
  };
}

/** Read one store as a reader of the version 3 text, from its metadata only. */
function read(store: string, onsets: Sample[], checks: Checks): Read {
  const root = attributes(store, "");
  if (root === null) return refuse(null, "zarr-requirements", "zarr.json");
  if (typeof root.format !== "string" || !FORMAT_NAMES.has(root.format)) {
    return refuse(null, "format-name", "format");
  }
  const declared = root.format_version;
  if (checks.layer1) {
    if (declared === undefined) return refuse(1, "format-version", "format_version");
    if (!isNumber(declared) || !Number.isInteger(declared)) {
      return refuse(1, "format-version", "format_version");
    }
    if (declared > HIGHEST_VERSION || declared < 2) {
      return refuse(1, "format-version", "format_version");
    }
  }
  // A reader that skips the version check reads the layout it knows, version 3, unless
  // the store says version 2.
  const version = declared === 2 ? 2 : 3;
  const channelGroups = root.channel_groups;
  if (!Array.isArray(channelGroups) || !channelGroups.every((n) => typeof n === "string")) {
    return refuse(null, "root-attributes", "channel_groups");
  }
  // timestamped_groups is checked after the groups of channel_groups, whose kind a reader
  // reads first: a store that claims version 3 and has no kind is refused at layer 2.
  const listed = version >= 3 ? root.timestamped_groups : [];
  const wellFormed = Array.isArray(listed) && listed.every((n) => typeof n === "string");
  const timestampedListed = wellFormed ? (listed as string[]) : [];
  if (checks.layer3) {
    const both = (channelGroups as string[]).find((name) => timestampedListed.includes(name));
    if (both !== undefined) return refuse(3, "reader-safety", both);
  }
  const uniform: Record<string, ReturnType<typeof readUniform>> = {};
  const timestamped: string[] = [];
  const groupAttributes = (name: string, expected: string): [Attributes, string] => {
    const attrs = attributes(store, name);
    if (attrs === null) return refuse(3, "reader-safety", name);
    if (version < 3) return [attrs, "uniform"];
    // Layer 2: read kind before any array; refuse a group with no kind or an unknown one.
    if (checks.layer2 && (typeof attrs.kind !== "string" || !KINDS.has(attrs.kind))) {
      return refuse(2, "reader-safety", name);
    }
    // A reader that skips layer 2 takes the kind from the list that names the group.
    const kind = checks.layer2 ? (attrs.kind as string) : expected;
    // Layer 3: channel_groups names only uniform groups, timestamped_groups only timestamped.
    if (checks.layer3 && kind !== expected) return refuse(3, "reader-safety", name);
    return [attrs, kind];
  };
  for (const name of channelGroups as string[]) {
    const [attrs, kind] = groupAttributes(name, "uniform");
    if (kind === "uniform") uniform[name] = readUniform(store, name, attrs, version, checks);
    else timestamped.push(name);
  }
  if (!wellFormed) return refuse(null, "root-attributes", "timestamped_groups");
  for (const name of timestampedListed) {
    if (timestamped.includes(name)) continue;
    const [, kind] = groupAttributes(name, "timestamped");
    if (kind !== "timestamped") continue;
    for (const node of ["time", "values", "time_index"]) {
      if (attributes(store, `${name}/${node}`) === null) return refuse(3, "reader-safety", name);
    }
    timestamped.push(name);
  }
  const events = attributes(store, "events");
  if (events === null) return refuse(null, "events-group", "events");
  const round = rounder(checks);
  const samples = onsets
    .filter((event) => event.group in uniform)
    .map(({ group, onset }) => {
      const g = uniform[group];
      // From an onset to a sample: i = round((onset - start_time) * rate); no sample when i
      // is outside [0, n_samples) or outside every valid interval, never a clamped one.
      const i = round((onset - g.start_time) * g.rate);
      const inside =
        i >= 0 && i < g.n_samples && g.valid_intervals.some((v) => v.start <= i && i < v.stop);
      return { group, onset, sample: inside ? i : null };
    });
  const groups: Record<string, GroupRead> = {};
  for (const [name, { n_samples: _n, rate: _r, ...group }] of Object.entries(uniform)) {
    groups[name] = group;
  }
  return {
    outcome: "accept",
    uniform_groups: Object.keys(uniform),
    timestamped_groups: timestamped,
    groups,
    events: {
      onset_source_basis: version >= 3 ? (events.onset_source_basis ?? null) : "unknown",
      samples,
    },
  };
}

function readOrRefuse(store: string, onsets: Sample[], checks: Checks): Read {
  try {
    return read(store, onsets, checks);
  } catch (error) {
    if (error instanceof Refused) return { outcome: "refuse", refusal: error.refusal };
    throw error;
  }
}

/** JSON text with the members of every object sorted, so that equal values compare equal. */
function canonical(value: unknown): string {
  return JSON.stringify(value, (_key, v) =>
    v !== null && typeof v === "object" && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)))
      : v,
  );
}

function same(a: unknown, b: unknown): boolean {
  return canonical(a) === canonical(b);
}

/** The anchors of the headings of spec/index.md, as GitHub renders them. */
function anchors(): Set<string> {
  const headings = readFileSync(SPEC, "utf8")
    .split("\n")
    .filter((line) => /^#{2,4} /.test(line))
    .map((line) =>
      line
        .replace(/^#+ /, "")
        .toLowerCase()
        .replace(/[^a-z0-9 -]/g, "")
        .replace(/ /g, "-"),
    );
  return new Set(headings);
}

/** Compare every vector's expect["3"] with what a reader of the version 3 text reads. */
export function checkVectors(
  checks: Checks = ALL_CHECKS,
  manifest: { vectors: Vector[] } = JSON.parse(
    readFileSync(join(CONFORMANCE, "manifest.json"), "utf8"),
  ),
): Problem[] {
  const problems: Problem[] = [];
  const headingAnchors = anchors();
  for (const vector of manifest.vectors) {
    const note = (message: string) => problems.push({ id: vector.id, message });
    if (!(vector.layer === null || [1, 2, 3, 4].includes(vector.layer as number))) {
      note(`layer ${JSON.stringify(vector.layer)} is not null or 1 to 4`);
    }
    if (!headingAnchors.has(vector.rule)) note(`rule ${vector.rule} is no heading of the text`);
    const expected = vector.expect["3"];
    if (!expected) {
      note("no outcome for a version 3 reader");
      continue;
    }
    const outcome = expected.outcome === "schema-invalid" ? expected.reader : expected.outcome;
    if (outcome === undefined) continue; // the text states no reader outcome
    const onsets = expected.events?.samples ?? [];
    const got = readOrRefuse(join(CONFORMANCE, vector.path), onsets, checks);
    if (got.outcome !== outcome) {
      const why = got.outcome === "refuse" ? ` (${JSON.stringify(got.refusal)})` : "";
      note(`expected ${outcome}, read ${got.outcome}${why}`);
      continue;
    }
    if (got.outcome === "refuse") {
      if (!same(got.refusal, expected.refusal)) {
        note(
          `refusal ${JSON.stringify(got.refusal)}, expected ${JSON.stringify(expected.refusal)}`,
        );
      }
      continue;
    }
    const uniformOnly = (expected.events?.samples ?? []).filter((s) => s.group in got.groups);
    const compared: [string, unknown, unknown][] = [
      ["uniform_groups", got.uniform_groups, expected.uniform_groups],
      ["timestamped_groups", got.timestamped_groups, expected.timestamped_groups],
      ["groups", got.groups, expected.groups],
      ["onset_source_basis", got.events.onset_source_basis, expected.events?.onset_source_basis],
      ["event samples", got.events.samples, uniformOnly],
    ];
    for (const [what, computed, stated] of compared) {
      if (!same(computed, stated)) {
        note(`${what}: read ${JSON.stringify(computed)}, expected ${JSON.stringify(stated)}`);
      }
    }
  }
  return problems;
}

if (import.meta.main) {
  const path = process.argv[2];
  const manifest = path ? JSON.parse(readFileSync(path, "utf8")) : undefined;
  const problems = checkVectors(ALL_CHECKS, manifest);
  for (const { id, message } of problems) console.error(`${id}: ${message}`);
  if (problems.length > 0) {
    console.error(`check-vectors: ${problems.length} problem(s)`);
    process.exit(1);
  }
  const count = (manifest ?? JSON.parse(readFileSync(join(CONFORMANCE, "manifest.json"), "utf8")))
    .vectors.length;
  console.log(`check-vectors: ${count} vectors read as a version 3 reader; no problems`);
}
