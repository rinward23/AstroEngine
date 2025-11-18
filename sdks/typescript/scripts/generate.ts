import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface ReleaseMetadata {
  schemaPath: string;
  schemaVersion: string;
  schemaHash: string;
  solarFireDigest: string;
  swissEphemerisDigest: string;
}

export interface OperationDescriptor {
  method: string;
  path: string;
  operationId: string;
  summary: string;
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(projectRoot, "../..");
const defaultSchemaPath = path.resolve(repoRoot, "openapi/v1.0.json");

function sha256(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

function digestFile(relativePath: string): string {
  const absolute = path.resolve(repoRoot, relativePath);
  if (!existsSync(absolute)) {
    return `missing:${relativePath}`;
  }
  const content = readFileSync(absolute, "utf8");
  return sha256(content).slice(0, 16);
}

function parseArgs(argv: string[]): string {
  const schemaIndex = argv.findIndex((value) => value === "--schema");
  if (schemaIndex !== -1 && argv[schemaIndex + 1]) {
    return path.resolve(argv[schemaIndex + 1]);
  }
  return defaultSchemaPath;
}

function ensureGeneratedDir(): string {
  const generatedDir = path.resolve(projectRoot, "src/generated");
  mkdirSync(generatedDir, { recursive: true });
  return generatedDir;
}

function writeOperationsFile(
  operations: OperationDescriptor[],
  generatedDir: string,
): void {
  const fileContent = `/* Auto-generated from OpenAPI */\nexport interface OperationDescriptor {\n  readonly method: string;\n  readonly path: string;\n  readonly operationId: string;\n  readonly summary: string;\n}\n\nexport const operations = ${JSON.stringify(operations, null, 2)} as const;\n`;
  writeFileSync(path.resolve(generatedDir, "operations.ts"), `${fileContent}`);
}

function writeReleaseFile(metadata: ReleaseMetadata, generatedDir: string): void {
  const fileContent = `/* Auto-generated from OpenAPI */\nexport const releaseMetadata = ${JSON.stringify(metadata, null, 2)} as const;\nexport type ReleaseMetadata = typeof releaseMetadata;\n`;
  writeFileSync(path.resolve(generatedDir, "release.ts"), fileContent);
}

function formatChangelogEntry(metadata: ReleaseMetadata): string {
  const today = new Date().toISOString().split("T")[0];
  return [
    `## Schema ${metadata.schemaVersion} — ${today}`,
    `- Schema: ${metadata.schemaPath} (sha256: ${metadata.schemaHash})`,
    `- Solar Fire dataset fingerprint: ${metadata.solarFireDigest}`,
    `- Swiss Ephemeris dataset fingerprint: ${metadata.swissEphemerisDigest}`,
    "",
  ].join("\n");
}

function updateChangelog(metadata: ReleaseMetadata): void {
  const changelogPath = path.resolve(projectRoot, "CHANGELOG.md");
  const existing = existsSync(changelogPath)
    ? readFileSync(changelogPath, "utf8")
    : "# @astroengine/sdk changelog\n\n";

  if (!existing.includes(metadata.schemaHash)) {
    const entry = formatChangelogEntry(metadata);
    let nextValue = existing.endsWith("\n") ? existing : `${existing}\n`;
    if (!nextValue.endsWith(`\n\n`)) {
      nextValue = `${nextValue}\n`;
    }
    writeFileSync(changelogPath, `${nextValue}${entry}`);
  }
}

export function generateFromSchema(schemaPath = defaultSchemaPath): ReleaseMetadata {
  const input = JSON.parse(readFileSync(schemaPath, "utf8"));
  const raw = JSON.stringify(input);
  const schemaHash = sha256(raw);

  const operations: OperationDescriptor[] = Object.entries(input.paths ?? {}).flatMap(
    ([pathKey, methods]) =>
      Object.entries(methods as Record<string, any>).map(([method, spec]) => ({
        method: method.toUpperCase(),
        path: pathKey,
        operationId: spec.operationId ?? `${method}_${pathKey}`.replace(/[^a-zA-Z0-9]/g, "_"),
        summary: spec.summary ?? spec.description ?? "",
      })),
  );

  const metadata: ReleaseMetadata = {
    schemaPath: path.relative(repoRoot, schemaPath),
    schemaVersion: input.info?.version ?? "0.0.0",
    schemaHash,
    solarFireDigest: digestFile("datasets/solarfire/README.md"),
    swissEphemerisDigest: digestFile("datasets/swisseph_stub/README.md"),
  };

  const generatedDir = ensureGeneratedDir();
  writeOperationsFile(operations, generatedDir);
  writeReleaseFile(metadata, generatedDir);
  updateChangelog(metadata);

  return metadata;
}

if (import.meta.url === `file://${__filename}`) {
  const schemaPath = parseArgs(process.argv.slice(2));
  const metadata = generateFromSchema(schemaPath);
  // eslint-disable-next-line no-console
  console.log(
    `Generated ${metadata.schemaVersion} from ${metadata.schemaPath} (sha256: ${metadata.schemaHash})`,
  );
}
