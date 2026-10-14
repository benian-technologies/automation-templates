#!/usr/bin/env python3
"""Loopback-only, authenticated controller for one configured collection job."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import stat

from collector import Collector, DemoTransport, PublicHTTPS, Refused


def read_token(path):
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise Refused("private_token_file_required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        actual = os.fstat(fd)
        if (actual.st_dev, actual.st_ino, actual.st_uid, stat.S_IMODE(actual.st_mode)) != (info.st_dev, info.st_ino, os.getuid(), 0o600):
            raise Refused("private_token_file_required")
        token = os.read(fd, 257).decode("ascii").strip()
    finally:
        os.close(fd)
    if not 32 <= len(token) <= 256 or not token.isalnum():
        raise Refused("invalid_controller_token")
    return token


def server(worker, token, port=8787):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PublicPageCollector"

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_):
            pass

        def reply(self, status, data):
            encoded = json.dumps(data, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def authorized(self):
            return hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token)

        def do_GET(self):
            if not self.authorized():
                return self.reply(401, {"error": "unauthorized"})
            if self.path != "/v1/status":
                return self.reply(404, {"error": "route_not_found"})
            self.reply(200, worker.summary())

        def do_POST(self):
            if not self.authorized():
                return self.reply(401, {"error": "unauthorized"})
            if self.path != "/v1/tick" or self.headers.get("Transfer-Encoding"):
                return self.reply(400, {"error": "invalid_request"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 100 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise Refused("invalid_request")
                body = json.loads(self.rfile.read(size))
                if body != {"job_id": worker.config["job_id"]}:
                    raise Refused("job_identity_mismatch")
                self.reply(200, worker.tick())
            except Refused as exc:
                self.reply(409, {"error": str(exc) if str(exc) in ("collector_busy", "job_identity_mismatch", "invalid_request") else "collector_failed"})
            except Exception:
                self.reply(500, {"error": "controller_failed"})
    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    try:
        token = read_token(args.token_file)
        worker = Collector(json.loads(Path(args.config).read_text()), args.state, PublicHTTPS() if args.live else DemoTransport())
        httpd = server(worker, token, args.port)
        print(json.dumps({"ready": True, "host": "127.0.0.1", "port": httpd.server_port, "mode": "live" if args.live else "offline_demo"}), flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            worker.close()
    except (Refused, ValueError, OSError):
        raise SystemExit("controller_start_refused") from None


if __name__ == "__main__":
    main()
