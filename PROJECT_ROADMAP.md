# Offline AI Learning Platform — Project Roadmap

Updated: 2026-10-18

## Version 1 foundation

| Area | Status | Evidence and limits |
| --- | --- | --- |
| Basic FastAPI and Ollama chat | Completed | Chat route, local Ollama service, status endpoint, React chat. |
| Document RAG | Completed | PDF/TXT upload, chunking, local embeddings, Chroma storage, retrieval, grounded answers. |
| Conversations and sources | Completed | SQLite sessions, follow-up context, source references, conversation API and tests. |
| Multi-document retrieval | Completed | Selected document IDs, comparison prompting, metadata filtering and retrieval tests. |
| Frontend experience | Completed | Document dashboard, saved conversations, responsive chat, loading and error states; build and lint pass. |
| Version 1 testing, security and deployment | In progress | Backend tests exist; frontend tests, deployment setup and security review remain. This work overlaps Version 2 final hardening. |

The Version 1 code remains the foundation. Version 2 does not replace its RAG pipeline.

## Version 2 phases

**Phase 5 overall status: Completed.** Teacher-owned courses, materials, quiz assignments, enrollment, student results, and analytics are implemented in the teacher portal.

**Phase 6 overall status: Automated implementation and validation complete; physical LAN acceptance pending.** Steps 6.1–6.9 are implemented. A trusted second-device browser and microphone check is required before declaring the deployment accepted.

