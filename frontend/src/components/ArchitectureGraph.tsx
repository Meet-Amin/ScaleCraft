import { useEffect, useMemo, useState } from "react";
import type { PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from "react";

import type { ArchitectureGraphEdge, ArchitectureGraphNode } from "../api/types";
import { titleCase } from "../utils/formatters";

interface ArchitectureGraphProps {
  nodes: ArchitectureGraphNode[];
  edges: ArchitectureGraphEdge[];
  selectedNodeId?: string | null;
  selectedEdgeId?: string | null;
  onSelectNode?: (nodeId: string) => void;
  onSelectEdge?: (edgeId: string) => void;
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

interface PanState {
  pointerId: number;
  startX: number;
  startY: number;
  startTranslateX: number;
  startTranslateY: number;
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
  if (kind === "database" || kind === "search" || kind === "object_storage") {
    return "#10b981";
  }
  if (kind === "cache" || kind === "queue" || kind === "worker") {
    return "#ff6b3d";
  }
  if (kind === "observability") {
    return "#0f172a";
  }
  if (kind === "external_api") {
    return "#334155";
  }
  return "#1e76ff";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function toCoordinate(clientValue: number, origin: number, renderedSize: number, viewBoxSize: number): number {
  return ((clientValue - origin) / renderedSize) * viewBoxSize;
}

export function ArchitectureGraph({
  nodes,
  edges,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
}: ArchitectureGraphProps) {
  const defaultNodes = useMemo(() => positionNodes(nodes), [nodes]);
  const defaultNodePositions = useMemo(
    () => Object.fromEntries(defaultNodes.map((node) => [node.id, { x: node.x, y: node.y }])),
    [defaultNodes],
  );
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [panState, setPanState] = useState<PanState | null>(null);
  const [view, setView] = useState<{ scale: number; translateX: number; translateY: number }>({
    scale: 1,
    translateX: 0,
    translateY: 0,
  });

  useEffect(() => {
    setNodePositions(defaultNodePositions);
    setDragState(null);
    setPanState(null);
    setView({ scale: 1, translateX: 0, translateY: 0 });
  }, [defaultNodePositions]);

  const positionedNodes = defaultNodes.map((node) => ({
    ...node,
    ...(nodePositions[node.id] ?? { x: node.x, y: node.y }),
  }));
  const nodeMap = new Map(positionedNodes.map((node) => [node.id, node]));
  const height = Math.max(360, 120 + Math.max(...positionedNodes.map((node) => node.y), 0));

  const [hoverLane, setHoverLane] = useState<(typeof lanes)[number] | null>(null);
  const [hoverEdgeId, setHoverEdgeId] = useState<string | null>(null);
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);

  function toContentCoordinate(clientX: number, clientY: number, svg: SVGSVGElement): { x: number; y: number } {
    const bounds = svg.getBoundingClientRect();
    const viewBoxX = toCoordinate(clientX, bounds.left, bounds.width, graphWidth);
    const viewBoxY = toCoordinate(clientY, bounds.top, bounds.height, height);

    return {
      x: (viewBoxX - view.translateX) / view.scale,
      y: (viewBoxY - view.translateY) / view.scale,
    };
  }

  function toViewBoxCoordinate(clientX: number, clientY: number, svg: SVGSVGElement): { x: number; y: number } {
    const bounds = svg.getBoundingClientRect();
    return {
      x: toCoordinate(clientX, bounds.left, bounds.width, graphWidth),
      y: toCoordinate(clientY, bounds.top, bounds.height, height),
    };
  }

  function updateNodePosition(nodeId: string, clientX: number, clientY: number, currentTarget: SVGGElement): void {
    const svg = currentTarget.ownerSVGElement;
    if (!svg || dragState?.nodeId !== nodeId) {
      return;
    }

    const pointer = toContentCoordinate(clientX, clientY, svg);

    setNodePositions((current) => ({
      ...current,
      [nodeId]: {
        x: clamp(pointer.x - dragState.offsetX, 24, graphWidth - nodeWidth - 24),
        y: clamp(pointer.y - dragState.offsetY, 40, 1200),
      },
    }));
  }

  function handlePointerDown(event: ReactPointerEvent<SVGGElement>, node: PositionedNode): void {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) {
      return;
    }

    onSelectNode?.(node.id);
    const pointer = toContentCoordinate(event.clientX, event.clientY, svg);

    setDragState({
      nodeId: node.id,
      pointerId: event.pointerId,
      offsetX: pointer.x - node.x,
      offsetY: pointer.y - node.y,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePanStart(event: ReactPointerEvent<SVGRectElement>): void {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) {
      return;
    }

    const start = toViewBoxCoordinate(event.clientX, event.clientY, svg);
    setPanState({
      pointerId: event.pointerId,
      startX: start.x,
      startY: start.y,
      startTranslateX: view.translateX,
      startTranslateY: view.translateY,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePanMove(event: ReactPointerEvent<SVGRectElement>): void {
    if (!panState || panState.pointerId !== event.pointerId) {
      return;
    }
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) {
      return;
    }

    const current = toViewBoxCoordinate(event.clientX, event.clientY, svg);
    const deltaX = current.x - panState.startX;
    const deltaY = current.y - panState.startY;

    setView((prev) => ({
      ...prev,
      translateX: panState.startTranslateX + deltaX,
      translateY: panState.startTranslateY + deltaY,
    }));
  }

  function handlePanEnd(event: ReactPointerEvent<SVGRectElement>): void {
    if (!panState || panState.pointerId !== event.pointerId) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setPanState(null);
  }

  function resetLayout(): void {
    setNodePositions(defaultNodePositions);
    setDragState(null);
  }

  function resetView(): void {
    setView({ scale: 1, translateX: 0, translateY: 0 });
    setPanState(null);
  }

  function handleWheel(event: ReactWheelEvent<SVGSVGElement>): void {
    const svg = event.currentTarget;
    const zoomIntensity = 0.0012;
    const nextScale = clamp(view.scale * (1 - event.deltaY * zoomIntensity), 0.55, 2.6);

    event.preventDefault();
    if (nextScale === view.scale) {
      return;
    }
    const pointer = toViewBoxCoordinate(event.clientX, event.clientY, svg);
    const contentX = (pointer.x - view.translateX) / view.scale;
    const contentY = (pointer.y - view.translateY) / view.scale;

    setView({
      scale: nextScale,
      translateX: pointer.x - contentX * nextScale,
      translateY: pointer.y - contentY * nextScale,
    });
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
      <div className="graph-toolbar">
        <button className="ghost-button" type="button" onClick={resetLayout}>
          Auto-layout
        </button>
        <button className="ghost-button ghost-button-inline" type="button" onClick={resetView}>
          Reset view
        </button>
      </div>
      <svg
        viewBox={`0 0 ${graphWidth} ${height}`}
        className="architecture-graph"
        role="img"
        aria-label="Architecture graph"
        onWheel={handleWheel}
      >
        <defs>
          <marker id="graph-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#1e76ff" />
          </marker>
        </defs>

        <rect
          className={panState ? "graph-pan-surface graph-pan-surface-panning" : "graph-pan-surface"}
          x={0}
          y={0}
          width={graphWidth}
          height={height}
          onPointerDown={handlePanStart}
          onPointerMove={handlePanMove}
          onPointerUp={handlePanEnd}
          onPointerCancel={handlePanEnd}
        />

        <g transform={`translate(${view.translateX} ${view.translateY}) scale(${view.scale})`}>
          {lanes.map((lane, index) => (
            <g key={lane}>
              {hoverLane === lane ? (
                <rect
                  x={56 + index * 246}
                  y={10}
                  width={laneWidth + laneSpacing}
                  height={height - 18}
                  rx={18}
                  className="graph-lane-highlight"
                />
              ) : null}
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
            const isSelected = selectedEdgeId === edge.id;
            const isHovered = hoverEdgeId === edge.id;
            const showLabel = isSelected || isHovered;
            const showFlow = isSelected || isHovered;

            return (
              <g key={edge.id}>
                <path
                  d={path}
                  className={
                    edge.critical_path
                      ? isSelected
                        ? "graph-edge graph-edge-critical graph-edge-selected"
                        : "graph-edge graph-edge-critical"
                      : isSelected
                        ? "graph-edge graph-edge-selected"
                        : "graph-edge"
                  }
                  markerEnd="url(#graph-arrow)"
                />
                {showFlow ? (
                  <path
                    d={path}
                    className={edge.critical_path ? "graph-edge-flow graph-edge-flow-critical" : "graph-edge-flow"}
                    markerEnd="url(#graph-arrow)"
                  />
                ) : null}
                <path
                  d={path}
                  className={isHovered ? "graph-edge-hit graph-edge-hit-hovered" : "graph-edge-hit"}
                  onPointerEnter={() => setHoverEdgeId(edge.id)}
                  onPointerLeave={() => setHoverEdgeId((current) => (current === edge.id ? null : current))}
                  onPointerDown={(event) => {
                    event.stopPropagation();
                    onSelectEdge?.(edge.id);
                  }}
                />
                <text
                  x={(startX + endX) / 2}
                  y={(startY + endY) / 2 - 8}
                  className={showLabel ? "graph-edge-label graph-edge-label-visible" : "graph-edge-label"}
                >
                  {edge.protocol}
                </text>
              </g>
            );
          })}

          {positionedNodes.map((node) => (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              className={
                dragState?.nodeId === node.id
                  ? "graph-node graph-node-dragging"
                  : selectedNodeId === node.id
                    ? "graph-node graph-node-selected"
                    : hoverNodeId === node.id
                      ? "graph-node graph-node-hovered"
                      : "graph-node"
              }
              onPointerEnter={() => {
                setHoverLane(laneForKind(node.kind));
                setHoverNodeId(node.id);
              }}
              onPointerLeave={() => {
                setHoverLane(null);
                setHoverNodeId((current) => (current === node.id ? null : current));
              }}
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
              <circle cx="126" cy="18" r="12" className="graph-node-aura" fill={nodeColor(node.kind)} />
              <circle cx="126" cy="18" r="6" fill={nodeColor(node.kind)} />
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
