import { readFile } from "node:fs/promises";
import { join } from "node:path";

const summaryPath = join(process.cwd(), "coverage", "coverage-summary.json");

async function main() {
  let raw;
  try {
    raw = await readFile(summaryPath, "utf8");
  } catch (error) {
    console.error(`Unable to read coverage summary at ${summaryPath}`);
    throw error;
  }

  const summary = JSON.parse(raw);
  const totals = summary.total ?? {};
  const failures = Object.entries(totals).filter(([, stats]) => {
    const pct = Number(stats?.pct ?? 0);
    return Number.isFinite(pct) && pct < 100;
  });

  if (failures.length > 0) {
    console.error("Vitest coverage must be 100% for all metrics. Below-threshold metrics:");
    for (const [metric, stats] of failures) {
      console.error(
        `  ${metric}: ${Number(stats?.pct ?? 0).toFixed(2)}% (covered ${stats?.covered ?? 0}/${stats?.total ?? 0})`
      );
    }
    process.exit(1);
  }

  console.log("Vitest coverage is at 100% across all metrics.");
}

await main();
