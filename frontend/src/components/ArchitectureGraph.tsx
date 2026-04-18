import type { ArchitectureGraphEdge, ArchitectureGraphNode } from "../api/types";
import { titleCase } from "../utils/formatters";

interface ArchitectureGraphProps {
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
}

interface PositionedNode extends ArchitectureGraphNode {
  x: number;
  y: number;
}

const lanes = ["edge", "services", "state", "async", "storage", "observability", "external"] as const;

function laneForKind(kind: ArchitectureGraphNode["kind"]): (typeof lanes)[number] {
  if (kind === "load_balancer" || kind === "cdn") {
    return "edge";
  }
  if (kind === "service") {
    return "services";
  }
  if (kind === "database" || kind === "search") {
    return "state";
  }
  if (kind === "worker" || kind === "queue" || kind === "cache") {
    return "async";
  }
  if (kind === "object_storage") {
    return "storage";
  }
  if (kind === "observability") {
    return "observability";
  }
  return "external";
}

function positionNodes(nodes: ArchitectureGraphNode[]): PositionedNode[] {
  const laneWidth = 210;
  const topPadding = 58;
  const nodeGap = 112;
  const laneSpacing = 36;

  const grouped = lanes.map((lane) => nodes.filter((node) => laneForKind(node.kind) === lane));

  return grouped.flatMap((laneNodes, laneIndex) =>
    laneNodes.map((node, index) => ({
      ...node,
      x: 72 + laneIndex * (laneWidth + laneSpacing),
      y: topPadding + index * nodeGap,
    })),
  );
}

function nodeColor(kind: ArchitectureGraphNode["kind"]): string {
  if (kind === "database" || kind === "search") {
    return "#c78a5f";
  }
  if (kind === "cache" || kind === "queue" || kind === "worker") {
    return "#d3a87c";
  }
  if (kind === "observability") {
    return "#98ae8a";
  }
  if (kind === "external_api") {
    return "#b58b7c";
  }
  return "#b56d4e";
}

export function ArchitectureGraph({ nodes, edges }: ArchitectureGraphProps) {
  const positionedNodes = positionNodes(nodes);
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));
  const height = Math.max(360, 120 + Math.max(...positionedNodes.map((node) => node.y), 0));
  const width = 72 + lanes.length * 246;

  return (
    <div className="graph-shell">
      <svg viewBox={`0 0 ${width} ${height}`} className="architecture-graph" role="img" aria-label="Architecture graph">
        <defs>
          <marker id="graph-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#b56d4e" />
          </marker>
        </defs>

        {lanes.map((lane, index) => (
          <g key={lane}>
            <text x={72 + index * 246} y={28} className="graph-lane-label">
              {titleCase(lane)}
            </text>
          </g>
        ))}

        {edges.map((edge) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);
          if (!source || !target) {
            return null;
          }

          const startX = source.x + 148;
          const startY = source.y + 30;
          const endX = target.x;
          const endY = target.y + 30;
          const curve = Math.max(50, Math.abs(endX - startX) * 0.45);
          const path = `M ${startX} ${startY} C ${startX + curve} ${startY}, ${endX - curve} ${endY}, ${endX} ${endY}`;

          return (
            <g key={edge.id}>
              <path
                d={path}
                className={edge.critical_path ? "graph-edge graph-edge-critical" : "graph-edge"}
                markerEnd="url(#graph-arrow)"
              />
              <text x={(startX + endX) / 2} y={(startY + endY) / 2 - 8} className="graph-edge-label">
                {edge.protocol}
              </text>
            </g>
          );
        })}

        {positionedNodes.map((node) => (
          <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
            <rect width="148" height="62" rx="18" className="graph-node-card" stroke={nodeColor(node.kind)} />
            <text x="14" y="22" className="graph-node-title">
              {node.label}
            </text>
            <text x="14" y="41" className="graph-node-subtitle">
              {titleCase(node.kind)}
            </text>
            <circle cx="126" cy="18" r="6" fill={nodeColor(node.kind)} />
          </g>
        ))}
      </svg>
    </div>
  );
}
