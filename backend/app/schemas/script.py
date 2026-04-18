from enum import Enum

from pydantic import Field

from app.schemas.common import ScaleCraftModel


class ScriptTarget(str, Enum):
    k6 = "k6"
    locust = "locust"


class GeneratedScript(ScaleCraftModel):
    target: ScriptTarget
    file_name: str = Field(..., min_length=3, max_length=120)
    language: str = Field(..., min_length=2, max_length=40)
    content: str = Field(..., min_length=20)
    entrypoint_command: str = Field(..., min_length=5, max_length=200)


class GenerateScriptRequest(ScaleCraftModel):
    architecture: "ArchitectureSpec"
    load_profile: "LoadProfileSpec"
    target: ScriptTarget


class GenerateScriptResponse(ScaleCraftModel):
    script: GeneratedScript


from app.schemas.architecture import ArchitectureSpec
from app.schemas.load_profile import LoadProfileSpec
