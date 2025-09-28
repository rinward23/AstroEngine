"use client";

import { useEditorStore } from "../../state/editorStore";

export const ValidationPanel = () => {
  const issues = useEditorStore((state) => state.validationIssues);
  if (issues.length === 0) {
    return (
      <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
        Schema validation clean.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {issues.map((issue, index) => (
        <div key={`${issue.message}-${index}`} className="rounded-md border border-destructive/40 bg-destructive/10 p-3">
          <p className="text-sm font-medium text-destructive-foreground">{issue.message}</p>
          {issue.path ? <p className="text-xs text-muted-foreground">{issue.path}</p> : null}
        </div>
      ))}
    </div>
  );
};
