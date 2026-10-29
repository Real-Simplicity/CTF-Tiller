"""Competition platform port and the TSecBench adapter."""

from ctf_tiller.platform.base import Platform
from ctf_tiller.platform.errors import (
    AuthenticationFailed,
    CapacityExceeded,
    ChallengeNotFound,
    ContestClosed,
    HintUnavailable,
    InvalidSubmission,
    PlatformError,
    PlatformInternalError,
    RateLimited,
    TargetNotReady,
    UnsupportedOperation,
)
from ctf_tiller.platform.models import (
    Attachment,
    Challenge,
    Endpoint,
    Hint,
    PlatformCapabilities,
    Submission,
    SubmissionOutcome,
    Target,
    TargetStatus,
)
from ctf_tiller.platform.tsecbench import TSecBenchPlatform

__all__ = [
    "Attachment",
    "AuthenticationFailed",
    "CapacityExceeded",
    "Challenge",
    "ChallengeNotFound",
    "ContestClosed",
    "Endpoint",
    "Hint",
    "HintUnavailable",
    "InvalidSubmission",
    "Platform",
    "PlatformCapabilities",
    "PlatformError",
    "PlatformInternalError",
    "RateLimited",
    "Submission",
    "SubmissionOutcome",
    "TSecBenchPlatform",
    "Target",
    "TargetNotReady",
    "TargetStatus",
    "UnsupportedOperation",
]
