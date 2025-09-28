"use client";

import { useEditorStore } from "../../state/editorStore";

export const LintPanel = () => {
  const lintIssues = useEditorStore((state) => state.lintIssues);
  if (lintIssues.length === 0) {
    return (
      <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
        No lint findings. Ready for preview.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {lintIssues.map((issue, index) => (
        <div key={`${issue.ruleId}-${index}`} className="rounded-md border border-yellow-500/40 bg-yellow-500/10 p-3">
          <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">{issue.message}</p>
          <p className="text-xs text-muted-foreground">Rule: {issue.ruleId}</p>
        </div>
      ))}
    </div>
  );
};
