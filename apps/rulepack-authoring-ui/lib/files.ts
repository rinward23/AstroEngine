import { useEditorStore } from "../state/editorStore";

export const downloadContent = async (content: string, filename: string) => {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

export const uploadFile = async () => {
  return new Promise<boolean>((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".yaml,.yml,.json";
    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement)?.files?.[0];
      if (!file) {
        resolve(false);
        return;
      }
      const content = await file.text();
      useEditorStore.getState().setContent(content);
      resolve(true);
    };
    input.onerror = () => reject(new Error("Unable to read file"));
    input.click();
  });
};
