"""Values the orchestrator sees. Platform field names stay inside an adapter."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TargetStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"


class SubmissionOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ALREADY_ACCEPTED = "already_accepted"


@dataclass(frozen=True)
class PlatformCapabilities:
    """What an adapter can actually do. Unknown limits stay None."""

    instances: bool
    hints: bool
    attachments: bool
    max_open_targets: int | None


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    description: str | None
    difficulty: str | None
    points: int | None
    flag_count: int
    flags_correct: int
    solved: bool
    category: str | None = None
    tier: int | None = None


@dataclass(frozen=True)
class Endpoint:
    address: str


@dataclass(frozen=True)
class Target:
    challenge_id: str
    status: TargetStatus
    endpoints: tuple[Endpoint, ...]


@dataclass(frozen=True)
class Attachment:
    name: str
    path: Path


@dataclass(frozen=True)
class Hint:
    challenge_id: str
    text: str | None
    score_affected: bool


@dataclass(frozen=True)
class Submission:
    outcome: SubmissionOutcome
    awarded: int | None
    challenge_score: int | None
    flags_correct: int | None
    flag_count: int | None
    matched_flag_index: int | None
