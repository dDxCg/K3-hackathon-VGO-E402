"""HTTP server tối giản phục vụ ``prototype.html`` và API chat thật."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.demo_service import DemoService, reply_dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = PROJECT_ROOT / "prototype.html"
MAX_BODY_BYTES = 64 * 1024


class DemoHandler(BaseHTTPRequestHandler):
    service: DemoService

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/prototype.html"}:
            self._file(PROTOTYPE)
            return
        if path == "/api/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Không tìm thấy endpoint"})

    def _payload(self) -> dict:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Content-Length không hợp lệ") from exc
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError("Request body rỗng hoặc quá lớn")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body phải là JSON hợp lệ") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body phải là JSON object")
        return payload

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._payload()
            session_id = str(payload.get("session_id", "")).strip()
            if not session_id or len(session_id) > 128:
                raise ValueError("session_id không hợp lệ")

            if path == "/api/chat":
                message = str(payload.get("message", "")).strip()
                if not message or len(message) > 2000:
                    raise ValueError("message rỗng hoặc quá 2000 ký tự")
                self._json(HTTPStatus.OK, reply_dict(self.service.chat(session_id, message)))
                return
            if path == "/api/reset":
                self.service.reset(session_id)
                self._json(HTTPStatus.OK, {"status": "ok"})
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "Không tìm thấy endpoint"})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self.log_error("API error: %s: %s", type(exc).__name__, exc)
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Chatbot đang gặp lỗi tạm thời. Vui lòng thử lại."},
            )

    def log_message(self, format: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def make_server(host: str = "127.0.0.1", port: int = 8000, service: DemoService | None = None):
    handler = type("ConfiguredDemoHandler", (DemoHandler,), {"service": service or DemoService()})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy web demo chatbot tuyển sinh")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(f"Demo: http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
