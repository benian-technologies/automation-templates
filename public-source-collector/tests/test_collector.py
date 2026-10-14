import copy
import json
import multiprocessing
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from collector import Collector, DemoTransport, PublicHTTPS, Refused, Robots, normalize, validate_config
from serve import read_token

ROOT = Path(__file__).resolve().parents[1]


def config():
    return json.loads((ROOT / "examples/config.demo.json").read_text())


class Clock:
    def __init__(self):
        self.value = 1000000.0
    def __call__(self):
        return self.value
    def advance(self, seconds=3):
        self.value += seconds


class Fake:
    def __init__(self, pages):
        self.pages, self.calls = pages, []
    def get(self, url, *_):
        self.calls.append(url)
        response = self.pages[url]
        if isinstance(response, list):
            response = response.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


HTML = lambda body: (200, {"content-type": "text/html"}, body.encode())
ROBOTS = (200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /guides/private")
HOME = "https://docs.example.com/guides"
ROBOTS_URL = "https://docs.example.com/robots.txt"


def slow_child(pipe, *_):
    time.sleep(10)
    pipe.close()


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / "state.sqlite"
        self.clock = Clock()
        self.workers = []
    def tearDown(self):
        for w in self.workers:
            w.close()
        self.temp.cleanup()
    def worker(self, transport=None, c=None):
        w = Collector(c or config(), self.state, transport or DemoTransport(), self.clock)
        self.workers.append(w)
        return w
    def finish(self, w):
        for _ in range(40):
            r = w.tick()
            if not r["continue"]:
                return r
            self.clock.advance(max(r["wait_seconds"], 3))
        self.fail("not bounded")

    def test_demo_full_continuation_dedup_and_restart(self):
        w = self.worker()
        self.assertTrue(w.tick()["continue"])
        w.close(); self.workers.remove(w)
        w = self.worker()
        receipt = self.finish(w)
        self.assertEqual((receipt["state"], receipt["pages"], receipt["unique_documents"]), ("complete", 3, 2))
        self.assertEqual(receipt["frontier"], {"blocked": 1, "done": 3})
        self.assertEqual(receipt["requests"], 4)
        self.assertEqual(w.tick()["requests"], 4)
        receipts = w.db.execute("SELECT count(*) FROM receipts").fetchone()[0]
        for _ in range(30):
            w.tick()
        self.assertEqual(w.db.execute("SELECT count(*) FROM receipts").fetchone()[0], receipts)
        self.assertEqual(w.db.execute("SELECT count(*) FROM documents WHERE text='' AND duplicate_of IS NOT NULL").fetchone()[0], 1)

    def test_discovery_replay_scope_and_changed_identity(self):
        w = self.worker()
        data = json.loads((ROOT / "examples/discovery.demo.json").read_text())
        self.assertEqual(w.discover(data), {"replay": False, "accepted": 2, "rejected": 1})
        self.assertTrue(w.discover(data)["replay"])
        self.assertEqual(w.db.execute("SELECT count(*) FROM frontier").fetchone()[0], 2)
        data["items"].append({"url": HOME + "/new"})
        with self.assertRaisesRegex(Refused, "discovery_identity_changed"):
            w.discover(data)
        data["status"] = "RUNNING"
        with self.assertRaises(Refused):
            w.discover(data)

    def test_config_and_mode_binding(self):
        self.worker()
        changed = config(); changed["limits"]["max_requests"] += 1
        with self.assertRaisesRegex(Refused, "state_config_mismatch"):
            self.worker(c=changed)
        with self.assertRaisesRegex(Refused, "state_config_mismatch"):
            self.worker(PublicHTTPS())

    def test_crash_reservation_is_charged_and_retry_bounded(self):
        w = self.worker()
        cap = w.limits["max_response_bytes"] + 1
        with w.db:
            w.db.execute("UPDATE frontier SET status='fetching',attempts=3")
            w.db.execute("INSERT INTO requests(status,reserved,charged) VALUES('started',?,?)", (cap, cap))
        w.recover()
        self.assertEqual(w.db.execute("SELECT status,charged FROM requests").fetchone()[:], ("unknown", cap))
        self.assertEqual(w.db.execute("SELECT status FROM frontier").fetchone()[0], "failed")

    def test_each_budget_stops_with_pending_state(self):
        for key, value, reason in [("max_requests", 2, "request_budget"), ("max_total_bytes", 524288, "byte_budget"), ("max_pages", 1, "page_budget")]:
            with self.subTest(key=key):
                c = config(); c["limits"][key] = value
                other = Path(self.temp.name) / (key + ".sqlite")
                w = Collector(c, other, DemoTransport(), self.clock)
                try:
                    r = self.finish(w)
                    self.assertEqual((r["state"], r["reason"], r["continue"]), ("paused", reason, False))
                finally:
                    w.close()
        w = self.worker(); self.clock.advance(601)
        self.assertEqual(w.tick()["reason"], "time_budget")

    def test_frontier_limit_is_visible_partial_not_complete(self):
        c = config(); c["limits"]["max_urls"] = 1
        r = self.finish(self.worker(c=c))
        self.assertEqual(r["state"], "partial")
        self.assertTrue(r["frontier_truncated"])

    def test_robots_unreachable_never_fetches_page(self):
        fake = Fake({ROBOTS_URL: (503, {"content-type": "text/plain"}, b"unavailable")})
        w = self.worker(fake)
        r = self.finish(w)
        self.assertEqual(r["state"], "partial")
        self.assertNotIn(HOME, fake.calls)

    def test_robots_html_and_redirect_fail_closed(self):
        for reply in [HTML("<html>login</html>"), (200, {"content-type": "text/plain"}, b"<html>login</html>"), (200, {"content-type": "text/plain"}, b"\xffinvalid"), (302, {"location": "http://127.0.0.1/"}, b"")]:
            other = Path(self.temp.name) / str(len(self.workers))
            fake = Fake({ROBOTS_URL: reply})
            w = Collector(config(), other, fake, self.clock); self.workers.append(w)
            self.assertEqual(self.finish(w)["state"], "partial")
            self.assertEqual(set(fake.calls), {ROBOTS_URL})

    def test_robot_delay_applies_after_robots_fetch(self):
        fake = Fake({ROBOTS_URL: (200, {"content-type": "text/plain"}, b"User-agent: *\nCrawl-delay: 30"), HOME: HTML("<p>Allowed</p>")})
        w = self.worker(fake); w.tick(); self.clock.advance(3); w.tick()
        self.assertEqual(fake.calls, [ROBOTS_URL])
        self.clock.advance(28); w.tick()
        self.assertEqual(fake.calls, [ROBOTS_URL, HOME])

    def test_retry_after_pacing_then_success(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: [(429, {"retry-after": "20"}, b""), HTML("<p>ok</p>")]})
        w = self.worker(fake); w.tick(); self.clock.advance(); w.tick()
        self.clock.advance(10); w.tick()
        self.assertEqual(fake.calls.count(HOME), 1)
        self.clock.advance(11); self.assertEqual(w.tick()["state"], "complete")

    def test_long_retry_after_wait_stops_at_job_deadline(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: (429, {"retry-after": "90000"}, b"")})
        w = self.worker(fake); w.tick(); self.clock.advance(); r = w.tick()
        self.assertLessEqual(r["wait_seconds"], 597)
        self.clock.advance(r["wait_seconds"])
        self.assertEqual(w.tick()["reason"], "time_budget")

    def test_retries_do_not_store_remote_error_or_credential(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: RuntimeError("Authorization Bearer secret-value")})
        w = self.worker(fake); self.assertEqual(self.finish(w)["state"], "partial")
        self.assertEqual(fake.calls.count(HOME), 3)
        dump = "\n".join(w.db.iterdump())
        self.assertNotIn("secret-value", dump)
        self.assertNotIn("Authorization", dump)

    def test_redirect_target_requires_scope_and_robots(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: (302, {"location": "/guides/private"}, b"")})
        w = self.worker(fake); r = self.finish(w)
        self.assertEqual(r["frontier"], {"blocked": 1, "redirect": 1})
        self.assertNotIn(HOME + "/private", fake.calls)

    def test_outside_redirect_is_not_requested(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: (302, {"location": "https://evil.example.org/"}, b"")})
        w = self.worker(fake); self.finish(w)
        self.assertEqual(fake.calls, [ROBOTS_URL, HOME])

    def test_noindex_nofollow_prevents_storage_and_discovery(self):
        fake = Fake({ROBOTS_URL: ROBOTS, HOME: HTML('<meta name="robots" content="noindex,nofollow"><p>Do not retain</p><a href="/guides/new">New</a>')})
        w = self.worker(fake); r = self.finish(w)
        self.assertEqual(r["pages"], 0)
        self.assertEqual(w.db.execute("SELECT count(*) FROM frontier").fetchone()[0], 1)
        self.assertNotIn("Do not retain", "\n".join(w.db.iterdump()))

    def test_oversized_and_encoded_body_stop(self):
        for response in [(200, {"content-type": "text/html"}, b"x" * 524289), (200, {"content-type": "text/html", "content-encoding": "gzip"}, b"bytes")]:
            state = Path(self.temp.name) / str(len(self.workers))
            w = Collector(config(), state, Fake({ROBOTS_URL: ROBOTS, HOME: response}), self.clock); self.workers.append(w)
            r = self.finish(w)
            self.assertEqual((r["state"], r["pages"]), ("partial", 0))
            self.assertGreaterEqual(r["charged_bytes"], 524289)

    def test_lock_prevents_parallel_tick(self):
        w = self.worker()
        with w.exclusive():
            with self.assertRaisesRegex(Refused, "collector_busy"):
                w.tick()

    def test_state_directory_requires_private_permissions(self):
        folder = Path(self.temp.name) / "shared"; folder.mkdir(mode=0o755)
        with self.assertRaisesRegex(Refused, "private_state_directory_required"):
            Collector(config(), folder / "state.sqlite", DemoTransport(), self.clock)

    def test_receipt_retention_keeps_request_ledger(self):
        w = self.worker()
        with w.db:
            w.db.executemany("INSERT INTO receipts(at,summary) VALUES(?,?)", [(self.clock(), str(i)) for i in range(1100)])
        w.tick()
        self.assertEqual(w.db.execute("SELECT count(*) FROM receipts").fetchone()[0], 1000)
        self.assertEqual(w.db.execute("SELECT count(*) FROM requests").fetchone()[0], 1)


