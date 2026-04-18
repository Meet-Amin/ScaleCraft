from fastapi import APIRouter, Depends

from app.api.dependencies import get_script_generator
from app.schemas.script import GenerateScriptRequest, GenerateScriptResponse
from app.services.scripts.script_generator import ScriptGenerator

router = APIRouter(tags=["generate-script"])


@router.post("/generate-script", response_model=GenerateScriptResponse)
def generate_script(
    request: GenerateScriptRequest,
    generator: ScriptGenerator = Depends(get_script_generator),
) -> GenerateScriptResponse:
    return GenerateScriptResponse(
        script=generator.generate(
            architecture=request.architecture,
            load_profile=request.load_profile,
            target=request.target,
        )
    )
