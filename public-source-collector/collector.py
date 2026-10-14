#!/usr/bin/env python3
"""Bounded, resumable collection of explicitly permitted public HTML pages."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import html.parser
import http.client
import ipaddress
import json
import multiprocessing
import math
import os
from pathlib import Path
import re
import socket
import sqlite3
import ssl
import time
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from email.utils import parsedate_to_datetime

PRODUCT = "PublicPageCollector"
UNRESERVED = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"


class Refused(Exception):
    """Only fixed codes cross the controller boundary."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def encoded_path(value):
    if re.search(r"%(?![0-9a-fA-F]{2})", value):
        raise Refused("invalid_encoding")
    value = re.sub(r"%([0-9a-fA-F]{2})", lambda m: chr(int(m[1], 16)) if chr(int(m[1], 16)) in UNRESERVED else "%" + m[1].upper(), value)
    return quote(value, safe="/%:@!$&'()*+,;=-._~")


def normalize(raw, base=None, query_keys=()):
    if not isinstance(raw, str) or len(raw) > 2048 or re.search(r"[\x00-\x20\x7f\\]", raw):
        raise Refused("invalid_url")
    try:
        p = urlsplit(urljoin(base, raw) if base else raw)
        host = (p.hostname or "").encode("idna").decode("ascii").lower()
        if p.scheme != "https" or p.username is not None or p.password is not None or p.port not in (None, 443):
            raise ValueError()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or "." not in host or ".." in host:
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        if host.endswith((".localhost", ".local", ".internal")):
            raise ValueError()
        path = encoded_path(p.path or "/")
        # Conservative: no ambiguous encoded separators, nested encoding or dot segments.
        if re.search(r"%(?:2F|5C|25|0[0-9A-F]|1[0-9A-F]|7F)", path) or any(x in (".", "..") for x in path.split("/")):
            raise ValueError()
        query = []
        seen = set()
        for k, v in parse_qsl(p.query, keep_blank_values=True, max_num_fields=20):
            if k.lower().startswith("utm_") or k.lower() in ("gclid", "fbclid"):
                continue
            if k not in query_keys or k in seen or len(v) > 100:
                raise ValueError()
            seen.add(k)
            query.append((k, v))
        return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))
    except (ValueError, UnicodeError):
        raise Refused("invalid_url") from None


def origin(url):
    p = urlsplit(url)
    return p.scheme + "://" + p.netloc


def validate_config(c):
    expected = {"job_id", "permission_confirmed", "origins", "seeds", "query_keys", "contact_url", "limits"}
    if not isinstance(c, dict) or set(c) != expected or not re.fullmatch(r"[a-z0-9-]{1,64}", str(c["job_id"])):
        raise Refused("invalid_config")
    if c["permission_confirmed"] is not True:
        raise Refused("permission_not_confirmed")
    if not isinstance(c["query_keys"], list) or len(c["query_keys"]) > 10 or any(not isinstance(x, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,30}", x) for x in c["query_keys"]):
        raise Refused("invalid_config")
    if not isinstance(c["origins"], dict) or not 1 <= len(c["origins"]) <= 10:
        raise Refused("invalid_config")
    for root, prefixes in c["origins"].items():
        if normalize(root) != root + "/" or not isinstance(prefixes, list) or not 1 <= len(prefixes) <= 10:
            raise Refused("invalid_config")
        for prefix in prefixes:
            if not isinstance(prefix, str) or not prefix.startswith("/") or normalize(root + prefix) != root + prefix:
                raise Refused("invalid_config")
    normalize(c["contact_url"])
    ranges = {"max_requests": (2, 10000), "max_pages": (1, 5000), "max_urls": (1, 10000),
              "max_depth": (0, 10), "max_attempts": (1, 5), "max_response_bytes": (1024, 2097152),
              "max_total_bytes": (1024, 100000000), "max_runtime_seconds": (10, 86400),
              "delay_seconds": (1, 3600), "batch_pages": (1, 10)}
    if not isinstance(c["limits"], dict) or set(c["limits"]) != set(ranges):
        raise Refused("invalid_config")
    for k, (low, high) in ranges.items():
        if type(c["limits"][k]) is not int or not low <= c["limits"][k] <= high:
            raise Refused("invalid_config")
    if c["limits"]["max_total_bytes"] < c["limits"]["max_response_bytes"]:
        raise Refused("invalid_config")
    if not isinstance(c["seeds"], list) or not 1 <= len(c["seeds"]) <= 100:
        raise Refused("invalid_config")
    for seed in c["seeds"]:
        u = normalize(seed, query_keys=c["query_keys"])
        if not in_scope(u, c):
            raise Refused("seed_outside_allowlist")
    return c


def in_scope(url, c):
    path = urlsplit(url).path
    return any(prefix == "/" or path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
               for prefix in c["origins"].get(origin(url), []))


class Robots:
    """Longest-rule matching, merged exact-agent groups, wildcard and end anchor."""
    def __init__(self, text):
        groups, agents, rules, delays = [], [], [], []
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]
            k = k.lower()
            if k == "user-agent":
                if rules or delays:
                    groups.append((agents, rules, delays))
                    agents, rules, delays = [], [], []
                agents.append(v.lower())
            elif agents and k in ("allow", "disallow") and v.startswith("/"):
                rules.append((encoded_path(v).replace("%3F", "?"), k == "allow"))
            elif agents and k == "crawl-delay":
                try:
                    delay = float(v)
                    if not 0 <= delay <= 86400:
                        raise ValueError()
                    delays.append(delay)
                except ValueError:
                    delays.append(86400)
        groups.append((agents, rules, delays))
        selected = [g for g in groups if PRODUCT.lower() in g[0]]
        if not selected:
            selected = [g for g in groups if "*" in g[0]]
        self.rules = [r for g in selected for r in g[1]]
        self.delay = max([d for g in selected for d in g[2]] or [0])

    def allowed(self, url):
        p = urlsplit(url)
        path = p.path + ("?" + p.query if p.query else "")
        matches = []
        for pattern, allow in self.rules:
            end = pattern.endswith("$")
            raw = pattern[:-1] if end else pattern
            regex = "^" + re.escape(raw).replace(r"\*", ".*") + ("$" if end else "")
            if re.search(regex, path):
                matches.append((len(raw.replace("*", "").encode()), allow))
        return max(matches)[1] if matches else True


