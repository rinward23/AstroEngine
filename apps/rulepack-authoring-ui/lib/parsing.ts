import YAML from "yaml";

export interface ParsedRulepack {
  [key: string]: unknown;
}

export const parseRulepack = (raw: string) => {
  const trimmed = raw.trim();
  if (!trimmed) {
    return {};
  }
  try {
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      return JSON.parse(trimmed) as ParsedRulepack;
    }
    return YAML.parse(trimmed) as ParsedRulepack;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown parse error";
    throw new Error(`Unable to parse rulepack content: ${message}`);
  }
};

export const stringifyRulepack = (data: unknown, mode: "json" | "yaml" = "yaml") => {
  if (mode === "json") {
    return JSON.stringify(data, null, 2);
  }
  return YAML.stringify(data, { indent: 2 });
};
