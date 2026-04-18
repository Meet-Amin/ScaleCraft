from app.schemas.requirement import (
    FunctionalRequirement,
    NonFunctionalRequirement,
    RequirementPriority,
    StructuredRequirementSpec,
    TrafficExpectation,
)
from app.services.architecture.architecture_generator import ArchitectureGenerator


def test_architecture_generator_adds_scaling_components() -> None:
    requirement = StructuredRequirementSpec(
        product_name="Global Shop",
        summary="Users search a catalog, checkout, upload media, and receive email notifications.",
        client_surfaces=["web"],
        functional_requirements=[
            FunctionalRequirement(
                name="Search catalog",
                description="Users can search and browse a large product catalog.",
                priority=RequirementPriority.high,
            ),
            FunctionalRequirement(
                name="Checkout orders",
                description="Users can checkout orders and receive notifications.",
                priority=RequirementPriority.critical,
            ),
            FunctionalRequirement(
                name="Upload assets",
                description="Users can upload product images and documents.",
                priority=RequirementPriority.medium,
            ),
        ],
        non_functional_requirements=[
            NonFunctionalRequirement(
                category="security",
                description="Protect privileged user workflows.",
                priority=RequirementPriority.high,
            )
        ],
        integrations=["Stripe"],
        traffic=TrafficExpectation(baseline_rps=300, peak_rps=2000, peak_concurrency=5000),
    )

    architecture = ArchitectureGenerator().generate(requirement)
    node_ids = {node.id for node in architecture.nodes}

    assert "redis" in node_ids
    assert "queue" in node_ids
    assert "worker" in node_ids
    assert "search" in node_ids
    assert "object-storage" in node_ids
    assert "auth-service" in node_ids
    assert "observability-stack" in node_ids
    assert any(edge.source == "api-service" and edge.target == "postgres" for edge in architecture.edges)
    assert architecture.services
    assert architecture.databases
    assert architecture.cache
    assert architecture.queues
    assert architecture.storage
    assert architecture.observability
    assert architecture.scaling_strategy
    assert architecture.failover_strategy
    assert architecture.graph_json.nodes
    assert architecture.graph_json.edges
    assert "Global Shop" in architecture.explanation


def test_architecture_generator_preserves_parallel_edges_in_graph_json() -> None:
    requirement = StructuredRequirementSpec(
        product_name="Search Portal",
        summary="Users search a catalog and browse results at moderate traffic.",
        client_surfaces=["web"],
        functional_requirements=[
            FunctionalRequirement(
                name="Search catalog",
                description="Users can search and filter a large catalog.",
                priority=RequirementPriority.high,
            )
        ],
        traffic=TrafficExpectation(baseline_rps=100, peak_rps=250, peak_concurrency=600),
    )

    architecture = ArchitectureGenerator().generate(requirement)
    search_edges = [
        edge for edge in architecture.graph_json.edges if edge.source == "api-service" and edge.target == "search"
    ]

    assert architecture.graph_json.multigraph is True
    assert len(search_edges) == 2
    assert {edge.interaction for edge in search_edges} == {"Executes search queries", "Updates search index"}
