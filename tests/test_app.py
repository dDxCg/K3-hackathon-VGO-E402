import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.app import make_server
from src.demo_service import DemoReply


class StubService:
    def __init__(self):
        self.reset_ids = []

    def chat(self, session_id, message):
        return DemoReply(
            answer=f"Đã nhận: {message}",
            sources=[],
            suggestions=[],
            grounded=True,
            top_score=0.9,
            path="test",
        )

    def reset(self, session_id):
        self.reset_ids.append(session_id)


def _request(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        base + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urlopen(request, timeout=3) as response:
        return response.status, response.read(), response.headers


def test_http_health_page_chat_and_reset():
    service = StubService()
    server = make_server(port=0, service=service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, body, _ = _request(base, "/api/health")
        assert status == 200 and json.loads(body) == {"status": "ok"}

        status, body, headers = _request(base, "/")
        assert status == 200
        assert "text/html" in headers["Content-Type"]
        assert b"/api/chat" in body

        status, body, _ = _request(
            base, "/api/chat", {"session_id": "demo", "message": "Xin chào"}
        )
        payload = json.loads(body)
        assert status == 200
        assert payload["answer"] == "Đã nhận: Xin chào"

        status, body, _ = _request(base, "/api/reset", {"session_id": "demo"})
        assert status == 200
        assert service.reset_ids == ["demo"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_http_rejects_empty_message():
    server = make_server(port=0, service=StubService())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        try:
            _request(base, "/api/chat", {"session_id": "demo", "message": ""})
        except HTTPError as exc:
            assert exc.code == 400
            assert "message" in json.loads(exc.read())["error"]
        else:
            raise AssertionError("API phải từ chối message rỗng")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
