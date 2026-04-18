from enum import Enum

from pydantic import Field, field_validator

from app.schemas.common import ScaleCraftModel


class ProductDomain(str, Enum):
    ecommerce = "ecommerce"
    saas = "saas"
    social = "social"
    fintech = "fintech"
    media = "media"
    logistics = "logistics"
    healthcare = "healthcare"
    ai_platform = "ai_platform"
    generic = "generic"


class RequirementPriority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ParserMode(str, Enum):
    llm = "llm"
    heuristic = "heuristic"


class FunctionalRequirement(ScaleCraftModel):
    name: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=5, max_length=400)
    priority: RequirementPriority = RequirementPriority.medium


class NonFunctionalRequirement(ScaleCraftModel):
    category: str = Field(..., min_length=2, max_length=60)
    description: str = Field(..., min_length=5, max_length=300)
    priority: RequirementPriority = RequirementPriority.medium


class TrafficExpectation(ScaleCraftModel):
    baseline_rps: int = Field(50, ge=1, le=1_000_000)
    peak_rps: int = Field(150, ge=1, le=2_000_000)
    peak_concurrency: int = Field(200, ge=1, le=5_000_000)
    daily_active_users: int | None = Field(default=None, ge=1)
    regions: list[str] = Field(default_factory=lambda: ["us-east-1"])


class StructuredRequirementSpec(ScaleCraftModel):
    product_name: str = Field(..., min_length=2, max_length=120)
    summary: str = Field(..., min_length=10, max_length=1200)
    domain: ProductDomain = ProductDomain.generic
    client_surfaces: list[str] = Field(default_factory=lambda: ["web"])
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    data_entities: list[str] = Field(default_factory=list)
    traffic: TrafficExpectation = Field(default_factory=TrafficExpectation)
    availability_target: str = Field("99.9%", min_length=3, max_length=20)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("client_surfaces")
    @classmethod
    def validate_surfaces(cls, value: list[str]) -> list[str]:
        return sorted({item.strip().lower() for item in value if item.strip()}) or ["web"]

    @field_validator("integrations", "data_entities", "assumptions")
    @classmethod
    def deduplicate_strings(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for item in value:
            normalized = item.strip()
            if normalized and normalized not in seen:
                seen.append(normalized)
        return seen


class ParseRequirementRequest(ScaleCraftModel):
    requirement_text: str = Field(..., min_length=20, max_length=10_000)


class ParseRequirementResponse(ScaleCraftModel):
    parser_mode: ParserMode
    requirement: StructuredRequirementSpec
