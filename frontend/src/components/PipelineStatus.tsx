import type { PipelineStatus as PipelineStatusModel, PipelineStepState } from "../hooks/useScaleCraft";

interface PipelineStatusProps {
  status: PipelineStatusModel;
}

const stepLabels: Array<{ key: keyof PipelineStatusModel; label: string }> = [
  { key: "parse", label: "Parse" },
  { key: "architecture", label: "Architecture" },
  { key: "loadProfile", label: "Load" },
  { key: "scripts", label: "Scripts" },
  { key: "risks", label: "Risks" },
];

function statusLabel(state: PipelineStepState): string {
  if (state === "loading") {
    return "Running";
  }
  if (state === "success") {
    return "Done";
  }
  if (state === "error") {
    return "Error";
  }
  return "Waiting";
}

export function PipelineStatus({ status }: PipelineStatusProps) {
  return (
    <section className="pipeline-strip">
      {stepLabels.map((step) => (
        <div key={step.key} className={`pipeline-pill pipeline-${status[step.key]}`}>
          <span>{step.label}</span>
          <strong>{statusLabel(status[step.key])}</strong>
        </div>
      ))}
    </section>
  );
}
