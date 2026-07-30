import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.app import PROTOTYPE, UI_ROOT, make_server
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
        assert b"/api/reset" in body
        assert b"../ui-vinuni" not in body
        assert b"mucLon:s.muc_lon" not in body
        assert b"warning:s.warning" not in body
        assert b"rich.textContent = partial" in body
        assert b"rich.innerHTML = mdToHtml(partial)" not in body
        assert b"if(isTableRow(ln)){" in body
        assert b"Failsafe: m" in body
        assert b'/wp-content/themes/assets/images/vinuni_banner.webp' in body
        assert b'/wp-content/themes/assets/images/footer_mb_cropped.webp' in body
        assert b'/wp-content/themes/assets/images/mascot.svg' in body
        assert (
            b'/wp-content/upload-2026/622514644_1324492253057030_4972566718972446318_n-600x600.webp'
            in body
        )
        actions_position = body.index(b"bubble.appendChild(holder.firstElementChild)")
        sources_position = body.index(
            b"bubble.insertAdjacentHTML('beforeend', sourcesHtml(opts.sources))"
        )
        assert actions_position < sources_position

        status, alias_body, _ = _request(base, "/ui/prototype.html")
        assert status == 200
        assert alias_body == body

        status, asset_body, asset_headers = _request(
            base, "/wp-content/themes/assets/images/mascot.svg"
        )
        assert status == 200
        assert "image/svg+xml" in asset_headers["Content-Type"]
        assert b"<svg" in asset_body

        status, alias_asset_body, _ = _request(
            base, "/ui/wp-content/themes/assets/images/mascot.svg"
        )
        assert status == 200
        assert alias_asset_body == asset_body

        for path in (
            "/wp-content/themes/assets/images/vinuni_banner.webp",
            "/wp-content/themes/assets/images/footer_mb_cropped.webp",
            "/wp-content/upload-2026/622514644_1324492253057030_4972566718972446318_n-600x600.webp",
        ):
            status, image_body, image_headers = _request(base, path)
            assert status == 200
            assert "image/webp" in image_headers["Content-Type"]
            assert image_body

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


def test_ui_path_and_static_route_are_confined_to_ui_folder():
    assert PROTOTYPE == UI_ROOT / "prototype.html"
    assert PROTOTYPE.is_file()
    assert not (UI_ROOT.parent / "prototype.html").exists()

    server = make_server(port=0, service=StubService())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        try:
            _request(base, "/..%2FREADME.md")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("Static route không được đọc file ngoài ui/")
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
