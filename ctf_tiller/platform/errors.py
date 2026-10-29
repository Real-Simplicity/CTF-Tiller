"""Failures of a competition platform that are not a flag judgement."""


class PlatformError(Exception):
    """A platform call failed before it could judge a flag."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class AuthenticationFailed(PlatformError):
    """The platform rejected the task credential."""


class ChallengeNotFound(PlatformError):
    """The challenge id is not in the current task."""


class ContestClosed(PlatformError):
    """The task has expired or been stopped."""


class CapacityExceeded(PlatformError):
    """The platform will not open another target until one is closed."""


class TargetNotReady(PlatformError):
    """The target could not be made reachable."""


class InvalidSubmission(PlatformError):
    """The platform rejected the flag text itself."""


class RateLimited(PlatformError):
    """The platform refused the call because it arrived too often."""


class PlatformInternalError(PlatformError):
    """The platform failed on its side."""


class UnsupportedOperation(PlatformError):
    """This platform has no such operation."""


class HintUnavailable(PlatformError):
    """The platform will not reveal a hint for this challenge."""
