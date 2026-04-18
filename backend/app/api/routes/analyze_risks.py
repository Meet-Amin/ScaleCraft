from fastapi import APIRouter, Depends

from app.api.dependencies import get_risk_analyzer
from app.schemas.risk import AnalyzeRisksRequest, AnalyzeRisksResponse
from app.services.risks.risk_analyzer import RiskAnalyzer

router = APIRouter(tags=["analyze-risks"])


@router.post("/analyze-risks", response_model=AnalyzeRisksResponse)
def analyze_risks(
    request: AnalyzeRisksRequest,
    analyzer: RiskAnalyzer = Depends(get_risk_analyzer),
) -> AnalyzeRisksResponse:
    return AnalyzeRisksResponse(
        report=analyzer.analyze(
            requirement=request.requirement,
            architecture=request.architecture,
            load_profile=request.load_profile,
        )
    )
