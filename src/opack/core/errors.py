class OperatingPackError(Exception):
    """Base domain error."""


class GateBlockedError(OperatingPackError):
    """Raised when a pipeline gate is blocked by critical issues."""
