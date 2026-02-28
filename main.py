"""
Minimal Stremio "stream" add-on server.

This exposes:
  - /manifest.json
  - /stream/{type}/{id}.json

It proxies Torrentio's stream responses and (optionally) filters by seeders.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _parse_seeders(title: str) -> int:
    # Torrentio stream titles usually include "👤 <n>".
    match = re.search(r"👤\s*(\d+)", title or "")
    return int(match.group(1)) if match else 0


def _fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": os.environ.get(
                "USER_AGENT",
                "streamdl-stremio-addon/0.1 (+https://github.com/)",
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_env_int("HTTP_TIMEOUT", 10)) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def _manifest() -> dict:
    addon_id = os.environ.get("ADDON_ID", "org.streamdl.local")
    addon_version = os.environ.get("ADDON_VERSION", "0.1.0")
    addon_name = os.environ.get("ADDON_NAME", "StreamDL (local)")
    description = os.environ.get(
        "ADDON_DESCRIPTION",
        "Local Stremio stream add-on that proxies Torrentio.",
    )
    return {
        "id": addon_id,
        "version": addon_version,
        "name": addon_name,
        "description": description,
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt"],
        "catalogs": [],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "streamdl/0.1"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200) -> None:
        body = (text + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path

        if path == "/" or path == "":
            self._send_text("OK. Open /manifest.json in Stremio to install this add-on.")
            return

        if path == "/manifest.json":
            self._send_json(_manifest())
            return

        # Stremio endpoint: /stream/{type}/{id}.json
        match = re.fullmatch(r"/stream/(movie|series)/(.+)\.json", path)
        if match:
            media_type = match.group(1)
            stremio_id = match.group(2)

            torrentio_base = os.environ.get(
                "TORRENTIO_BASE", "https://torrentio.strem.fun"
            ).rstrip("/")
            upstream = f"{torrentio_base}/stream/{media_type}/{urllib.parse.quote(stremio_id)}.json"

            data = _fetch_json(upstream) or {}
            streams = data.get("streams") or []

            min_seeders = _env_int("MIN_SEEDERS", 0)
            if min_seeders > 0:
                streams = [
                    s for s in streams if _parse_seeders(s.get("title", "")) >= min_seeders
                ]

            max_streams = _env_int("MAX_STREAMS", 0)
            if max_streams > 0:
                streams = streams[:max_streams]

            self._send_json({"streams": streams})
            return

        self._send_json({"error": "not_found"}, status=404)


if __name__ == "__main__":
    load_dotenv()

    host = os.environ.get("HOST", "127.0.0.1")
    port = _env_int("PORT", 7000)

    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving Stremio add-on at http://{host}:{port}/manifest.json")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        httpd.server_close()
