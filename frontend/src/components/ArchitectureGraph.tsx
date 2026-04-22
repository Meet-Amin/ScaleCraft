import { useEffect, useMemo, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

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

interface DragState {
  nodeId: string;
  pointerId: number;
  offsetX: number;
  offsetY: number;
}

const lanes = ["edge", "services", "state", "async", "storage", "observability", "external"] as const;
const laneWidth = 210;
const topPadding = 58;
const nodeGap = 112;
const laneSpacing = 36;
const nodeWidth = 148;
const nodeHeight = 62;
const graphWidth = 72 + lanes.length * 246;

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

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function toCoordinate(clientValue: number, origin: number, renderedSize: number, viewBoxSize: number): number {
  return ((clientValue - origin) / renderedSize) * viewBoxSize;
}

export function ArchitectureGraph({ nodes, edges }: ArchitectureGraphProps) {
  const defaultNodes = useMemo(() => positionNodes(nodes), [nodes]);
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const [dragState, setDragState] = useState<DragState | null>(null);

  useEffect(() => {
    setNodePositions(
      Object.fromEntries(defaultNodes.map((node) => [node.id, { x: node.x, y: node.y }])),
    );
    setDragState(null);
  }, [defaultNodes]);

  const positionedNodes = defaultNodes.map((node) => ({
    ...node,
    ...(nodePositions[node.id] ?? { x: node.x, y: node.y }),
  }));
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));
  const height = Math.max(360, 120 + Math.max(...positionedNodes.map((node) => node.y), 0));

  function updateNodePosition(nodeId: string, clientX: number, clientY: number, currentTarget: SVGGElement): void {
    const svg = currentTarget.ownerSVGElement;
    if (!svg || dragState?.nodeId !== nodeId) {
      return;
    }

    const bounds = svg.getBoundingClientRect();
    const pointerX = toCoordinate(clientX, bounds.left, bounds.width, graphWidth);
    const pointerY = toCoordinate(clientY, bounds.top, bounds.height, height);

    setNodePositions((current) => ({
      ...current,
      [nodeId]: {
        x: clamp(pointerX - dragState.offsetX, 24, graphWidth - nodeWidth - 24),
        y: clamp(pointerY - dragState.offsetY, 40, 1200),
      },
    }));
  }

  function handlePointerDown(event: ReactPointerEvent<SVGGElement>, node: PositionedNode): void {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) {
      return;
    }

    const bounds = svg.getBoundingClientRect();
    const pointerX = toCoordinate(event.clientX, bounds.left, bounds.width, graphWidth);
    const pointerY = toCoordinate(event.clientY, bounds.top, bounds.height, height);

    setDragState({
      nodeId: node.id,
      pointerId: event.pointerId,
      offsetX: pointerX - node.x,
      offsetY: pointerY - node.y,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: ReactPointerEvent<SVGGElement>, nodeId: string): void {
    if (!dragState || dragState.nodeId !== nodeId || dragState.pointerId !== event.pointerId) {
      return;
    }

    updateNodePosition(nodeId, event.clientX, event.clientY, event.currentTarget);
  }

  function handlePointerEnd(event: ReactPointerEvent<SVGGElement>, nodeId: string): void {
    if (!dragState || dragState.nodeId !== nodeId || dragState.pointerId !== event.pointerId) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDragState(null);
  }

  return (
    <div className="graph-shell">
      <svg viewBox={`0 0 ${graphWidth} ${height}`} className="architecture-graph" role="img" aria-label="Architecture graph">
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
          <g
            key={node.id}
            transform={`translate(${node.x}, ${node.y})`}
            className={dragState?.nodeId === node.id ? "graph-node graph-node-dragging" : "graph-node"}
            onPointerDown={(event) => handlePointerDown(event, node)}
            onPointerMove={(event) => handlePointerMove(event, node.id)}
            onPointerUp={(event) => handlePointerEnd(event, node.id)}
            onPointerCancel={(event) => handlePointerEnd(event, node.id)}
          >
            <rect width={nodeWidth} height={nodeHeight} rx="18" className="graph-node-card" stroke={nodeColor(node.kind)} />
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
