-- Smart Job Agent V2 — PostgreSQL Schema
-- Run: psql -U smartjob -d smartjob_v2 -f schema.sql

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector (semantic search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy text search

-- ─── USERS ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE,
    name            TEXT,
    is_anonymous    BOOLEAN DEFAULT TRUE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── RESUMES ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resumes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    version         INT NOT NULL DEFAULT 1,
    template_name   TEXT NOT NULL DEFAULT 'ats_pro',   -- jakes|harvard|ats_pro
    raw_text        TEXT,
    parsed_json     JSONB NOT NULL DEFAULT '{}',
    tailored_json   JSONB,
    enhanced_json   JSONB,
    final_json      JSONB,
    pdf_path        TEXT,
    download_url    TEXT,
    ats_score       FLOAT,          -- 0–100 from quality gate
    mentor_score    FLOAT,          -- 0.0–10.0 from Agent 7
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_resumes_session  ON resumes(session_id);
CREATE INDEX IF NOT EXISTS idx_resumes_user     ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_updated  ON resumes(updated_at DESC);

-- ─── RESUME EMBEDDINGS (pgvector) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resume_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id       UUID REFERENCES resumes(id) ON DELETE CASCADE,
    embedding       vector(384),    -- sentence-transformers all-MiniLM-L6-v2
    chunk_text      TEXT NOT NULL,
    chunk_index     INT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_resume_emb_vec
    ON resume_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ─── JD MATCH SESSIONS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jd_matches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id       UUID REFERENCES resumes(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    job_description TEXT NOT NULL,
    jd_embedding    vector(384),
    match_score     FLOAT NOT NULL DEFAULT 0,
    skill_match_pct FLOAT DEFAULT 0,
    keyword_cov_pct FLOAT DEFAULT 0,
    matched_skills  TEXT[] DEFAULT '{}',
    missing_skills  TEXT[] DEFAULT '{}',
    caution_issued  BOOLEAN DEFAULT FALSE,
    override_by_user BOOLEAN DEFAULT FALSE,
    full_report     JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jd_matches_session ON jd_matches(session_id);
CREATE INDEX IF NOT EXISTS idx_jd_matches_score   ON jd_matches(match_score DESC);

-- ─── APPLICATIONS TRACKER ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id      TEXT,
    company         TEXT NOT NULL,
    role            TEXT NOT NULL,
    job_url         TEXT DEFAULT '',
    resume_id       UUID REFERENCES resumes(id) ON DELETE SET NULL,
    resume_filename TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'applied',
                    -- applied|interviewed|offered|rejected|ghosted|withdrawn
    notes           TEXT DEFAULT '',
    follow_up       TEXT DEFAULT 'pending',  -- pending|sent|no_reply
    source          TEXT DEFAULT 'manual',   -- manual|auto_apply
    auto_apply_data JSONB DEFAULT '{}',
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_applications_user    ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status  ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_applied ON applications(applied_at DESC);

-- ─── AGENT SESSIONS (LangGraph execution tracking) ───────────────────────────
CREATE TABLE IF NOT EXISTS agent_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT UNIQUE NOT NULL,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    graph_run_id    TEXT,           -- LangSmith trace ID
    state_snapshot  JSONB NOT NULL DEFAULT '{}',
    agents_completed TEXT[] DEFAULT '{}',
    current_agent   TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
                    -- running|completed|failed|interrupted|paused
    error           TEXT,
    retry_count     INT DEFAULT 0,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_ms     INT
);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_id     ON agent_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user   ON agent_sessions(user_id);

-- ─── AGENT HEALTH LOG (Agent 6 — Supervisor) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_health_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT NOT NULL,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL,  -- ok|degraded|failed|recovered|fallback_used
    message         TEXT,
    intervention    TEXT,           -- what the supervisor did
    duration_ms     INT,
    logged_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_health_session ON agent_health_log(session_id);
CREATE INDEX IF NOT EXISTS idx_health_agent   ON agent_health_log(agent_name, logged_at DESC);

-- ─── RESUME SCORES (Agent 7 — Scorer & Mentor) ───────────────────────────────
CREATE TABLE IF NOT EXISTS resume_scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id       UUID REFERENCES resumes(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    total_score     FLOAT NOT NULL CHECK (total_score >= 0 AND total_score <= 10),
    breakdown       JSONB NOT NULL DEFAULT '{}',
    -- {ats_compliance, content_quality, skill_alignment, profile_strength, presentation}
    mentor_feedback TEXT,
    recommendations JSONB NOT NULL DEFAULT '[]',
    -- [{title, url, provider, duration_hours, free, relevance_score, domain}]
    domain          TEXT,           -- backend|frontend|data|flutter|fullstack
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scores_resume  ON resume_scores(resume_id);
CREATE INDEX IF NOT EXISTS idx_scores_session ON resume_scores(session_id);

-- ─── COLD EMAILS (Agent 4) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cold_emails (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id       UUID REFERENCES resumes(id) ON DELETE CASCADE,
    session_id      TEXT NOT NULL,
    candidate_email TEXT,
    recruiter_email TEXT,
    company_name    TEXT,
    role_title      TEXT,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    framework       TEXT,           -- AIDA|PAS|STAR|custom
    tone            TEXT,           -- formal|casual|friendly
    mailto_link     TEXT,
    gmail_url       TEXT,
    word_count      INT,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cold_emails_session  ON cold_emails(session_id);
CREATE INDEX IF NOT EXISTS idx_cold_emails_recruiter ON cold_emails(recruiter_email);

-- ─── AUTO-APPLY LOG (Agent 8) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auto_apply_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT NOT NULL,
    resume_id       UUID REFERENCES resumes(id) ON DELETE SET NULL,
    platform        TEXT NOT NULL,  -- linkedin|naukri
    job_title       TEXT,
    company         TEXT,
    job_url         TEXT,
    match_score     FLOAT,
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- pending|submitted|failed|skipped|rate_limited
    error_detail    TEXT,
    screenshot_path TEXT,           -- Playwright screenshot on failure
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_auto_apply_session  ON auto_apply_log(session_id);
CREATE INDEX IF NOT EXISTS idx_auto_apply_status   ON auto_apply_log(status);
CREATE INDEX IF NOT EXISTS idx_auto_apply_platform ON auto_apply_log(platform, applied_at DESC);

-- ─── ANALYTICS EVENTS (replaces backend/data/events.json) ────────────────────
CREATE TABLE IF NOT EXISTS analytics_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT,
    event_type      TEXT NOT NULL,
    -- generate_attempt|resume_built|jd_matched|cold_email_generated|
    -- pdf_downloaded|auto_apply_started|score_generated|user_edit_accepted
    payload         JSONB DEFAULT '{}',
    ip_hash         TEXT,           -- SHA-256 of IP, never raw IP (privacy)
    logged_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_type ON analytics_events(event_type, logged_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON analytics_events(session_id);

-- ─── GDPR CONSENT LOG (Article 7 — Lawful basis for AI processing) ───────────
CREATE TABLE IF NOT EXISTS gdpr_consent_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT UNIQUE NOT NULL,
    consent_given   BOOLEAN NOT NULL DEFAULT FALSE,
    purposes        TEXT[] DEFAULT ARRAY['resume_generation'],
    -- granular consent: resume_generation|jd_matching|cold_email|auto_apply
    consented_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    withdrawn_at    TIMESTAMPTZ,            -- set when consent_given → false
    ip_hash         TEXT NOT NULL DEFAULT 'anonymised',
    -- SHA-256 of IP — never store raw IP (GDPR Article 25 data minimisation)
    retention_days  INT NOT NULL DEFAULT 30  -- data auto-deleted after this
);
CREATE INDEX IF NOT EXISTS idx_gdpr_session ON gdpr_consent_log(session_id);

-- Auto-delete expired sessions (GDPR Article 5(1)(e) — storage limitation)
-- Run this nightly via pg_cron or the Agent 5 vacuum schedule:
-- DELETE FROM agent_sessions
--   WHERE created_at < NOW() - INTERVAL '30 days';
-- DELETE FROM gdpr_consent_log
--   WHERE consented_at < NOW() - INTERVAL '30 days';

-- ─── Updated-at triggers ──────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['users', 'resumes', 'applications', 'agent_sessions']
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trg_%s_updated ON %s;
            CREATE TRIGGER trg_%s_updated
                BEFORE UPDATE ON %s
                FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        ', t, t, t, t);
    END LOOP;
END;
$$;
