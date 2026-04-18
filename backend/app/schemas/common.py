from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScaleCraftModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ErrorResponse(ScaleCraftModel):
    detail: str = Field(..., description="Human-readable error message.")


class HealthResponse(ScaleCraftModel):
    status: str = "ok"
    service: str = "ScaleCraft"


JsonDict = dict[str, Any]
