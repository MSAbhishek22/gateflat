"""Vercel entrypoint for GateFlat — NEW code, written 10 Nov 2026.

WSGI app. Delegates every request to app/service.handle, the same
handler the local demo server uses. Read-only app: no /tmp store, no
writes; receipts and the USDG demo ledger live in process memory.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import service  # noqa: E402


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/") or "/"
    query_string = environ.get("QUERY_STRING", "")
    query = {}
    if query_string:
        from urllib.parse import parse_qs

        query = parse_qs(query_string)
    body = None
    if method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        body = environ["wsgi.input"].read(length) if length > 0 else b""
    status, content_type, payload = service.handle(method, path, query, body)
    start_response(f"{status} OK", [
        ("Content-Type", content_type),
        ("Content-Length", str(len(payload))),
    ])
    return [payload]
