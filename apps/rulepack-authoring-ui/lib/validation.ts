import Ajv2020, { ErrorObject } from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { parseRulepack } from "./parsing";
import schema from "./schema/rulepack.schema.json";
import { ValidationIssue } from "../state/editorStore";

const ajv = new Ajv2020({
  strict: false,
  allErrors: true,
  allowUnionTypes: true
});
addFormats(ajv);
const validator = ajv.compile(schema);

const formatError = (error: ErrorObject): ValidationIssue => {
  const path = error.instancePath || error.schemaPath;
  return {
    message: `${error.message ?? "schema validation error"}`,
    path,
    severity: "error"
  };
};

export const validateRulepack = (content: string) => {
  try {
    const payload = parseRulepack(content);
    const valid = validator(payload);
    if (valid) {
      return { valid: true as const, issues: [] as ValidationIssue[] };
    }
    const issues = (validator.errors ?? []).map(formatError);
    return { valid: false as const, issues };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown parse error";
    const issues: ValidationIssue[] = [
      {
        message,
        severity: "error"
      }
    ];
    return { valid: false as const, issues };
  }
};
