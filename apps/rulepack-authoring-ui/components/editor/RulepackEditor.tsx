"use client";

import Editor, { OnMount } from "@monaco-editor/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { useEditorStore } from "../../state/editorStore";
import schema from "../../lib/schema/rulepack.schema.json";

const JSON_SCHEMA_URI = "inmemory://model/rulepack.schema.json";

export const RulepackEditor = ({
  editorRef
}: {
  editorRef: React.MutableRefObject<MonacoEditor.IStandaloneCodeEditor | null>;
}) => {
  const { content, setContent, mode } = useEditorStore((state) => ({
    content: state.content,
    setContent: state.setContent,
    mode: state.mode
  }));

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      schemas: [
        {
          uri: JSON_SCHEMA_URI,
          fileMatch: ["*.json", "rulepack.json"],
          schema
        }
      ]
    });

    import("monaco-yaml").then(({ configureMonacoYaml }) => {
      configureMonacoYaml(monaco, {
        enableSchemaRequest: false,
        hover: true,
        completion: true,
        validate: true,
        schemas: [
          {
            uri: JSON_SCHEMA_URI,
            fileMatch: ["*.yaml", "*.yml", "rulepack.yaml"],
            schema
          }
        ]
      });
    });
  };

  return (
    <div className="h-full w-full overflow-hidden rounded-lg border">
      <Editor
        height="100%"
        path={mode === "yaml" ? "rulepack.yaml" : "rulepack.json"}
        defaultLanguage={mode === "yaml" ? "yaml" : "json"}
        language={mode === "yaml" ? "yaml" : "json"}
        theme="vs-dark"
        value={content}
        onMount={handleMount}
        onChange={(value) => setContent(value ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          automaticLayout: true,
          wordWrap: "on"
        }}
      />
    </div>
  );
};
