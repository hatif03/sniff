-- Supabase Database Schema for Sherlock Mystery Shopper
-- This schema supports beautiful graph/timeline visualizations on the web dashboard

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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes for efficient querying
    INDEX idx_runs_run_id (run_id),
    INDEX idx_runs_created_at (created_at DESC),
    INDEX idx_runs_outcome (outcome),
    INDEX idx_runs_persona (persona_name)
);

-- Enable Row Level Security
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

-- Policy: Allow public read access
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
    last_action_result JSONB,

    -- Composite index for efficient step queries
    INDEX idx_observations_run_step (run_id, step),
    INDEX idx_observations_timestamp (timestamp)
);

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
    timestamp TIMESTAMPTZ NOT NULL,

    INDEX idx_actions_run_step (run_id, step),
    INDEX idx_actions_success (run_id, success)
);

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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_diagnoses_severity (severity),
    INDEX idx_diagnoses_root_cause (root_cause)
);

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
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,

    INDEX idx_reasoning_run_step (run_id, step),
    INDEX idx_reasoning_confidence (confidence)
);

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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_reviews_sentiment (overall_sentiment),
    INDEX idx_reviews_rating (experience_rating),
    INDEX idx_reviews_abandonment (abandonment_likelihood)
);

ALTER TABLE persona_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public reviews are viewable by everyone"
    ON persona_reviews FOR SELECT
    USING (true);

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

-- sherlock-screenshots (public)
-- sherlock-videos (public)
-- sherlock-traces (public)

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

COMMENT ON VIEW run_summaries IS 'Denormalized view for dashboard run list';
COMMENT ON VIEW persona_metrics IS 'Aggregated persona performance metrics';
COMMENT ON VIEW friction_analytics IS 'Friction point frequency analysis';
COMMENT ON VIEW agent_confidence_metrics IS 'Agent decision quality metrics';
