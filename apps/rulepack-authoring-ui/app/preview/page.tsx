"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { JsonView, darkStyles } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import { Button } from "../../components/ui/Button";
import { useEditorStore } from "../../state/editorStore";
import { previewRelationship, computeSynastry } from "../../lib/api";
import sampleHits from "../../lib/examples/hits.json";
import samplePositionsA from "../../lib/examples/positionsA.json";
import samplePositionsB from "../../lib/examples/positionsB.json";

const PreviewPage = () => {
  const router = useRouter();
  const content = useEditorStore((state) => state.content);
  const [source, setSource] = useState<"hits" | "positions">("hits");
  const [hitsInput, setHitsInput] = useState(JSON.stringify(sampleHits, null, 2));
  const [positionsA, setPositionsA] = useState(JSON.stringify(samplePositionsA, null, 2));
  const [positionsB, setPositionsB] = useState(JSON.stringify(samplePositionsB, null, 2));
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    try {
      if (source === "hits") {
        const parsedHits = JSON.parse(hitsInput);
        const response = await previewRelationship(content, {
          scope: parsedHits.scope ?? "synastry",
          hits: parsedHits
        });
        setResult(response);
      } else {
        const a = JSON.parse(positionsA);
        const b = JSON.parse(positionsB);
        const response = await previewRelationship(content, {
          scope: "synastry",
          positions: {
            a,
            b
          }
        });
        setResult(response);
      }
    } catch (previewError) {
      const message = previewError instanceof Error ? previewError.message : "Preview failed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleComputeHits = async () => {
    setLoading(true);
    setError(null);
    try {
      const a = JSON.parse(positionsA);
      const b = JSON.parse(positionsB);
      const response = await computeSynastry({ positions: { a, b } });
      setHitsInput(JSON.stringify(response, null, 2));
      setSource("hits");
    } catch (computeError) {
      const message = computeError instanceof Error ? computeError.message : "Unable to compute hits.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between border-b bg-card px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">Live preview</h1>
          <p className="text-sm text-muted-foreground">Evaluate your unsaved draft against sample data.</p>
        </div>
        <Button variant="outline" onClick={() => router.push("/")}>
          Back to editor
        </Button>
      </div>
      <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden p-6 lg:grid-cols-2">
        <div className="flex flex-col gap-4 overflow-y-auto">
          <div className="rounded-md border p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Input</h2>
              <div className="flex items-center gap-2 text-sm">
                <Button
                  variant={source === "hits" ? "default" : "outline"}
                  onClick={() => setSource("hits")}
                >
                  Hits JSON
                </Button>
                <Button
                  variant={source === "positions" ? "default" : "outline"}
                  onClick={() => setSource("positions")}
                >
                  Positions A/B
                </Button>
              </div>
            </div>
            {source === "hits" ? (
              <textarea
                className="mt-3 h-72 w-full rounded-md border border-input bg-background p-3 font-mono text-xs"
                value={hitsInput}
                onChange={(event) => setHitsInput(event.target.value)}
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <textarea
                  className="mt-3 h-72 w-full rounded-md border border-input bg-background p-3 font-mono text-xs"
                  value={positionsA}
                  onChange={(event) => setPositionsA(event.target.value)}
                />
                <textarea
                  className="mt-3 h-72 w-full rounded-md border border-input bg-background p-3 font-mono text-xs"
                  value={positionsB}
                  onChange={(event) => setPositionsB(event.target.value)}
                />
              </div>
            )}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Button onClick={handlePreview} disabled={loading}>
                {loading ? "Running..." : "Preview"}
              </Button>
              <Button variant="outline" onClick={handleComputeHits} disabled={loading}>
                Compute hits from positions
              </Button>
            </div>
            {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
          </div>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto">
          <div className="rounded-md border p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Findings</h2>
            {result ? (
              <div className="mt-4 rounded-md border bg-muted/40 p-3">
                <JsonView
                  data={result as Record<string, unknown>}
                  style={darkStyles}
                  shouldExpandNode={(_keyPath, _data, level) =>
                    typeof level === "number" ? level < 2 : false}
                />
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">
                Run a preview to view findings. The server response appears here with the exact data returned.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PreviewPage;
