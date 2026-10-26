"""Safe client/parser errors that never retain raw input or secrets."""


class PsegError(Exception):
    """Base utility client error."""


class SessionExpired(PsegError):
    """The portal requires authentication."""


class CannotConnect(PsegError):
    """The portal could not be reached."""


class InvalidResponse(PsegError):
    """The portal returned an unsupported response."""


class MeterNotFound(PsegError):
    """The requested meter is unavailable."""


class InvalidUsage(ValueError):
    """A controlled translation key describing invalid CSV data."""

    def __init__(self, translation_key: str) -> None:
        """Initialize without retaining raw data."""
        super().__init__(translation_key)
        self.translation_key = translation_key
