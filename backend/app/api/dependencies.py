from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.architecture.architecture_generator import ArchitectureGenerator
from app.services.load.load_profile_generator import LoadProfileGenerator
from app.services.llm.factory import build_llm_provider
from app.services.parser.requirement_parser import RequirementParser
from app.services.risks.risk_analyzer import RiskAnalyzer
from app.services.scripts.script_generator import ScriptGenerator


def get_app_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def get_requirement_parser() -> RequirementParser:
    return RequirementParser(llm_provider=build_llm_provider(get_settings()))


@lru_cache(maxsize=1)
def get_architecture_generator() -> ArchitectureGenerator:
    return ArchitectureGenerator()


@lru_cache(maxsize=1)
def get_load_profile_generator() -> LoadProfileGenerator:
    return LoadProfileGenerator()


@lru_cache(maxsize=1)
def get_script_generator() -> ScriptGenerator:
    return ScriptGenerator()


@lru_cache(maxsize=1)
def get_risk_analyzer() -> RiskAnalyzer:
    return RiskAnalyzer()
