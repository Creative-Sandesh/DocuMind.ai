"""Run the built app and API over HTTPS on a private desktop LAN address."""

import argparse
import getpass
import os
from pathlib import Path
import socket

import uvicorn

from scripts.lan_certificate import ensure_certificate, lan_ip


BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="This desktop's private LAN IPv4 address")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--cert-dir", type=Path, default=BACKEND_DIR / ".certs",
                        help="Private certificate directory (default: backend/.certs)")
    args = parser.parse_args()
    try:
        host = str(lan_ip(args.host))
        with socket.socket() as check:
            check.bind((host, 0))
    except (ValueError, OSError) as error:
        parser.error(f"Host IP must be assigned to this desktop: {error}")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    if not (FRONTEND_DIST / "index.html").is_file():
        parser.error("Build the frontend first: cd frontend; npm run build")

    password = os.environ.get("LAN_ACCESS_PASSWORD") or getpass.getpass("LAN access password (12+ characters): ")
    if len(password) < 12:
        parser.error("LAN access password must contain at least 12 characters")
    os.environ["LAN_ACCESS_PASSWORD"] = password

    try:
        ca_cert, server_cert, server_key = ensure_certificate(host, args.cert_dir.resolve())
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(f"Cannot prepare local HTTPS certificate: {error}")
    print(f"Open https://{host}:{args.port}/ after trusting {ca_cert} on each client device.")
    print("Keep lan-ca-key.pem and lan-server-key.pem private on this desktop.")
    uvicorn.run("app.main:app", host=host, port=args.port, ssl_certfile=str(server_cert),
                ssl_keyfile=str(server_key), proxy_headers=False, workers=1)


if __name__ == "__main__":
    main()
