"""Local demo server — adapted 10 Nov 2026 for GateFlat.

Stdlib only (http.server). Thin wrapper over service.handle, which
also serves the Vercel deployment — local and deployed behaviour
cannot drift apart. Run:

    python3 app/server.py            # http://127.0.0.1:8000

Allow/block lists start with the demo allowlist (see service.py).
Pass --allow 0x... to allowlist more destinations for a demo run.
"""

from __future__ import annotations

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import service  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def _handle(self, method: str) -> None:
        split = urlsplit(self.path)
        query = parse_qs(split.query)
        body = None
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length > 0 else b""
        status, content_type, payload = service.handle(
            method, split.path, query, body)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        self._handle("GET")

    def do_POST(self):  # noqa: N802
        self._handle("POST")


def main() -> None:
    parser = argparse.ArgumentParser(description="GateFlat local demo")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--allow", action="append", default=[],
                        help="allowlisted destination address (repeatable)")
    parser.add_argument("--block", action="append", default=[],
                        help="blocklisted destination address (repeatable)")
    args = parser.parse_args()
    service.ALLOWLIST.update(a.lower() for a in args.allow)
    service.BLOCKLIST.update(b.lower() for b in args.block)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GateFlat demo at http://127.0.0.1:{args.port} "
          f"(local gate; chain reads are live, nothing is sent onchain)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
