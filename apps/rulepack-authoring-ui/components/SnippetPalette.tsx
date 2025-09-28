"use client";

import { useState } from "react";
import { RULE_SNIPPETS } from "../lib/snippets";
import { Button } from "./ui/Button";
import { useEditorStore } from "../state/editorStore";

export const SnippetPalette = () => {
  const [active, setActive] = useState<string | null>(null);
  const { content, setContent } = useEditorStore((state) => ({
    content: state.content,
    setContent: state.setContent
  }));

  const handleInsert = (snippet: string) => {
    const next = content.endsWith("\n") ? content + snippet : `${content}\n${snippet}`;
    setContent(next);
  };

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold">Rule snippets</h3>
        <p className="text-xs text-muted-foreground">
          Insert frequently used structures without leaving the editor.
        </p>
      </div>
      <div className="space-y-2">
        {RULE_SNIPPETS.map((snippet) => (
          <div key={snippet.id} className="rounded-md border p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{snippet.label}</p>
                <p className="text-xs text-muted-foreground">{snippet.description}</p>
              </div>
              <Button variant="outline" onClick={() => handleInsert(snippet.content)}>
                Insert
              </Button>
            </div>
            <Button
              variant="ghost"
              className="mt-2 h-auto w-full justify-start text-xs"
              onClick={() => setActive((current) => (current === snippet.id ? null : snippet.id))}
            >
              {active === snippet.id ? "Hide" : "Preview"} example
            </Button>
            {active === snippet.id ? (
              <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-xs text-muted-foreground">
                {snippet.content}
              </pre>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
};
