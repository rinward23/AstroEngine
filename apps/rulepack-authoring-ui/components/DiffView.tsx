"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { stringifyRulepack } from "../lib/parsing";

const DiffViewer = dynamic(() => import("react-diff-viewer-continued"), { ssr: false });

export interface DiffViewProps {
  left: unknown;
  right: unknown;
  mode?: "yaml" | "json";
}

export const DiffView = ({ left, right, mode = "yaml" }: DiffViewProps) => {
  const [leftText, setLeftText] = useState("");
  const [rightText, setRightText] = useState("");

  useEffect(() => {
    setLeftText(stringifyRulepack(left, mode));
  }, [left, mode]);

  useEffect(() => {
    setRightText(stringifyRulepack(right, mode));
  }, [right, mode]);

  return (
    <div className="overflow-hidden rounded-md border">
      <DiffViewer
        oldValue={leftText}
        newValue={rightText}
        splitView
        disableWordDiff
        useDarkTheme
      />
    </div>
  );
};
