"""Start a temporary HTTPS server on an assigned IP and check its LAN gate."""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from scripts.lan_certificate import ensure_certificate


BACKEND_DIR = Path(__file__).resolve().parents[1]
PASSWORD = "lan-smoke-password-123"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="Assigned private IPv4 to test (default: loopback)")
    args = parser.parse_args()
    host = args.host
    with TemporaryDirectory() as directory:
        ca, _, _ = ensure_certificate(host, Path(directory))
        with socket.socket() as sock:
            sock.bind((host, 0))
            port = sock.getsockname()[1]
        command = [sys.executable, "-m", "scripts.run_lan", "--host", host,
                   "--port", str(port), "--cert-dir", directory]
        process = subprocess.Popen(
            command, cwd=BACKEND_DIR, env={**os.environ, "LAN_ACCESS_PASSWORD": PASSWORD},
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(base_url=f"https://{host}:{port}", verify=str(ca),
                              trust_env=False, follow_redirects=False, timeout=5) as client:
                last_error = ""
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("LAN server exited during startup")
                    try:
                        response = client.get("/health")
                        break
                    except (httpx.ConnectError, httpx.ConnectTimeout) as error:
                        last_error = str(error)
                        time.sleep(0.2)
                else:
                    raise RuntimeError(f"LAN server was unreachable: {last_error}")
                if response.status_code != 401 or client.get("/").status_code != 303:
                    raise RuntimeError("LAN gate did not protect the app")
                if client.get("/lan/unlock").status_code != 200:
                    raise RuntimeError("LAN unlock page is unavailable")
                unlocked = client.post("/lan/unlock", data={"password": PASSWORD})
                if unlocked.status_code != 303:
                    raise RuntimeError("LAN unlock failed")
                if client.get("/health").json() != {"status": "healthy"}:
                    raise RuntimeError("Authenticated API health check failed")
                account = client.get("/api/student/me")
                if account.status_code != 401 or account.headers.get("cache-control") != "no-store":
                    raise RuntimeError("Account API authorization or cache header failed")
                page = client.get("/")
                if page.status_code != 200 or "<html" not in page.text:
                    raise RuntimeError("Built frontend was not served over HTTPS")
                if "default-src 'self'" not in page.headers.get("content-security-policy", ""):
                    raise RuntimeError("LAN security headers are missing")
                print(f"HTTPS LAN smoke OK on {host}:{port}: gate, cookie, API and React build")
        except Exception as error:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            logs = process.stderr.read().decode(errors="replace") if process.stderr else ""
            raise RuntimeError(f"HTTPS smoke failed: {error}; server logs: {logs[-2000:]}") from error
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
