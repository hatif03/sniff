import { supabase } from './supabase';

export async function getRunDetails(runId: string) {
  // Fetch from run_summaries instead of RPC function
  const { data, error } = await supabase
    .from('run_summaries')
    .select('*')
    .eq('run_id', runId)
    .single();

  if (error) throw error;
  return data;
}

export async function getRecentRuns(limit = 10) {
  const { data, error } = await supabase
    .from('run_summaries')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data;
}

export async function getPersonaMetrics() {
  const { data, error } = await supabase
    .from('persona_metrics')
    .select('*');

  if (error) throw error;
  return data;
}

export async function getObservations(runId: string) {
  const { data, error } = await supabase
    .from('observations')
    .select('step, url, screenshot_url, timestamp')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getActions(runId: string) {
  const { data, error } = await supabase
    .from('actions')
    .select('step, action, target, success, duration_ms')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getAgentReasoning(runId: string) {
  const { data, error } = await supabase
    .from('agent_reasoning')
    .select('*')
    .eq('run_id', runId)
    .order('step');

  if (error) throw error;
  return data || [];
}

export async function getPersonaReview(runId: string) {
  const { data, error } = await supabase
    .from('persona_reviews')
    .select('*')
    .eq('run_id', runId)
    .single();

  if (error) throw error;
  return data;
}

export async function getFrictionAnalytics() {
  const { data, error} = await supabase
    .from('friction_analytics')
    .select('*')
    .order('occurrence_count', { ascending: false })
    .limit(20);

  if (error) throw error;
  return data || [];
}
