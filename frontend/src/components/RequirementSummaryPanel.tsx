import type { ParseRequirementResponse } from "../api/types";
import { titleCase } from "../utils/formatters";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface RequirementSummaryPanelProps {
  parseResult: ParseRequirementResponse | null;
  isLoading: boolean;
  error?: string | null;
}

export function RequirementSummaryPanel({ parseResult, isLoading, error }: RequirementSummaryPanelProps) {
  const requirement = parseResult?.requirement;
  const trafficRatio = requirement
    ? Math.max(18, Math.min(100, Math.round((requirement.traffic.baseline_rps / requirement.traffic.peak_rps) * 100)))
    : 0;
  const availabilityRatio = requirement ? Number.parseFloat(requirement.availability_target.replace("%", "")) : 0;

  return (
    <SectionCard title="Requirement Summary" subtitle="Visual overview of the parsed product brief">
      {!parseResult && isLoading ? (
        <StateNotice title="Parsing requirement" message="Converting natural language into a typed product spec." tone="loading" />
      ) : null}
      {error ? <StateNotice title="Requirement error" message={error} tone="error" /> : null}
      {!parseResult && !isLoading ? (
        <StateNotice title="No requirement parsed yet" message="Submit a requirement to see the product shape visually." />
      ) : null}
      {requirement ? (
        <div className="stack-md">
          <div className="visual-summary-grid">
            <div className="headline-card">
              <span className="eyebrow">{titleCase(requirement.domain)}</span>
              <strong>{requirement.product_name}</strong>
              <p className="body-copy compact-copy">{requirement.summary}</p>
              <div className="pill-row">
                {requirement.client_surfaces.slice(0, 3).map((surface) => (
                  <span key={surface} className="pill pill-subtle">
                    {titleCase(surface)}
                  </span>
                ))}
                {requirement.integrations.slice(0, 2).map((integration) => (
                  <span key={integration} className="pill pill-subtle">
                    {integration}
                  </span>
                ))}
              </div>
            </div>

            <div className="gauge-card">
              <div
                className="gauge-ring"
                style={{
                  background: `conic-gradient(#73f0db 0 ${Math.max(0, Math.min(availabilityRatio, 100))}%, rgba(49, 66, 102, 0.9) ${Math.max(0, Math.min(availabilityRatio, 100))}% 100%)`,
                }}
              >
                <div className="gauge-inner">
                  <span>Availability</span>
                  <strong>{requirement.availability_target}</strong>
                </div>
              </div>
            </div>

            <div className="visual-metric-card">
              <span>Traffic Envelope</span>
              <strong>{requirement.traffic.peak_rps} peak RPS</strong>
              <div className="traffic-bar-shell">
                <div className="traffic-bar-fill" style={{ width: `${trafficRatio}%` }} />
              </div>
              <div className="split-metric-row">
                <small>{requirement.traffic.baseline_rps} baseline</small>
                <small>{requirement.traffic.peak_concurrency} concurrency</small>
              </div>
            </div>

            <div className="visual-metric-card">
              <span>Delivery Footprint</span>
              <strong>{requirement.traffic.regions.length} regions</strong>
              <div className="region-dot-row">
                {requirement.traffic.regions.map((region) => (
                  <span key={region} className="region-dot" title={region} />
                ))}
              </div>
              <small>{requirement.traffic.regions.join(" • ")}</small>
            </div>
          </div>

          <div className="signal-strip">
            {requirement.functional_requirements.slice(0, 4).map((item) => (
              <div key={item.name} className="signal-card">
                <strong>{item.name}</strong>
                <span>{titleCase(item.priority)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
