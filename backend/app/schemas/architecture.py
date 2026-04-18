from enum import Enum

from pydantic import Field, field_validator

from app.schemas.common import JsonDict, ScaleCraftModel


class ComponentKind(str, Enum):
    load_balancer = "load_balancer"
    service = "service"
    worker = "worker"
    database = "database"
    cache = "cache"
    queue = "queue"
    object_storage = "object_storage"
    cdn = "cdn"
    search = "search"
    external_api = "external_api"
    observability = "observability"


class ArchitectureNode(ScaleCraftModel):
    id: str = Field(..., min_length=2, max_length=60)
    name: str = Field(..., min_length=2, max_length=120)
    kind: ComponentKind
    technology: str = Field(..., min_length=2, max_length=120)
    description: str = Field(..., min_length=5, max_length=400)
    responsibilities: list[str] = Field(default_factory=list)
    scaling_notes: list[str] = Field(default_factory=list)
    stateful: bool = False


class ArchitectureEdge(ScaleCraftModel):
    source: str = Field(..., min_length=2, max_length=60)
    target: str = Field(..., min_length=2, max_length=60)
    interaction: str = Field(..., min_length=3, max_length=120)
    protocol: str = Field(..., min_length=2, max_length=40)
    critical_path: bool = False


class ArchitectureGraphNode(ScaleCraftModel):
    id: str = Field(..., min_length=2, max_length=60)
    label: str = Field(..., min_length=2, max_length=120)
    kind: ComponentKind
    technology: str = Field(..., min_length=2, max_length=120)
    attributes: JsonDict = Field(default_factory=dict)


class ArchitectureGraphEdge(ScaleCraftModel):
    id: str = Field(..., min_length=3, max_length=120)
    source: str = Field(..., min_length=2, max_length=60)
    target: str = Field(..., min_length=2, max_length=60)
    interaction: str = Field(..., min_length=3, max_length=120)
    protocol: str = Field(..., min_length=2, max_length=40)
    critical_path: bool = False


class ArchitectureGraphJson(ScaleCraftModel):
    directed: bool = True
    multigraph: bool = True
    nodes: list[ArchitectureGraphNode] = Field(default_factory=list)
    edges: list[ArchitectureGraphEdge] = Field(default_factory=list)


class ArchitectureSpec(ScaleCraftModel):
    overview: str = Field(..., min_length=10, max_length=800)
    nodes: list[ArchitectureNode] = Field(default_factory=list)
    edges: list[ArchitectureEdge] = Field(default_factory=list)
    services: list[ArchitectureNode] = Field(default_factory=list)
    databases: list[ArchitectureNode] = Field(default_factory=list)
    cache: list[ArchitectureNode] = Field(default_factory=list)
    queues: list[ArchitectureNode] = Field(default_factory=list)
    storage: list[ArchitectureNode] = Field(default_factory=list)
    observability: list[ArchitectureNode] = Field(default_factory=list)
    availability_strategy: list[str] = Field(default_factory=list)
    scaling_strategy: list[str] = Field(default_factory=list)
    failover_strategy: list[str] = Field(default_factory=list)
    data_strategy: list[str] = Field(default_factory=list)
    scaling_notes: list[str] = Field(default_factory=list)
    graph_json: ArchitectureGraphJson = Field(default_factory=ArchitectureGraphJson)
    explanation: str = Field(default="", max_length=2_000)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("nodes")
    @classmethod
    def unique_node_ids(cls, value: list[ArchitectureNode]) -> list[ArchitectureNode]:
        identifiers = [node.id for node in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Architecture node IDs must be unique")
        return value


class GenerateArchitectureRequest(ScaleCraftModel):
    requirement: "StructuredRequirementSpec"


class GenerateArchitectureResponse(ScaleCraftModel):
    architecture: ArchitectureSpec


from app.schemas.requirement import StructuredRequirementSpec