class PolicyTests(unittest.TestCase):
    def test_normalization_dedup_and_query_policy(self):
        self.assertEqual(normalize("https://DOCS.example.com:443/guides/%7eintro?utm_source=x#top"), "https://docs.example.com/guides/~intro")
        self.assertEqual(normalize("?page=2", HOME, ["page"]), HOME + "?page=2")
        for url in ["http://docs.example.com/", "https://user:pass@docs.example.com/", "https://127.0.0.1/", "https://localhost/", "https://docs.example.com:444/", HOME + "/%2fprivate", HOME + "/%252fprivate", HOME + "/%2e%2e/private", HOME + "?token=secret", HOME + "?page=2&page=3", "https://docs.example.com/\n"]:
            with self.subTest(url=url), self.assertRaises(Refused):
                normalize(url)

    def test_robots_specificity_wildcard_groups_and_query(self):
        r = Robots("User-agent: *\nDisallow: /\nUser-agent: PublicPageCollector\nDisallow: /guides/*\nAllow: /guides/open$\nUser-agent: PublicPageCollector\nDisallow: /download?private=true")
        self.assertTrue(r.allowed(HOME + "/open"))
        self.assertFalse(r.allowed(HOME + "/open/more"))
        self.assertFalse(r.allowed("https://docs.example.com/download?private=true"))
        self.assertTrue(r.allowed("https://docs.example.com/other"))

    def test_dns_mixed_private_and_public_is_refused(self):
        def resolver(*_, **__):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (x, 443)) for x in ["93.184.215.14", "127.0.0.1"]]
        with self.assertRaisesRegex(Refused, "non_public_destination"):
            PublicHTTPS(resolver).addresses("docs.example.com")

    def test_live_transport_timeout_reaps_fixed_child(self):
        before = {p.pid for p in multiprocessing.active_children()}
        started = time.monotonic()
        with patch("collector._fetch_child", slow_child):
            with self.assertRaisesRegex(Refused, "transport_timeout"):
                PublicHTTPS().get(HOME, 1024, 0.2, "SyntheticTest")
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)

    def test_permission_and_unknown_config_rejected(self):
        for mutate in [lambda c: c.update(permission_confirmed=False), lambda c: c.update(proxy="http://proxy"), lambda c: c.update(query_keys=[None]), lambda c: c["origins"].update({"http://bad.example.com": ["/"]})]:
            c = config(); mutate(c)
            with self.assertRaises(Refused):
                validate_config(c)

    def test_token_file_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "controller.token"; p.write_text("a" * 48); p.chmod(0o600)
            self.assertEqual(read_token(p), "a" * 48)
            p.chmod(0o644)
            with self.assertRaises(Refused): read_token(p)
            p.chmod(0o600); link = Path(folder) / "link"; link.symlink_to(p)
            with self.assertRaises(Refused): read_token(link)

    def test_local_tls_content_length_eof_and_verified_host(self):
        # A real local TLS server exercises HTTPResponse EOF. No public network.
        with tempfile.TemporaryDirectory() as folder:
            cert, key = Path(folder) / "cert.pem", Path(folder) / "key.pem"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-keyout", str(key), "-out", str(cert), "-subj", "/CN=docs.example.com", "-addext", "subjectAltName=DNS:docs.example.com"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            body = b"<title>Local TLS</title>" + b"x" * 65536
            class Handler(BaseHTTPRequestHandler):
                protocol_version = "HTTP/1.1"
                def log_message(self, *_): pass
                def do_GET(self):
                    self.send_response(200); self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(body))); self.send_header("Connection", "close")
                    self.end_headers(); self.wfile.write(body)
            srv = HTTPServer(("127.0.0.1", 0), Handler)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert, key)
            srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
            thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
            trusted = ssl.create_default_context(cafile=str(cert))
            connect = socket.create_connection
            transport = PublicHTTPS()
            try:
                with patch.object(transport, "addresses", return_value=["93.184.215.14"]), patch("collector.socket.create_connection", side_effect=lambda *_args, **kw: connect(srv.server_address, **kw)), patch("collector.ssl.create_default_context", return_value=trusted):
                    status, headers, got = transport._get(HOME, 100000, 5, "SyntheticTest")
                self.assertEqual((status, got), (200, body))
                self.assertEqual(headers["content-type"], "text/html")
            finally:
                srv.shutdown(); srv.server_close(); thread.join(2)


if __name__ == "__main__":
    unittest.main()
