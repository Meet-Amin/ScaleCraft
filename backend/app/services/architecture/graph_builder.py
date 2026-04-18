import networkx as nx

from app.schemas.architecture import ArchitectureGraphEdge, ArchitectureGraphJson, ArchitectureGraphNode, ArchitectureSpec


class GraphBuilder:
    def build(self, architecture: ArchitectureSpec) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()
        for node in architecture.nodes:
            graph.add_node(
                node.id,
                id=node.id,
                label=node.name,
                kind=node.kind,
                technology=node.technology,
                description=node.description,
                responsibilities=node.responsibilities,
                scaling_notes=node.scaling_notes,
                stateful=node.stateful,
            )

        node_ids = {node.id for node in architecture.nodes}
        for index, edge in enumerate(architecture.edges, start=1):
            if edge.source not in node_ids or edge.target not in node_ids:
                raise ValueError(f"Edge references unknown node: {edge.source} -> {edge.target}")
            graph.add_edge(
                edge.source,
                edge.target,
                key=f"edge-{index}",
                id=f"edge-{index}",
                interaction=edge.interaction,
                protocol=edge.protocol,
                critical_path=edge.critical_path,
            )

        return graph

    def serialize(self, graph: nx.MultiDiGraph) -> ArchitectureGraphJson:
        nodes = [
            ArchitectureGraphNode(
                id=str(node_id),
                label=str(data.get("label", node_id)),
                kind=data["kind"],
                technology=str(data.get("technology", "unknown")),
                attributes={
                    "description": data.get("description"),
                    "responsibilities": data.get("responsibilities", []),
                    "scaling_notes": data.get("scaling_notes", []),
                    "stateful": data.get("stateful", False),
                },
            )
            for node_id, data in graph.nodes(data=True)
        ]
        edges = [
            ArchitectureGraphEdge(
                id=str(data.get("id", f"{source}-{target}-{key}")),
                source=str(source),
                target=str(target),
                interaction=str(data.get("interaction", "connects")),
                protocol=str(data.get("protocol", "unknown")),
                critical_path=bool(data.get("critical_path", False)),
            )
            for source, target, key, data in graph.edges(keys=True, data=True)
        ]
        return ArchitectureGraphJson(nodes=nodes, edges=edges)
