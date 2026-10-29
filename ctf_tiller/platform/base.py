"""The only platform surface the orchestrator depends on."""

from pathlib import Path
from typing import Protocol

from ctf_tiller.platform.models import (
    Attachment,
    Challenge,
    Hint,
    PlatformCapabilities,
    Submission,
    Target,
)


class Platform(Protocol):
    def capabilities(self) -> PlatformCapabilities:
        """Declare instance, hint, attachment, and concurrency support."""

    def list_challenges(self) -> list[Challenge]:
        """Return every challenge in the current task, with solve progress."""

    def get_challenge(self, challenge_id: str) -> Challenge:
        """Return one challenge. Raise if the id is not in the task."""

    def download_attachments(self, challenge_id: str, dest: Path) -> list[Attachment]:
        """Save files the platform hosts for this challenge. An empty list is valid."""

    def open_target(self, challenge_id: str) -> Target:
        """Make the challenge reachable and report its current status."""

    def target_status(self, challenge_id: str) -> Target:
        """Report whether the challenge endpoint can be used."""

    def close_target(self, challenge_id: str) -> None:
        """Release the challenge endpoint."""

    def submit_flag(self, challenge_id: str, flag: str) -> Submission:
        """Judge one flag. A wrong flag is a result, not an exception."""

    def get_hint(self, challenge_id: str) -> Hint:
        """Fetch a hint. Callers decide whether the score cost is acceptable."""
