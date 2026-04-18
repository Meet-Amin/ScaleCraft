from enum import Enum

from pydantic import Field

from app.schemas.common import ScaleCraftModel


class TrafficPattern(str, Enum):
    steady = "steady"
    spiky = "spiky"
    bursty = "bursty"
    diurnal = "diurnal"


class LoadScenarioType(str, Enum):
    generic = "generic"
    chat_app = "chat_app"
    ecommerce_flash_sale = "ecommerce_flash_sale"
    video_platform = "video_platform"
    saas_dashboard = "saas_dashboard"


class TrafficWindow(ScaleCraftModel):
    rps: int = Field(..., ge=1, le=2_000_000)
    requests_per_minute: int = Field(..., ge=1, le=120_000_000)
    description: str = Field(..., min_length=5, max_length=200)


class RequestMixItem(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    method: str = Field(..., min_length=3, max_length=10)
    path: str = Field(..., min_length=1, max_length=120)
    percentage: int = Field(..., ge=1, le=100)


class RampStage(ScaleCraftModel):
    duration_minutes: int = Field(..., ge=1, le=240)
    target_rps: int = Field(..., ge=1, le=2_000_000)
    target_concurrency: int = Field(..., ge=1, le=5_000_000)


class ConcurrencyLevels(ScaleCraftModel):
    baseline_users: int = Field(..., ge=1, le=5_000_000)
    target_users: int = Field(..., ge=1, le=5_000_000)
    peak_users: int = Field(..., ge=1, le=5_000_000)
    background_workers: int = Field(..., ge=0, le=50_000)


class SpikeProfile(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    peak_multiplier: float = Field(..., ge=1.1, le=100.0)
    duration_minutes: int = Field(..., ge=1, le=180)
    recovery_minutes: int = Field(..., ge=1, le=180)


class SpikeTraffic(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    trigger: str = Field(..., min_length=5, max_length=160)
    peak_rps: int = Field(..., ge=1, le=2_000_000)
    peak_concurrency: int = Field(..., ge=1, le=5_000_000)
    duration_minutes: int = Field(..., ge=1, le=180)
    recovery_minutes: int = Field(..., ge=1, le=180)


class UserJourneyStep(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    method: str = Field(..., min_length=3, max_length=10)
    path: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=5, max_length=200)


class UserJourney(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    persona: str = Field(..., min_length=2, max_length=80)
    percentage: int = Field(..., ge=1, le=100)
    steps: list[UserJourneyStep] = Field(default_factory=list)


class BackgroundWorkerTraffic(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    queue_name: str = Field(..., min_length=2, max_length=80)
    job_type: str = Field(..., min_length=2, max_length=80)
    steady_jobs_per_minute: int = Field(..., ge=0, le=60_000_000)
    peak_jobs_per_minute: int = Field(..., ge=0, le=60_000_000)
    trigger_sources: list[str] = Field(default_factory=list)


class LoadScenario(ScaleCraftModel):
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., min_length=10, max_length=400)
    scenario_type: LoadScenarioType = LoadScenarioType.generic
    traffic_pattern: TrafficPattern
    duration_minutes: int = Field(..., ge=5, le=24 * 60)
    steady_state_rps: int = Field(..., ge=1, le=2_000_000)
    peak_rps: int = Field(..., ge=1, le=2_000_000)
    concurrency: int = Field(..., ge=1, le=5_000_000)
    think_time_seconds: float = Field(..., ge=0.1, le=60)
    baseline_traffic: TrafficWindow = Field(
        default_factory=lambda: TrafficWindow(rps=1, requests_per_minute=60, description="Baseline traffic")
    )
    spike_traffic: SpikeTraffic | None = None
    concurrency_levels: ConcurrencyLevels = Field(
        default_factory=lambda: ConcurrencyLevels(
            baseline_users=1,
            target_users=1,
            peak_users=1,
            background_workers=0,
        )
    )
    request_mix: list[RequestMixItem] = Field(default_factory=list)
    endpoint_request_mix: list[RequestMixItem] = Field(default_factory=list)
    ramp_up: list[RampStage] = Field(default_factory=list)
    ramp_up_stages: list[RampStage] = Field(default_factory=list)
    spikes: list[SpikeProfile] = Field(default_factory=list)
    user_journeys: list[UserJourney] = Field(default_factory=list)
    background_worker_traffic: list[BackgroundWorkerTraffic] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class LoadProfileSpec(ScaleCraftModel):
    objective: str = Field(..., min_length=10, max_length=300)
    scenarios: list[LoadScenario] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    global_assumptions: list[str] = Field(default_factory=list)


class GenerateLoadProfileRequest(ScaleCraftModel):
    requirement: "StructuredRequirementSpec"


class GenerateLoadProfileResponse(ScaleCraftModel):
    load_profile: LoadProfileSpec


from app.schemas.requirement import StructuredRequirementSpec
