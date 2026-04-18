class ScaleCraftError(Exception):
    """Base application error."""


class ProviderConfigurationError(ScaleCraftError):
    """Raised when an LLM provider is misconfigured."""


class ScriptGenerationError(ScaleCraftError):
    """Raised when a requested script target is unsupported."""
