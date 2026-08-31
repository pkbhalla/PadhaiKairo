# Agentic Learning Coach — Feature Map & USP

**Purpose:** single source of truth for (a) the parity features we must match, and (b) the
USP in full detail — for the build, the README, and the Devpost submission.
**Priorities:** `P0` = in the hackathon demo · `P1` = stretch, only if P0 is green · `P2` = roadmap slide.

---

## Part 1 — Parity features (table stakes)

Everything below is already shipped, mostly for free, by NotebookLM, ChatGPT Study Mode,
Gemini Guided Learning, StudyFetch, or Khanmigo. Users expect all of it. We never pitch
these as differentiators — they are the admission ticket.

| # | Feature | What it does | Who ships it today | Ours |
|---|---|---|---|---|
| 1 | Multimodal ingestion | Upload PDFs, slides, docs, YouTube links, audio, images/handwritten notes, pasted text | NotebookLM, ChatGPT, Gemini, StudyFetch | **P0** — PDF/notes/YouTube via our cost-router ingest; audio/handwriting via Gemini multimodal |
| 2 | Source-grounded chat with citations | Answers cite your materials, not the open internet | NotebookLM (flagship), all others | **P0** — File Search grounding |
| 3 | Summaries & study guides | Briefing docs, study guides, FAQs, timelines from sources | NotebookLM reports, StudyFetch Notes AI | **P0** — one grounded prompt, three output formats |
| 4 | Auto flashcards | One-click decks; adjustable count/difficulty; review missed cards only | NotebookLM, StudyFetch (spaced repetition + stats), Quizlet | **P1** — quiz-first; flashcards reuse the same generator |
| 5 | Quizzes & practice tests | Auto-generated, auto-graded, instant feedback | NotebookLM, StudyFetch (Quizfetch + stats), ChatGPT | **P0** — but ours feeds the mastery graph (see USP) |
| 6 | Socratic tutor mode | Guides with questions instead of giving answers | ChatGPT Study Mode, Gemini Guided Learning, Khanmigo (core identity) | **P0** — system prompt + grounding |
| 7 | Adaptive difficulty | Adjusts to learner level within/between sessions | ChatGPT Study Mode, Gemini Guided Learning, NotebookLM (Apr 2026) | **P0** — but driven by our mastery graph, not chat vibes |
| 8 | Weak-topic recap + next steps | Post-quiz: "you struggled with X; study this next"; regenerate targeted drills | NotebookLM (Apr 2026 upgrade) | **P0** — we extend this across weeks, not one session |
| 9 | Study plan generation | Breaks material into a structured plan | StudyFetch (Spark.E plans), Gemini Guided Learning | **P0** — ours lands in the real Calendar (see USP) |
| 10 | Progress tracking | Scores, completion, streaks, achievements | StudyFetch, NotebookLM (per-notebook) | **P0** — mastery table; streaks **P2** |
| 11 | Mind maps / visual outlines | Interactive concept maps from sources | NotebookLM | **P2** — skip; off-USP |
| 12 | Audio overviews / recaps | Podcast-style summary of materials | NotebookLM Audio Overviews, StudyFetch Audio Recap | **P2** — wow factor, not our wedge |
| 13 | Video explainers | Generated explainer videos from notes | StudyFetch Explainers | **P2** — skip |
| 14 | Live lecture transcription | Record a lecture → live transcript + notes | StudyFetch Live Lecture | **P1** — our ingest covers recordings already |
| 15 | Essay grading / writing coach | Rubric feedback on written work | StudyFetch, Khanmigo (coach, never ghostwrites) | **P2** — not needed for MCQ-based online-degree exams |
| 16 | Gamification | XP, streaks, rewards shops, leaderboards | StudyFetch (Bone Shop), Duolingo-style apps | **P2** — roadmap; deliberately not core (see §4) |
| 17 | Voice-to-voice tutor | Talk to the tutor hands-free | StudyFetch Spark.E, ChatGPT voice | **P1** — ADK bidirectional streaming if time allows |
| 18 | Multi-language | Tutoring and materials in many languages | StudyFetch (20+), Gemini/ChatGPT | **P1** — Gemini-native; ingest already pulls en/hi/ta captions |
| 19 | Mobile app + sharing | Native apps, shareable study sets | NotebookLM, StudyFetch, all | **P2** — responsive web app now; PWA on roadmap |
| 20 | Domain verification engines | e.g., real-time math-checking | Khanmigo (math verifier) | **P2** — out of scope |

