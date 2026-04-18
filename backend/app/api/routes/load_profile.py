from fastapi import APIRouter, Depends

from app.api.dependencies import get_load_profile_generator
from app.schemas.load_profile import GenerateLoadProfileRequest, GenerateLoadProfileResponse
from app.services.load.load_profile_generator import LoadProfileGenerator

router = APIRouter(tags=["load-profile"])


@router.post("/load-profile", response_model=GenerateLoadProfileResponse)
def generate_load_profile(
    request: GenerateLoadProfileRequest,
    generator: LoadProfileGenerator = Depends(get_load_profile_generator),
) -> GenerateLoadProfileResponse:
    return GenerateLoadProfileResponse(load_profile=generator.generate(request.requirement))
