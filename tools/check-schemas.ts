// Check the JSON Schemas against the conformance vectors.
//
// 1. Compile every schema under schemas/ with JSON Schema draft 2020-12, in Ajv's strict mode.
// 2. Check that each schema's $id is https://w3id.org/biosig-zarr/<path of the file>.
// 3. Validate every metadata document of every valid vector against the schema for its node.
// 4. For every vector whose manifest entry cites a schema failure, confirm that the cited
//    document fails the cited schema at the cited instance path with the cited keyword,
//    and that every other document of the vector passes.
//
// A document's schema follows from its place in the hierarchy (spec/index.md, "Hierarchy"):
// the root zarr.json, events/zarr.json, <group>/zarr.json, <group>/0/zarr.json, and
// <group>/view/<level>/zarr.json; in version 3 also <group>/time/zarr.json and
// <group>/values/zarr.json, and a group named in the root's timestamped_groups takes the
// timestamped-group schema. The view group, time_index and the event arrays have no schema.
// The check lists directories because it reads local files; a reader navigates by attributes.
//
// A store is checked against the schemas of the directory it sits in, stores/v<N>/, which is
// the version it was written for before any alteration; a directory with no schemas/v<N>/,
// such as stores/v1/, is not validated. Every required, enum, const and pattern in
// schemas/v3/ must sit beside a $comment that names the heading of the text it comes from.
//
// It also checks that each vector's class agrees with its expected outcome: a valid vector is
// accepted and cites no schema failure; an invalid vector is refused or schema-invalid.
//
// Usage: bun run check:schemas [manifest.json] [--schemas <directory>]
// --schemas reads the schemas from another directory laid out as schemas/ is; the tests use it.
// The manifest defaults to conformance/manifest.json; its store paths resolve from conformance/.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import Ajv2020, { type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";

const ROOT = new URL("..", import.meta.url).pathname;
const args = process.argv.slice(2);
const schemasFlag = args.indexOf("--schemas");
const SCHEMAS = schemasFlag >= 0 ? args[schemasFlag + 1] : join(ROOT, "schemas");
const positional =
  schemasFlag >= 0 ? args.filter((_, i) => i < schemasFlag || i > schemasFlag + 1) : args;
const CONFORMANCE = join(ROOT, "conformance");
const ID_BASE = "https://w3id.org/biosig-zarr/";

type SchemaFailure = { schema: string; document: string; instance_path: string; keyword: string };
type Vector = {
  id: string;
  path: string;
  format_version: number;
  class: "valid" | "invalid";
  expect: Record<string, { outcome: string; schema_failure?: SchemaFailure }>;
};

const problems: string[] = [];

function walk(dir: string): string[] {
  return readdirSync(dir)
    .sort()
    .flatMap((name) => {
      const path = join(dir, name);
      return statSync(path).isDirectory() ? walk(path) : [path];
    });
}

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

// 1 and 2: compile every schema and check its $id.
const ajv = new Ajv2020({ strict: true, allErrors: true });
const schemaFiles = walk(SCHEMAS).filter((path) => path.endsWith(".schema.json"));
for (const file of schemaFiles) {
  const schema = readJson(file) as { $id?: string };
  const expected = `${ID_BASE}schemas/${relative(SCHEMAS, file).split(sep).join("/")}`;
  if (schema.$id !== expected) problems.push(`${relative(ROOT, file)}: $id is not ${expected}`);
  ajv.addSchema(schema);
}
// Every constraint of a version 3 schema names its source in the text.
const CITED = ["required", "enum", "const", "pattern"];
function uncited(node: unknown, at: string): string[] {
  if (Array.isArray(node)) return node.flatMap((item, i) => uncited(item, `${at}/${i}`));
  if (node === null || typeof node !== "object") return [];
  const object = node as Record<string, unknown>;
  const here = CITED.some((keyword) => keyword in object) && typeof object.$comment !== "string";
  return [
    ...(here ? [at || "/"] : []),
    ...Object.entries(object)
      .filter(([key]) => key !== "enum" && key !== "const")
      .flatMap(([key, value]) => uncited(value, `${at}/${key}`)),
  ];
}
for (const file of schemaFiles.filter((path) => relative(SCHEMAS, path).startsWith(`v3${sep}`))) {
  for (const at of uncited(readJson(file), "")) {
    problems.push(
      `${relative(ROOT, file)}${at}: a constraint without a $comment naming its source`,
    );
  }
}

const validators = new Map<string, ValidateFunction>();
for (const file of schemaFiles) {
  const id = (readJson(file) as { $id: string }).$id;
  const validate = ajv.getSchema(id);
  if (!validate) problems.push(`${id}: did not compile`);
  else validators.set(id, validate);
}

/**
 * The schema $id for a metadata document, from its path inside a store, or null.
 * `timestamped` names the groups the root lists in timestamped_groups (version 3 only).
 */
