from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.architecture.architecture_generator import ArchitectureGenerator
from app.services.llm.factory import build_llm_provider
from app.services.parser.requirement_parser import RequirementParser


def get_app_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def get_requirement_parser() -> RequirementParser:
    return RequirementParser(llm_provider=build_llm_provider(get_settings()))


@lru_cache(maxsize=1)
def get_architecture_generator() -> ArchitectureGenerator:
    return ArchitectureGenerator()
