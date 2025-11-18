import { describe, expect, it } from "vitest";
import { ApiClient } from "../src/client";

function createPaginationFetch() {
  const payloads = [
    { data: [{ id: "1" }], next: "/charts?page=2" },
    { data: [{ id: "2" }], next: null },
  ];
  return (async () => {
    const next = payloads.shift();
    return new Response(JSON.stringify(next), { status: 200 });
  }) as typeof fetch;
}

describe("Workflow helpers", () => {
  it("iterates over paginated endpoints", async () => {
    const client = new ApiClient({ baseUrl: "https://api.local", transport: createPaginationFetch() });
    const collected: Array<Record<string, string>> = [];
    for await (const page of client.paginate<Record<string, string>>("/charts")) {
      collected.push(...page);
    }
    expect(collected.map((item) => item.id)).toEqual(["1", "2"]);
  });

  it("streams NDJSON chunks", async () => {
    const data = "{\"id\":1}\n{\"id\":2}\n";
    const response = new Response(data, { status: 200 });
    const transport: typeof fetch = async () => response;
    const client = new ApiClient({ baseUrl: "https://api.local", transport });

    const results: Array<Record<string, number>> = [];
    for await (const chunk of client.stream<Record<string, number>>("/charts")) {
      results.push(chunk);
    }
    expect(results).toEqual([{ id: 1 }, { id: 2 }]);
  });
});
