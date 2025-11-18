export interface ClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
  token?: string;
  userAgentSuffix?: string;
  transport?: typeof fetch;
}

export interface RequestOptions {
  searchParams?: Record<string, string | number | boolean | undefined>;
  body?: Record<string, unknown>;
  idempotencyKey?: string;
}
