from enum import Enum

from pydantic import Field

from app.schemas.common import ScaleCraftModel


class RiskSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RiskItem(ScaleCraftModel):
    title: str = Field(..., min_length=5, max_length=120)
    severity: RiskSeverity
    category: str = Field(..., min_length=3, max_length=60)
    explanation: str = Field(..., min_length=10, max_length=500)
    recommendation: str = Field(..., min_length=10, max_length=300)
    description: str = Field(..., min_length=10, max_length=400)
    affected_components: list[str] = Field(default_factory=list)
    rationale: str = Field(..., min_length=10, max_length=400)
    recommendations: list[str] = Field(default_factory=list)


class RiskReport(ScaleCraftModel):
    summary: str = Field(..., min_length=10, max_length=500)
    top_risks: list[RiskItem] = Field(default_factory=list)
    scaling_actions: list[str] = Field(default_factory=list)
    resilience_gaps: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class AnalyzeRisksRequest(ScaleCraftModel):
    requirement: "StructuredRequirementSpec"
    architecture: "ArchitectureSpec"
    load_profile: "LoadProfileSpec"


class AnalyzeRisksResponse(ScaleCraftModel):
    report: RiskReport


from app.schemas.architecture import ArchitectureSpec
from app.schemas.load_profile import LoadProfileSpec
from app.schemas.requirement import StructuredRequirementSpec
