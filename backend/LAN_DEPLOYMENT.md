# Offline LAN deployment (Phase 6.8)

The desktop hosts the built React app and FastAPI on one HTTPS origin. Student
devices need only a browser on the same private network. Ollama, Marker, Chroma,
SQLite, Piper, and Vosk stay on the host desktop; no external server or internet
connection is used while the platform runs.

## Prepare the host once

1. Install backend packages and cache Ollama, embedding, Marker, Piper, and Vosk
   models before disconnecting from the internet. See `requirements.txt`,
   `MARKER_SETUP.md`, and the speech section of the root `Readme.md`.
2. Build the React frontend from the `frontend` directory with `npm ci` and
   `npm run build`. The resulting `frontend/dist` is served by FastAPI.
3. Find the desktop's private IPv4 address with `ipconfig` (for example,
   `192.168.1.25`). Keep the address stable with a DHCP reservation if possible.
4. Start the local Ollama service and confirm the configured model is present.
   Leave Ollama bound to the host; student devices connect only to FastAPI.

## Start the HTTPS server

From the `backend` directory on Windows:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_lan --host 192.168.1.25 --port 8443
```

Replace the IP with the desktop's actual private address. The launcher prompts
for a LAN access password of at least 12 characters. It creates a private local
CA and server certificate under `backend/.certs/`, then binds one Uvicorn worker
to the chosen address. The certificates, private keys, and cached models are
ignored by Git. The first visit to the site asks for the LAN password before
showing React or allowing API access. Student and teacher account sign-in still
uses their own credentials. LAN access cookies last 12 hours and are invalidated
when the server restarts. Account routes and password attempts are rate limited.

If the host IP changes, use a new `--cert-dir` path to create a certificate for
the new IP and trust its new CA on each client. Do not copy private key files to
student devices.

## Connect a student device

1. Copy only `backend/.certs/lan-ca.pem` to the device through a trusted local
   transfer and install it as a trusted certificate authority using that
   device's operating-system or browser instructions. Confirm its SHA-256
   fingerprint on the host with `Get-FileHash backend/.certs/lan-ca.pem -Algorithm SHA256`.
2. On the same private network, open `https://192.168.1.25:8443/` in the
   browser. Use the same IP as the certificate, enter the LAN access password,
   then sign in with a student or teacher account.
3. If Windows Firewall blocks the connection, allow inbound TCP port 8443 for
   the **Private** network profile only. Do not forward this port to the public
   internet.

The browser microphone needs a [secure context](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia),
so the CA must be trusted on each student device for speech capture. A browser
warning bypass is not a substitute for installing the CA. Voice recognition in
this checkout uses English (US) models. The real microphone flow on a second
device still needs manual acceptance testing.

## Verify and maintain

```powershell
# From backend, checks TLS, the password gate, cookie, API, and built React app.
.\.venv\Scripts\python.exe -m scripts.smoke_lan

# Also bind to this desktop's assigned private IP (replace with your actual IP).
.\.venv\Scripts\python.exe -m scripts.smoke_lan --host 192.168.1.25

# Checks authenticated offline speech with synthetic audio.
.\.venv\Scripts\python.exe -m scripts.smoke_speech
```

The SQLite database, Chroma index, and uploaded documents remain under
`backend/app/data/`. Stop the server before copying these folders for a backup.
For LAN mode, keep one backend worker because the SQLite stores and in-process
rate limits are shared by requests in this process. Large Marker uploads can
still use substantial CPU, GPU, and memory while other students are connected.

To restore, stop the HTTPS server and Ollama, keep a copy of the current
`backend/app/data/`, then replace that whole directory with the matching backup
of SQLite, Chroma, and documents. Start the backend and check `/health`, the
document list, and a student dashboard. Keep the model caches and Ollama model
store separately; data backups do not include them. If the host IP or machine
changes, generate and trust a new LAN certificate rather than reusing a key
from another host.

The automated checks cover a real HTTPS loopback connection. For release on a
LAN, complete the physical-device checklist in `FINAL_VALIDATION.md`, including
the trusted certificate, sign-in, document question, quiz, and microphone flow.
