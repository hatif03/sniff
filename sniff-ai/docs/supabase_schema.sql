-- Supabase Database Schema for Sniff Mystery Shopper
-- This schema supports beautiful graph/timeline visualizations on the web dashboard
--
-- Note: earlier drafts of this file used inline `INDEX name (...)` clauses
-- inside CREATE TABLE, which is MySQL syntax and is not valid PostgreSQL -
-- fixed here to separate CREATE INDEX statements after each table.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- RUNS TABLE
-- Main table for test run metadata
-- =============================================================================
CREATE TABLE runs (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    goal TEXT NOT NULL,
    persona_name TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'error', 'aborted')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC NOT NULL,
    total_steps INTEGER NOT NULL,
    successful_actions INTEGER NOT NULL,
    failed_actions INTEGER NOT NULL,
    starting_url TEXT,
    final_url TEXT,
    trace_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_runs_run_id ON runs (run_id);
CREATE INDEX idx_runs_created_at ON runs (created_at DESC);
CREATE INDEX idx_runs_outcome ON runs (outcome);
CREATE INDEX idx_runs_persona ON runs (persona_name);

ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public runs are viewable by everyone"
    ON runs FOR SELECT
    USING (true);

-- =============================================================================
-- OBSERVATIONS TABLE
-- Browser state observations at each step
-- =============================================================================
CREATE TABLE observations (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    url TEXT NOT NULL,
    screenshot_url TEXT,
    visible_text TEXT[],
    timing JSONB,
    console_errors TEXT[],
    network_events JSONB[],
    last_action_result JSONB
);

CREATE INDEX idx_observations_run_step ON observations (run_id, step);
CREATE INDEX idx_observations_timestamp ON observations (timestamp);

ALTER TABLE observations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public observations are viewable by everyone"
    ON observations FOR SELECT
    USING (true);

-- =============================================================================
-- ACTIONS TABLE
-- Action execution results (for timeline visualization)
-- =============================================================================
CREATE TABLE actions (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('tap', 'type', 'scroll', 'wait', 'back', 'abort')),
    target TEXT,
    success BOOLEAN NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'timeout', 'element_not_found', 'invalid_action')),
    error TEXT,
    duration_ms INTEGER NOT NULL,
    details JSONB,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_actions_run_step ON actions (run_id, step);
CREATE INDEX idx_actions_success ON actions (run_id, success);

ALTER TABLE actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public actions are viewable by everyone"
    ON actions FOR SELECT
    USING (true);

