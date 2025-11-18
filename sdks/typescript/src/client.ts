import { ApiError, InvalidBodyError, RateLimitedError } from "./errors";
import { withRetry, RetryConfig } from "./middleware/retry";
import { ClientOptions, RequestOptions } from "./types";
import { operations } from "./generated/operations";
import { releaseMetadata } from "./generated/release";
import pkg from "../package.json" assert { type: "json" };

const DEFAULT_BASE_URL = "https://api.astroengine.local";
const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly retryConfig: RetryConfig;
  private readonly transport: typeof fetch;
  private readonly defaultHeaders: HeadersInit;
  private currentIdempotencyKey?: string;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.transport = options.transport ?? globalThis.fetch.bind(globalThis);
    this.retryConfig = {
      maxAttempts: 5,
      baseDelayMs: 200,
      maxDelayMs: 5000,
    };

    const baseUserAgent = `AstroEngineTS/${pkg.version}`;
    const datasetSuffix = `(+solarfire-hash:${releaseMetadata.solarFireDigest};swiss:${releaseMetadata.swissEphemerisDigest};schema:${releaseMetadata.schemaVersion})`;
    const userAgent = [baseUserAgent, datasetSuffix, options.userAgentSuffix].filter(Boolean).join(" ");

    const headers: Record<string, string> = {
      "User-Agent": userAgent,
      "Content-Type": "application/json",
      "AstroEngine-Schema": `${releaseMetadata.schemaVersion}`,
    };
    if (options.token) {
      headers.Authorization = `Bearer ${options.token}`;
    }
    this.defaultHeaders = headers;
  }

  get supportedOperations() {
    return operations;
  }

  withIdempotency<T>(key: string, fn: () => Promise<T>): Promise<T> {
    this.currentIdempotencyKey = key;
    return fn().finally(() => {
      this.currentIdempotencyKey = undefined;
    });
  }

  async request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
    const url = new URL(path, this.baseUrl);
    if (options.searchParams) {
      for (const [key, value] of Object.entries(options.searchParams)) {
        if (value === undefined) continue;
        url.searchParams.set(key, String(value));
      }
    }

    const headers = new Headers(this.defaultHeaders);
    if (options.idempotencyKey ?? this.currentIdempotencyKey) {
      headers.set("Idempotency-Key", options.idempotencyKey ?? this.currentIdempotencyKey ?? "");
    }

    const body = options.body ? JSON.stringify(options.body) : undefined;

    return withRetry(async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
      try {
        const response = await this.transport(url, {
          method,
          headers,
          body,
          signal: controller.signal,
        });

        if (response.status >= 200 && response.status < 300) {
          if (response.status === 204) {
            return undefined as T;
          }
          return (await response.json()) as T;
        }

        return Promise.reject(this.toError(response));
      } finally {
        clearTimeout(timeout);
      }
    }, this.retryConfig);
  }

  async *paginate<T>(path: string, options: RequestOptions = {}): AsyncGenerator<T[], void, unknown> {
    let nextPath: string | null = path;
    let searchParams = { ...(options.searchParams ?? {}) };
    while (nextPath) {
      const result = (await this.request<{ data: T[]; next?: string | null }>(
        "GET",
        nextPath,
        { ...options, searchParams },
      ));
      yield result.data;
      nextPath = result.next ?? null;
      searchParams = {};
    }
  }

  async *stream<T>(path: string, options: RequestOptions = {}): AsyncGenerator<T, void, unknown> {
    const url = new URL(path, this.baseUrl);
    const headers = new Headers(this.defaultHeaders);
    const response = await this.transport(url, {
      method: "GET",
      headers,
    });

    if (!response.body) {
      throw new Error("Streaming requires a readable body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex: number;
      while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
        const chunk = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (chunk) {
          yield JSON.parse(chunk) as T;
        }
      }
    }

    if (buffer.trim()) {
      yield JSON.parse(buffer.trim()) as T;
    }
  }

  private async toError(response: Response): Promise<ApiError> {
    const payload = await response.text();
    let parsed: any = {};
    try {
      parsed = payload ? JSON.parse(payload) : {};
    } catch (error) {
      // no-op
    }

    const code = parsed.code ?? `HTTP_${response.status}`;
    const message = parsed.message ?? response.statusText;

    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfterMs = retryAfterHeader ? Number(retryAfterHeader) * 1000 : undefined;

    if (response.status === 429) {
      const error = new RateLimitedError({ code, httpStatus: response.status, message, details: parsed });
      (error as RateLimitedError & { retryAfterMs?: number }).retryAfterMs = retryAfterMs;
      return error;
    }

    if (response.status === 400) {
      return new InvalidBodyError({ code, httpStatus: response.status, message, details: parsed });
    }

    return new ApiError({ code, httpStatus: response.status, message, details: parsed });
  }
}
