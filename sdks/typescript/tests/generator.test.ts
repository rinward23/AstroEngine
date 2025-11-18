import { describe, expect, it } from "vitest";
import path from "node:path";
import { generateFromSchema } from "../scripts/generate";

describe("generator", () => {
  it("captures schema metadata and dataset fingerprints", () => {
    const schemaPath = path.resolve(__dirname, "../../../openapi/v1.0.json");
    const metadata = generateFromSchema(schemaPath);
    expect(metadata.schemaVersion).toBe("1.0.0");
    expect(metadata.schemaHash).toHaveLength(64);
    expect(metadata.solarFireDigest).toMatch(/^(?:[0-9a-f]{16}|missing:)/);
  });
});