| Step | Status | Dependency or evidence |
| --- | --- | --- |
| 1.1 FastAPI project setup | Completed | Existing `backend/app/main.py`. |
| 1.2 Ollama integration | Completed | Existing local Ollama service. |
| 1.3 Chat API | Completed | Existing chat request/response schemas and route. |
| 1.4 React chat interface | Completed | Existing chat components and API service. |
| 2.1 Document upload | Completed | Existing PDF/TXT upload with 100 MB limit. |
| 2.2 Text extraction | Completed | Existing PDF/TXT extraction. |
| 2.3 Text chunking | Completed | Existing chunking service and source metadata. |
| 2.4 Embedding generation | Completed | Existing local sentence-transformer service. |
| 2.5 Vector database | Completed | Existing Chroma collection and document filters. |
| 2.6 RAG pipeline | Completed | Existing retrieval, grounding and Ollama response path. |
| 2.7 Document management | Completed | Existing list and delete API and frontend. |
| 3.1 Learning content structure | Completed | Migrated SQLite catalog and tested subject, topic, lesson, objective and document-link APIs. |
| 3.2 AI lesson generator | Completed | Structured local Ollama lesson endpoint; optional document-grounded excerpts; live lesson check passed. |
| 3.3 Explanation levels | Completed | Beginner, intermediate and advanced request values and prompt instructions. |
| 3.4 Automatic quiz generation | Completed | Typed MCQ, true/false and short-answer quiz drafts with count/type checks, duplicate detection and source validation. |
| 3.5 Quiz evaluation | Completed | Deterministic practice scoring, answer explanations and provisional short-answer rubric feedback; no authoritative scores saved. |
| 3.6 Flashcard generator | Completed | Topic, lesson text, document and quiz-mistake inputs; browser flip/known controls. Persistent reviews were added in 6.5. |
| 3.7 Vocabulary practice | Completed | Definitions, examples, Nepali meanings and self-check prompts. |
| 3.8 Bilingual explanations | Completed | English, Nepali and bilingual controls, local prompts and Devanagari checks; human review remains important. |
| 3.9 Learning tools frontend | Completed | Lesson viewer, quiz draft editor/player/results, flashcards, vocabulary, difficulty/language/source selectors. Build and lint pass. |
| 4.1 Student database design | Completed | Additive SQLite migration for users, profiles, enrollment, saved quizzes, attempts/answers, lesson progress and study sessions. |
| 4.2 Authentication | Completed | Registration, PBKDF2 password hashes, login, seven-day revocable bearer sessions, logout and protected routes. |
| 4.3 Student profiles | Completed | Display name, email, language, goals and enrolled-course relation; dashboard shows progress. |
| 4.4 Quiz attempt history | Completed | Server-stored quiz snapshot, owned attempts and answers, score, time and topic aggregates. |
| 4.5 Learning progress | Completed | Idempotent lesson completion, attempt totals/scores, server-measured study sessions and topic totals. |
| 4.6 Student dashboard | Completed | Courses, completed lessons, recent scores, study history and topic progress; recommendations and due reviews were added in 6.5–6.6. |
| 4.7 Student API security | Completed | Bearer checks and user-scoped queries; cross-account access tests for quizzes, attempts, lessons and sessions. |
| 5.1 User roles | Completed | Student and teacher roles; teacher signup requires a server-configured code; protected routes enforce role and ownership. |
| 5.2 Course management | Completed | Teacher-owned courses, topics and ordered lessons with editing; legacy unowned catalog remains separate. |
| 5.3 Material management | Completed | Teacher PDF/TXT upload through existing pipeline, course association, metadata editing, authorized download/removal; student download requires enrollment. |
| 5.4 Quiz management | Completed | Generated/manual drafts, question editing, immutable publication, enrolled-student assignment and server-scored one-time submission. |
| 5.5 Student management | Completed | Enrollment by account email, removal, roster, course progress and assigned results limited to the owning teacher. |
| 5.6 Teacher analytics | Completed | SQL-based completion, assigned scores, topic averages, course-tagged study time, lesson progress and evidence-gated weak-topic distribution. |
| 5.7 Teacher frontend | Completed | Teacher portal for courses, topics/lessons, materials, quiz editor/assignment/results, students and charts; build/lint pass. |
| 6.1 Student knowledge profiles | Completed | Student-scoped topic profiles derived from saved answer records; catalog IDs stay distinct, free-practice topics normalize names, provisional answers are excluded from mastery. API, dashboard, and tests pass. |
| 6.2 Weak-topic detection | Completed | Evidence-gated student topic status and reasons from saved objective answers; provisional-only and sparse records remain unclassified. |
| 6.3 Adaptive difficulty | Completed | Optional signed-in quiz setting adjusts one level from selected difficulty using the student's own free-practice topic status; server returns effective level and reason. |
| 6.4 Personalized quizzes | Completed | Student-scoped weak/unpracticed topic planner, prior-error cues and lesson objectives feed structured quiz generation; catalog topic identity persists with attempts. |
| 6.5 Spaced repetition | Completed | Saved flashcard decks, due queue, deterministic Again/Hard/Good/Easy schedule and owned review history. |
| 6.6 Recommendations | Completed | Explainable next actions from due cards, assigned quizzes, weak topics, completed lessons to revisit and available next lessons. |
| 6.7 Optional speech module | Completed | Local Piper/Vosk adapters, capability status, speech UI, vocabulary listening and repeat-after-me transcription. English voice and recognizer are cached in this workspace; authenticated synthesis and transcription of Piper-generated audio passed. Browser microphone interaction remains for final testing. |
| 6.8 Offline LAN deployment | Automated checks complete; second-device check pending | React and API use one configurable HTTPS origin; local CA/certificate launcher, LAN password gate, rate limits, security headers, offline instructions and real TLS loopback smoke pass. A trusted second-device browser and microphone check remain. |
| 6.9 Final testing and docs | Automated checks and docs complete; physical acceptance pending | 82 backend tests, 3 frontend tests, build/lint, TLS, speech and scanned-PDF-to-sourced-quiz smoke pass. Architecture, restore instructions, security notes and a device checklist are documented. |

### Phase 5 completion record

