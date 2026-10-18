# Phase 6.9 validation and acceptance

Validated on 2026-10-18 in the project Windows environment. All checks below
use local services and models; test PDFs and speech samples are synthetic or
temporary, and the scripts do not create student accounts in the live database.

| Check | Command from `backend/` or `frontend/` as shown | Result |
| --- | --- | --- |
| Backend unit and API integration, including role ownership and RAG regression | `.\.venv\Scripts\python.exe -m unittest discover -s tests` | 82 passed. |
| Frontend build and TypeScript | From `frontend/`: `npm run build` | Passed. |
| Frontend lint | From `frontend/`: `npm run lint` | Passed. |
| Frontend offline path and microphone WAV tests | From `frontend/`: `npm test` | 3 passed with Node 24. |
| Real HTTPS loopback, certificate trust, LAN gate, API and built React | `.\.venv\Scripts\python.exe -m scripts.smoke_lan` | Passed. |
| HTTPS bind to this desktop's Wi-Fi address and verified certificate | `.\.venv\Scripts\python.exe -m scripts.smoke_lan --host 192.168.1.73` | Passed on 2026-10-18; this address may change. |
| Local Piper WAV and Vosk transcription through authenticated API | `.\.venv\Scripts\python.exe -m scripts.smoke_speech` | Passed. |
| Scanned PDF → Marker → embeddings → Chroma → RAG/Ollama → sourced quiz | `.\.venv\Scripts\python.exe -m scripts.smoke_pipeline --quiz` | Passed: one page, one sourced answer, one sourced question. |

The LAN tests also cover password throttling, account request throttling,
secure/HTTP-only cookies, response security headers, and `no-store` API
responses. Course and student API tests cover teacher ownership, enrollment,
and cross-account access. Model answers remain practice material requiring
human review.

## Physical-device acceptance still required

This workspace has no trusted second device or accessible microphone. Edge
headless automation also failed to accept DevTools commands in this Windows
session, so it did not establish a browser interaction result. Complete these
checks on a separate device before declaring the LAN deployment accepted:

1. Disconnect the host and client from the internet while keeping both on the
   same private LAN. Start local Ollama and the HTTPS launcher as described in
   `LAN_DEPLOYMENT.md`.
2. Trust only the copied `lan-ca.pem` on the client, verify its fingerprint,
   and open the host IP over HTTPS. Confirm no certificate warning, and confirm
   the password gate rejects a wrong password and accepts the correct one.
3. Sign in as a student. Open the dashboard and learning tools. Use a teacher
   account to create or view a course, then verify an enrolled student's
   assigned material and quiz. Confirm an unenrolled student cannot access it.
4. Upload a small PDF, ask a question that is answered on a known page, and
   inspect the source reference. Generate a quiz and save an attempt.
5. In the Speech tab, play a phrase, grant microphone permission, record it,
   and confirm a local transcript appears. Test browser reload and sign-out.
6. Inspect network activity: all app requests should target the host's HTTPS
   origin. Stop Ollama and confirm the app reports it unavailable without
   trying a cloud endpoint.

Record the client OS/browser, host IP, certificate fingerprint, test date, and
any failures. Browser microphone access requires a trusted HTTPS certificate.
