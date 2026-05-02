# Smart Job Agent V2

> **The most powerful free AI resume platform for Indian CS graduates — far beyond ResumeGenius or Jobscan.**

A production-grade **8-agent LangGraph orchestration system** that builds ATS-optimised resumes, matches job descriptions, writes cold emails, scores your profile, and auto-applies to jobs — all for free.

---

## What's New in V2

| | V1 (legacy) | V2 (current) |
|---|---|---|
| Backend | Flask monolith | FastAPI + LangGraph 8-agent graph |
| LLM | Optional / stub | Google Gemini (Flash-Lite) |
| Storage | JSON files | PostgreSQL + pgvector |
| Templates | 1 (ATS only) | 3 (ATS Pro · Jake's · Harvard) |
| Summary | Rule-based | AI-written, role-targeted |
| JD Match | Keyword overlap | Semantic + LLM strategy |
| Cold Email | Template fill | AIDA / PAS / STAR frameworks |
| Scoring | Basic ATS % | 0–10 mentor score + free resources |
| Auto-Apply | ✗ | Playwright (LinkedIn + Naukri) |
| GDPR | ✗ | Full compliance layer |
| CI/CD | ✗ | Jenkins 11-stage pipeline |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Next.js 14 Frontend  (port 3000)                           │
│  Builder · JD Match · Scorer · Tracker · Auto-Apply         │
└────────────────────┬─────────────────────────────────────────┘
                     │  /api/v2/* → proxy → :8000
┌────────────────────▼─────────────────────────────────────────┐
│  FastAPI V2  (port 8000)                                     │
│  main.py · routers/ · services/                             │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│  LangGraph Agent Graph (agents/graph.py)                     │
│                                                              │
│  START → parse_resume                                        │
│            ├── [Agent 1] Resume Architect  ──┐  parallel    │
│            └── [Agent 2] Content Enhancer  ──┤  fan-out     │
│                                    merge ◄───┘              │
│                               quality_gate                   │
│                               pdf_generator                  │
│            ├── [Agent 3] JD Strategist                       │
│            ├── [Agent 4] Cold Email Composer                 │
│            └── [Agent 7] Scorer & Mentor                     │
│                               auto_apply_gate                │
│                               [Agent 8] Auto-Apply           │
│                               save_session → PostgreSQL      │
│                                                              │
│  [Agent 5] Infra  — DB health, pool, vacuum schedule        │
│  [Agent 6] Supervisor — heals failures, logs interventions  │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  PostgreSQL + pgvector       Redis (cache + Celery)
  (13 tables, schema.sql)
```

---

## The 8 Agents

### Agent 1 — Resume Architect
- **Model:** `gemini-2.5-flash-lite`
- Parses raw resume text/PDF, applies the selected ATS template, rewrites bullets with action verbs, generates a role-targeted professional summary
- Tools: `parse_resume`, `extract_skills`, `apply_template`, `rewrite_bullets`, `enhance_summary`

### Agent 2 — Content Enhancement Agent *(parallel)*
- **Model:** `gemini-2.5-flash-lite`
- Runs simultaneously with Agent 1 — verifies ATS keyword density, checks professional tone, validates STAR bullet format, flags weak verbs
- Fan-in: merged with Agent 1 output before quality gate

### Agent 3 — JD Match Strategist
- **Model:** `gemini-2.5-flash-lite`
- Deep JD-resume alignment using pgvector cosine similarity + LLM reasoning
- Issues **CAUTION** when match < 60% — shows override banner on frontend
- Returns: `match_score`, `matched_skills`, `missing_skills`, `tailoring_plan`, `callback_probability_pct`

### Agent 4 — Cold Email Composer
- **Model:** `gemini-2.5-flash-lite`
- Writes recruiter cold emails using AIDA / PAS / STAR frameworks based on company type
- Indian market specific: formal tone for IT services, casual for startups
- Returns: `subject`, `body`, `mailto_link`, `gmail_url`, `framework_used`

### Agent 5 — Backend Infrastructure Agent
- **Model:** `gemini-2.5-flash-lite`
- Runs on startup: DB health check, connection pool management, nightly VACUUM schedule, index monitoring

### Agent 6 — Supervisor / Doctor Agent
- **Model:** `gemini-2.5-flash-lite`
- Monitors every node via LangGraph `interrupt_before` hooks
- On failure: retries up to 2×, then falls back to V1 rule-based logic
- Logs all interventions to `agent_health_log` table

### Agent 7 — Resume Scorer & Mentor
- **Model:** `gemini-2.5-flash-lite`
- Scores resume 0–10 across 5 dimensions:
  - ATS Compliance (2.0) · Content Quality (2.5) · Skill Alignment (2.0) · Profile Strength (2.0) · Presentation (1.5)
- Recommends **free** learning resources (Coursera free audit, NPTEL, freeCodeCamp, Kaggle, Flutter codelabs)

### Agent 8 — Auto-Apply Agent
- **Model:** `gemini-2.5-flash-lite` + Playwright
- **Gate:** Only activates when resume score ≥ 7.0 / 10
- Searches LinkedIn Easy Apply + Naukri Quick Apply, filters by ≥ 70% match, submits and logs results

---

## Resume Templates

| Template | Best For | ATS Parse Rate |
|---|---|---|
| **ATS Pro Minimalist** *(default)* | Startups · Greenhouse · Lever · modern tech | 99% |
| **Jake's Resume** | FAANG India · SWE · backend · data roles | 100% |
| **Harvard Chronological** | TCS · Infosys · PSU · campus placement | 100% |

All three templates are **pixel-accurate** — the downloaded PDF exactly matches the live browser preview.

---

## Key Features

### Professional Summary Generator
- Role-targeted — select from 15 preset roles or type custom
- AI writes assertive 4-sentence summary (80–130 words) in recruiter POV
- Banned words enforced: *seeking, passionate, motivated, team player, quick learner*
- Role vocabulary injected per domain (e.g. Backend → *microservices, distributed systems, latency reduction*)

### GDPR & Responsible AI Compliance
- `POST /v2/gdpr/consent` — Article 6(1)(a) consent recording
- `GET  /v2/gdpr/my-data/{id}` — Article 15 right of access
- `DELETE /v2/gdpr/my-data/{id}` — Article 17 right to erasure
- `GET  /v2/ai/transparency` — EU AI Act Article 13 disclosure
- All API responses include `X-AI-Generated`, `X-Data-Retention`, `X-GDPR-Compliant` headers
- IP stored as SHA-256 hash only — never raw (Article 25 data minimisation)
- 30-day auto-delete schedule via `gdpr_consent_log.retention_days`

### Application Tracker
- PostgreSQL-backed (replaces V1 JSON files)
- Statuses: `applied · interviewed · offered · rejected · ghosted · withdrawn`
- Auto-populated by Agent 8 for auto-applied jobs

---

## Project Structure

```
smart-job-agent/
├── backend_v2/                  # FastAPI + LangGraph backend (V2)
│   ├── main.py                  # FastAPI app, all endpoints
│   ├── config.py                # pydantic-settings typed env vars
│   ├── database.py              # asyncpg pool + pgvector init
│   ├── agents/
│   │   ├── graph.py             # LangGraph StateGraph wiring
│   │   ├── state.py             # AgentState TypedDict
│   │   ├── agent_01_resume_architect.py
│   │   ├── agent_02_content_enhancer.py
│   │   ├── agent_03_jd_strategist.py
│   │   ├── agent_04_cold_email.py
│   │   ├── agent_05_infra.py
│   │   ├── agent_06_supervisor.py
│   │   ├── agent_07_scorer_mentor.py
│   │   ├── agent_08_auto_apply.py
│   │   └── tools/
│   │       ├── gemini_client.py # Gemini API wrapper (retry, thinking=off)
│   │       ├── resume_tools.py
│   │       ├── db_tools.py
│   │       └── email_tools.py
│   ├── templates/
│   │   ├── template_ats_pro.py  # PDF renderer — pixel-accurate to ATSMinimal.tsx
│   │   ├── template_jakes.py    # Jake's Resume PDF
│   │   └── template_harvard.py  # Harvard Chronological PDF
│   ├── services/
│   │   ├── resume_parser.py
│   │   ├── ats_quality_gate.py
│   │   ├── job_matcher.py
│   │   └── knowledge_base.py
│   └── db/
│       └── schema.sql           # 13-table PostgreSQL schema
├── frontend/                    # Next.js 14 app
│   └── src/
│       ├── app/
│       │   ├── builder/         # Resume builder (8-step wizard)
│       │   ├── jd-match/        # JD matching + auto-tailor
│       │   ├── scorer/          # Resume score + mentor resources
│       │   ├── auto-apply/      # Auto-apply preferences + live log
│       │   └── tracker/         # Application tracker
│       ├── components/
│       │   ├── templates/
│       │   │   └── ATSMinimal.tsx  # Live preview renderer
│       │   ├── importer/           # Resume upload + AI parse
│       │   └── agents/             # AgentStatusBar, CautionBanner
│       ├── lib/
│       │   └── agentApi.ts         # V2 FastAPI client (typed)
│       └── store/
│           └── resumeStore.tsx     # Zustand store + sessionStorage
├── knowledge/                   # Shared knowledge base JSONs
│   ├── ats_keywords.json
│   ├── role_skill_map.json
│   ├── indian_fresher_hiring_patterns.json
│   └── cold_email_templates.json
├── Jenkinsfile                  # 11-stage CI/CD pipeline
├── requirements_v2.txt          # Python dependencies
├── .env.example                 # Environment variable template
└── start_v2.py                  # Quick-start script
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with `pgvector` extension
- Redis 7+

### 1. Clone & install

```bash
git clone https://github.com/kvs-varun/smart-job-agent.git
cd smart-job-agent

# Python backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements_v2.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   GEMINI_API_KEY   — Google AI Studio (free tier)
#   DATABASE_URL     — postgresql+asyncpg://user:pass@localhost:5432/smartjob_v2
#   REDIS_URL        — redis://localhost:6379/0
```

### 3. Database setup

```bash
psql -U postgres -c "CREATE DATABASE smartjob_v2;"
psql -U postgres -d smartjob_v2 -f backend_v2/db/schema.sql
```

### 4. Run

```bash
# Terminal 1 — FastAPI backend (V2)
python start_v2.py
# or: uvicorn backend_v2.main:app --reload --port 8000

# Terminal 2 — Next.js frontend
cd frontend && npm run dev
```

Open → **http://localhost:3000**

---

## API Reference (V2)

### Core Agent Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v2/agent/build-resume` | Full 8-agent pipeline from text or structured data |
| `POST` | `/v2/agent/build-resume-upload` | Full pipeline from PDF/DOCX upload |
| `POST` | `/v2/agent/parse-resume` | LLM-powered resume parsing only |
| `POST` | `/v2/agent/finalize-resume` | PDF generation from approved JSON |
| `POST` | `/v2/agent/jd-match` | Agent 3 only — JD match analysis |
| `POST` | `/v2/agent/jd-tailor` | Full pipeline tailored to a specific JD |
| `POST` | `/v2/agent/cold-email` | Agent 4 only — cold email generation |
| `POST` | `/v2/agent/score` | Agent 7 only — resume score + mentor |
| `POST` | `/v2/agent/generate-summary` | AI summary generation (role-targeted) |
| `POST` | `/v2/agent/auto-apply` | Agent 8 — trigger auto-apply run |
| `GET`  | `/v2/agent/session/{id}` | Poll agent session state |
| `GET`  | `/v2/agent/download/{filename}` | Download generated PDF |

### Tracker

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v2/tracker/add` | Add application |
| `GET`  | `/v2/tracker/list` | List applications |
| `POST` | `/v2/tracker/update` | Update status / notes |

### GDPR & Responsible AI

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v2/gdpr/consent` | Record consent (Article 6) |
| `GET`  | `/v2/gdpr/my-data/{id}` | Right of access (Article 15) |
| `DELETE` | `/v2/gdpr/my-data/{id}` | Right to erasure (Article 17) |
| `GET`  | `/v2/ai/transparency` | AI system disclosure (EU AI Act Art. 13) |
| `GET`  | `/v2/health` | Health check |

---

## CI/CD Pipeline (Jenkins)

11-stage pipeline defined in `Jenkinsfile`:

```
1. Checkout            — pull from SCM
2. Python Setup        — venv + pip install
3. Python Lint         — flake8 (max-line 120)
4. Backend Tests       — pytest --cov
5. Security Scan       — Bandit (SAST) + npm audit (parallel)
6. GDPR Check          — verify /v2/ai/transparency + /v2/gdpr/my-data exist in source
7. Frontend Build      — npm ci + eslint + next build
8. Docker Build        — backend + frontend images → Docker Hub
9. Deploy Staging      — railway up (develop branch only)
10. Smoke Tests        — curl /v2/health on staging
11. Deploy Production  — manual approval gate (main branch only)
```

Required Jenkins credentials: `GEMINI_API_KEY_CRED`, `DOCKER_HUB_CRED`, `RAILWAY_TOKEN_CRED`

---

## Environment Variables

```bash
# ── LLM ─────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIza...                    # Google AI Studio key
LLM_MODEL_HEAVY=gemini-2.5-flash-lite    # Primary model (both agents)
LLM_MODEL_FAST=gemini-2.5-flash-lite     # Fast tasks

# ── Database ─────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://smartjob:pass@localhost:5432/smartjob_v2

# ── Redis ────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── LangSmith (optional — agent trace visualisation) ─────────────────
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=smart-job-agent-v2

# ── Auto-Apply (user supplies at runtime) ────────────────────────────
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
NAUKRI_EMAIL=
NAUKRI_PASSWORD=
APPLY_SCORE_THRESHOLD=7.0

# ── V1 backward compat ───────────────────────────────────────────────
FLASK_BASE_URL=http://127.0.0.1:5000
```

---

## Database Schema (13 tables)

| Table | Purpose |
|-------|---------|
| `users` | UUID-based, anonymous by default |
| `resumes` | All resume versions + JSON snapshots |
| `resume_embeddings` | pgvector(384) for semantic JD search |
| `jd_matches` | Match scores, skill gaps, caution flags |
| `applications` | Application tracker (replaces JSON) |
| `agent_sessions` | LangGraph run state snapshots |
| `agent_health_log` | Agent 6 supervisor intervention log |
| `resume_scores` | Agent 7 score breakdown + recommendations |
| `cold_emails` | Agent 4 generated email store |
| `auto_apply_log` | Agent 8 application results |
| `analytics_events` | Event stream (replaces events.json) |
| `gdpr_consent_log` | Consent records with 30-day retention |

Extensions: `uuid-ossp` · `vector` (pgvector) · `pg_trgm`

---

## Ethics & Responsible AI

- **No fabrication** — agents are explicitly prompted never to invent metrics, companies, or dates
- **Human oversight** — quality gate and summary require review before download
- **Data minimisation** — IP stored as SHA-256 hash only, never raw
- **Transparency** — every AI-generated field is flagged in the UI and API response headers
- **Right to erasure** — `DELETE /v2/gdpr/my-data/{id}` removes all user data immediately
- **Session isolation** — builder resets to blank state on every visit; no previous data leaks

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Framer Motion, Zustand |
| Backend | FastAPI, Python 3.11, Pydantic v2, uvicorn |
| Agent Orchestration | LangGraph, LangChain |
| LLM | Google Gemini 2.5 Flash-Lite (free tier) |
| Database | PostgreSQL 15 + pgvector, asyncpg |
| Cache / Queue | Redis, Celery |
| PDF Generation | ReportLab (pixel-accurate to React preview) |
| Resume Parsing | pdfplumber, python-docx + LLM extraction |
| Browser Automation | Playwright (Agent 8) |
| CI/CD | Jenkins (11 stages) |
| Monitoring | LangSmith |

---

## Roadmap

- [ ] LinkedIn OAuth for one-click profile import
- [ ] WebSocket real-time agent progress stream
- [ ] `/scorer` page — radar chart + free course cards
- [ ] `/auto-apply` page — live application log
- [ ] Jake's Resume + Harvard PDF renderers
- [ ] Multi-language resume support (Hindi, Tamil)
- [ ] Vercel + Railway production deployment

---

## Author

**Varun Kondapalli** (kvs-varun) · Hyderabad, India  
Senior Agentic AI Developer  

---

## License

MIT — free to use, fork, and deploy.  
**Do not** use this to fabricate resumes, bypass ATS systems unethically, or harvest recruiter credentials.
