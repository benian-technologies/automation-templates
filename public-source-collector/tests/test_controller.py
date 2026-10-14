import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ControllerTest(unittest.TestCase):
    def test_http_auth_resume_and_completed_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            token = folder / "controller.token"
            token.write_text("syntheticControllerToken" * 3); token.chmod(0o600)
            c = json.loads((ROOT / "examples/config.demo.json").read_text())
            c["limits"]["delay_seconds"] = 1
            cfg = folder / "config.json"; cfg.write_text(json.dumps(c))
            state = folder / "state.sqlite"
            proc = None
            def start():
                nonlocal proc
                proc = subprocess.Popen([sys.executable, "-B", str(ROOT / "serve.py"), "--config", str(cfg), "--state", str(state), "--token-file", str(token), "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                ready = json.loads(proc.stdout.readline())
                self.assertEqual((ready["host"], ready["mode"]), ("127.0.0.1", "offline_demo"))
                return ready["port"]
            def stop():
                nonlocal proc
                if proc:
                    proc.terminate()
                    stdout, stderr = proc.communicate(timeout=5)
                    self.assertNotIn(token.read_text(), stdout + stderr)
                    proc = None
            def request(port, method="POST", body=None, authorized=True, route="/v1/tick"):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=7)
                headers = {"Content-Type": "application/json"}
                if authorized: headers["Authorization"] = "Bearer " + token.read_text()
                conn.request(method, route, json.dumps(body or {"job_id": c["job_id"]}), headers)
                r = conn.getresponse(); data = json.loads(r.read()); status = r.status; conn.close()
                return status, data
            try:
                port = start()
                self.assertEqual(request(port, authorized=False)[0], 401)
                self.assertEqual(request(port, body={"job_id": "wrong"})[0], 409)
                _, first = request(port)
                self.assertEqual(first["requests"], 1)
                stop(); port = start()
                for _ in range(12):
                    status, receipt = request(port)
                    self.assertEqual(status, 200)
                    if not receipt["continue"]: break
                    time.sleep(receipt["wait_seconds"])
                self.assertEqual((receipt["state"], receipt["pages"], receipt["unique_documents"], receipt["requests"]), ("complete", 3, 2, 4))
                self.assertEqual(request(port)[1]["requests"], 4)
                # A partial body cannot permanently block the serial controller.
                raw = socket.create_connection(("127.0.0.1", port), timeout=2)
                raw.sendall(("POST /v1/tick HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer " + token.read_text() + "\r\nContent-Type: application/json\r\nContent-Length: 99\r\n\r\n{").encode())
                time.sleep(5.1); raw.close()
                self.assertEqual(request(port, method="GET", route="/v1/status")[0], 200)
            finally:
                stop()


if __name__ == "__main__":
    unittest.main()
