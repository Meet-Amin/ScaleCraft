"""Traffic and load-profile schemas for ScaleCraft.

This module exists so the scaffold has a dedicated traffic schema entrypoint,
while the existing load-profile route and services keep their current imports.
"""

from app.schemas.load_profile import GenerateLoadProfileRequest
from app.schemas.load_profile import GenerateLoadProfileResponse
from app.schemas.load_profile import BackgroundWorkerTraffic
from app.schemas.load_profile import ConcurrencyLevels
from app.schemas.load_profile import LoadProfileSpec
from app.schemas.load_profile import LoadScenario
from app.schemas.load_profile import LoadScenarioType
from app.schemas.load_profile import RampStage
from app.schemas.load_profile import RequestMixItem
from app.schemas.load_profile import SpikeProfile
from app.schemas.load_profile import SpikeTraffic
from app.schemas.load_profile import TrafficWindow
from app.schemas.load_profile import TrafficPattern
from app.schemas.load_profile import UserJourney
from app.schemas.load_profile import UserJourneyStep

__all__ = [
    "TrafficPattern",
    "LoadScenarioType",
    "TrafficWindow",
    "RequestMixItem",
    "RampStage",
    "ConcurrencyLevels",
    "SpikeProfile",
    "SpikeTraffic",
    "UserJourneyStep",
    "UserJourney",
    "BackgroundWorkerTraffic",
    "LoadScenario",
    "LoadProfileSpec",
    "GenerateLoadProfileRequest",
    "GenerateLoadProfileResponse",
]
