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
// <group>/view/<level>/zarr.json. The view group and the event arrays have no schema.
// The check lists directories because it reads local files; a reader navigates by attributes.
//
// It also checks that each vector's class agrees with its expected outcome: a valid vector is
// accepted and cites no schema failure; an invalid vector is refused or schema-invalid.
//
// Usage: bun run check:schemas [manifest.json]
// The manifest defaults to conformance/manifest.json; its store paths resolve from conformance/.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import Ajv2020, { type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";

const ROOT = new URL("..", import.meta.url).pathname;
const SCHEMAS = join(ROOT, "schemas");
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
  const expected = ID_BASE + relative(ROOT, file).split(sep).join("/");
  if (schema.$id !== expected) problems.push(`${relative(ROOT, file)}: $id is not ${expected}`);
  ajv.addSchema(schema);
}
const validators = new Map<string, ValidateFunction>();
for (const file of schemaFiles) {
  const id = (readJson(file) as { $id: string }).$id;
  const validate = ajv.getSchema(id);
  if (!validate) problems.push(`${id}: did not compile`);
  else validators.set(id, validate);
}

/** The schema $id for a metadata document, from its path inside a store, or null. */
function schemaFor(version: number, documentPath: string): string | null {
  const parts = documentPath.split("/");
  const base = `${ID_BASE}schemas/v${version}/`;
  if (parts.length === 1) return `${base}root.schema.json`;
  if (parts.length === 2 && parts[0] === "events") return `${base}events-group.schema.json`;
  if (parts[0] === "events") return null;
  if (parts.length === 2) return `${base}uniform-group.schema.json`;
  if (parts.length === 3 && parts[1] === "0") return `${base}level0-array.schema.json`;
  if (parts.length === 4 && parts[1] === "view") return `${base}view-array.schema.json`;
  return null;
}

function describe(errors: ErrorObject[] | null | undefined): string {
  return (errors ?? [])
    .map((e) => `${e.instancePath || "/"} ${e.keyword}: ${e.message}`)
    .join("; ");
}

// 3 and 4: validate the vectors.
const manifestPath = process.argv[2] ?? join(CONFORMANCE, "manifest.json");
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
  for (const file of walk(store).filter((path) => path.endsWith("zarr.json"))) {
    const documentPath = relative(store, file).split(sep).join("/");
    const id = schemaFor(vector.format_version, documentPath);
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
