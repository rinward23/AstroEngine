import { RulepackMetadata } from "../state/editorStore";
import { parseRulepack } from "./parsing";

const INT_API = process.env.NEXT_PUBLIC_INT_API;
const REL_API = process.env.NEXT_PUBLIC_REL_API;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

const defaultHeaders = () => {
  const headers: HeadersInit = {
    "Content-Type": "application/json"
  };
  if (API_KEY) {
    headers["Authorization"] = `Bearer ${API_KEY}`;
  }
  return headers;
};

export interface RulepackListResponse {
  items: RulepackMetadata[];
}

export const listRulepacks = async () => {
  if (!INT_API) {
    throw new Error("Interpretation API base URL is not configured.");
  }
  const response = await fetch(`${INT_API}/v1/interpret/rulepacks`, {
    headers: defaultHeaders(),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Failed to list rulepacks: ${response.statusText}`);
  }
  const payload = (await response.json()) as RulepackListResponse;
  return payload.items.map((item) => ({
    ...item,
    updatedAt: (item as any).updated_at ?? item.updatedAt
  }));
};

export const getRulepack = async (id: string) => {
  if (!INT_API) {
    throw new Error("Interpretation API base URL is not configured.");
  }
  const response = await fetch(`${INT_API}/v1/interpret/rulepacks/${id}`, {
    headers: defaultHeaders(),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch rulepack ${id}: ${response.statusText}`);
  }
  return response.json();
};

export const saveRulepack = async (content: string) => {
  if (!INT_API) {
    throw new Error("Interpretation API base URL is not configured.");
  }
  const parsed = parseRulepack(content);
  const response = await fetch(`${INT_API}/v1/interpret/rulepacks`, {
    method: "POST",
    headers: defaultHeaders(),
    body: JSON.stringify(parsed)
  });
  if (!response.ok) {
    throw new Error(`Failed to save rulepack: ${response.statusText}`);
  }
  return (await response.json()) as RulepackMetadata;
};

export interface RelationshipPreviewRequest {
  scope?: string;
  hits?: unknown;
  positions?: {
    a: unknown;
    b: unknown;
  };
}

export const previewRelationship = async (content: string, payload: RelationshipPreviewRequest) => {
  if (!INT_API) {
    throw new Error("Interpretation API base URL is not configured.");
  }
  const parsed = parseRulepack(content);
  const response = await fetch(`${INT_API}/v1/interpret/relationship`, {
    method: "POST",
    headers: defaultHeaders(),
    body: JSON.stringify({ ...payload, rulepack: parsed })
  });
  if (!response.ok) {
    throw new Error(`Failed to preview relationship: ${response.statusText}`);
  }
  return response.json();
};

export const computeSynastry = async (payload: unknown) => {
  if (!REL_API) {
    throw new Error("Relationship API base URL is not configured.");
  }
  const response = await fetch(`${REL_API}/v1/relationship/synastry`, {
    method: "POST",
    headers: defaultHeaders(),
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Failed to compute synastry hits: ${response.statusText}`);
  }
  return response.json();
};
