import { describe, expect, it } from "vitest";
import { lintRulepack } from "../lint";
import { parseRulepack, stringifyRulepack } from "../parsing";

const SAMPLE_CONTENT = `version: 1\nrules:\n  - id: sample.rule\n    scope: synastry\n    if:\n      bodies: [Sun, Moon]\n      aspect: 120\n    then:\n      summary: Sample\n`;

describe("lintRulepack", () => {
  it("flags duplicate rule ids", () => {
    const parsed = parseRulepack(SAMPLE_CONTENT);
    if (!Array.isArray(parsed.rules)) {
      throw new Error("Sample does not include rules array");
    }
    const duplicate = {
      ...parsed,
      rules: [...parsed.rules, parsed.rules[0]]
    };
    const issues = lintRulepack(stringifyRulepack(duplicate, "json"));
    expect(issues.some((issue) => issue.message.includes("Duplicate rule id"))).toBe(true);
  });

  it("warns when no rules are present", () => {
    const issues = lintRulepack("version: 1\nrules: []\n");
    expect(issues.some((issue) => issue.message.includes("does not contain any rules"))).toBe(true);
  });
});
