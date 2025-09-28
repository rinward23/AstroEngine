import localforage from "localforage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type EditorMode = "yaml" | "json";

export interface ValidationIssue {
  message: string;
  path?: string;
  severity?: "error" | "warning";
}

export interface LintIssue extends ValidationIssue {
  ruleId: string;
}

export interface RulepackMetadata {
  id?: string;
  title?: string;
  description?: string;
  version?: number;
  tags?: string[];
  updatedAt?: string;
}

interface EditorState {
  mode: EditorMode;
  content: string;
  metadata: RulepackMetadata;
  validationIssues: ValidationIssue[];
  lintIssues: LintIssue[];
  lastSavedHash?: string;
  setMode: (mode: EditorMode) => void;
  setContent: (content: string) => void;
  setMetadata: (metadata: Partial<RulepackMetadata>) => void;
  setValidationIssues: (issues: ValidationIssue[]) => void;
  setLintIssues: (issues: LintIssue[]) => void;
  setLastSavedHash: (hash?: string) => void;
  reset: () => void;
}

const EMPTY_DRAFT = `version: 1\nmetadata:\n  title: "New Rulepack"\n  description: ""\nrules: []\n`;

localforage.config({
  name: "rulepack-authoring-ui",
  storeName: "drafts"
});

export const useEditorStore = create<EditorState>()(
  persist(
    (set) => ({
      mode: "yaml",
      content: EMPTY_DRAFT,
      metadata: {},
      validationIssues: [],
      lintIssues: [],
      lastSavedHash: undefined,
      setMode: (mode) => set({ mode }),
      setContent: (content) => set({ content }),
      setMetadata: (metadata) =>
        set((state) => ({ metadata: { ...state.metadata, ...metadata } })),
      setValidationIssues: (issues) => set({ validationIssues: issues }),
      setLintIssues: (issues) => set({ lintIssues: issues }),
      setLastSavedHash: (hash) => set({ lastSavedHash: hash }),
      reset: () =>
        set({
          mode: "yaml",
          content: EMPTY_DRAFT,
          metadata: {},
          validationIssues: [],
          lintIssues: [],
          lastSavedHash: undefined
        })
    }),
    {
      name: "rulepack-editor-store",
      storage: createJSONStorage(() => localforage)
    }
  )
);

export const computeContentHash = async (content: string) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(content);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
};