**Deliberate skips (documented for judges):** mind maps, audio overviews, video explainers,
essay grading, gamification. They don't serve our wedge persona — deadline-bound exam prep
for working professionals — and each costs build days. Scope restraint is a feature.

---

## Part 2 — The USP in detail

### One-liner

> **NotebookLM knows your documents. Ours knows you — and acts before you ask.**

### The problem we attack

Every tool in Part 1 is **pull-based**: the learner must open the app, remember what they
studied, decide what to review, and ask. Working professionals in online degree programs
fail precisely at these four moments — not at comprehension, but at consistency. The
forgetting curve doesn't care that you had a sprint review. By exam week, three weeks of
"I'll revise this weekend" has quietly decayed into a cramming panic.

### The closed loop (this is the product)

```
        ┌──────────────────────────────────────────────────┐
        │                                                  │
        ▼                                                  │
   1. ASSESS ──► 2. MODEL ──► 3. PLAN ──► 4. INTERVENE ────┘
   grounded        mastery      calendar     proactive watchdog
   quizzes         graph        events       (runs unasked)
```

### Pillar 1 — Persistent mastery graph

**What:** every quiz answer updates a per-concept record: current mastery (0–1), full
attempt history, last-assessed timestamp, personal forgetting speed. Stored in Firestore,
persists forever, grows with every interaction.

**Why incumbents don't:** NotebookLM tracks missed flashcards *per notebook*; ChatGPT
"memory" stores fuzzy preferences ("user likes examples"); StudyFetch tracks quiz stats.
None maintain a structured, queryable, cross-session model of *what you know and how fast
you lose it*. Chat products remember conversations. We remember competence.

### Pillar 2 — Forgetting-curve engine

**What:** a decay model, not a scoreboard.
`effective_mastery = mastery × 0.5^(days_since_last_assessed / half_life)`, where the
half-life grows with successful repetitions (7 days after one pass, 21 after three).
Mastery you earned but haven't revisited is treated as **leaking**, not kept.

**Why incumbents don't:** StudyFetch's spaced repetition schedules *flashcard decks*;
nothing recomputes *concept-level* competence against wall-clock time and triggers action.
The difference: a deck tells you what to review if you show up; our engine assumes you
won't show up — and does something about it (Pillar 4).

### Pillar 3 — Deadline-aware autonomous planning

**What:** the learner states one fact — "my exam is on the 12th." The planner agent
backward-schedules spaced repetition from that date, weighted by mastery and decay, and
writes the sessions as **real events in the learner's actual Google Calendar** — next to
their standups and their kid's birthday, where time is actually negotiated.

**Why incumbents don't:** StudyFetch and Guided Learning produce plans *inside their app* —
a second calendar the learner must remember to check. A plan that lives outside your real
schedule is a wish, not a plan.

### Pillar 4 — Proactive watchdog (the signature)

