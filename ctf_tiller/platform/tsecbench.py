"""TSec Benchmark Platform adapter.

`base_url` is the platform origin, for example ``https://bench.example.com``.
Requests go to ``/openapi/v1/challenges``. The task token is sent as the
``BENCHMARK_TOKEN`` header. Reaching a target still requires the bench VPN;
this adapter only returns the address.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NoReturn

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

_API = "/openapi/v1/challenges"
_CAPABILITIES = PlatformCapabilities(
    instances=True,
    hints=True,
    attachments=False,
    max_open_targets=3,
)
_STATUS = {
    "pending": TargetStatus.PENDING,
    "available": TargetStatus.READY,
    "stop_pending": TargetStatus.STOPPING,
    "stopped": TargetStatus.STOPPED,
}


class TSecBenchPlatform:
    def __init__(self, base_url: str, token: str, *, timeout: float = 30) -> None:
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not token.strip():
            raise ValueError("token is required")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def capabilities(self) -> PlatformCapabilities:
        return _CAPABILITIES

    def list_challenges(self) -> list[Challenge]:
        payload = self._request("list", "GET", _API)
        return [self._challenge(item) for item in self._items(payload)]

    def get_challenge(self, challenge_id: str) -> Challenge:
        for challenge in self.list_challenges():
            if challenge.challenge_id == challenge_id:
                return challenge
        raise ChallengeNotFound(f"challenge not found: {challenge_id}")

    def download_attachments(self, challenge_id: str, dest: Path) -> list[Attachment]:
        del dest
        self.get_challenge(challenge_id)
        return []

    def open_target(self, challenge_id: str) -> Target:
        payload = self._request(
            "start",
            "POST",
            f"{_API}/start",
            query={"unique_code": challenge_id},
        )
        addresses = self._addresses(self._object(payload))
        status = TargetStatus.READY if addresses else TargetStatus.PENDING
        return self._target(challenge_id, status, addresses)

    def target_status(self, challenge_id: str) -> Target:
        payload = self._request("list", "GET", _API)
        for item in self._items(payload):
            if self._text(item, "unique_code") == challenge_id:
                return self._target_from_item(item)
        raise ChallengeNotFound(f"challenge not found: {challenge_id}")

    def close_target(self, challenge_id: str) -> None:
        payload = self._request(
            "close",
            "POST",
            f"{_API}/close",
            query={"unique_code": challenge_id},
        )
        body = self._object(payload)
        closed = body.get("closed")
        if closed is not True:
            raise PlatformError("platform did not close the target", status=200)

    def submit_flag(self, challenge_id: str, flag: str) -> Submission:
        status, payload = self._exchange(
            "POST",
            f"{_API}/submit",
            body={"unique_code": challenge_id, "flag": flag},
        )
        if status == 200:
            return self._submission(payload)
        if isinstance(payload, dict) and payload.get("code") == "duplicate":
            return Submission(
                outcome=SubmissionOutcome.ALREADY_ACCEPTED,
                awarded=None,
                challenge_score=None,
                flags_correct=None,
                flag_count=None,
                matched_flag_index=None,
            )
        self._raise("submit", status, payload)

    def get_hint(self, challenge_id: str) -> Hint:
        payload = self._request(
            "hint",
            "GET",
            f"{_API}/hint",
            query={"unique_code": challenge_id},
        )
        body = self._object(payload)
        text = body.get("hint")
        if text is not None and not isinstance(text, str):
            raise PlatformError("response field hint has an unexpected type")
        return Hint(challenge_id=challenge_id, text=text, score_affected=True)

    def _request(self, operation: str, method: str, path: str, **kwargs: Any) -> Any:
        status, payload = self._exchange(method, path, **kwargs)
        if status == 200:
            return payload
        self._raise(operation, status, payload)

    def _exchange(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        url = self._base_url + path
        if query:
            url = url + "?" + urllib.parse.urlencode(query)
        data = None
        headers = {"BENCHMARK_TOKEN": self._token, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return response.status, self._decode(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, self._decode(exc.read())
        except TimeoutError as exc:
            raise PlatformError("platform request timed out") from exc
        except urllib.error.URLError as exc:
            raise PlatformError(f"platform request failed: {exc.reason}") from exc

    def _raise(self, operation: str, status: int, payload: Any) -> NoReturn:
        code = payload.get("code") if isinstance(payload, dict) else None
        code_text = code if isinstance(code, str) else None
        message = _message(payload, status)
        if code_text == "task_not_found" or status == 401:
            raise AuthenticationFailed(message, code=code_text, status=status)
        if code_text == "challenge_not_found":
            raise ChallengeNotFound(message, code=code_text, status=status)
        if code_text == "resource_unavailable" or status == 503:
            raise TargetNotReady(message, code=code_text, status=status)
        if code_text == "invalid_state":
            raise _invalid_state(operation, message)
        if status == 422:
            raise InvalidSubmission(_validation_message(payload), code=code_text, status=status)
        if status == 429 or code_text == "rate_limited":
            raise RateLimited(message, code=code_text, status=status)
        if code_text == "internal_error" or status >= 500:
            raise PlatformInternalError(message, code=code_text, status=status)
        raise PlatformError(message, code=code_text, status=status)

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise PlatformError("challenge list has an unexpected shape")
        items: list[dict[str, Any]] = []
        for item in payload:
            items.append(self._object(item))
        return items

    def _challenge(self, item: dict[str, Any]) -> Challenge:
        description = item.get("description")
        if description is not None and not isinstance(description, str):
            raise PlatformError("response field description has an unexpected type")
        return Challenge(
            challenge_id=self._text(item, "unique_code"),
            description=description,
            difficulty=self._text(item, "difficulty"),
            points=self._whole(item, "total_score"),
            flag_count=self._whole(item, "flag_count"),
            flags_correct=self._whole(item, "correct_flag_count"),
            solved=self._flag(item, "is_completed"),
            category=None,
            tier=self._whole(item, "level"),
        )

    def _target_from_item(self, item: dict[str, Any]) -> Target:
        status = _STATUS.get(self._text(item, "container_status"))
        if status is None:
            raise PlatformError("response field container_status has an unexpected value")
        return self._target(self._text(item, "unique_code"), status, self._addresses(item))

    def _target(
        self,
        challenge_id: str,
        status: TargetStatus,
        addresses: tuple[str, ...],
    ) -> Target:
        visible = addresses if status is TargetStatus.READY else ()
        return Target(
            challenge_id=challenge_id,
            status=status,
            endpoints=tuple(Endpoint(address) for address in visible),
        )

    def _submission(self, payload: Any) -> Submission:
        body = self._object(payload)
        correct = self._flag(body, "correct")
        matched = body.get("matched_flag_index")
        if correct:
            if not isinstance(matched, int) or isinstance(matched, bool):
                raise PlatformError("accepted submit is missing matched_flag_index")
            outcome = SubmissionOutcome.ACCEPTED
        else:
            if matched is not None:
                raise PlatformError("rejected submit included matched_flag_index")
            outcome = SubmissionOutcome.REJECTED
        return Submission(
            outcome=outcome,
            awarded=self._whole(body, "awarded"),
            challenge_score=self._whole(body, "cumulative_score"),
            flags_correct=self._whole(body, "correct_flag_count"),
            flag_count=self._whole(body, "total_flag_count"),
            matched_flag_index=matched if correct else None,
        )

    def _addresses(self, payload: dict[str, Any]) -> tuple[str, ...]:
        raw = payload.get("container_addr")
        if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
            raise PlatformError("response field container_addr has an unexpected type")
        return tuple(raw)

    def _object(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PlatformError("response has an unexpected shape")
        return payload

    def _text(self, payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise PlatformError(f"response field {key} has an unexpected type")
        return value

    def _whole(self, payload: dict[str, Any], key: str) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise PlatformError(f"response field {key} has an unexpected type")
        return value

    def _flag(self, payload: dict[str, Any], key: str) -> bool:
        value = payload.get(key)
        if not isinstance(value, bool):
            raise PlatformError(f"response field {key} has an unexpected type")
        return value

    @staticmethod
    def _decode(raw: bytes) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlatformError("platform returned a body that is not JSON") from exc


def _message(payload: Any, status: int) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
    return f"HTTP {status}"


def _validation_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "request failed validation"
    detail = payload.get("detail")
    if not isinstance(detail, list):
        return "request failed validation"
    parts: list[str] = []
    for item in detail:
        if not isinstance(item, dict):
            continue
        loc = item.get("loc")
        place = ".".join(str(piece) for piece in loc) if isinstance(loc, list) else ""
        msg = item.get("msg")
        text = msg if isinstance(msg, str) else ""
        parts.append(f"{place}: {text}" if place else text)
    return "; ".join(part for part in parts if part) or "request failed validation"


def _invalid_state(operation: str, message: str) -> PlatformError:
    """TSecBench reuses invalid_state for three different failures.

    The code alone cannot tell them apart. The documented messages can:
    a full task is "任务已结束", too many live targets mentions "上限",
    and a hint on a finished challenge mentions "通关" or "提示".
    """
    lowered = message.lower()
    if operation == "start" and ("上限" in message or "capacity" in lowered):
        return CapacityExceeded(message, code="invalid_state", status=409)
    if operation == "hint" and ("通关" in message or "提示" in message or "completed" in lowered):
        return HintUnavailable(message, code="invalid_state", status=409)
    return ContestClosed(message, code="invalid_state", status=409)
