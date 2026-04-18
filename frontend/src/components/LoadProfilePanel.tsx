import type { BackgroundWorkerTraffic, LoadProfileSpec, LoadScenario } from "../api/types";
import { titleCase } from "../utils/formatters";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface LoadProfilePanelProps {
  loadProfile: LoadProfileSpec | null;
  isLoading: boolean;
  error?: string | null;
}

function WorkerCard({ worker }: { worker: BackgroundWorkerTraffic }) {
  const ratio = worker.peak_jobs_per_minute === 0 ? 0 : Math.min(100, Math.round((worker.steady_jobs_per_minute / worker.peak_jobs_per_minute) * 100));

  return (
    <article className="mini-card visual-mini-card">
      <strong>{worker.name}</strong>
      <span>{worker.queue_name}</span>
      <div className="traffic-bar-shell compact-bar-shell">
        <div className="traffic-bar-fill" style={{ width: `${ratio}%` }} />
      </div>
      <small>{worker.peak_jobs_per_minute.toLocaleString()} peak jobs/min</small>
    </article>
  );
}

function StageBars({ scenario }: { scenario: LoadScenario }) {
  const stages = scenario.ramp_up_stages.slice(0, 4);
  const maxRps = Math.max(...stages.map((stage) => stage.target_rps), 1);

  return (
    <div className="stage-chart">
      {stages.map((stage, index) => (
        <div key={`${stage.duration_minutes}-${index}`} className="stage-column">
          <div className="stage-bar-shell">
            <div className="stage-bar-fill" style={{ height: `${Math.max(20, (stage.target_rps / maxRps) * 100)}%` }} />
          </div>
          <span>{stage.target_rps}</span>
        </div>
      ))}
    </div>
  );
}

function MixBars({ scenario }: { scenario: LoadScenario }) {
  return (
    <div className="mix-visual-list">
      {scenario.endpoint_request_mix.slice(0, 4).map((item) => (
        <div key={`${item.method}-${item.path}`} className="mix-visual-row">
          <strong>{item.name}</strong>
          <div className="mix-bar-shell">
            <div className="mix-bar-fill" style={{ width: `${item.percentage}%` }} />
          </div>
          <span>{item.percentage}%</span>
        </div>
      ))}
    </div>
  );
}

function ScenarioPanel({ scenario }: { scenario: LoadScenario }) {
  return (
    <article className="scenario-card visual-scenario-card">
      <div className="scenario-header-row">
        <div>
          <h3>{scenario.name}</h3>
          <p>{titleCase(scenario.scenario_type)}</p>
        </div>
        {scenario.spike_traffic ? <span className="scenario-tag">Spike</span> : <span className="scenario-tag">Steady</span>}
      </div>

      <div className="metric-grid metric-grid-compact">
        <div className="visual-metric-card">
          <span>Baseline</span>
          <strong>{scenario.baseline_traffic.rps} RPS</strong>
        </div>
        <div className="visual-metric-card">
          <span>Peak</span>
          <strong>{scenario.peak_rps} RPS</strong>
        </div>
        <div className="visual-metric-card">
          <span>Users</span>
          <strong>{scenario.concurrency_levels.peak_users}</strong>
        </div>
        <div className="visual-metric-card">
          <span>Workers</span>
          <strong>{scenario.concurrency_levels.background_workers}</strong>
        </div>
      </div>

      <div className="dashboard-columns two-up visual-two-up">
        <div className="visual-block">
          <h4>Endpoint Mix</h4>
          <MixBars scenario={scenario} />
        </div>

        <div className="visual-block">
          <h4>Ramp Stages</h4>
          <StageBars scenario={scenario} />
        </div>
      </div>

      <div className="dashboard-columns two-up visual-two-up">
        <div className="visual-block">
          <h4>User Journeys</h4>
          <div className="signal-strip compact-strip">
            {scenario.user_journeys.slice(0, 3).map((journey) => (
              <div key={journey.name} className="signal-card">
                <strong>{journey.name}</strong>
                <span>{journey.percentage}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="visual-block">
          <h4>Worker Load</h4>
          {scenario.background_worker_traffic.length > 0 ? (
            <div className="mini-card-grid compact-grid">
              {scenario.background_worker_traffic.slice(0, 2).map((worker) => (
                <WorkerCard key={worker.name} worker={worker} />
              ))}
            </div>
          ) : (
            <p className="muted-copy">No background jobs modeled.</p>
          )}
        </div>
      </div>
    </article>
  );
}

export function LoadProfilePanel({ loadProfile, isLoading, error }: LoadProfilePanelProps) {
  const primaryScenario = loadProfile?.scenarios[0] ?? null;

  return (
    <SectionCard title="Load Profile" subtitle="Traffic visuals instead of long detail blocks">
      {!loadProfile && isLoading ? (
        <StateNotice title="Building load profile" message="Calculating traffic shape, journeys, concurrency, and worker load." tone="loading" />
      ) : null}
      {error ? <StateNotice title="Load profile error" message={error} tone="error" /> : null}
      {!loadProfile && !isLoading ? (
        <StateNotice title="No load profile yet" message="Generate a load profile to see traffic visuals." />
      ) : null}
      {loadProfile && primaryScenario ? (
        <div className="stack-md">
          <div className="signal-strip compact-strip">
            {loadProfile.kpis.slice(0, 3).map((kpi) => (
              <div key={kpi} className="signal-card signal-card-muted">
                <strong>KPI</strong>
                <span>{kpi}</span>
              </div>
            ))}
          </div>
          <ScenarioPanel scenario={primaryScenario} />
        </div>
      ) : null}
    </SectionCard>
  );
}