function schemaFor(version: number, documentPath: string, timestamped: string[]): string | null {
  const parts = documentPath.split("/");
  const base = `${ID_BASE}schemas/v${version}/`;
  if (parts.length === 1) return `${base}root.schema.json`;
  if (parts.length === 2 && parts[0] === "events") return `${base}events-group.schema.json`;
  if (parts[0] === "events") return null;
  if (version >= 3 && timestamped.includes(parts[0])) {
    if (parts.length === 2) return `${base}timestamped-group.schema.json`;
    if (parts.length === 3 && parts[1] === "time") return `${base}time-array.schema.json`;
    if (parts.length === 3 && parts[1] === "values") return `${base}values-array.schema.json`;
    return null;
  }
  if (parts.length === 2) return `${base}uniform-group.schema.json`;
  if (parts.length === 3 && parts[1] === "0") return `${base}level0-array.schema.json`;
  if (parts.length === 4 && parts[1] === "view") return `${base}view-array.schema.json`;
  return null;
}

/** The version of the schemas a store is checked against: the N of its stores/v<N>/ directory. */
function schemaVersion(vector: Vector): number | null {
  const match = /^stores\/v([0-9]+)\//.exec(vector.path);
  if (!match) return null;
  const version = Number(match[1]);
  return schemaFiles.some((file) => relative(SCHEMAS, file).startsWith(`v${version}${sep}`))
    ? version
    : null;
}

function describe(errors: ErrorObject[] | null | undefined): string {
  return (errors ?? [])
    .map((e) => `${e.instancePath || "/"} ${e.keyword}: ${e.message}`)
    .join("; ");
}

// 3 and 4: validate the vectors.
const manifestPath = positional[0] ?? join(CONFORMANCE, "manifest.json");
const manifest = readJson(manifestPath) as { vectors: Vector[] };
let documents = 0;
for (const vector of manifest.vectors) {
  const store = join(CONFORMANCE, vector.path);
  const expect = vector.expect[String(vector.format_version)];
  const failure = expect?.schema_failure;
  if (!expect) {
    problems.push(`${vector.id}: no outcome for a version ${vector.format_version} reader`);
  } else if (vector.class === "valid") {
    if (expect.outcome !== "accept") {
      problems.push(`${vector.id}: class valid, but the outcome is ${expect.outcome}`);
    }
    if (failure) problems.push(`${vector.id}: class valid, but a schema_failure is cited`);
  } else if (vector.class === "invalid") {
    if (expect.outcome !== "refuse" && expect.outcome !== "schema-invalid") {
      problems.push(`${vector.id}: class invalid, but the outcome is ${expect.outcome}`);
    }
    if (expect.outcome === "schema-invalid" && !failure) {
      problems.push(`${vector.id}: schema-invalid, but no schema_failure is cited`);
    }
  } else {
    problems.push(`${vector.id}: class is neither valid nor invalid`);
  }
  let failureSeen = false;
  const version = schemaVersion(vector);
  const rootAttributes = (readJson(join(store, "zarr.json")) as { attributes?: unknown })
    .attributes;
  const listed = (rootAttributes as { timestamped_groups?: unknown } | undefined)
    ?.timestamped_groups;
  const timestamped = Array.isArray(listed)
    ? listed.filter((name) => typeof name === "string")
    : [];
  const documentFiles = version === null ? [] : walk(store).filter((p) => p.endsWith("zarr.json"));
  for (const file of documentFiles) {
    const documentPath = relative(store, file).split(sep).join("/");
    const id = schemaFor(version, documentPath, timestamped);
    if (!id) continue;
    const validate = validators.get(id);
    if (!validate) {
      problems.push(`${vector.id}/${documentPath}: no schema ${id}`);
      continue;
    }
    documents += 1;
    const ok = validate(readJson(file));
    const cited = failure && failure.document === documentPath && failure.schema === id;
    if (cited) {
      failureSeen = true;
      const match = (validate.errors ?? []).some(
        (e) => e.instancePath === failure.instance_path && e.keyword === failure.keyword,
      );
      if (ok) problems.push(`${vector.id}/${documentPath}: passes ${id}, but should fail`);
      else if (!match) {
        problems.push(
          `${vector.id}/${documentPath}: fails, but not at ${failure.instance_path} ` +
            `(${failure.keyword}): ${describe(validate.errors)}`,
        );
      }
    } else if (!ok) {
      problems.push(`${vector.id}/${documentPath}: ${describe(validate.errors)}`);
    }
  }
  if (failure && !failureSeen) {
    problems.push(`${vector.id}: the cited document ${failure.document} was not checked`);
  }
}

if (problems.length > 0) {
  for (const problem of problems) console.error(problem);
  console.error(`check-schemas: ${problems.length} problem(s)`);
  process.exit(1);
}
console.log(
  `check-schemas: ${schemaFiles.length} schemas compiled; ` +
    `${documents} documents in ${manifest.vectors.length} vectors checked; no problems`,
);
