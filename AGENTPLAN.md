# AGENTPLAN.md — Agentic Learning Coach

**Project:** Agentic Learning Coach — All Things Agentic Hackathon (deadline: Aug 31, 2026)
**Executor:** Antigravity (agentic IDE) — read §0 before doing anything
**Constraint #1:** Total cost must be ₹0. Every decision below is checked against the
Google Cloud Free Tier and the Gemini API free tier. If a step would cost money, STOP and ask.
**Constraint #2:** This is a 2-day build. Scope discipline beats elegance.

---

## 0. Rules for the executing agent (Antigravity)

1. Execute phases in order: 0 → 6. Do not skip ahead.
2. Every phase ends with a **Definition of Done (DoD)**. Do not proceed until all boxes check.
3. Never use anything on the **DO-NOT-USE** list (§4), even if it seems easier.
4. Never change the Firestore location, Cloud Run region, or model ID without asking.
5. If a command fails twice with the same error, stop and report — do not brute-force.
6. Prefer the simplest thing that passes the DoD. No extra features.
7. Secrets never go in code, git, or logs. Only `.env` locally and Secret Manager in cloud.

### Locked assumptions (flip only if the human says so)

| Assumption | Value |
|---|---|
| Demo user | One Google account (the developer's Gmail), pre-consented via OAuth |
| Demo persona | "Priya" — working professional, IITM-BS-style online degree, DBMS course |
| Demo course | DBMS, weeks 1–6, 4–5 YouTube lectures **with captions enabled** |
| Exam date | Demo day + 5 days (set relative, so the demo always works) |
| Cloud region | `us-central1` (free-tier-safe for every service we use) |
| Firestore location | `nam5` multi-region, created ONCE (location is permanent) |
| Model | Gemini 3.5 Flash via **AI Studio API key** (confirm exact model ID in AI Studio) |
| Local env | Windows + WSL or Linux, Python 3.12, `gcloud` CLI installed |

---

## 1. What we are building

A learning coach that is an **agent**, not a chatbot. Generic tools (NotebookLM, ChatGPT
Study Mode) wait to be asked and forget between sessions. Ours maintains a per-concept
**mastery graph**, backward-plans revision into the learner's real Google Calendar against
their exam date, and a nightly **watchdog** job detects decaying concepts and proactively
creates a targeted drill + email nudge — with human approval before anything is sent.

**The 30-second demo moment:** the watchdog runs live on stage, notices "Normalization"
mastery has decayed to 0.38, generates a 5-question drill, drops a revision block into
Calendar, and drafts a nudge email. The presenter clicks **Approve**, the email sends.
ChatGPT cannot do this. That is the whole pitch.

---

## 2. Free-tier ground rules (read before touching the console)

### 2.1 The one uncomfortable truth

**Free tier ≠ no billing account.** All Google Cloud services require an active billing
account. Sign up for the **Free Trial**: $300 credit / 90 days, a card is required for
identity verification (temporary $0–$1 hold, **no automatic charges**, ever, during trial).
Do NOT click "Activate/Upgrade" — upgrading converts the account to paid-billing mode.

### 2.2 Cost architecture (why the bill is ₹0)

- **Model calls** → Gemini API key from **AI Studio** (free tier: Flash models, roughly
  5–15 RPM and ~1,000–1,500 requests/day; verify live numbers in AI Studio). Completely
  separate from Cloud billing; no card needed. Our single-user demo uses <100 calls/day.
- **Infrastructure** → Cloud free tier (table below). Our expected usage is <1% of every limit.
- **Two known micro-cost exceptions**, accepted and minimized:
  - *File Search indexing*: embeddings charged $0.15/1M tokens **once at indexing**.
    5 lecture transcripts ≈ 100K tokens ≈ **$0.015**, absorbed by free trial credit.
    Storage and query-time embeddings are free; free tier allows 1 GB / 10 stores.
    Strict-zero fallback (only if human insists): §10.4.
  - *Cloud Scheduler*: not in the Always-Free table; its own pricing grants
    **3 free jobs/month per billing account**. We use exactly 1 job. Fallback: §10.3.

### 2.3 Our services vs free limits

| Service | Free allowance | Our usage |
|---|---|---|
| Cloud Run | 2M requests/mo, 180K vCPU-s, 360K GB-s | <500 requests total |
| Firestore | 1 GiB, 50K reads/day, 20K writes/day | few hundred docs |
| Pub/Sub | 10 GiB messages/mo | ~60 messages total |
| Secret Manager | 6 active secret versions | 3 secrets |
| Cloud Build (deploys) | 2,500 build-min/mo | ~5 builds × 3 min |
| Artifact Registry | 0.5 GB images | keep 1 image, delete old |
| Cloud Logging | 50 GiB/mo | negligible |

### 2.4 Guardrails (do these in Phase 0, non-negotiable)

1. Create a **budget alert**: Billing → Budgets → amount **$1**, alerts at 50/90/100% to email.
2. Cloud Run: `--max-instances=1 --min-instances=0` (cold starts are fine for a demo).
3. After the hackathon, run the **kill switch** (§10.5) to leave nothing running.

---

## 3. Architecture

```
                         ┌──────────────────────────────────────────┐
  Browser (single-page   │            Cloud Run (us-central1)        │
  HTML/JS, served by     │  FastAPI app                              │
  FastAPI)               │   ├─ /ingest  ──► ingest.py cost router   │
   │  REST/JSON          │   │              (transcript API → Gemini) │
   ▼                     │   ├─ /chat, /quiz/* ──► ADK agent runner  │
                         │   │      coach (root)                     │
   Cloud Scheduler ──┐   │   │       ├─ tutor_agent  (File Search)   │
   1 job, nightly ───┼──► Pub/Sub   │       ├─ quizmaster_agent      │
   (fallback: GitHub │   topic      │       └─ planner_agent         │
   Actions cron)     │     │ push   │   ├─ /plan/* (Calendar tools)  │
                     │     ▼ (OIDC) │   └─ /internal/watchdog        │
                     │  /internal/  │        → decay scan → drills   │
                     │  watchdog    │        → pendingNudges (HITL)  │
                     └──────┬───────┴───────────────┬───────────────┘
                            │                       │
              ┌─────────────▼─────────┐   ┌─────────▼──────────────┐
              │ Firestore (nam5)      │   │ Google APIs (OAuth)    │
              │ learners, concepts,   │   │ Calendar (plan events) │
              │ quizAttempts, nudges  │   │ Gmail (approved nudges)│
              └───────────────────────┘   └────────────────────────┘
              ┌───────────────────────┐
              │ Gemini API (AI Studio)│  ← only paid surface is the
              │ + File Search store   │    ₹1-ish one-time indexing
              └───────────────────────┘
```

Four flows to implement, in this order:
1. **Ingest:** YouTube URL → free transcript → (fallback: Gemini reads URL) → .txt → File Search store → course doc in Firestore.
2. **Chat/Quiz:** user message → ADK `coach` routes to tutor (Socratic, grounded via File Search) or quizmaster (generates JSON quiz → grades → writes mastery to Firestore).
3. **Plan:** planner reads syllabus topics + mastery + exam date → creates spaced-repetition events in Google Calendar.
4. **Watchdog (the USP):** Scheduler → Pub/Sub → push (OIDC) → `/internal/watchdog` → recompute decayed mastery → for each weak concept: generate drill, create Calendar block, write `pendingNudges` doc → human approves in UI → Gmail send.

---

## 4. Tech stack — locked

### USE

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Team's strongest language |
| Agent framework | **google-adk** (Python) | Hackathon requirement; workflow + LLM agents |
| Model | Gemini 3.5 Flash, AI Studio key | Free tier; hackathon requires Gemini 3.5+ |
| RAG | Gemini **File Search** | Managed, free storage/query, auto-citations |
| Backend | FastAPI + uvicorn | Team knows it; one Cloud Run service |
| DB | Firestore Native | Free tier; ADK session/memory support |
| Events | Pub/Sub + Cloud Scheduler (1 job) | Event-driven story judges want |
| Auth | OAuth 2.0 (Testing-mode consent) | Calendar/Gmail write access |
| Actions | google-api-python-client (Calendar, Gmail) | Team already knows these APIs |
| Deploy | `gcloud run deploy --source` | Uses free Cloud Build minutes; no Docker needed |
| Frontend | ONE `static/index.html` + fetch() | 2 days; React build is a time trap |
| Retry | `tenacity` exponential backoff on all Gemini calls | Free tier throws 429s |

### DO-NOT-USE (each exists here because it costs money or kills the timeline)

| Do NOT use | Use instead | Reason |
|---|---|---|
| Vertex AI Gemini endpoints | AI Studio Gemini API key | No meaningful free tier; billing exposure |
| Vertex AI RAG Engine / Vector Search | Gemini File Search | Paid; File Search free tier covers us |
| Cloud SQL / AlloyDB / Spanner | Firestore | No Always-Free tier (trials only) |
| Memorystore (Redis) | Firestore / in-process cache | No free tier |
| GKE | Cloud Run | Cluster ops = days lost; free credit excludes compute |
| Cloud Storage buckets | Firestore document fields | Transcripts are text; keep zero moving parts (if ever needed: only us-* regions have the 5 GB free allowance) |
| Firebase Auth / multi-user login | One pre-consented demo user | OAuth web onboarding is post-hackathon scope |
| Cloud Functions | Same Cloud Run service | One service, one deploy, less to break |
| BigQuery analytics | `events` audit collection in Firestore | Roadmap, not demo |
| TTS / voice / Live API | Skip (roadmap slide) | Stretch goal only if Phase 5 finishes early |
| Pro models | Flash only | Free tier = Flash-class models only |
| React/Next.js | Static HTML + vanilla JS | Build tooling burns hours we don't have |

---

## 5. Repo layout

```
coach-agent/
├── AGENTPLAN.md              ← this file
├── requirements.txt
├── main.py                   ← FastAPI app: all HTTP endpoints
├── ingest.py                 ← DONE (exists) — YouTube cost router
├── google_auth.py            ← DONE (exists) — OAuth bootstrap
├── agents/
│   ├── coach.py              ← root LlmAgent + routing instructions
│   ├── tutor.py              ← Socratic tutor + File Search tool
│   ├── quizmaster.py         ← quiz gen (structured JSON) + grading + mastery writes
│   ├── planner.py            ← revision plan + Calendar tool calls
│   └── watchdog.py           ← headless decay-scan agent (no chat UI)
├── core/
│   ├── db.py                 ← Firestore client + all collection helpers
│   ├── mastery.py            ← decay math + next-review scheduling
│   ├── gemini.py             ← genai client, MODEL constant, tenacity retry wrapper
│   └── config.py             ← env vars, constants (region, model, half-life)
├── tools/
│   ├── calendar_tools.py     ← create_event, list_events (ADK FunctionTools)
│   └── gmail_tools.py        ← send_email (HITL-gated)
├── scripts/
│   ├── seed_demo.py          ← creates Priya, course, pre-decayed mastery
│   └── kill_switch.sh        ← §10.5
└── static/
    └── index.html            ← chat + quiz + mastery table + nudge approvals
```

`requirements.txt`: `google-adk google-genai fastapi uvicorn google-cloud-firestore
google-api-python-client google-auth google-auth-oauthlib youtube-transcript-api
tenacity python-dotenv pydantic`

---

## 6. Firestore data model (all writes go through `core/db.py`)

```
learners/{learnerId}
  name, email, timezone:"Asia/Kolkata", createdAt

learners/{learnerId}/courses/{courseId}
  title, examDate (timestamp), fileSearchStore (store name),
  sourceVideos: [ {videoId, path_used, chars} ], syllabusTopics: [str]

concepts/{autoId}                      ← the mastery graph
  learnerId, courseId, name,
  mastery (0..1), attempts (int), halfLifeDays (default 7),
  lastAssessedAt, nextReviewAt,
  history: [ {ts, score} ]             ← append-only, powers the analytics line

quizAttempts/{autoId}
  learnerId, courseId, conceptNames: [str], score, items: [...], createdAt

pendingNudges/{autoId}                 ← HITL queue; nothing sends without approval
  learnerId, conceptName, reason, drillQuizId, calendarEventId,
  emailDraft {subject, body}, status: "pending|approved|sent", createdAt

events/{autoId}                        ← audit log; screenshot this for the demo
  type ("ingest|quiz|plan|watchdog|nudge"), payload, createdAt
```

**Decay math (`core/mastery.py`):**
`effective_mastery = mastery × 0.5 ** (days_since_last_assessed / halfLifeDays)`
`halfLifeDays = 7 × min(attempts, 3)` (more practice → slower forgetting)
Watchdog fires when `effective_mastery < 0.5` **or** `nextReviewAt <= now`.
On re-assessment: `mastery = 0.4×old + 0.6×new_score`, recompute `nextReviewAt`.

---

## 7. Phases

### Phase 0 — Accounts & guardrails (~1 h, human does this with agent guiding)

- [ ] Create/select GCP project; sign up Free Trial (card → temporary hold only; do NOT "Activate/Upgrade")
- [ ] Create budget alert $1 (50/90/100% → email)
- [ ] Enable APIs:
  `gcloud services enable run.googleapis.com firestore.googleapis.com pubsub.googleapis.com cloudscheduler.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com calendar-json.googleapis.com gmail.googleapis.com`
- [ ] Create Firestore: `gcloud firestore databases create --location=nam5 --type=firestore-native` (⚠ location is PERMANENT)
- [ ] AI Studio → create API key → note live free-tier rate limits shown for your account
- [ ] OAuth consent screen: External, **Testing**; add demo Gmail as test user; scopes:
  `openid`, `userinfo.email`, `userinfo.profile`, `calendar.events`, `gmail.send`
- [ ] OAuth client (Web application), redirect `http://localhost:8080/`; download `client_secret.json`

**DoD:** budget alert visible in console; Firestore DB exists; API key works with a
one-line `generate_content("say hi")`; `client_secret.json` downloaded.

### Phase 1 — Local skeleton + existing files green (~2 h)

- [ ] `python -m venv .venv && pip install -r requirements.txt`
- [ ] `.env`: `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `MODEL=gemini-3.5-flash` (confirm ID in AI Studio)
- [ ] Run `google_auth.py` → consent as demo user → smoke test prints calendars + Gmail address
  (⚠ Testing-mode refresh tokens expire after **7 days** — re-run this file if auth breaks on demo day)
- [ ] Run `ingest.py <youtube-url>` on all 4–5 demo lectures → transcripts in `transcripts/`, `ingest_cost_log.jsonl` shows `free_transcript` path
  (⚠ this works from a laptop; Cloud Run IPs are usually blocked by YouTube — that is expected; ingestion is a local/seed-time activity)
- [ ] Create ONE File Search store; upload transcripts; store its name in the course doc

**DoD:** transcripts on disk; cost log shows free path; OAuth smoke test passes;
a File Search query returns a grounded answer with citation.

### Phase 2 — Agent core: tutor + quizmaster + mastery (~4 h)

- [ ] `core/gemini.py`: genai client + `generate_with_retry()` (tenacity, backoff on 429, max 5 tries)
- [ ] `agents/tutor.py`: Socratic system prompt ("never give the answer directly; ask guiding questions; cite material"); attach File Search (use ADK's built-in FileSearchTool if present in installed version, else a FunctionTool calling the genai client)
- [ ] `agents/quizmaster.py`: generates 5-question JSON quiz for a topic (structured output schema); `grade()` compares answers; writes `quizAttempts` + updates `concepts` via `core/mastery.py`
- [ ] `agents/coach.py`: root agent, routes between tutor/quizmaster/planner by intent
- [ ] CLI test harness (`python -m agents.coach`) — no web UI yet

**DoD:** from CLI: ask a DBMS question → Socratic grounded answer; request "quiz me on
normalization" → 5 questions → submit answers → Firestore `concepts` doc updated with
new mastery + `nextReviewAt`.

### Phase 3 — Planner + Calendar (~2 h)

- [ ] `tools/calendar_tools.py`: `create_revision_event(title, start_iso, duration_min, description)` using stored OAuth token
- [ ] `agents/planner.py`: input = syllabusTopics + mastery + examDate → output = spaced plan (weak concepts early+repeated; strong concepts once); creates events via tool; writes `events` audit doc
- [ ] Verify events appear in the demo account's real Google Calendar

**DoD:** "make my study plan" → 6–10 Calendar events across the coming days, weighted
toward low-mastery concepts; audit doc written.

### Phase 4 — Watchdog: the event-driven USP (~3 h)

- [ ] `agents/watchdog.py` headless function `run_nightly()`: scan all concepts → decay filter → per weak concept: generate drill quiz (reuse quizmaster), create Calendar block, create `pendingNudges` doc with drafted email. **Never sends email.**
- [ ] Endpoint `POST /internal/watchdog` in `main.py`, protected: verify OIDC token from Pub/Sub push (use `google.oauth2.id_token.verify_oauth2_token` with audience = service URL) AND reject if missing
- [ ] Pub/Sub: `gcloud pubsub topics create watchdog-tick`
- [ ] Push subscription with OIDC service account (grant it `roles/run.invoker`)
- [ ] Scheduler (1 job, within the 3-free-jobs allowance):
  `gcloud scheduler jobs create pubsub watchdog-nightly --location=us-central1 --schedule="0 19 * * *" --time-zone="Asia/Kolkata" --topic=watchdog-tick --message-body='{"action":"nightly"}'`
- [ ] Approve flow: `GET /nudges` lists pending; `POST /nudges/{id}/approve` → `gmail_tools.send_email` → status `sent`
- [ ] Local test: `curl -X POST localhost:8080/internal/watchdog` (dev bypass flag) → pending nudge appears

**DoD:** one command triggers the full chain: decayed "Normalization" → new drill +
Calendar block + pending email draft → approve → real email received. Audit docs for
each step.

### Phase 5 — Minimal web UI + deploy (~3 h)

- [ ] `static/index.html`: four panels — (1) chat, (2) quiz display/answer, (3) mastery table (`GET /mastery` → name, effective mastery bar, next review), (4) pending nudges with Approve button. Vanilla JS `fetch()`, no frameworks, no build step
- [ ] Secrets: create 3 secrets (`gemini-key`, `oauth-token`, `client-secret`) — 3 of 6 free versions
- [ ] Deploy: `gcloud run deploy coach --source . --region=us-central1 --max-instances=1 --min-instances=0 --allow-unauthenticated --set-secrets=GEMINI_API_KEY=gemini-key:latest --update-secrets=...` (map all three)
- [ ] Add the Cloud Run URL as an OAuth redirect URI (for future web flow; token already works)
- [ ] Delete old Artifact Registry images beyond the latest (0.5 GB cap)

**DoD:** public Cloud Run URL serves the UI; full loop works on the deployed URL;
Logs Explorer shows the watchdog run; billing report shows $0.00 usage cost.

### Phase 6 — Seed, demo, submit (~3 h, Aug 31)

- [ ] `scripts/seed_demo.py`: learner "Priya", DBMS course, examDate = today+5, transcripts ingested, mastery seeded so **Normalization is decayed (0.38)** and 2 other concepts are healthy
- [ ] Rehearse the 30-second watchdog moment end-to-end twice
- [ ] Record ~4-min video: problem → chatbot comparison ("ChatGPT forgets; this acts") → live loop → architecture slide → free-tier cost slide ($0.00) → roadmap
- [ ] README: problem, USP, architecture diagram, free-tier table, setup steps, demo script
- [ ] Public GitHub repo; Devpost submission: track = Collaborative Partner (Taskmaster elements inside); explicit requirement checklist: **Gemini 3.5 ✓, ADK ✓, Cloud Run + Firestore + Pub/Sub + Scheduler + Secret Manager ✓**
- [ ] Bonus: short public build post with the hackathon hashtag

**DoD:** submitted on Devpost before the deadline. Everything else is secondary.

---

## 8. Security & HITL rules (judging rubric: architectural discipline)

1. No email ever sends automatically. Watchdog only drafts; humans approve.
2. `/internal/*` endpoints require the OIDC token (cloud) or `DEV_BYPASS=1` (local only; never set in cloud env).
3. OAuth token and API key only in Secret Manager / `.env` (gitignored). Never logged.
4. Least-privilege scopes only (`calendar.events`, `gmail.send` — no full-mailbox scope).
5. Every agent action writes an `events` audit doc — this doubles as demo material.

---

## 9. Rate-limit survival (Gemini free tier)

- All Gemini calls go through `generate_with_retry()` (tenacity, exponential backoff, honor 429).
- Batch: ONE quiz-generation call per topic (not per question).
- Cache: File Search store name, learner doc, and course doc in memory per process.
- The demo script uses <50 model calls; a fresh day of quota is >1,000. If quota is ever
  exhausted mid-demo: UI shows "daily free quota reached — resets at midnight Pacific"
  (graceful degradation is itself a rubric point).

---

## 10. Gotchas & contingencies

1. **YouTube blocks datacenter IPs.** Ingestion from Cloud Run will fail. Ingestion is a
   seed-time/local activity by design; the demo uses pre-ingested material. State this
   proudly in the writeup — it is a deliberate cost decision, and `ingest.py` logs it.
2. **OAuth Testing mode → refresh tokens die in 7 days.** If Calendar/Gmail calls start
   returning 401, re-run `google_auth.py` and update the `oauth-token` secret.
3. **Cloud Scheduler free jobs:** the Always-Free table doesn't list Scheduler; its product
   pricing grants 3 free jobs/month per billing account. We use 1. Strict-zero fallback:
   delete the job and use a **GitHub Actions cron** (free) that POSTs to
   `/internal/watchdog` with a shared-secret header — document the swap in README.
4. **Strict-zero File Search fallback (only if the ₹1 indexing cost is unacceptable):**
   skip File Search; store transcript chunks (≤500 docs) in Firestore; retrieve by keyword
   overlap in `tutor.py`. Quality drops slightly; cost becomes exactly ₹0.
5. **Kill switch (run after judging):**
   `gcloud scheduler jobs delete watchdog-nightly -q;
    gcloud run services delete coach --region=us-central1 -q;
    gcloud pubsub subscriptions delete watchdog-push -q; gcloud pubsub topics delete watchdog-tick -q`
   then delete Artifact Registry images and the 3 secrets. Firestore data < 1 GiB is free to keep.
6. **Cold starts:** first request after idle takes a few seconds — warm the service with
   one refresh before recording the demo.

---

## 11. Post-hackathon roadmap (for the pitch, not the build)

Multi-user OAuth onboarding → WhatsApp nudge channel → voice viva mode (ADK streaming) →
BigQuery learning analytics → per-institution cohorts (IITM BS pilot) → mobile PWA.
