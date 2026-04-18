from fastapi import APIRouter, Depends

from app.api.dependencies import get_requirement_parser
from app.schemas.requirement import ParseRequirementRequest, ParseRequirementResponse
from app.services.parser.requirement_parser import RequirementParser

router = APIRouter(tags=["parser"])


@router.post("/parse", response_model=ParseRequirementResponse)
def parse_requirement(
    request: ParseRequirementRequest,
    parser: RequirementParser = Depends(get_requirement_parser),
) -> ParseRequirementResponse:
    return parser.parse(request)