-- =============================================================================
-- DIAGNOSES TABLE
-- Root cause analysis for failures
-- =============================================================================
CREATE TABLE diagnoses (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    root_cause TEXT NOT NULL CHECK (root_cause IN ('Backend', 'UX/Content', 'Performance', 'Integration')),
    severity TEXT NOT NULL CHECK (severity IN ('P0', 'P1', 'P2', 'P3')),
    evidence JSONB,
    likely_owner TEXT NOT NULL,
    repro_steps TEXT[],
    suggested_fix TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_diagnoses_severity ON diagnoses (severity);
CREATE INDEX idx_diagnoses_root_cause ON diagnoses (root_cause);

ALTER TABLE diagnoses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public diagnoses are viewable by everyone"
    ON diagnoses FOR SELECT
    USING (true);

-- =============================================================================
-- AGENT_REASONING TABLE
-- Agent decision-making timeline (for transparency visualization)
-- =============================================================================
CREATE TABLE agent_reasoning (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    url TEXT,
    action TEXT NOT NULL,
    target TEXT,
    reasoning TEXT NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    attempt INTEGER NOT NULL DEFAULT 1,
    repaired BOOLEAN NOT NULL DEFAULT FALSE,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_reasoning_run_step ON agent_reasoning (run_id, step);
CREATE INDEX idx_reasoning_confidence ON agent_reasoning (confidence);

ALTER TABLE agent_reasoning ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public reasoning is viewable by everyone"
    ON agent_reasoning FOR SELECT
    USING (true);

-- =============================================================================
-- PERSONA_REVIEWS TABLE
-- Persona experience reviews (for UX insights visualization)
-- =============================================================================
CREATE TABLE persona_reviews (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    persona_name TEXT NOT NULL,
    persona_display_name TEXT NOT NULL,
    overall_sentiment TEXT NOT NULL CHECK (overall_sentiment IN ('positive', 'neutral', 'negative')),
    experience_rating INTEGER NOT NULL CHECK (experience_rating >= 1 AND experience_rating <= 10),
    friction_points TEXT[],
    positive_aspects TEXT[],
    abandonment_likelihood TEXT NOT NULL CHECK (abandonment_likelihood IN ('low', 'medium', 'high')),
    narrative TEXT NOT NULL,
    recommendations TEXT[],
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reviews_sentiment ON persona_reviews (overall_sentiment);
CREATE INDEX idx_reviews_rating ON persona_reviews (experience_rating);
CREATE INDEX idx_reviews_abandonment ON persona_reviews (abandonment_likelihood);

ALTER TABLE persona_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public reviews are viewable by everyone"
    ON persona_reviews FOR SELECT
    USING (true);

-- =============================================================================
-- AUDITS TABLE
-- Landing-page conversion audit results (public-read, matches runs' pattern)
-- =============================================================================
CREATE TABLE audits (
    id BIGSERIAL PRIMARY KEY,
    audit_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    persona TEXT,
    overall_score NUMERIC,
    label TEXT,
    verdict TEXT,
    -- Pulled out of report_json as real, queryable/indexable columns rather
    -- than left buried in JSONB, so Core Web Vitals trend queries (grouping
    -- across many audits for the same url) don't need JSON extraction.
    lcp NUMERIC,
    fcp NUMERIC,
    cls NUMERIC,
    -- Nullable: most audits are still standalone single-page audits. Set
    -- when this audit is one page of a whole-site audit (see site_audits
    -- below - the FK constraint is added after that table exists, further
    -- down this file, since it's defined later for readability).
    site_audit_id TEXT,
    report_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audits_audit_id ON audits (audit_id);
CREATE INDEX idx_audits_created_at ON audits (created_at DESC);
CREATE INDEX idx_audits_url ON audits (url);
CREATE INDEX idx_audits_site_audit_id ON audits (site_audit_id);

ALTER TABLE audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public audits are viewable by everyone"
    ON audits FOR SELECT
    USING (true);

-- =============================================================================
-- SCHEDULES TABLE
-- Recurring runs/audits, ticked by an external Cloud Scheduler job hitting
-- POST /internal/scheduler/tick (see src/api/main.py) - not an in-process
-- scheduler, since the backend autoscales to multiple Cloud Run instances
-- and an in-process scheduler would fire the same job on every instance.
-- =============================================================================
CREATE TABLE schedules (
    id BIGSERIAL PRIMARY KEY,
    schedule_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('run', 'audit')),
    url TEXT NOT NULL,
    goal TEXT,
    persona TEXT,
    device TEXT,
    network TEXT,
    interval_minutes INTEGER NOT NULL CHECK (interval_minutes >= 5),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_run_id TEXT,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_schedules_schedule_id ON schedules (schedule_id);
CREATE INDEX idx_schedules_due ON schedules (enabled, next_run_at);

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public schedules are viewable by everyone"
    ON schedules FOR SELECT
    USING (true);

-- =============================================================================
-- SITE_AUDITS TABLE
-- Whole-site audit crawls (parent record). Each page it visits is a normal
-- row in the existing `audits` table, tagged via audits.site_audit_id - the
-- per-page report/screenshot/CTA-click-evidence shape is completely reused,
-- unchanged, from the single-page audit feature.
-- =============================================================================
CREATE TABLE site_audits (
    id BIGSERIAL PRIMARY KEY,
    site_audit_id TEXT UNIQUE NOT NULL,
    seed_url TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    max_pages INTEGER NOT NULL,
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_audited INTEGER NOT NULL DEFAULT 0,
    -- Per-URL {status: audited|skipped|failed, ...} record - the literal
    -- "what we visited and what not" proof surfaced in the dashboard.
    manifest JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_site_audits_site_audit_id ON site_audits (site_audit_id);
CREATE INDEX idx_site_audits_created_at ON site_audits (created_at DESC);

ALTER TABLE site_audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public site audits are viewable by everyone"
    ON site_audits FOR SELECT
    USING (true);

-- Deferred FK: audits.site_audit_id references this table, added here now
-- that site_audits exists (the column itself was declared nullable, with no
-- inline constraint, back in the AUDITS TABLE section above).
ALTER TABLE audits
    ADD CONSTRAINT fk_audits_site_audit_id
    FOREIGN KEY (site_audit_id) REFERENCES site_audits(site_audit_id) ON DELETE CASCADE;

-- =============================================================================
-- VIEWS FOR DASHBOARD QUERIES
-- Pre-computed views for efficient dashboard rendering
-- =============================================================================

-- Run summary with diagnosis and review
CREATE VIEW run_summaries AS
SELECT
    r.run_id,
    r.goal,
    r.persona_name,
    r.outcome,
    r.start_time,
    r.end_time,
    r.duration_seconds,
    r.total_steps,
    r.successful_actions,
    r.failed_actions,
    r.starting_url,
    r.final_url,
    d.root_cause,
    d.severity,
    d.suggested_fix,
    pr.overall_sentiment,
    pr.experience_rating,
    pr.abandonment_likelihood,
    r.created_at
FROM runs r
LEFT JOIN diagnoses d ON r.run_id = d.run_id
LEFT JOIN persona_reviews pr ON r.run_id = pr.run_id
ORDER BY r.created_at DESC;

-- Persona performance metrics
CREATE VIEW persona_metrics AS
SELECT
    pr.persona_name,
    COUNT(*) as total_runs,
    AVG(pr.experience_rating) as avg_rating,
    COUNT(CASE WHEN pr.overall_sentiment = 'positive' THEN 1 END) as positive_runs,
    COUNT(CASE WHEN pr.overall_sentiment = 'negative' THEN 1 END) as negative_runs,
    COUNT(CASE WHEN pr.abandonment_likelihood = 'high' THEN 1 END) as high_abandonment_runs,
    AVG(r.duration_seconds) as avg_duration,
    COUNT(CASE WHEN r.outcome = 'success' THEN 1 END) as successful_runs,
    COUNT(CASE WHEN r.outcome = 'failure' THEN 1 END) as failed_runs
FROM persona_reviews pr
JOIN runs r ON pr.run_id = r.run_id
GROUP BY pr.persona_name;

-- Friction point analytics
CREATE VIEW friction_analytics AS
SELECT
    pr.persona_name,
    UNNEST(pr.friction_points) as friction_point,
    COUNT(*) as occurrence_count
FROM persona_reviews pr
GROUP BY pr.persona_name, friction_point
ORDER BY occurrence_count DESC;

-- Agent confidence metrics
CREATE VIEW agent_confidence_metrics AS
SELECT
    ar.run_id,
    COUNT(*) as total_decisions,
    AVG(ar.confidence) as avg_confidence,
    MIN(ar.confidence) as min_confidence,
    MAX(ar.confidence) as max_confidence,
    COUNT(CASE WHEN ar.repaired THEN 1 END) as repaired_decisions,
    COUNT(CASE WHEN ar.is_fallback THEN 1 END) as fallback_decisions
FROM agent_reasoning ar
GROUP BY ar.run_id;

-- =============================================================================
-- STORAGE BUCKETS (Create via Supabase dashboard or API)
-- =============================================================================

-- sniff-screenshots (public)
-- sniff-videos (public)
-- sniff-traces (public)

-- =============================================================================
-- FUNCTIONS FOR DASHBOARD
-- =============================================================================

-- Get complete run details with all related data
CREATE OR REPLACE FUNCTION get_run_details(p_run_id TEXT)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'run', (SELECT row_to_json(r.*) FROM runs r WHERE r.run_id = p_run_id),
        'observations', (SELECT json_agg(o.*) FROM observations o WHERE o.run_id = p_run_id ORDER BY o.step),
        'actions', (SELECT json_agg(a.*) FROM actions a WHERE a.run_id = p_run_id ORDER BY a.step),
        'diagnosis', (SELECT row_to_json(d.*) FROM diagnoses d WHERE d.run_id = p_run_id),
        'reasoning', (SELECT json_agg(ar.*) FROM agent_reasoning ar WHERE ar.run_id = p_run_id ORDER BY ar.step),
        'review', (SELECT row_to_json(pr.*) FROM persona_reviews pr WHERE pr.run_id = p_run_id)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE runs IS 'Main test run records with metadata and outcomes';
COMMENT ON TABLE observations IS 'Browser state snapshots at each step for timeline visualization';
COMMENT ON TABLE actions IS 'Action execution results for step-by-step playback';
COMMENT ON TABLE diagnoses IS 'Root cause analysis for failed runs';
COMMENT ON TABLE agent_reasoning IS 'Agent decision-making transparency log';
COMMENT ON TABLE persona_reviews IS 'Persona experience reviews for UX insights';
COMMENT ON TABLE audits IS 'Landing-page conversion audit records, full report stored as JSONB';
COMMENT ON TABLE schedules IS 'Recurring run/audit definitions, ticked by an external Cloud Scheduler job';
COMMENT ON TABLE site_audits IS 'Whole-site audit crawls - parent record; each visited page is a normal audits row tagged via site_audit_id';

COMMENT ON VIEW run_summaries IS 'Denormalized view for dashboard run list';
COMMENT ON VIEW persona_metrics IS 'Aggregated persona performance metrics';
COMMENT ON VIEW friction_analytics IS 'Friction point frequency analysis';
COMMENT ON VIEW agent_confidence_metrics IS 'Agent decision quality metrics';
