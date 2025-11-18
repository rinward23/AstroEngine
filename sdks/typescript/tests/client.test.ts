import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "../src/client";

describe("ApiClient", () => {
  it("attaches idempotency headers via withIdempotency", async () => {
    const calls: Array<Record<string, string>> = [];
    const mockFetch: typeof fetch = vi.fn(async (_input, init) => {
      const headers = new Headers(init?.headers);
      calls.push({
        idempotency: headers.get("Idempotency-Key") ?? "",
        userAgent: headers.get("User-Agent") ?? "",
      });
      return new Response(JSON.stringify({ data: [] }), { status: 200 });
    });

    const client = new ApiClient({ baseUrl: "https://api.local", transport: mockFetch });
    await client.withIdempotency("demo-key", () =>
      client.request("POST", "/charts", { body: { label: "test" } }),
    );

    expect(calls).toHaveLength(1);
    expect(calls[0].idempotency).toBe("demo-key");
    expect(calls[0].userAgent).toContain("AstroEngineTS");
  });

  it("retries on rate limits and respects Retry-After headers", async () => {
    vi.useFakeTimers();
    const responses = [
      new Response(JSON.stringify({ code: "rate_limited" }), {
        status: 429,
        headers: { "Retry-After": "0" },
      }),
      new Response(JSON.stringify({ data: [] }), { status: 200 }),
    ];
    const mockFetch: typeof fetch = vi.fn(async () => {
      return responses.shift()!;
    });

    const client = new ApiClient({ baseUrl: "https://api.local", transport: mockFetch });
    const promise = client.request("GET", "/charts");

    await vi.runAllTimersAsync();
    await expect(promise).resolves.toEqual({ data: [] });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});
