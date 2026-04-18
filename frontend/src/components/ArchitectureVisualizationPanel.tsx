import type { ArchitectureSpec } from "../api/types";
import { ArchitectureGraph } from "./ArchitectureGraph";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface ArchitectureVisualizationPanelProps {
  architecture: ArchitectureSpec | null;
  isLoading: boolean;
  error?: string | null;
}

export function ArchitectureVisualizationPanel({ architecture, isLoading, error }: ArchitectureVisualizationPanelProps) {
  return (
    <SectionCard title="Architecture" subtitle="Graph-first system view">
      {!architecture && isLoading ? (
        <StateNotice title="Generating architecture" message="Mapping structured requirements into a system graph." tone="loading" />
      ) : null}
      {error ? <StateNotice title="Architecture error" message={error} tone="error" /> : null}
      {!architecture && !isLoading ? (
        <StateNotice title="No architecture yet" message="Generate an architecture to see the system graph." />
      ) : null}
      {architecture ? (
        <div className="stack-md">
          <div className="signal-strip compact-strip">
            <div className="signal-card">
              <strong>{architecture.services.length}</strong>
              <span>Services</span>
            </div>
            <div className="signal-card">
              <strong>{architecture.databases.length}</strong>
              <span>Data Stores</span>
            </div>
            <div className="signal-card">
              <strong>{architecture.graph_json.edges.length}</strong>
              <span>Connections</span>
            </div>
          </div>

          <ArchitectureGraph nodes={architecture.graph_json.nodes} edges={architecture.graph_json.edges} />
        </div>
      ) : null}
    </SectionCard>
  );
}
