import { ArchitectureVisualizationPanel } from "../components/ArchitectureVisualizationPanel";
import { RequirementInput } from "../components/RequirementInput";
import { RequirementSummaryPanel } from "../components/RequirementSummaryPanel";
import { useScaleCraft } from "../hooks/useScaleCraft";

interface HomePageProps {
  requirementText: string;
  onRequirementTextChange: (value: string) => void;
}

export function HomePage({ requirementText, onRequirementTextChange }: HomePageProps) {
  const {
    activeStepLabel,
    architecture,
    error,
    isLoading,
    parseResult,
    pipelineStatus,
    runAnalysis,
    stepErrors,
  } = useScaleCraft();

  return (
    <main className="page-shell">
      <RequirementInput
        value={requirementText}
        isLoading={isLoading}
        statusMessage={activeStepLabel}
        onChange={onRequirementTextChange}
        onSubmit={() => runAnalysis(requirementText)}
      />

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="dashboard-grid">
        <RequirementSummaryPanel
          parseResult={parseResult}
          isLoading={pipelineStatus.parse === "loading"}
          error={stepErrors.parse}
        />

        <ArchitectureVisualizationPanel
          architecture={architecture}
          isLoading={pipelineStatus.architecture === "loading"}
          error={stepErrors.architecture}
        />
      </div>
    </main>
  );
}
