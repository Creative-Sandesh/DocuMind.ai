"""LAN gate, account throttling, and local certificate checks."""

import tempfile
import unittest
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.lan_access import AuthRateLimit, LanAccessGate, SecurityHeaders
from scripts.lan_certificate import ensure_certificate


class LanDeploymentTests(unittest.TestCase):
    def test_gate_requires_password_and_allows_same_origin_cookie(self):
        app = FastAPI()
        app.add_middleware(LanAccessGate, password="example-long-password")

        @app.get("/")
        def home():
            return {"ready": True}

        @app.get("/api/private")
        def private():
            return {"ready": True}

        with TestClient(app, base_url="https://testserver", follow_redirects=False) as client:
            self.assertEqual(client.get("/").status_code, 303)
            self.assertEqual(client.get("/api/private").status_code, 401)
            self.assertEqual(client.get("/lan/unlock").status_code, 200)
            self.assertEqual(client.post("/lan/unlock", data={"password": "wrong"}).status_code, 401)
            unlocked = client.post("/lan/unlock", data={"password": "example-long-password"})
            self.assertEqual(unlocked.status_code, 303)
            self.assertIn("httponly", unlocked.headers["set-cookie"].lower())
            self.assertIn("secure", unlocked.headers["set-cookie"].lower())
            self.assertEqual(client.get("/api/private").json(), {"ready": True})

    def test_account_requests_are_limited_by_client_and_route(self):
        app = FastAPI()
        app.add_middleware(AuthRateLimit)

        @app.post("/api/student/login")
        def login():
            return {"ok": True}

        with TestClient(app) as client:
            for _ in range(12):
                self.assertEqual(client.post("/api/student/login").status_code, 200)
            limited = client.post("/api/student/login")
            self.assertEqual(limited.status_code, 429)
            self.assertIn("Retry-After", limited.headers)

    def test_lan_gate_limits_bad_passwords_and_prevents_api_caching(self):
        app = FastAPI()
        app.add_middleware(LanAccessGate, password="example-long-password")
        app.add_middleware(SecurityHeaders)

        @app.get("/api/student/me")
        def account():
            return {"email": "student@example.invalid"}

        with TestClient(app, base_url="https://testserver", follow_redirects=False) as client:
            for _ in range(5):
                self.assertEqual(client.post("/lan/unlock", data={"password": "wrong"}).status_code, 401)
            limited = client.post("/lan/unlock", data={"password": "example-long-password"})
            self.assertEqual(limited.status_code, 429)
            self.assertIn("Retry-After", limited.headers)
            self.assertEqual(client.get("/api/student/me").status_code, 401)

        restarted = FastAPI()
        restarted.add_middleware(LanAccessGate, password="example-long-password")
        restarted.add_middleware(SecurityHeaders)

        @restarted.get("/api/student/me")
        def restarted_account():
            return {"email": "student@example.invalid"}

        with TestClient(restarted, base_url="https://testserver", follow_redirects=False) as client:
            self.assertEqual(client.post("/lan/unlock", data={"password": "example-long-password"}).status_code, 303)
            response = client.get("/api/student/me")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_certificate_matches_lan_ip_and_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = ensure_certificate("192.168.1.25", Path(directory))
            self.assertEqual(paths, ensure_certificate("192.168.1.25", Path(directory)))
            certificate = x509.load_pem_x509_certificate(paths[1].read_bytes())
            names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            self.assertIn(ip_address("192.168.1.25"), names.get_values_for_type(x509.IPAddress))
            with self.assertRaisesRegex(RuntimeError, "different IP"):
                ensure_certificate("192.168.1.26", Path(directory))
