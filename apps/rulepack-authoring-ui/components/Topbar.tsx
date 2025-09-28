"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import type { Route } from "next";
import { Button } from "./ui/Button";
import { Save, FileDown, FileUp, Play, Menu } from "lucide-react";
import { useEditorStore } from "../state/editorStore";
import { useMemo } from "react";
import { validateRulepack } from "../lib/validation";
import { lintRulepack } from "../lib/lint";
import { saveRulepack } from "../lib/api";
import { computeContentHash } from "../state/editorStore";
import { downloadContent, uploadFile } from "../lib/files";

interface TopbarProps {
  onModeToggle: () => void;
  onFormat: () => void;
  onPreview: () => void;
}

const NAVIGATION: { href: Route; label: string }[] = [
  { href: "/", label: "Editor" },
  { href: "/preview", label: "Preview" },
  { href: "/versions", label: "Versions" }
];

export const Topbar = ({ onModeToggle, onFormat, onPreview }: TopbarProps) => {
  const pathname = usePathname();
  const { content, mode, setValidationIssues, setLintIssues, setLastSavedHash } =
    useEditorStore((state) => ({
      content: state.content,
      mode: state.mode,
      setValidationIssues: state.setValidationIssues,
      setLintIssues: state.setLintIssues,
      setLastSavedHash: state.setLastSavedHash
    }));

  const draftHashPromise = useMemo(() => computeContentHash(content), [content]);

  const handleValidate = () => {
    const validation = validateRulepack(content);
    setValidationIssues(validation.issues);
  };

  const handleLint = () => {
    const issues = lintRulepack(content);
    setLintIssues(issues);
  };

  const handleSave = async () => {
    handleValidate();
    handleLint();
    const response = await saveRulepack(content);
    const hash = await draftHashPromise;
    setLastSavedHash(hash);
    setValidationIssues([]);
    setLintIssues([]);
    if (response) {
      // eslint-disable-next-line no-alert
      alert(`Saved rulepack '${response.title ?? response.id ?? "draft"}'`);
    }
  };

  const handleExport = async () => {
    await downloadContent(content, `rulepack.${mode}`);
  };

  const handleImport = async () => {
    const imported = await uploadFile();
    if (imported) {
      // eslint-disable-next-line no-alert
      alert("File imported into editor. Draft saved to local storage.");
    }
  };

  return (
    <header className="flex items-center justify-between border-b bg-card px-4 py-2">
      <nav className="flex items-center gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide">
          <Menu className="h-4 w-4" /> Rulepack Studio
        </span>
        {NAVIGATION.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname === item.href
                ? "bg-primary text-primary-foreground shadow"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-2">
        <Button variant="ghost" onClick={onModeToggle}>
          {mode === "yaml" ? "YAML" : "JSON"}
        </Button>
        <Button variant="ghost" onClick={onFormat}>
          Format
        </Button>
        <Button variant="ghost" onClick={handleValidate}>
          Validate
        </Button>
        <Button variant="ghost" onClick={handleLint}>
          Lint
        </Button>
        <Button variant="outline" onClick={onPreview}>
          <Play className="mr-2 h-4 w-4" /> Preview
        </Button>
        <Button variant="outline" onClick={handleExport}>
          <FileDown className="mr-2 h-4 w-4" /> Export
        </Button>
        <Button variant="outline" onClick={handleImport}>
          <FileUp className="mr-2 h-4 w-4" /> Import
        </Button>
        <Button variant="default" onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" /> Save
        </Button>
      </div>
    </header>
  );
};