class PublicHTTPS:
    """No environment proxy, cookies, auth, automatic redirects or second DNS lookup."""
    def __init__(self, resolver=socket.getaddrinfo):
        self.resolver = resolver

    def addresses(self, host):
        infos = self.resolver(host, 443, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(x[4][0] for x in infos))
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise Refused("non_public_destination")
        return ips

    def get(self, url, limit, timeout, user_agent):
        # A separate process bounds DNS, TLS, headers and slow body reads together.
        # The child accepts only this fixed GET operation, never a command or script.
        ctx = multiprocessing.get_context("spawn")
        receive, send = ctx.Pipe(duplex=False)
        child = ctx.Process(target=_fetch_child, args=(send, url, limit, timeout, user_agent))
        child.start()
        send.close()
        try:
            if not receive.poll(timeout):
                raise Refused("transport_timeout")
            ok, result = receive.recv()
            if not ok:
                raise Refused(result)
            return result
        except (EOFError, OSError):
            raise Refused("transport_error") from None
        finally:
            if child.is_alive():
                child.terminate()
            child.join(2)
            if child.is_alive():
                child.kill()
                child.join()
            receive.close()

    def _get(self, url, limit, timeout, user_agent):
        p = urlsplit(normalize(url, query_keys=[k for k, _ in parse_qsl(urlsplit(url).query)]))
        ips = self.addresses(p.hostname)
        deadline = time.monotonic() + timeout
        conn = http.client.HTTPSConnection(p.hostname, timeout=timeout, context=ssl.create_default_context())
        # Connect to a validated IP while retaining the original TLS SNI and Host.
        raw = socket.create_connection((ips[0], 443), timeout=timeout)
        try:
            tls_socket = conn._context.wrap_socket(raw, server_hostname=p.hostname)
            conn.sock = tls_socket
            conn.request("GET", p.path + ("?" + p.query if p.query else ""), headers={
                "User-Agent": user_agent, "Accept": "text/html,text/plain", "Accept-Encoding": "identity", "Connection": "close"})
            response = conn.getresponse()
            headers = {k.lower(): v for k, v in response.getheaders() if k.lower() in ("content-type", "location", "retry-after", "content-encoding")}
            chunks, size = [], 0
            while size <= limit and response.fp is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                # HTTPResponse.read1 makes at most one underlying read.
                tls_socket.settimeout(remaining)
                chunk = response.read1(min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            return response.status, headers, b"".join(chunks)
        finally:
            conn.close()
            raw.close()


def _fetch_child(pipe, url, limit, timeout, user_agent):
    try:
        pipe.send((True, PublicHTTPS()._get(url, limit, timeout, user_agent)))
    except Exception as exc:
        pipe.send((False, str(exc) if isinstance(exc, Refused) else "transport_error"))
    finally:
        pipe.close()


class Document(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.title_depth = 0
        self.title, self.text, self.links = [], [], []
        self.noindex = self.nofollow = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if tag == "title":
            self.title_depth += 1
        if tag == "meta" and a.get("name", "").lower() in ("robots", PRODUCT.lower()):
            directives = set(re.split(r"[\s,]+", a.get("content", "").lower()))
            self.noindex |= bool(directives & {"noindex", "none"})
            self.nofollow |= bool(directives & {"nofollow", "none"})
        if tag == "a" and a.get("href") and "nofollow" not in a.get("rel", "").lower().split() and len(self.links) < 1000:
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.title_depth = max(0, self.title_depth - 1)

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
            if self.title_depth:
                self.title.append(data)


class Collector:
    def __init__(self, config, state, transport=None, clock=time.time):
        self.config = validate_config(config)
        self.limits = config["limits"]
        self.path = Path(state)
        if self.path.is_symlink():
            raise Refused("state_symlink_refused")
        self.path = self.path.parent.resolve() / self.path.name
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent_stat = self.path.parent.stat()
        if parent_stat.st_uid != os.getuid() or parent_stat.st_mode & 0o077:
            raise Refused("private_state_directory_required")
        self.transport = transport or PublicHTTPS()
        self.mode = "live" if isinstance(self.transport, PublicHTTPS) else "offline_demo"
        self.clock = clock
        self.db = sqlite3.connect(self.path, timeout=5)
        os.chmod(self.path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS frontier(url TEXT PRIMARY KEY,depth INTEGER,hops INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,next_at REAL DEFAULT 0,code TEXT);
          CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY,url_hash TEXT,kind TEXT,status TEXT,
            reserved INTEGER,charged INTEGER,code TEXT,started REAL,finished REAL);
          CREATE TABLE IF NOT EXISTS hosts(origin TEXT PRIMARY KEY,next_at REAL DEFAULT 0,
            robots TEXT,robots_until REAL DEFAULT 0,robots_code INTEGER);
          CREATE TABLE IF NOT EXISTS documents(url TEXT PRIMARY KEY,title TEXT,text TEXT,content_hash TEXT,
            duplicate_of TEXT,fetched_at REAL);
          CREATE TABLE IF NOT EXISTS imports(source_id TEXT PRIMARY KEY,digest TEXT,accepted INTEGER,rejected INTEGER);
          CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,at REAL,summary TEXT);
        """)
        fingerprint = digest({"config": config, "mode": self.mode})
        existing = self.meta("config_hash")
        if existing and existing != fingerprint:
            self.db.close()
            raise Refused("state_config_mismatch")
        with self.db:
            self.set_meta("config_hash", fingerprint)
            if not self.meta("created_at"):
                self.set_meta("created_at", str(self.clock()))
            for seed in config["seeds"]:
                self.enqueue(seed, 0)

    def close(self):
        self.db.close()

    def meta(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, value))

    @contextlib.contextmanager
    def exclusive(self):
        with open(str(self.path) + ".lock", "a") as lock:
            os.chmod(lock.name, 0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused("collector_busy") from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def enqueue(self, raw, depth, base=None, hops=0):
        try:
            url = normalize(raw, base, self.config["query_keys"])
        except Refused:
            return False
        if not in_scope(url, self.config) or depth > self.limits["max_depth"] or hops > 5:
            return False
        if self.db.execute("SELECT 1 FROM frontier WHERE url=?", (url,)).fetchone():
            return True
        if self.db.execute("SELECT count(*) FROM frontier").fetchone()[0] >= self.limits["max_urls"]:
            self.set_meta("frontier_truncated", "true")
            return False
        self.db.execute("INSERT INTO frontier(url,depth,hops) VALUES(?,?,?)", (url, depth, hops))
        return True

    def discover(self, data):
        if not isinstance(data, dict) or set(data) != {"source", "run_id", "status", "items"} or data["source"] != "apify-export" or data["status"] != "SUCCEEDED":
            raise Refused("invalid_discovery_export")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", str(data["run_id"])) or not isinstance(data["items"], list) or len(data["items"]) > 10000:
            raise Refused("invalid_discovery_export")
        # Only URLs enter the queue. All other supplied dataset fields are ignored.
        urls = [r.get("url") or r.get("website") if isinstance(r, dict) else None for r in data["items"]]
        identity, fingerprint = "apify-export:" + data["run_id"], digest(urls)
        with self.exclusive(), self.db:
            old = self.db.execute("SELECT * FROM imports WHERE source_id=?", (identity,)).fetchone()
            if old:
                if old["digest"] != fingerprint:
                    raise Refused("discovery_identity_changed")
                return {"replay": True, "accepted": old["accepted"], "rejected": old["rejected"]}
            if self.db.execute("SELECT count(*) FROM imports").fetchone()[0] >= 100:
                raise Refused("discovery_import_limit")
            accepted = sum(self.enqueue(u, 0) for u in urls)
            rejected = len(urls) - accepted
            self.db.execute("INSERT INTO imports VALUES(?,?,?,?)", (identity, fingerprint, accepted, rejected))
            return {"replay": False, "accepted": accepted, "rejected": rejected}

    def recover(self):
        # A completed remote GET with no local receipt is ambiguous, never free.
        # Charge its full reservation; bounded retry is allowed because requests are GET only.
        with self.db:
            self.db.execute("UPDATE requests SET status='unknown',charged=reserved,code='interrupted',finished=? WHERE status='started'", (self.clock(),))
            self.db.execute("UPDATE frontier SET status=CASE WHEN attempts>=? THEN 'failed' ELSE 'pending' END,code='interrupted' WHERE status='fetching'", (self.limits["max_attempts"],))

    def budget(self):
        count, charged = self.db.execute("SELECT count(*),coalesce(sum(charged),0) FROM requests").fetchone()
        pages = self.db.execute("SELECT count(*) FROM documents").fetchone()[0]
        if self.clock() - float(self.meta("created_at")) >= self.limits["max_runtime_seconds"]:
            return "time_budget"
        if count >= self.limits["max_requests"]:
            return "request_budget"
        if charged + self.limits["max_response_bytes"] + 1 > self.limits["max_total_bytes"]:
            return "byte_budget"
        if pages >= self.limits["max_pages"]:
            return "page_budget"
        return None

    def request(self, url, kind, delay):
        reason = self.budget()
        if reason:
            raise Refused(reason)
        root = origin(url)
        now = self.clock()
        cap = self.limits["max_response_bytes"] + 1
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO hosts(origin) VALUES(?)", (root,))
            next_at = self.db.execute("SELECT next_at FROM hosts WHERE origin=?", (root,)).fetchone()[0]
            if next_at > now:
                raise Refused("rate_wait")
            self.db.execute("UPDATE hosts SET next_at=? WHERE origin=?", (now + delay, root))
            cur = self.db.execute("INSERT INTO requests(url_hash,kind,status,reserved,charged,started) VALUES(?,?,'started',?,?,?)", (hashlib.sha256(url.encode()).hexdigest(), kind, cap, cap, now))
            request_id = cur.lastrowid
        try:
            timeout = min(10, max(0.1, float(self.meta("created_at")) + self.limits["max_runtime_seconds"] - now))
            status, headers, body = self.transport.get(url, self.limits["max_response_bytes"], timeout, PRODUCT + "/1.0 (+" + self.config["contact_url"] + ")")
            if len(body) > self.limits["max_response_bytes"]:
                raise Refused("response_too_large")
            if headers.get("content-encoding", "identity").lower() not in ("identity", ""):
                raise Refused("encoded_response_refused")
            with self.db:
                self.db.execute("UPDATE requests SET status='received',charged=?,code=?,finished=? WHERE id=?", (len(body), "http_" + str(status), self.clock(), request_id))
            return status, headers, body
        except Exception as exc:
            code = str(exc) if isinstance(exc, Refused) else "transport_error"
            with self.db:
                self.db.execute("UPDATE requests SET status='failed',code=?,finished=? WHERE id=?", (code, self.clock(), request_id))
            raise Refused(code) from None

    def robots(self, url):
        root = origin(url)
        row = self.db.execute("SELECT * FROM hosts WHERE origin=?", (root,)).fetchone()
        if row and row["robots_until"] > self.clock():
            if row["robots_code"] not in (200, 404, 410):
                raise Refused("robots_unavailable")
            return Robots(row["robots"] or "")
        status, headers, body = self.request(root + "/robots.txt", "robots", self.limits["delay_seconds"])
        if status == 200 and "text/plain" not in headers.get("content-type", "").lower():
            status = 0  # Captive portal or HTML login response is not an allow-all robots file.
        try:
            text = body.decode("utf-8-sig") if status == 200 else ""
            if text.lstrip().startswith("<"):
                status, text = 0, ""
        except UnicodeDecodeError:
            status, text = 0, ""
        with self.db:
            self.db.execute("UPDATE hosts SET robots=?,robots_code=?,robots_until=? WHERE origin=?", (text, status, self.clock() + (86400 if status in (200, 404, 410) else 60), root))
        if status not in (200, 404, 410):
            raise Refused("robots_unavailable")
        parsed = Robots(text)
        with self.db:
            self.db.execute("UPDATE hosts SET next_at=max(next_at,?) WHERE origin=?", (self.clock() + max(parsed.delay, self.limits["delay_seconds"]), root))
        return parsed

    def finish(self, url, state, code):
        with self.db:
            self.db.execute("UPDATE frontier SET status=?,code=? WHERE url=?", (state, code, url))

    def process(self, row):
        url = row["url"]
        try:
            robots = self.robots(url)
            if not robots.allowed(url):
                self.finish(url, "blocked", "robots_disallow")
                return
            host = self.db.execute("SELECT next_at FROM hosts WHERE origin=?", (origin(url),)).fetchone()
            if host[0] > self.clock():
                raise Refused("rate_wait")
            with self.db:
                self.db.execute("UPDATE frontier SET status='fetching',attempts=attempts+1 WHERE url=?", (url,))
            status, headers, body = self.request(url, "page", max(self.limits["delay_seconds"], robots.delay))
            if status in (301, 302, 303, 307, 308):
                with self.db:
                    accepted = self.enqueue(headers.get("location", ""), row["depth"], url, row["hops"] + 1)
                self.finish(url, "redirect" if accepted else "blocked", "redirect_queued" if accepted else "redirect_refused")
                return
            if status in (408, 429) or status >= 500:
                delay = 2 ** (row["attempts"] + 1)
                retry = headers.get("retry-after", "")
                if retry.isdigit():
                    delay = max(delay, int(retry[:10]))
                elif retry:
                    try:
                        delay = max(delay, parsedate_to_datetime(retry).timestamp() - self.clock())
                    except (ValueError, TypeError, OverflowError):
                        pass
                with self.db:
                    self.db.execute("UPDATE hosts SET next_at=max(next_at,?) WHERE origin=?", (self.clock() + delay, origin(url)))
                raise Refused("retryable_http")
            if status != 200 or "text/html" not in headers.get("content-type", "").lower():
                self.finish(url, "skipped", "non_html_or_http_error")
                return
            doc = Document()
            doc.feed(body.decode("utf-8", "replace"))
            title = " ".join(" ".join(doc.title).split())[:300]
            text = " ".join(" ".join(doc.text).split())[:100000]
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            with self.db:
                if not doc.noindex:
                    duplicate = self.db.execute("SELECT url FROM documents WHERE content_hash=? ORDER BY url LIMIT 1", (content_hash,)).fetchone()
                    self.db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?)", (url, title, "" if duplicate else text, content_hash, duplicate[0] if duplicate else None, self.clock()))
                if not doc.nofollow:
                    for link in doc.links:
                        self.enqueue(link, row["depth"] + 1, url)
                self.db.execute("UPDATE frontier SET status='done',code=? WHERE url=?", ("noindex" if doc.noindex else "collected", url))
        except Refused as exc:
            code = str(exc)
            if code.endswith("_budget") or code == "rate_wait":
                self.finish(url, "pending", code)
                return
            attempts = self.db.execute("SELECT attempts FROM frontier WHERE url=?", (url,)).fetchone()[0]
            # Robots failures also count toward the finite per-URL attempt ceiling.
            if attempts == row["attempts"]:
                attempts += 1
            state = "failed" if attempts >= self.limits["max_attempts"] or code in ("non_public_destination", "response_too_large", "encoded_response_refused") else "pending"
            with self.db:
                self.db.execute("UPDATE frontier SET status=?,attempts=?,next_at=?,code=? WHERE url=?", (state, attempts, self.clock() + min(60, 2 ** attempts), code, url))

    def summary(self):
        states = dict(self.db.execute("SELECT status,count(*) FROM frontier GROUP BY status"))
        requests, charged = self.db.execute("SELECT count(*),coalesce(sum(charged),0) FROM requests").fetchone()
        pages, unique = self.db.execute("SELECT count(*),count(DISTINCT content_hash) FROM documents").fetchone()
        pending = states.get("pending", 0) + states.get("fetching", 0)
        reason = self.budget() if pending else None
        truncated = self.meta("frontier_truncated") == "true"
        result = "paused" if reason else ("running" if pending else ("partial" if states.get("failed") or truncated else "complete"))
        wait = 0
        if pending and not reason:
            # A conservative global wait also prevents a hot loop on blocked origins.
            waits = [r[0] for r in self.db.execute("SELECT next_at FROM frontier WHERE status='pending' UNION ALL SELECT next_at FROM hosts")]
            lifetime_left = math.ceil(float(self.meta("created_at")) + self.limits["max_runtime_seconds"] - self.clock())
            wait = max(1, min(86400, lifetime_left, int(max(waits or [self.clock()]) - self.clock()) + 1))
        return {"job_id": self.config["job_id"], "mode": self.mode, "state": result, "continue": bool(pending and not reason),
                "wait_seconds": wait, "reason": reason, "frontier": states, "frontier_truncated": truncated,
                "requests": requests, "charged_bytes": charged, "pages": pages, "unique_documents": unique}

    def tick(self):
        with self.exclusive():
            self.recover()
            for _ in range(self.limits["batch_pages"]):
                if self.budget():
                    break
                rows = self.db.execute("SELECT * FROM frontier WHERE status='pending' AND next_at<=? ORDER BY depth,url", (self.clock(),)).fetchall()
                row = next((r for r in rows if not self.db.execute("SELECT 1 FROM hosts WHERE origin=? AND next_at>?", (origin(r["url"]), self.clock())).fetchone()), None)
                if row is None:
                    break
                self.process(row)
            result = self.summary()
            with self.db:
                encoded = json.dumps(result, sort_keys=True)
                previous = self.db.execute("SELECT summary FROM receipts ORDER BY id DESC LIMIT 1").fetchone()
                if not previous or previous[0] != encoded:
                    self.db.execute("INSERT INTO receipts(at,summary) VALUES(?,?)", (self.clock(), encoded))
                    self.db.execute("DELETE FROM receipts WHERE id NOT IN (SELECT id FROM receipts ORDER BY id DESC LIMIT 1000)")
            return result


class DemoTransport:
    """Fixed in-memory public-docs fixture. It cannot open a socket."""
    def get(self, url, limit, timeout, user_agent):
        pages = {
            "https://docs.example.com/robots.txt": (200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /guides/private\n"),
            "https://docs.example.com/guides": (200, {"content-type": "text/html"}, b'<title>Demo documentation</title><p>Start here.</p><a href="/guides/setup?utm_source=demo">Setup</a><a href="/guides/setup#copy">Again</a><a href="/guides/private">Private</a><a href="https://outside.example.org/">Outside</a>'),
            "https://docs.example.com/guides/setup": (200, {"content-type": "text/html"}, b'<title>Setup guide</title><p>This is synthetic documentation.</p><a href="/guides/copy">Copy</a>'),
            "https://docs.example.com/guides/copy": (200, {"content-type": "text/html"}, b'<title>Setup guide</title><p>This is synthetic documentation.</p><a href="/guides/copy">Copy</a>'),
        }
        if url not in pages:
            return 404, {"content-type": "text/plain"}, b""
        return pages[url]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("plan", "tick", "status", "discover", "export"))
    ap.add_argument("--config", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--input", help="Completed discovery export, used only by discover")
    ap.add_argument("--live", action="store_true", help="Enable real HTTPS GETs. Omitted means fixed offline demo.")
    args = ap.parse_args()
    try:
        c = validate_config(json.loads(Path(args.config).read_text()))
        if args.action == "plan":
            print(json.dumps({"job_id": c["job_id"], "mode": "live" if args.live else "offline_demo", "origins": len(c["origins"]), "seeds": len(c["seeds"]), "limits": c["limits"]}))
            return
        worker = Collector(c, args.state, PublicHTTPS() if args.live else DemoTransport())
        try:
            if args.action == "tick":
                result = worker.tick()
            elif args.action == "discover":
                if not args.input or Path(args.input).stat().st_size > 10000000:
                    raise Refused("invalid_discovery_export")
                result = worker.discover(json.loads(Path(args.input).read_text()))
            elif args.action == "export":
                result = [dict(r) for r in worker.db.execute("SELECT * FROM documents ORDER BY url")]
            else:
                result = worker.summary()
            print(json.dumps(result, sort_keys=True))
        finally:
            worker.close()
    except (Refused, ValueError, OSError):
        raise SystemExit("collector_failed: inspect configuration and local state; no remote response logged") from None


if __name__ == "__main__":
    main()
