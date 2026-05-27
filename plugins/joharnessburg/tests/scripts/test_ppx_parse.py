"""Tests for scripts/ppx_parse.py.

Tests focus on the script's HTTP error handling vs connectivity error handling
(v0.1.9 — Codex #4: HTTPError must be caught before URLError since HTTPError
is a subclass). Uses a tiny localhost HTTP server fixture instead of mocking.
"""

import json
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tests._helpers import run_script


def _free_port() -> int:
    """Get an unused local port for the fixture server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(BaseHTTPRequestHandler):
    """Configurable HTTP handler.

    The behavior is set via class attributes before each test:
    - response_status: int
    - response_body: bytes (raw bytes to return)
    """

    response_status = 200
    response_body = b'{"success": true}'

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        self.send_response(self.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.response_body)))
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, format, *args):  # silence access log
        return


class _ServerCtx:
    """Run an HTTPServer on a free port for the duration of one test."""

    def __init__(self, status: int, body: bytes):
        self.port = _free_port()
        _Handler.response_status = status
        _Handler.response_body = body
        self.server = HTTPServer(("127.0.0.1", self.port), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class TestPpxParse(unittest.TestCase):
    def test_http_422_parsed_correctly(self):
        # v0.1.9 — Codex #4: a server-side 422 must NOT be reported as
        # "could not reach server". The structured error body should surface.
        body = json.dumps({"error": "bad input path", "detail": "fixture 422"}).encode()
        with _ServerCtx(status=422, body=body) as srv:
            with tempfile.TemporaryDirectory() as td:
                tdp = Path(td)
                pdf = tdp / "fake.pdf"
                pdf.write_bytes(b"%PDF-1.4 fake")
                out_dir = tdp / "out"

                rc, out, err_text = run_script(
                    "ppx_parse.py",
                    str(pdf), str(out_dir),
                    "--client-url", f"http://127.0.0.1:{srv.port}",
                )
                self.assertEqual(rc, 1)
                self.assertFalse(out["success"])
                # Critical assertion: the error message must reflect the
                # server-side body, NOT the "could not reach" wording.
                self.assertIn("HTTP 422", out["error"])
                self.assertIn("bad input path", out["error"])
                self.assertNotIn("Could not reach", out["error"])

    def test_connection_refused_reported_as_unreachable(self):
        # When the server is not running, the URLError path should fire
        # with the "could not reach" wording.
        port = _free_port()  # bind + release so port is free, no server listening
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            pdf = tdp / "fake.pdf"
            pdf.write_bytes(b"%PDF-1.4 fake")
            out_dir = tdp / "out"

            rc, out, _ = run_script(
                "ppx_parse.py",
                str(pdf), str(out_dir),
                "--client-url", f"http://127.0.0.1:{port}",
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("Could not reach", out["error"])

    def test_success_passes_through(self):
        # Sanity: a 200 response with success=true returns rc=0 and stdout
        # carries the server's ParseResult fields.
        body = json.dumps({
            "success": True,
            "input_path": "/x",
            "output_dir": "/y",
            "backend": "default",
            "doc_md": "/y/doc.md",
            "doc_json": "/y/doc.json",
            "metadata_json": "/y/metadata.json",
            "elapsed_seconds": 1.5,
        }).encode()
        with _ServerCtx(status=200, body=body) as srv:
            with tempfile.TemporaryDirectory() as td:
                tdp = Path(td)
                pdf = tdp / "fake.pdf"
                pdf.write_bytes(b"%PDF-1.4 fake")
                out_dir = tdp / "out"

                rc, out, _ = run_script(
                    "ppx_parse.py",
                    str(pdf), str(out_dir),
                    "--client-url", f"http://127.0.0.1:{srv.port}",
                )
                self.assertEqual(rc, 0)
                self.assertTrue(out["success"])
                self.assertEqual(out["doc_md"], "/y/doc.md")
                self.assertEqual(out["elapsed_seconds"], 1.5)


if __name__ == "__main__":
    unittest.main()
