from fastapi import APIRouter, Depends

from app.api.dependencies import get_architecture_generator
from app.schemas.architecture import GenerateArchitectureRequest, GenerateArchitectureResponse
from app.services.architecture.architecture_generator import ArchitectureGenerator

router = APIRouter(tags=["architecture"])


@router.post("/architecture", response_model=GenerateArchitectureResponse)
def generate_architecture(
    request: GenerateArchitectureRequest,
    generator: ArchitectureGenerator = Depends(get_architecture_generator),
) -> GenerateArchitectureResponse:
    return GenerateArchitectureResponse(architecture=generator.generate(request.requirement))
