"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "../../components/ui/Button";
import { DiffView } from "../../components/DiffView";
import { listRulepacks, getRulepack } from "../../lib/api";
import { useEditorStore } from "../../state/editorStore";
import { parseRulepack, stringifyRulepack } from "../../lib/parsing";
import type { RulepackMetadata } from "../../state/editorStore";

interface RulepackVersion extends RulepackMetadata {
  content?: unknown;
}

const VersionsPage = () => {
  const router = useRouter();
  const [rulepacks, setRulepacks] = useState<RulepackVersion[]>([]);
  const [selected, setSelected] = useState<RulepackVersion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { content, setContent, setMode } = useEditorStore((state) => ({
    content: state.content,
    setContent: state.setContent,
    setMode: state.setMode
  }));

  useEffect(() => {
    setLoading(true);
    listRulepacks()
      .then((items) => setRulepacks(items))
      .catch((listError) => {
        const message = listError instanceof Error ? listError.message : "Unable to list rulepacks.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSelect = async (item: RulepackMetadata) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getRulepack(item.id ?? "");
      const entry: RulepackVersion = { ...item, content: payload };
      setSelected(entry);
    } catch (selectError) {
      const message = selectError instanceof Error ? selectError.message : "Failed to fetch version.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadIntoEditor = () => {
    if (!selected?.content) {
      return;
    }
    const formatted = stringifyRulepack(selected.content, "yaml");
    const header = `# Imported from version ${selected.version ?? "?"}${selected.updatedAt ? ` (${selected.updatedAt})` : ""}`;
    setContent(`${header}\n${formatted}`);
    setMode("yaml");
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between border-b bg-card px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">Rulepack Versions</h1>
          <p className="text-sm text-muted-foreground">Compare your local draft to saved versions from the API.</p>
        </div>
        <Button variant="outline" onClick={() => router.back()}>
          Back
        </Button>
      </div>
      <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden p-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-3 overflow-y-auto">
          <div className="rounded-md border p-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Saved versions</h2>
            {loading ? <p className="text-sm text-muted-foreground">Loading…</p> : null}
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <ul className="mt-3 space-y-2">
              {rulepacks.map((item) => (
                <li key={`${item.id}-${item.version}`}>
                  <button
                    type="button"
                    onClick={() => handleSelect(item)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-left text-sm hover:bg-muted"
                  >
                    <span className="block font-medium">{item.title ?? item.id}</span>
                    <span className="block text-xs text-muted-foreground">
                      v{item.version ?? "?"} · {item.updatedAt ? new Date(item.updatedAt).toLocaleString() : "unknown"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>
        <main className="flex flex-col gap-4 overflow-y-auto">
          {selected ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Diff vs Draft</h2>
                  <p className="text-xs text-muted-foreground">
                    Comparing current editor content with version {selected.version ?? "?"} ({selected.id}).
                  </p>
                </div>
                <Button variant="secondary" onClick={handleLoadIntoEditor}>
                  Load into editor
                </Button>
              </div>
              <DiffView left={selected.content} right={parseRulepack(content)} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Select a saved version to view the diff.</p>
          )}
        </main>
      </div>
    </div>
  );
};

export default VersionsPage;
