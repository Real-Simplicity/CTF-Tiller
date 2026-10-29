import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from ctf_tiller.platform import (
    AuthenticationFailed,
    CapacityExceeded,
    ChallengeNotFound,
    ContestClosed,
    HintUnavailable,
    InvalidSubmission,
    PlatformError,
    PlatformInternalError,
    RateLimited,
    SubmissionOutcome,
    TSecBenchPlatform,
    TargetNotReady,
    TargetStatus,
)

LIST_BODY = [
    {
        "unique_code": "web_sql_injection_01",
        "description": "通过 SQL 注入获取管理员凭证并读取 flag",
        "difficulty": "easy",
        "level": 1,
        "total_score": 100,
        "flag_count": 2,
        "correct_flag_count": 1,
        "is_completed": False,
        "container_status": "available",
        "container_addr": ["10.0.1.5:8080"],
    },
    {
        "unique_code": "crypto_rsa_02",
        "description": "RSA 参数不当导致私钥可恢复",
        "difficulty": "hard",
        "level": 3,
        "total_score": 200,
        "flag_count": 1,
        "correct_flag_count": 0,
        "is_completed": False,
        "container_status": "stopped",
        "container_addr": [],
    },
]


class _BenchServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.calls: list[dict] = []
        self.queue: list[tuple[int, object]] = []


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_GET(self) -> None:
        self._respond()

    def do_POST(self) -> None:
        self._respond()

    def _respond(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        host = self.server
        if not isinstance(host, _BenchServer):
            raise RuntimeError("handler is bound to the wrong server")
        host.calls.append(
            {
                "method": self.command,
                "path": self.path,
                "token": self.headers.get("BENCHMARK_TOKEN"),
                "content_type": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        status, payload = host.queue.pop(0)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        return


@pytest.fixture
def bench():
    server = _BenchServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    client = TSecBenchPlatform(f"http://{host}:{port}", "token-1", timeout=2)
    yield server, client
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def push(server: _BenchServer, status: int, payload: object) -> None:
    server.queue.append((status, payload))


def error(code: str, message: str) -> dict[str, object]:
    return {"code": code, "message": message, "detail": {}}


def test_capabilities_match_the_documented_bench() -> None:
    client = TSecBenchPlatform("https://bench.example.com/", "token-1")
    caps = client.capabilities()
    assert caps.instances is True
    assert caps.hints is True
    assert caps.attachments is False
    assert caps.max_open_targets == 3


def test_constructor_requires_url_and_token() -> None:
    with pytest.raises(ValueError):
        TSecBenchPlatform("  ", "token")
    with pytest.raises(ValueError):
        TSecBenchPlatform("https://bench.example.com", " ")


def test_list_maps_the_documented_payload(bench) -> None:
    server, client = bench
    push(server, 200, LIST_BODY)
    challenges = client.list_challenges()
    assert server.calls[0]["method"] == "GET"
    assert server.calls[0]["path"] == "/openapi/v1/challenges"
    assert server.calls[0]["token"] == "token-1"
    web, crypto = challenges
    assert web.challenge_id == "web_sql_injection_01"
    assert web.description.startswith("通过 SQL")
    assert web.difficulty == "easy"
    assert web.points == 100
    assert web.flag_count == 2
    assert web.flags_correct == 1
    assert web.solved is False
    assert web.category is None
    assert web.tier == 1
    assert crypto.tier == 3
    assert crypto.points == 200


def test_target_status_hides_addresses_until_ready(bench) -> None:
    server, client = bench
    pending = dict(LIST_BODY[0], container_status="pending", container_addr=["10.0.0.8:1"])
    stopping = dict(LIST_BODY[1], container_status="stop_pending")
    push(server, 200, [pending, stopping])
    push(server, 200, [pending, stopping])
    pending_target = client.target_status("web_sql_injection_01")
    stopping_target = client.target_status("crypto_rsa_02")
    assert pending_target.status is TargetStatus.PENDING
    assert pending_target.endpoints == ()
    assert stopping_target.status is TargetStatus.STOPPING
    assert stopping_target.endpoints == ()


def test_ready_target_exposes_every_address(bench) -> None:
    server, client = bench
    item = dict(LIST_BODY[0], container_addr=["10.0.1.5:8080", "10.0.1.5:8443"])
    push(server, 200, [item])
    target = client.target_status("web_sql_injection_01")
    assert target.status is TargetStatus.READY
    assert [endpoint.address for endpoint in target.endpoints] == [
        "10.0.1.5:8080",
        "10.0.1.5:8443",
    ]


def test_get_challenge_and_missing_id(bench, tmp_path: Path) -> None:
    server, client = bench
    push(server, 200, LIST_BODY)
    found = client.get_challenge("crypto_rsa_02")
    assert found.difficulty == "hard"
    push(server, 200, LIST_BODY)
    assert client.download_attachments("crypto_rsa_02", tmp_path) == []
    push(server, 200, LIST_BODY)
    with pytest.raises(ChallengeNotFound):
        client.get_challenge("missing")


def test_open_and_close_target(bench) -> None:
    server, client = bench
    push(server, 200, {"unique_code": "web_sql_injection_01", "container_addr": ["10.0.1.5:8080"]})
    opened = client.open_target("web_sql_injection_01")
    assert server.calls[0]["method"] == "POST"
    assert server.calls[0]["path"] == "/openapi/v1/challenges/start?unique_code=web_sql_injection_01"
    assert opened.status is TargetStatus.READY
    assert opened.endpoints[0].address == "10.0.1.5:8080"
    push(server, 200, {"unique_code": "web_sql_injection_01", "closed": True})
    assert client.close_target("web_sql_injection_01") is None
    assert server.calls[1]["method"] == "POST"
    assert server.calls[1]["path"] == "/openapi/v1/challenges/close?unique_code=web_sql_injection_01"


def test_open_without_address_stays_pending(bench) -> None:
    server, client = bench
    push(server, 200, {"unique_code": "web_sql_injection_01", "container_addr": []})
    opened = client.open_target("web_sql_injection_01")
    assert opened.status is TargetStatus.PENDING
    assert opened.endpoints == ()


def test_start_errors_follow_the_documented_codes(bench) -> None:
    server, client = bench
    push(server, 503, error("resource_unavailable", "靶场资源不可用"))
    with pytest.raises(TargetNotReady) as not_ready:
        client.open_target("web_sql_injection_01")
    assert not_ready.value.code == "resource_unavailable"
    push(server, 409, error("invalid_state", "当前活跃的题目实例数已达到上限，需先关闭已有题目再启动新题目"))
    with pytest.raises(CapacityExceeded):
        client.open_target("web_sql_injection_01")
    push(server, 409, error("invalid_state", "任务已结束"))
    with pytest.raises(ContestClosed):
        client.open_target("web_sql_injection_01")
    push(server, 404, error("challenge_not_found", "题目不存在"))
    with pytest.raises(ChallengeNotFound):
        client.open_target("missing")


def test_submit_accepted_rejected_and_duplicate(bench) -> None:
    server, client = bench
    push(
        server,
        200,
        {
            "correct": True,
            "awarded": 50,
            "cumulative_score": 80,
            "correct_flag_count": 2,
            "total_flag_count": 3,
            "matched_flag_index": 1,
        },
    )
    accepted = client.submit_flag("web_sql_injection_01", "flag{示例}")
    sent = json.loads(server.calls[0]["body"].decode("utf-8"))
    assert sent == {"unique_code": "web_sql_injection_01", "flag": "flag{示例}"}
    assert server.calls[0]["content_type"] == "application/json"
    assert accepted.outcome is SubmissionOutcome.ACCEPTED
    assert accepted.awarded == 50
    assert accepted.challenge_score == 80
    assert accepted.flags_correct == 2
    assert accepted.flag_count == 3
    assert accepted.matched_flag_index == 1

    push(
        server,
        200,
        {
            "correct": False,
            "awarded": 0,
            "cumulative_score": 80,
            "correct_flag_count": 2,
            "total_flag_count": 3,
            "matched_flag_index": None,
        },
    )
    rejected = client.submit_flag("web_sql_injection_01", "nope")
    assert rejected.outcome is SubmissionOutcome.REJECTED
    assert rejected.awarded == 0
    assert rejected.matched_flag_index is None

    push(server, 409, error("duplicate", "同一个 flag 被重复正确提交"))
    duplicate = client.submit_flag("web_sql_injection_01", "flag{示例}")
    assert duplicate.outcome is SubmissionOutcome.ALREADY_ACCEPTED
    assert duplicate.awarded is None


def test_submit_validation_and_task_errors(bench) -> None:
    server, client = bench
    push(
        server,
        422,
        {
            "detail": [
                {
                    "loc": ["body", "flag"],
                    "msg": "String should have at least 1 character",
                    "type": "string_too_short",
                }
            ]
        },
    )
    with pytest.raises(InvalidSubmission, match="body.flag"):
        client.submit_flag("web_sql_injection_01", "")
    push(server, 404, error("task_not_found", "token 无效"))
    with pytest.raises(AuthenticationFailed) as auth:
        client.submit_flag("web_sql_injection_01", "flag{x}")
    assert auth.value.status == 404
    push(server, 429, error("rate_limited", "慢一点"))
    with pytest.raises(RateLimited):
        client.submit_flag("web_sql_injection_01", "flag{x}")
    push(server, 500, error("internal_error", "内部错误"))
    with pytest.raises(PlatformInternalError):
        client.submit_flag("web_sql_injection_01", "flag{x}")


def test_hint_marks_the_score_cost_and_refuses_a_finished_challenge(bench) -> None:
    server, client = bench
    push(server, 200, {"unique_code": "web_sql_injection_01", "hint": "尝试在用户名字段使用单引号"})
    hint = client.get_hint("web_sql_injection_01")
    assert server.calls[0]["path"] == "/openapi/v1/challenges/hint?unique_code=web_sql_injection_01"
    assert hint.text == "尝试在用户名字段使用单引号"
    assert hint.score_affected is True
    push(server, 200, {"unique_code": "web_sql_injection_01", "hint": None})
    assert client.get_hint("web_sql_injection_01").text is None
    push(server, 409, error("invalid_state", "该题目已通关（所有 flag 均已正确提交），不允许再查看提示"))
    with pytest.raises(HintUnavailable):
        client.get_hint("web_sql_injection_01")
    push(server, 409, error("invalid_state", "任务已结束"))
    with pytest.raises(ContestClosed):
        client.get_hint("web_sql_injection_01")


def test_close_failure_and_broken_payload(bench) -> None:
    server, client = bench
    push(server, 200, {"unique_code": "web_sql_injection_01", "closed": False})
    with pytest.raises(PlatformError, match="did not close"):
        client.close_target("web_sql_injection_01")
    push(server, 200, {"not": "a list"})
    with pytest.raises(PlatformError, match="unexpected shape"):
        client.list_challenges()
