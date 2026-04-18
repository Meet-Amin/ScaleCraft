from app.core.exceptions import ScriptGenerationError
from app.schemas.architecture import ArchitectureSpec
from app.schemas.load_profile import LoadProfileSpec
from app.schemas.script import GeneratedScript, ScriptTarget
from app.services.scripts.k6_exporter import K6Exporter
from app.services.scripts.locust_exporter import LocustExporter


class ScriptGenerator:
    def __init__(self) -> None:
        self._k6_exporter = K6Exporter()
        self._locust_exporter = LocustExporter()

    def generate(
        self,
        *,
        architecture: ArchitectureSpec,
        load_profile: LoadProfileSpec,
        target: ScriptTarget,
    ) -> GeneratedScript:
        if target == ScriptTarget.k6:
            return self._k6_exporter.export(architecture, load_profile)
        if target == ScriptTarget.locust:
            return self._locust_exporter.export(architecture, load_profile)
        raise ScriptGenerationError(f"Unsupported script target: {target}")
