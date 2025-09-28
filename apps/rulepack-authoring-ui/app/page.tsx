"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import type { editor as MonacoEditor } from "monaco-editor";
import { RulepackEditor } from "../components/editor/RulepackEditor";
import { Topbar } from "../components/Topbar";
import { ValidationPanel } from "../components/panels/ValidationPanel";
import { LintPanel } from "../components/panels/LintPanel";
import { MetaPanel } from "../components/panels/MetaPanel";
import { SnippetPalette } from "../components/SnippetPalette";
import { useEditorStore } from "../state/editorStore";
import { parseRulepack, stringifyRulepack } from "../lib/parsing";

const EditorPage = () => {
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const router = useRouter();
  const { content, mode, setContent, setMode } = useEditorStore((state) => ({
    content: state.content,
    mode: state.mode,
    setContent: state.setContent,
    setMode: state.setMode
  }));

  const handleModeToggle = () => {
    const nextMode = mode === "yaml" ? "json" : "yaml";
    try {
      const parsed = parseRulepack(content);
      const formatted = stringifyRulepack(parsed, nextMode);
      setContent(formatted);
      setMode(nextMode);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to convert between formats.";
      // eslint-disable-next-line no-alert
      alert(message);
    }
  };

  const handleFormat = () => {
    try {
      const parsed = parseRulepack(content);
      const formatted = stringifyRulepack(parsed, mode);
      setContent(formatted);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Format failed.";
      // eslint-disable-next-line no-alert
      alert(message);
    }
  };

  const handlePreview = () => {
    router.push("/preview");
  };

  return (
    <div className="flex h-screen flex-col">
      <Topbar onModeToggle={handleModeToggle} onFormat={handleFormat} onPreview={handlePreview} />
      <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden p-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <div className="flex flex-col gap-4 overflow-hidden">
          <RulepackEditor editorRef={editorRef} />
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto pb-6">
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Validation
            </h2>
            <ValidationPanel />
          </section>
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Lint</h2>
            <LintPanel />
          </section>
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Metadata
            </h2>
            <MetaPanel />
          </section>
          <section>
            <SnippetPalette />
          </section>
        </div>
      </div>
    </div>
  );
};

export default EditorPage;
