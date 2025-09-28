import { LintIssue } from "../state/editorStore";
import { parseRulepack } from "./parsing";

const KNOWN_BODIES = new Set([
  "Sun",
  "Moon",
  "Mercury",
  "Venus",
  "Earth",
  "Mars",
  "Jupiter",
  "Saturn",
  "Uranus",
  "Neptune",
  "Pluto",
  "Ascendant",
  "Midheaven",
  "Descendant",
  "IC"
]);

const KNOWN_TAGS = new Set([
  "major",
  "minor",
  "binding",
  "growth",
  "challenge",
  "compatibility"
]);

const KNOWN_ASPECTS = new Set([0, 30, 45, 60, 72, 90, 120, 135, 150, 180]);

interface RuleKey {
  scope?: string;
  bodies?: string[];
  aspect?: number | string;
}

const normalizeBodies = (bodies?: unknown) => {
  if (!Array.isArray(bodies)) {
    return [] as string[];
  }
  return bodies.map((body) => String(body)).sort();
};

const normalizeAspect = (aspect?: unknown) => {
  if (typeof aspect === "number" || typeof aspect === "string") {
    return aspect;
  }
  return undefined;
};

const keyForRule = (key: RuleKey) => {
  const bodies = key.bodies?.join("|") ?? "";
  return `${key.scope ?? ""}::${bodies}::${key.aspect ?? ""}`;
};

export const lintRulepack = (content: string) => {
  const issues: LintIssue[] = [];
  let parsed: any;
  try {
    parsed = parseRulepack(content);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to parse rulepack";
    issues.push({
      message,
      severity: "error",
      ruleId: "global"
    });
    return issues;
  }

  const rules: any[] = Array.isArray(parsed?.rules) ? parsed.rules : [];
  if (rules.length === 0) {
    issues.push({
      message: "Rulepack does not contain any rules.",
      severity: "warning",
      ruleId: "global"
    });
  }

  const seenIds = new Map<string, number>();
  const seenKeys = new Map<string, { ruleId: string; then: unknown }>();

  for (const rule of rules) {
    const ruleId = String(rule?.id ?? "(missing)");
    if (!rule?.id) {
      issues.push({
        message: "Rule is missing an id.",
        severity: "error",
        ruleId
      });
    }

    const occurrences = seenIds.get(ruleId) ?? 0;
    if (occurrences > 0) {
      issues.push({
        message: `Duplicate rule id '${ruleId}' detected.`,
        severity: "error",
        ruleId
      });
    }
    seenIds.set(ruleId, occurrences + 1);

    const bodies = normalizeBodies(rule?.if?.bodies ?? rule?.if?.bodiesA);
    for (const body of bodies) {
      if (!KNOWN_BODIES.has(body)) {
        issues.push({
          message: `Unknown body '${body}' referenced.`,
          severity: "warning",
          ruleId
        });
      }
    }

    if (Array.isArray(rule?.then?.tags)) {
      for (const tag of rule.then.tags) {
        if (typeof tag === "string" && !KNOWN_TAGS.has(tag)) {
          issues.push({
            message: `Tag '${tag}' is not part of the project catalogue.`,
            severity: "warning",
            ruleId
          });
        }
      }
    }

    const aspect = normalizeAspect(rule?.if?.aspect);
    if (typeof aspect === "number" && !KNOWN_ASPECTS.has(aspect)) {
      issues.push({
        message: `Aspect '${aspect}'° is not recognised.`,
        severity: "warning",
        ruleId
      });
    }

    const severity = typeof rule?.then?.severity === "number" ? rule.then.severity : undefined;
    const minSeverity = typeof rule?.min_severity === "number" ? rule.min_severity : undefined;
    if (typeof minSeverity === "number" && (minSeverity < 0 || minSeverity > 1)) {
      issues.push({
        message: "min_severity must be within [0, 1].",
        severity: "error",
        ruleId
      });
    } else if (
      typeof minSeverity === "number" &&
      typeof severity === "number" &&
      minSeverity > severity
    ) {
      issues.push({
        message: `min_severity (${minSeverity}) is higher than rule severity (${severity}).`,
        severity: "warning",
        ruleId
      });
    }

    const key = keyForRule({
      scope: typeof rule?.scope === "string" ? rule.scope : undefined,
      bodies,
      aspect
    });
    if (seenKeys.has(key)) {
      const prior = seenKeys.get(key)!;
      if (JSON.stringify(prior.then) !== JSON.stringify(rule?.then)) {
        issues.push({
          message: `Rule conflicts with '${prior.ruleId}' for identical trigger.`,
          severity: "warning",
          ruleId
        });
      }
    } else {
      seenKeys.set(key, { ruleId, then: rule?.then });
    }
  }

  const tagUsage = new Map<string, number>();
  for (const rule of rules) {
    if (Array.isArray(rule?.then?.tags)) {
      for (const tag of rule.then.tags) {
        if (typeof tag === "string") {
          tagUsage.set(tag, (tagUsage.get(tag) ?? 0) + 1);
        }
      }
    }
  }
  for (const tag of KNOWN_TAGS) {
    if (!tagUsage.has(tag)) {
      issues.push({
        message: `Tag '${tag}' is defined in catalogue but unused.`,
        severity: "warning",
        ruleId: "global"
      });
    }
  }

  return issues;
};
