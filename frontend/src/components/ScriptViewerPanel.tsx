import { useState } from "react";

import type { GeneratedScript, ScriptTarget } from "../api/types";
import { titleCase } from "../utils/formatters";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface ScriptViewerPanelProps {
  scripts: GeneratedScript[];
  isLoading: boolean;
  error?: string | null;
}

function downloadScript(script: GeneratedScript): void {
  const blob = new Blob([script.content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = script.file_name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ScriptViewerPanel({ scripts, isLoading, error }: ScriptViewerPanelProps) {
  const [activeTarget, setActiveTarget] = useState<ScriptTarget>("k6");
  const script = scripts.find((item) => item.target === activeTarget) ?? scripts[0] ?? null;

  async function copyCommand(): Promise<void> {
    if (!script) {
      return;
    }
    await navigator.clipboard.writeText(script.entrypoint_command);
  }

  return (
      <SectionCard title="Generated Scripts" subtitle="Visual runner cards with download-only output">
      {scripts.length === 0 && isLoading ? (
        <StateNotice title="Exporting scripts" message="Generating runnable k6 and Locust files from the current architecture and load profile." tone="loading" />
      ) : null}
      {error ? <StateNotice title="Script export error" message={error} tone="error" /> : null}
      {scripts.length === 0 && !isLoading ? (
        <StateNotice title="No scripts yet" message="Run the workflow to generate executable scripts." />
      ) : null}
      {script ? (
        <div className="stack-md">
          <div className="script-selector-grid">
            {scripts.map((item) => (
              <button
                key={item.target}
                className={`script-tile ${item.target === script.target ? "script-tile-active" : ""}`}
                type="button"
                onClick={() => setActiveTarget(item.target)}
              >
                <span>{titleCase(item.target)}</span>
                <strong>{item.file_name}</strong>
              </button>
            ))}
          </div>

          <div className="visual-script-card">
            <div className="metric-grid metric-grid-compact">
              <div className="visual-metric-card">
                <span>Runner</span>
                <strong>{titleCase(script.target)}</strong>
              </div>
              <div className="visual-metric-card">
                <span>Language</span>
                <strong>{titleCase(script.language)}</strong>
              </div>
              <div className="visual-metric-card metric-card-wide">
                <span>Run</span>
                <strong className="mono-inline">{script.entrypoint_command}</strong>
              </div>
            </div>

            <div className="tab-row compact-actions-row">
              <button className="ghost-button" type="button" onClick={copyCommand}>
                Copy Command
              </button>
              <button className="ghost-button" type="button" onClick={() => downloadScript(script)}>
                Download
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