- Backend: 56 unit/API tests passed on 2026-10-17, including teacher role and ownership checks, course materials, quiz assignment and grading, enrollment, and analytics over stored records.
- Frontend: production build and lint passed on 2026-10-17 for the teacher and student portals.
- Teacher quiz generation uses the existing Ollama service; the Phase 5 API workflow was tested with a mocked model response. A live teacher-route Ollama check and browser interaction tests remain for final testing.

### Phase 6.1 completion record

- Topic profiles report attempts, correct and incorrect objective answers, provisional answer count, recent accuracy, mastery estimate, last practice time, and evidence level. The estimate weights the most recent three attempts at 60% and all attempts at 40%; it is a practice indicator, not a validated prediction.
- A protected `GET /api/student/knowledge-profile` endpoint and the student dashboard expose each student's own results. Existing saved attempts are projected on read, so no migration or duplicate profile table is needed.
- Backend: 59 tests passed on 2026-10-18, including new calculation, ownership, provisional-answer, and catalog-ID checks. Frontend production build and lint passed.

### Phase 6.2–6.3 completion record

- A topic becomes weak only after at least two attempts and five scored objective answers. Mastery below 60%, or recent accuracy below 50% with repeated incorrect answers, identifies a review topic. Strong topics need both mastery and recent accuracy of at least 80%; other supported topics are developing.
- The dashboard shows the status, explanation, and an intermediate-baseline difficulty suggestion. Its practice action opens a free-practice topic with adaptive mode selected. Signed-in quiz generation can optionally move one level down for weak topics or up for strong topics; it keeps the chosen level for sparse or mixed evidence and returns the applied decision. Manual mode remains available.
- Adaptive quiz lookup uses only the authenticated student's normalized free-practice topic. Catalog topics remain separate by ID in the dashboard and are not conflated by title during quiz generation. No data migration was needed.
- Backend: 62 tests passed on 2026-10-18, including weak/strong thresholds, sparse evidence, ownership, and adaptive generation. Frontend production build and lint passed.

### Phase 6.4–6.7 implementation record

- Personalized quizzes choose a student-owned weak topic, an accessible unpracticed catalog topic, or a topic needing more evidence. Up to three saved objective mistakes and available lesson objectives guide new questions. Catalog topic IDs remain linked after attempts. Manual quizzes remain available.
- Migration `0004_spaced_repetition.sql` adds catalog-linked personalized quiz IDs, saved decks/cards, due dates and rating events. The interval rule is deterministic and bounded; review history and due cards enforce student ownership.
- Dashboard recommendations explain why to review cards, take an assigned quiz, practice a weak topic, revisit a completed lesson or read an available next lesson.
- Speech has local-only Piper/Vosk endpoints and UI. Piper 1.8.0, Vosk 0.3.45, the `en_US-lessac-medium` voice and `vosk-model-small-en-us-0.15` recognizer are installed in the project environment/cache. `scripts.smoke_speech` passed authenticated status, WAV synthesis and recognition of Piper-generated speech. Missing model files disable the corresponding capability and return 503. Transcription is not a phonetic assessment.
- Backend: 78 tests passed on 2026-10-18, including personalized focus, catalog access/identity, deterministic review intervals, ownership, recommendations and speech failure paths. Frontend production build and lint passed.

### Phase 6.8 implementation record

- FastAPI serves the built React app and API from one HTTPS origin. Frontend requests are relative to that origin, while Vite proxies local development requests.
- `scripts.run_lan` binds a private IPv4 address, generates a local CA and certificate with that IP in its SAN, prompts for a LAN password and starts one HTTPS worker. The gate uses a secure, HTTP-only cookie; account and gate attempts are rate limited. Security headers limit browser resource origins.
- `scripts.smoke_lan` passed a real TLS loopback check of certificate trust, the password gate, cookie, API health and built React page. Backend: 81 tests passed; frontend build and lint passed on 2026-10-18.
- `backend/LAN_DEPLOYMENT.md` covers offline prerequisites, client CA trust, private-network firewall access, backups and verification. A second-device browser and microphone acceptance test is still needed.

