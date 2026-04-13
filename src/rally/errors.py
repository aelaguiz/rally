class RallyError(RuntimeError):
    """Base exception for Rally runtime errors."""


class RallyUsageError(RallyError):
    """Raised when a CLI invocation is incomplete or unsupported."""


class RallyConfigError(RallyError):
    """Raised when authored or compiled Rally inputs are incompatible."""