**What:** an event-driven nightly job (Cloud Scheduler → Pub/Sub → Cloud Run) that needs
no human prompt. It recomputes decayed mastery across every concept; when something drops
below threshold or a review comes due, the agent: generates a fresh drill targeting exactly
that concept, blocks 15 minutes in the Calendar, and drafts a plain-English nudge email
("Your grasp of *Normalization* has slipped to ~38% since Tuesday — I've put a 5-question
drill on your calendar for tomorrow 8 PM").

**Why incumbents don't:** ChatGPT, Gemini, NotebookLM, StudyFetch — none will ever message
you first. They are products you *visit*. The entire hackathon thesis — "most AI waits for
you to ask; the next generation doesn't" — is this pillar.

### Pillar 5 — HITL-gated real-world action

**What:** the agent operates on real accounts (Calendar, Gmail), but nothing external ships
without a human clicking **Approve**. Every agent action — ingest, quiz, plan, watchdog,
nudge — writes an audit-log document, so "what did the agent do and why" is always
answerable. Autonomy with a paper trail.

**Why it matters:** un-gated automation on a user's real inbox is how agents lose trust in
one mistake. The approval queue is the trust contract — and it demonstrates the
architectural discipline the rubric scores.

### Pillar 6 — Honest longitudinal analytics

**What:** because the mastery graph holds *history*, the coach can say what no session-based
chatbot will: "You've attempted deadlocks 4 times in 3 weeks and stayed under 50% — your
errors cluster on lock-ordering, not definitions." Chatbots grade the current quiz and
flatter. A coach that owns your outcome across a semester can afford honesty.

---

## Part 3 — Head-to-head matrix

| Capability | NotebookLM | ChatGPT Study Mode | Gemini Guided Learning | StudyFetch | Khanmigo | **Ours** |
|---|---|---|---|---|---|---|
| Structured cross-session learner model | ✗ (per-notebook cards) | ✗ (fuzzy memory) | ✗ | partial (stats) | partial (in-course) | **✓ mastery graph** |
| Forgetting-curve modeling | ✗ | ✗ | ✗ | partial (deck-level SR) | ✗ | **✓ concept-level decay** |
| Initiates contact unasked | ✗ | ✗ | ✗ | ✗ (streak push notifs) | ✗ | **✓ watchdog agent** |
| Acts in real world (Calendar/Gmail) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ HITL-gated** |
| Real exam-date backward planning | ✗ | ✗ | partial (study plans) | partial (in-app plan) | ✗ | **✓ into real Calendar** |
| Honest longitudinal grading | ✗ | ✗ (sycophantic) | ✗ | partial | ✗ | **✓ pattern-level feedback** |
| Institution/course-context awareness | ✗ | ✗ | ✗ | ✗ | ✓ (Khan only) | **✓ any course, incl. institutional syllabi** |
| Content generation breadth | ✓✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ (parity subset, by choice) |

**Closest threats, stated honestly:** NotebookLM's April 2026 upgrade (weak-topic summary →
next-step → regenerate targeted drill) and StudyFetch's spaced repetition are within one
product cycle of Pillars 1–2. Neither crosses into Pillars 3–5: leaving their app, touching
your real calendar and inbox, and initiating contact. That crossing is the whole company.

---

## Part 4 — Defensibility (honest PM note)

Features are copyable; Google proved it by shipping quizzes into NotebookLM. What is not
copyable overnight: **distribution** (an institutional pilot, e.g., an online-degree
program whose syllabus, exam calendar, and grading patterns the agent natively knows),
**workflow embedding** (once a semester of your plan lives in your real Calendar, switching
costs are real), and **outcome data** (longitudinal mastery graphs compound in value).
Also structural: proactive outreach conflicts with the engagement model of chat products —
they are built to be visited; an agent is built to *work*. Strategy stays in the pitch:
wedge (deadline-bound online-degree learners) → expand.

---

## Part 5 — Demo proof & judging mapping

**The 30-second moment:** watchdog runs live → detects "Normalization" decayed to 0.38 →
generates a 5-question drill → drops a revision block in Calendar → drafts the nudge →
presenter clicks **Approve** → real email lands. Then the cut: "ChatGPT forgets you the
moment you close the tab. This one doesn't let you forget."

| Judging criterion | What evidences it |
|---|---|
| Innovation & operational utility (40%) | Real problem (working professionals + forgetting curve), closed loop, real actions |
| Architectural discipline (30%) | Event-driven watchdog, HITL gate, audit log, decay model, cost-routed ingestion, free-tier engineering |
| Demo & production readiness (30%) | Live Cloud Run URL, observable Scheduler/Pub/Sub/Firestore chain, rehearsed 30-sec moment, README spin-up |

---

## Part 6 — Devpost-ready copy

**Tagline:** The study coach that works while you sleep — it remembers what you're
forgetting and fixes it before your exam does.

**100-word description:**
Every AI study tool waits for you to ask. Agentic Learning Coach doesn't. It ingests your
lectures, quizzes you against your real exam date, and maintains a per-concept mastery
graph with a forgetting-curve model. A nightly watchdog agent detects decaying knowledge,
generates a targeted drill, books revision time in your Google Calendar, and drafts a nudge
email — you approve, it sends. Built with Gemini 3.5 Flash, Google ADK multi-agent
architecture, and Cloud Run + Firestore + Pub/Sub on a ₹0 free-tier budget, it closes the
loop that chatbots leave open: assess → model → plan → intervene → re-assess. Chatbots are
places you visit. This is an agent that works for you.