### Phase 6.9 validation record

- Backend: 82 unit/API tests passed on 2026-10-18, including role ownership, RAG regression, LAN password throttling and API cache prevention. Real HTTPS smoke passed on loopback and the desktop's Wi-Fi IP (192.168.1.73) after the final build.
- Frontend: 3 Node tests passed for same-origin API paths and microphone WAV encoding/resampling; production build and lint passed. These tests do not replace real browser interaction checks.
- Offline smoke: authenticated Piper/Vosk synthesis and transcription passed. A synthetic scanned PDF was parsed by Marker, embedded into temporary Chroma, answered by local Ollama with a page source, and used to generate a sourced quiz.
- `ARCHITECTURE.md`, `backend/FINAL_VALIDATION.md`, and expanded `backend/LAN_DEPLOYMENT.md` document the data flow, stores, test commands, backup restoration and physical-device acceptance. Edge headless automation did not complete in this Windows session; a trusted second device and microphone remain unverified.

## Current and next task

- **Latest implemented task:** Version 2 step 6.9 automated validation and documentation.
- **Next task:** Trusted second-device LAN and microphone acceptance using `backend/FINAL_VALIDATION.md`.

## Known issues and constraints

- `backend/requirements.txt` pins direct backend packages. Marker and speech model files are cached separately under `backend/.models/` and must be downloaded once before offline use on a new machine.
- The production frontend uses same-origin API paths; the Vite development server proxies `/api` and `/rag` to local FastAPI. A second-device browser check of the built site remains.
- Student and teacher records use revocable bearer sessions and owner-scoped queries. Teacher registration is disabled until `TEACHER_REGISTRATION_CODE` is set on the backend.
- Lesson source IDs refer to Chroma documents, which have no relational foreign key. Creation validates the source; future document deletion can leave a stale link. Lesson generation must recheck sources.
- Legacy unowned catalog records remain editable through the older public catalog API for backward compatibility. Teacher-owned course catalog records are hidden from its public reads and protected from its writes.
- Frontend path/audio unit tests pass; full browser interaction and a second-device offline/LAN check remain for physical acceptance. HTTPS, gate, cookie, API and built frontend passed a loopback smoke check.
- Anonymous quiz drafts remain temporary; signed-in student practice and teacher-assigned attempts are persisted. Published teacher quizzes are immutable and assigned once per student.
- Public draft scoring still accepts a client-supplied quiz. Saved student attempts use the server-stored quiz, but all AI-generated questions remain practice material; short-answer keyword feedback is provisional.
- Course creation, enrollment and materials are available in the teacher portal. Student recommendations now use saved progress, enrollment and review records.
- Phase 5 analytics use only teacher-assigned quizzes, currently enrolled students and course-tagged study sessions. Existing general study sessions are excluded from course study totals. Weak-topic distribution requires at least two attempts and less than 60% total points for that student/topic.
- Phase 6 mastery is an explainable score over saved objective answers, not a validated measure of comprehension. Short-answer rubric feedback remains provisional and does not affect mastery or weak-topic status; topics with fewer than two attempts or five objective answers are marked as early estimates. Personalized quiz prompts use prior errors and catalog objectives as cues; generated content still needs human review.
- The local speech runtime has English (US) models configured on this host. Other installations need matching model files. HTTPS and CA trust are documented for LAN microphones; real browser capture on another device remains unverified.
- Bearer tokens are stored in browser session storage and expire after seven days. LAN mode has HTTPS, a shared access password, secure cookies, rate limits, response security headers and `no-store` API responses. General document chat is a shared workspace for anyone with the LAN password; course materials have separate enrollment checks. Do not expose the LAN port to the public internet.
- Local model outputs can have factual or Nepali-language errors even when they pass structural checks. A teacher should review generated material.
