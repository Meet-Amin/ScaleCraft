import { useEffect, useState } from "react";

import type {
  ArchitectureGraphEdge,
  ArchitectureGraphNode,
  ArchitectureNode,
  ArchitectureSpec,
  ComponentKind,
} from "../api/types";
import { prettyJson, titleCase } from "../utils/formatters";
import { ArchitectureGraph } from "./ArchitectureGraph";
import { SectionCard } from "./SectionCard";
import { StateNotice } from "./StateNotice";

interface ArchitectureVisualizationPanelProps {
  architecture: ArchitectureSpec | null;
  isLoading: boolean;
  error?: string | null;
}

interface NodeEditorState {
  label: string;
  kind: ComponentKind;
  technology: string;
  description: string;
}

interface EdgeEditorState {
  source: string;
  target: string;
  protocol: string;
  interaction: string;
  criticalPath: boolean;
}

const kindOptions: Array<{ value: ComponentKind; label: string }> = [
  { value: "service", label: "Service" },
  { value: "database", label: "Database" },
  { value: "cache", label: "Cache" },
  { value: "queue", label: "Queue" },
  { value: "worker", label: "Worker" },
  { value: "search", label: "Search" },
  { value: "object_storage", label: "Object Storage" },
  { value: "load_balancer", label: "Load Balancer" },
  { value: "cdn", label: "CDN" },
  { value: "observability", label: "Observability" },
  { value: "external_api", label: "External API" },
];

const emptyNodeEditorState: NodeEditorState = {
  label: "",
  kind: "service",
  technology: "",
  description: "",
};

const emptyEdgeEditorState: EdgeEditorState = {
  source: "",
  target: "",
  protocol: "HTTP",
  interaction: "Calls service",
  criticalPath: false,
};

