import { ArchitectureVisualizationPanel } from "../components/ArchitectureVisualizationPanel";
import { LoadProfilePanel } from "../components/LoadProfilePanel";
import { RequirementInput } from "../components/RequirementInput";
import { RequirementSummaryPanel } from "../components/RequirementSummaryPanel";
import { RiskAnalysisPanel } from "../components/RiskAnalysisPanel";
import { ScriptViewerPanel } from "../components/ScriptViewerPanel";
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
    loadProfile,
    parseResult,
    riskReport,
    pipelineStatus,
    runAnalysis,
    scripts,
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

        <LoadProfilePanel
          loadProfile={loadProfile}
          isLoading={pipelineStatus.loadProfile === "loading"}
          error={stepErrors.loadProfile}
        />

        <ScriptViewerPanel
          scripts={scripts}
          isLoading={pipelineStatus.scripts === "loading"}
          error={stepErrors.scripts}
        />
        <RiskAnalysisPanel
          riskReport={riskReport}
          isLoading={pipelineStatus.risks === "loading"}
          error={stepErrors.risks}
        />
      </div>
    </main>
  );
}
