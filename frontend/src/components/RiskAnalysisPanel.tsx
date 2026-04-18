import type { RiskItem, RiskReport } from "../api/types";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface RiskAnalysisPanelProps {
  riskReport: RiskReport | null;
  isLoading: boolean;
  error?: string | null;
}

function severityWidth(severity: RiskItem["severity"]): number {
  if (severity === "critical") {
    return 100;
  }
  if (severity === "high") {
    return 78;
  }
  if (severity === "medium") {
    return 56;
  }
  return 32;
}

function RiskIcon({ severity }: { severity: RiskItem["severity"] }) {
  return (
    <svg viewBox="0 0 32 32" className={`risk-icon risk-icon-${severity}`} aria-hidden="true">
      <circle cx="16" cy="16" r="14" className="risk-icon-ring" />
      <path d="M16 8 L23 22 H9 Z" className="risk-icon-mark" />
    </svg>
  );
}

export function RiskAnalysisPanel({ riskReport, isLoading, error }: RiskAnalysisPanelProps) {
  const topRisks = riskReport?.top_risks.slice(0, 3) ?? [];

  return (
    <SectionCard title="Risk Analysis" subtitle="Visual risk heat and top actions">
      {!riskReport && isLoading ? (
        <StateNotice title="Analyzing risks" message="Inspecting the generated architecture and load profile for scale and reliability issues." tone="loading" />
      ) : null}
      {error ? <StateNotice title="Risk analysis error" message={error} tone="error" /> : null}
      {!riskReport && !isLoading ? (
        <StateNotice title="No risk report yet" message="Generate a run to see visual risk highlights." />
      ) : null}
      {riskReport ? (
        <div className="stack-md">
          <div className="risk-summary-band">
            {topRisks.map((risk) => (
              <div key={risk.title} className="risk-band-row">
                <strong>{risk.title}</strong>
                <div className="risk-band-shell">
                  <div className={`risk-band-fill risk-band-${risk.severity}`} style={{ width: `${severityWidth(risk.severity)}%` }} />
                </div>
              </div>
            ))}
          </div>

          <div className="risk-grid">
            {topRisks.map((risk) => (
              <article key={risk.title} className="risk-card visual-risk-card">
                <div className="risk-hero-row">
                  <RiskIcon severity={risk.severity} />
                  <div>
                    <h3>{risk.title}</h3>
                    <div className={`severity severity-${risk.severity}`}>{risk.severity}</div>
                  </div>
                </div>
                <div className="risk-chip-row">
                  <span className="pill pill-subtle">{risk.category.replace(/_/g, " ")}</span>
                  <span className="pill pill-subtle">Action</span>
                </div>
              </article>
            ))}
          </div>

          <div className="signal-strip compact-strip">
            {riskReport.scaling_actions.slice(0, 3).map((action) => (
              <div key={action} className="signal-card signal-card-muted">
                <strong>Action</strong>
                <span>{action}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