function isArchitectureSpec(value: unknown): value is ArchitectureSpec {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const graphJson = candidate.graph_json;

  if (!graphJson || typeof graphJson !== "object") {
    return false;
  }

  const graph = graphJson as Record<string, unknown>;

  return (
    typeof candidate.overview === "string" &&
    Array.isArray(candidate.services) &&
    Array.isArray(candidate.databases) &&
    Array.isArray(candidate.scaling_notes) &&
    Array.isArray(graph.nodes) &&
    Array.isArray(graph.edges)
  );
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function isStatefulKind(kind: ComponentKind): boolean {
  return kind === "database" || kind === "cache" || kind === "search" || kind === "object_storage";
}

function descriptionFromGraphNode(node: ArchitectureGraphNode, existingNode?: ArchitectureNode): string {
  const attributeDescription = node.attributes.description;
  if (typeof attributeDescription === "string" && attributeDescription.trim().length > 0) {
    return attributeDescription;
  }
  if (existingNode?.description) {
    return existingNode.description;
  }
  return `${node.label} handles ${titleCase(node.kind).toLowerCase()} responsibilities.`;
}

function buildArchitectureNode(graphNode: ArchitectureGraphNode, existingNode?: ArchitectureNode): ArchitectureNode {
  return {
    id: graphNode.id,
    name: graphNode.label,
    kind: graphNode.kind,
    technology: graphNode.technology,
    description: descriptionFromGraphNode(graphNode, existingNode),
    responsibilities: existingNode?.responsibilities ?? toStringArray(graphNode.attributes.responsibilities),
    scaling_notes: existingNode?.scaling_notes ?? toStringArray(graphNode.attributes.scaling_notes),
    stateful:
      typeof graphNode.attributes.stateful === "boolean"
        ? graphNode.attributes.stateful
        : existingNode?.stateful ?? isStatefulKind(graphNode.kind),
  };
}

function syncArchitectureStructure(architecture: ArchitectureSpec): ArchitectureSpec {
  const existingNodes = new Map(architecture.nodes.map((node) => [node.id, node]));
  const nodes = architecture.graph_json.nodes.map((node) => buildArchitectureNode(node, existingNodes.get(node.id)));
  const edges = architecture.graph_json.edges.map((edge) => ({
    source: edge.source,
    target: edge.target,
    interaction: edge.interaction,
    protocol: edge.protocol,
    critical_path: edge.critical_path,
  }));

  return {
    ...architecture,
    nodes,
    edges,
    services: nodes.filter((node) => node.kind === "service"),
    databases: nodes.filter((node) => node.kind === "database"),
    cache: nodes.filter((node) => node.kind === "cache"),
    queues: nodes.filter((node) => node.kind === "queue"),
    storage: nodes.filter((node) => node.kind === "object_storage"),
    observability: nodes.filter((node) => node.kind === "observability"),
  };
}

function nodeEditorStateFromNode(graphNode: ArchitectureGraphNode, architectureNode?: ArchitectureNode): NodeEditorState {
  return {
    label: graphNode.label,
    kind: graphNode.kind,
    technology: graphNode.technology,
    description: descriptionFromGraphNode(graphNode, architectureNode),
  };
}

function createNodeId(label: string, existingIds: string[]): string {
  const baseId =
    label
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "node";

  let candidate = baseId;
  let index = 2;
  while (existingIds.includes(candidate)) {
    candidate = `${baseId}-${index}`;
    index += 1;
  }
  return candidate;
}

function edgeEditorStateFromEdge(edge: ArchitectureGraphEdge): EdgeEditorState {
  return {
    source: edge.source,
    target: edge.target,
    protocol: edge.protocol,
    interaction: edge.interaction,
    criticalPath: edge.critical_path,
  };
}

function buildNewEdgeEditorState(nodes: ArchitectureGraphNode[], preferredSourceId?: string | null): EdgeEditorState {
  if (nodes.length === 0) {
    return emptyEdgeEditorState;
  }

  const source = preferredSourceId && nodes.some((node) => node.id === preferredSourceId) ? preferredSourceId : nodes[0].id;
  const target = nodes.find((node) => node.id !== source)?.id ?? "";

  return {
    ...emptyEdgeEditorState,
    source,
    target,
  };
}

function createEdgeId(source: string, target: string, existingIds: string[]): string {
  const baseId = `${source}-${target}`;
  let candidate = baseId;
  let index = 2;
  while (existingIds.includes(candidate)) {
    candidate = `${baseId}-${index}`;
    index += 1;
  }
  return candidate;
}

export function ArchitectureVisualizationPanel({ architecture, isLoading, error }: ArchitectureVisualizationPanelProps) {
  const [editableArchitecture, setEditableArchitecture] = useState<ArchitectureSpec | null>(
    architecture ? syncArchitectureStructure(architecture) : null,
  );
  const [draftJson, setDraftJson] = useState<string>(architecture ? prettyJson(architecture) : "");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(architecture?.graph_json.nodes[0]?.id ?? null);
  const [nodeEditor, setNodeEditor] = useState<NodeEditorState>(
    architecture?.graph_json.nodes[0]
      ? nodeEditorStateFromNode(architecture.graph_json.nodes[0], architecture.nodes.find((node) => node.id === architecture.graph_json.nodes[0]?.id))
      : emptyNodeEditorState,
  );
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(architecture?.graph_json.edges[0]?.id ?? null);
  const [edgeEditor, setEdgeEditor] = useState<EdgeEditorState>(
    architecture?.graph_json.edges[0]
      ? edgeEditorStateFromEdge(architecture.graph_json.edges[0])
      : buildNewEdgeEditorState(architecture?.graph_json.nodes ?? [], architecture?.graph_json.nodes[0]?.id),
  );
  const [nodeEditorError, setNodeEditorError] = useState<string | null>(null);
  const [edgeEditorError, setEdgeEditorError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    const timeout = window.setTimeout(() => setToastMessage(null), 1400);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  useEffect(() => {
    const syncedArchitecture = architecture ? syncArchitectureStructure(architecture) : null;
    setEditableArchitecture(syncedArchitecture);
    setDraftJson(syncedArchitecture ? prettyJson(syncedArchitecture) : "");
    if (syncedArchitecture?.graph_json.nodes[0]) {
      const firstNode = syncedArchitecture.graph_json.nodes[0];
      setSelectedNodeId(firstNode.id);
      setNodeEditor(nodeEditorStateFromNode(firstNode, syncedArchitecture.nodes.find((node) => node.id === firstNode.id)));
    } else {
      setSelectedNodeId(null);
      setNodeEditor(emptyNodeEditorState);
    }
    setNodeEditorError(null);
    if (syncedArchitecture?.graph_json.edges[0]) {
      const firstEdge = syncedArchitecture.graph_json.edges[0];
      setSelectedEdgeId(firstEdge.id);
      setEdgeEditor(edgeEditorStateFromEdge(firstEdge));
    } else {
      setSelectedEdgeId(null);
      setEdgeEditor(buildNewEdgeEditorState(syncedArchitecture?.graph_json.nodes ?? [], syncedArchitecture?.graph_json.nodes[0]?.id));
    }
    setEdgeEditorError(null);
    setIsEditing(false);
    setEditorError(null);
  }, [architecture]);

  function syncSelection(nextArchitecture: ArchitectureSpec, preferredNodeId: string | null): void {
    const selectedNode =
      (preferredNodeId ? nextArchitecture.graph_json.nodes.find((node) => node.id === preferredNodeId) : null) ??
      nextArchitecture.graph_json.nodes[0] ??
      null;

    if (!selectedNode) {
      setSelectedNodeId(null);
      setNodeEditor(emptyNodeEditorState);
      setNodeEditorError(null);
      return;
    }

    setSelectedNodeId(selectedNode.id);
    setNodeEditor(nodeEditorStateFromNode(selectedNode, nextArchitecture.nodes.find((node) => node.id === selectedNode.id)));
    setNodeEditorError(null);
  }

  function syncEdgeSelection(nextArchitecture: ArchitectureSpec, preferredEdgeId: string | null, preferredSourceId?: string | null): void {
    const selectedEdge =
      (preferredEdgeId ? nextArchitecture.graph_json.edges.find((edge) => edge.id === preferredEdgeId) : null) ??
      nextArchitecture.graph_json.edges[0] ??
      null;

    if (!selectedEdge) {
      setSelectedEdgeId(null);
      setEdgeEditor(buildNewEdgeEditorState(nextArchitecture.graph_json.nodes, preferredSourceId));
      setEdgeEditorError(null);
      return;
    }

    setSelectedEdgeId(selectedEdge.id);
    setEdgeEditor(edgeEditorStateFromEdge(selectedEdge));
    setEdgeEditorError(null);
  }

  function commitArchitecture(
    nextArchitecture: ArchitectureSpec,
    preferredNodeId: string | null,
    preferredEdgeId: string | null,
  ): void {
    setEditableArchitecture(nextArchitecture);
    setDraftJson(prettyJson(nextArchitecture));
    setEditorError(null);
    syncSelection(nextArchitecture, preferredNodeId);
    syncEdgeSelection(nextArchitecture, preferredEdgeId, preferredNodeId);
  }

  function selectNode(nodeId: string): void {
    if (!editableArchitecture) {
      return;
    }

    const graphNode = editableArchitecture.graph_json.nodes.find((node) => node.id === nodeId);
    if (!graphNode) {
      return;
    }

    setSelectedNodeId(nodeId);
    setNodeEditor(nodeEditorStateFromNode(graphNode, editableArchitecture.nodes.find((node) => node.id === nodeId)));
    setNodeEditorError(null);
  }

  function startNewNode(): void {
    setSelectedNodeId(null);
    setNodeEditor(emptyNodeEditorState);
    setNodeEditorError(null);
  }

  function selectEdge(edgeId: string): void {
    if (!editableArchitecture) {
      return;
    }

    const edge = editableArchitecture.graph_json.edges.find((item) => item.id === edgeId);
    if (!edge) {
      return;
    }

    setSelectedEdgeId(edgeId);
    setEdgeEditor(edgeEditorStateFromEdge(edge));
    setEdgeEditorError(null);
  }

  function startNewEdge(): void {
    if (!editableArchitecture) {
      return;
    }

    setSelectedEdgeId(null);
    setEdgeEditor(buildNewEdgeEditorState(editableArchitecture.graph_json.nodes, selectedNodeId));
    setEdgeEditorError(null);
  }

  function applyDraft(): void {
    try {
      const parsed = JSON.parse(draftJson) as unknown;
      if (!isArchitectureSpec(parsed)) {
        setEditorError("Edited JSON must keep the architecture shape, including graph nodes and edges.");
        return;
      }

      commitArchitecture(syncArchitectureStructure(parsed), selectedNodeId, selectedEdgeId);
      setIsEditing(false);
    } catch {
      setEditorError("Edited JSON must be valid JSON before it can be applied.");
    }
  }

  function resetToGenerated(): void {
    const syncedArchitecture = architecture ? syncArchitectureStructure(architecture) : null;
    setEditableArchitecture(syncedArchitecture);
    setDraftJson(syncedArchitecture ? prettyJson(syncedArchitecture) : "");
    setEditorError(null);
    if (syncedArchitecture) {
      syncSelection(syncedArchitecture, syncedArchitecture.graph_json.nodes[0]?.id ?? null);
      syncEdgeSelection(syncedArchitecture, syncedArchitecture.graph_json.edges[0]?.id ?? null, syncedArchitecture.graph_json.nodes[0]?.id);
    } else {
      setSelectedNodeId(null);
      setNodeEditor(emptyNodeEditorState);
      setNodeEditorError(null);
      setSelectedEdgeId(null);
      setEdgeEditor(emptyEdgeEditorState);
      setEdgeEditorError(null);
    }
    setIsEditing(false);
  }

  function saveNode(): void {
    if (!editableArchitecture) {
      return;
    }

    const label = nodeEditor.label.trim();
    if (!label) {
      setNodeEditorError("Node name is required.");
      return;
    }

    const technology = nodeEditor.technology.trim() || "Custom";
    const description = nodeEditor.description.trim() || `${label} handles ${titleCase(nodeEditor.kind).toLowerCase()} responsibilities.`;

    let nextArchitecture: ArchitectureSpec;
    if (selectedNodeId) {
      nextArchitecture = syncArchitectureStructure({
        ...editableArchitecture,
        graph_json: {
          ...editableArchitecture.graph_json,
          nodes: editableArchitecture.graph_json.nodes.map((node) =>
            node.id === selectedNodeId
              ? {
                  ...node,
                  label,
                  kind: nodeEditor.kind,
                  technology,
                  attributes: {
                    ...node.attributes,
                    description,
                  },
                }
              : node,
          ),
        },
      });
      commitArchitecture(nextArchitecture, selectedNodeId, selectedEdgeId);
      setToastMessage("Node saved");
      return;
    }

    const nodeId = createNodeId(label, editableArchitecture.graph_json.nodes.map((node) => node.id));
    const nextNode: ArchitectureGraphNode = {
      id: nodeId,
      label,
      kind: nodeEditor.kind,
      technology,
      attributes: {
        description,
      },
    };

    nextArchitecture = syncArchitectureStructure({
      ...editableArchitecture,
      graph_json: {
        ...editableArchitecture.graph_json,
        nodes: [...editableArchitecture.graph_json.nodes, nextNode],
      },
    });
    commitArchitecture(nextArchitecture, nodeId, selectedEdgeId);
    setToastMessage("Node added");
  }

  function deleteSelectedNode(): void {
    if (!editableArchitecture || !selectedNodeId) {
      return;
    }

    const nextArchitecture = syncArchitectureStructure({
      ...editableArchitecture,
      graph_json: {
        ...editableArchitecture.graph_json,
        nodes: editableArchitecture.graph_json.nodes.filter((node) => node.id !== selectedNodeId),
        edges: editableArchitecture.graph_json.edges.filter(
          (edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId,
        ),
      },
    });
    commitArchitecture(nextArchitecture, null, selectedEdgeId);
    setToastMessage("Node deleted");
  }

  function saveEdge(): void {
    if (!editableArchitecture) {
      return;
    }

    if (editableArchitecture.graph_json.nodes.length < 2) {
      setEdgeEditorError("Add at least two nodes before creating a connection.");
      return;
    }

    if (!edgeEditor.source || !edgeEditor.target) {
      setEdgeEditorError("Choose both the starting node and the destination node.");
      return;
    }

    if (edgeEditor.source === edgeEditor.target) {
      setEdgeEditorError("A connection must link two different nodes.");
      return;
    }

    const protocol = edgeEditor.protocol.trim() || "HTTP";
    const interaction = edgeEditor.interaction.trim() || "Calls service";

    let nextArchitecture: ArchitectureSpec;
    if (selectedEdgeId) {
      nextArchitecture = syncArchitectureStructure({
        ...editableArchitecture,
        graph_json: {
          ...editableArchitecture.graph_json,
          edges: editableArchitecture.graph_json.edges.map((edge) =>
            edge.id === selectedEdgeId
              ? {
                  ...edge,
                  source: edgeEditor.source,
                  target: edgeEditor.target,
                  protocol,
                  interaction,
                  critical_path: edgeEditor.criticalPath,
                }
              : edge,
          ),
        },
      });
      commitArchitecture(nextArchitecture, selectedNodeId, selectedEdgeId);
      setToastMessage("Connection saved");
      return;
    }

    const edgeId = createEdgeId(
      edgeEditor.source,
      edgeEditor.target,
      editableArchitecture.graph_json.edges.map((edge) => edge.id),
    );

    nextArchitecture = syncArchitectureStructure({
      ...editableArchitecture,
      graph_json: {
        ...editableArchitecture.graph_json,
        edges: [
          ...editableArchitecture.graph_json.edges,
          {
            id: edgeId,
            source: edgeEditor.source,
            target: edgeEditor.target,
            protocol,
            interaction,
            critical_path: edgeEditor.criticalPath,
          },
        ],
      },
    });
    commitArchitecture(nextArchitecture, selectedNodeId, edgeId);
    setToastMessage("Connection added");
  }

  function deleteSelectedEdge(): void {
    if (!editableArchitecture || !selectedEdgeId) {
      return;
    }

    const nextArchitecture = syncArchitectureStructure({
      ...editableArchitecture,
      graph_json: {
        ...editableArchitecture.graph_json,
        edges: editableArchitecture.graph_json.edges.filter((edge) => edge.id !== selectedEdgeId),
      },
    });
    commitArchitecture(nextArchitecture, selectedNodeId, null);
    setToastMessage("Connection deleted");
  }

  const renderedArchitecture = editableArchitecture;

  return (
    <SectionCard title="Architecture" subtitle="System graph with the key scaling notes">
      {!architecture && isLoading ? (
        <div className="skeleton-stack" aria-label="Generating architecture">
          <div className="skeleton-card">
            <div className="skeleton skeleton-line" style={{ width: "42%" }} />
            <div className="skeleton skeleton-line" style={{ width: "86%", marginTop: 10 }} />
          </div>
          <div className="skeleton-card">
            <div className="skeleton" style={{ height: 240 }} />
          </div>
          <div className="skeleton-grid-4">
            <div className="skeleton-card">
              <div className="skeleton skeleton-line" style={{ width: "60%" }} />
              <div className="skeleton skeleton-line-lg" style={{ width: "34%", marginTop: 12 }} />
            </div>
            <div className="skeleton-card">
              <div className="skeleton skeleton-line" style={{ width: "64%" }} />
              <div className="skeleton skeleton-line-lg" style={{ width: "38%", marginTop: 12 }} />
            </div>
            <div className="skeleton-card">
              <div className="skeleton skeleton-line" style={{ width: "56%" }} />
              <div className="skeleton skeleton-line-lg" style={{ width: "32%", marginTop: 12 }} />
            </div>
            <div className="skeleton-card">
              <div className="skeleton skeleton-line" style={{ width: "62%" }} />
              <div className="skeleton skeleton-line-lg" style={{ width: "36%", marginTop: 12 }} />
            </div>
          </div>
          <StateNotice title="Generating architecture" message="Mapping structured requirements into a system graph." tone="loading" />
        </div>
      ) : null}
      {error ? <StateNotice title="Architecture error" message={error} tone="error" /> : null}
      {!architecture && !isLoading ? (
        <StateNotice title="No architecture yet" message="Generate an architecture to see the system graph." />
      ) : null}
      {renderedArchitecture ? (
        <div className="stack-md">
          <div className="tab-row compact-actions-row">
            <button className="ghost-button ghost-button-inline" type="button" onClick={startNewNode}>
              Add Node
            </button>
            <button className="ghost-button ghost-button-inline" type="button" onClick={startNewEdge}>
              Add Connection
            </button>
            <button className="ghost-button" type="button" onClick={() => setIsEditing((current) => !current)}>
              {isEditing ? "Hide Advanced JSON" : "Advanced JSON"}
            </button>
            <button className="ghost-button" type="button" onClick={resetToGenerated}>
              Reset to Generated
            </button>
          </div>

          <div className="architecture-builder-grid">
            <div className="visual-block node-list-panel">
              <div className="builder-header-row">
                <div>
                  <h3>Easy Node Editor</h3>
                  <p className="compact-copy">Pick a node to edit it, or add a new one with simple fields.</p>
                </div>
              </div>

              <div className="node-list">
                {renderedArchitecture.graph_json.nodes.map((node) => (
                  <button
                    key={node.id}
                    className={`node-list-button ${selectedNodeId === node.id ? "node-list-button-active" : ""}`}
                    type="button"
                    onClick={() => selectNode(node.id)}
                  >
                    <strong>{node.label}</strong>
                    <span>
                      {titleCase(node.kind)}{node.technology ? ` • ${node.technology}` : ""}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="visual-block node-editor-panel">
              <div className="builder-header-row">
                <div>
                  <h3>{selectedNodeId ? "Edit Selected Node" : "Add New Node"}</h3>
                  <p className="compact-copy">Use plain fields instead of editing raw architecture JSON.</p>
                </div>
              </div>

              <label className="node-form-field">
                <span>Node Name</span>
                <input
                  className="node-form-input"
                  type="text"
                  value={nodeEditor.label}
                  onChange={(event) => setNodeEditor((current) => ({ ...current, label: event.target.value }))}
                  placeholder="Checkout Service"
                />
              </label>

              <label className="node-form-field">
                <span>Node Type</span>
                <select
                  className="node-form-input"
                  value={nodeEditor.kind}
                  onChange={(event) =>
                    setNodeEditor((current) => ({ ...current, kind: event.target.value as ComponentKind }))
                  }
                >
                  {kindOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="node-form-field">
                <span>Technology</span>
                <input
                  className="node-form-input"
                  type="text"
                  value={nodeEditor.technology}
                  onChange={(event) => setNodeEditor((current) => ({ ...current, technology: event.target.value }))}
                  placeholder="FastAPI, Postgres, Redis"
                />
              </label>

              <label className="node-form-field">
                <span>What It Does</span>
                <textarea
                  className="node-form-input node-form-textarea"
                  value={nodeEditor.description}
                  onChange={(event) => setNodeEditor((current) => ({ ...current, description: event.target.value }))}
                  rows={4}
                  placeholder="Handles orders and checkout requests"
                />
              </label>

              <div className="tab-row compact-actions-row">
                <button className="primary-button" type="button" onClick={saveNode}>
                  {selectedNodeId ? "Save Node" : "Add Node"}
                </button>
                {selectedNodeId ? (
                  <button className="ghost-button ghost-button-inline" type="button" onClick={deleteSelectedNode}>
                    Delete Node
                  </button>
                ) : null}
              </div>

              {nodeEditorError ? <StateNotice title="Node editor error" message={nodeEditorError} tone="error" /> : null}
            </div>
          </div>

          <div className="connection-builder-grid">
            <div className="visual-block connection-list-panel">
              <div className="builder-header-row">
                <div>
                  <h3>Easy Connection Editor</h3>
                  <p className="compact-copy">Choose a connection to edit it, or add a new link between nodes.</p>
                </div>
              </div>

              <div className="node-list">
                {renderedArchitecture.graph_json.edges.map((edge) => (
                  <button
                    key={edge.id}
                    className={`node-list-button ${selectedEdgeId === edge.id ? "node-list-button-active" : ""}`}
                    type="button"
                    onClick={() => selectEdge(edge.id)}
                  >
                    <strong>
                      {edge.source} {"->"} {edge.target}
                    </strong>
                    <span>
                      {edge.protocol} • {edge.interaction}
                    </span>
                  </button>
                ))}
                {renderedArchitecture.graph_json.edges.length === 0 ? (
                  <p className="muted-copy compact-copy">No connections yet. Add one with the form.</p>
                ) : null}
              </div>
            </div>

            <div className="visual-block connection-editor-panel">
              <div className="builder-header-row">
                <div>
                  <h3>{selectedEdgeId ? "Edit Selected Connection" : "Add New Connection"}</h3>
                  <p className="compact-copy">Describe how one node talks to another in plain language.</p>
                </div>
              </div>

              <label className="node-form-field">
                <span>From Node</span>
                <select
                  className="node-form-input"
                  value={edgeEditor.source}
                  onChange={(event) => setEdgeEditor((current) => ({ ...current, source: event.target.value }))}
                >
                  <option value="">Select a node</option>
                  {renderedArchitecture.graph_json.nodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="node-form-field">
                <span>To Node</span>
                <select
                  className="node-form-input"
                  value={edgeEditor.target}
                  onChange={(event) => setEdgeEditor((current) => ({ ...current, target: event.target.value }))}
                >
                  <option value="">Select a node</option>
                  {renderedArchitecture.graph_json.nodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="node-form-field">
                <span>Protocol</span>
                <input
                  className="node-form-input"
                  type="text"
                  value={edgeEditor.protocol}
                  onChange={(event) => setEdgeEditor((current) => ({ ...current, protocol: event.target.value }))}
                  placeholder="HTTP, gRPC, queue"
                />
              </label>

              <label className="node-form-field">
                <span>What Happens</span>
                <input
                  className="node-form-input"
                  type="text"
                  value={edgeEditor.interaction}
                  onChange={(event) => setEdgeEditor((current) => ({ ...current, interaction: event.target.value }))}
                  placeholder="Sends checkout requests"
                />
              </label>

              <label className="checkbox-row" htmlFor="critical-path-toggle">
                <input
                  id="critical-path-toggle"
                  type="checkbox"
                  checked={edgeEditor.criticalPath}
                  onChange={(event) => setEdgeEditor((current) => ({ ...current, criticalPath: event.target.checked }))}
                />
                <span>This is a critical path connection</span>
              </label>

              <div className="tab-row compact-actions-row">
                <button className="primary-button" type="button" onClick={saveEdge}>
                  {selectedEdgeId ? "Save Connection" : "Add Connection"}
                </button>
                {selectedEdgeId ? (
                  <button className="ghost-button ghost-button-inline" type="button" onClick={deleteSelectedEdge}>
                    Delete Connection
                  </button>
                ) : null}
              </div>

              {edgeEditorError ? <StateNotice title="Connection editor error" message={edgeEditorError} tone="error" /> : null}
            </div>
          </div>

          {isEditing ? (
            <div className="stack-sm">
              <label className="input-label architecture-editor-label" htmlFor="architecture-json-editor">
                Advanced Architecture JSON
              </label>
              <textarea
                id="architecture-json-editor"
                className="architecture-editor"
                value={draftJson}
                onChange={(event) => setDraftJson(event.target.value)}
                spellCheck={false}
                rows={20}
              />
              <div className="tab-row compact-actions-row">
                <button className="primary-button" type="button" onClick={applyDraft}>
                  Apply Changes
                </button>
                <button className="ghost-button ghost-button-inline" type="button" onClick={resetToGenerated}>
                  Discard Changes
                </button>
              </div>
              {editorError ? <StateNotice title="Invalid architecture JSON" message={editorError} tone="error" /> : null}
            </div>
          ) : null}

          <div className="signal-strip compact-strip">
            <div className="signal-card">
              <strong>{renderedArchitecture.services.length}</strong>
              <span>Services</span>
            </div>
            <div className="signal-card">
              <strong>{renderedArchitecture.databases.length}</strong>
              <span>Data Stores</span>
            </div>
            <div className="signal-card">
              <strong>{renderedArchitecture.graph_json.edges.length}</strong>
              <span>Connections</span>
            </div>
          </div>

          <p className="drag-hint">Drag nodes in the graph to rearrange the layout.</p>

          <ArchitectureGraph
            nodes={renderedArchitecture.graph_json.nodes}
            edges={renderedArchitecture.graph_json.edges}
            selectedNodeId={selectedNodeId}
            selectedEdgeId={selectedEdgeId}
            onSelectNode={(nodeId) => {
              selectNode(nodeId);
            }}
            onSelectEdge={(edgeId) => {
              selectEdge(edgeId);
            }}
          />

          {toastMessage ? <div className="action-toast">{toastMessage}</div> : null}

          <p className="body-copy compact-copy">{renderedArchitecture.overview}</p>

          <div className="signal-strip compact-strip">
            {renderedArchitecture.scaling_notes.slice(0, 3).map((note) => (
              <div key={note} className="signal-card signal-card-muted">
                <strong>Scaling Note</strong>
                <span>{note}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
