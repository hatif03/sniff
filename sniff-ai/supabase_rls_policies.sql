-- Supabase RLS Policies for Sherlock
-- Run this in Supabase SQL Editor to allow uploads

-- =============================================================================
-- Option 1: Allow all inserts (Simple, for testing)
-- =============================================================================

-- Runs table
CREATE POLICY "Allow all inserts on runs" ON runs
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on runs" ON runs
FOR SELECT TO anon, authenticated
USING (true);

-- Observations table
CREATE POLICY "Allow all inserts on observations" ON observations
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on observations" ON observations
FOR SELECT TO anon, authenticated
USING (true);

-- Actions table
CREATE POLICY "Allow all inserts on actions" ON actions
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on actions" ON actions
FOR SELECT TO anon, authenticated
USING (true);

-- Diagnoses table
CREATE POLICY "Allow all inserts on diagnoses" ON diagnoses
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on diagnoses" ON diagnoses
FOR SELECT TO anon, authenticated
USING (true);

-- Agent reasoning table
CREATE POLICY "Allow all inserts on agent_reasoning" ON agent_reasoning
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on agent_reasoning" ON agent_reasoning
FOR SELECT TO anon, authenticated
USING (true);

-- Persona reviews table
CREATE POLICY "Allow all inserts on persona_reviews" ON persona_reviews
FOR INSERT TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow all selects on persona_reviews" ON persona_reviews
FOR SELECT TO anon, authenticated
USING (true);

-- =============================================================================
-- Option 2: Disable RLS entirely (Easiest for testing)
-- =============================================================================
-- Run these if you want to completely disable RLS:

-- ALTER TABLE runs DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE observations DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE actions DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE diagnoses DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE agent_reasoning DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE persona_reviews DISABLE ROW LEVEL SECURITY;

-- =============================================================================
-- Storage Bucket Policies
-- =============================================================================

-- Allow uploads to screenshots bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('sherlock-screenshots', 'sherlock-screenshots', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow uploads to screenshots" ON storage.objects
FOR INSERT TO anon, authenticated
WITH CHECK (bucket_id = 'sherlock-screenshots');

CREATE POLICY "Allow public access to screenshots" ON storage.objects
FOR SELECT TO anon, authenticated
USING (bucket_id = 'sherlock-screenshots');

-- Allow uploads to videos bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('sherlock-videos', 'sherlock-videos', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow uploads to videos" ON storage.objects
FOR INSERT TO anon, authenticated
WITH CHECK (bucket_id = 'sherlock-videos');

CREATE POLICY "Allow public access to videos" ON storage.objects
FOR SELECT TO anon, authenticated
USING (bucket_id = 'sherlock-videos');

-- Allow uploads to traces bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('sherlock-traces', 'sherlock-traces', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow uploads to traces" ON storage.objects
FOR INSERT TO anon, authenticated
WITH CHECK (bucket_id = 'sherlock-traces');

CREATE POLICY "Allow public access to traces" ON storage.objects
FOR SELECT TO anon, authenticated
USING (bucket_id = 'sherlock-traces');
