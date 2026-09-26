import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Missing Supabase environment variables. Dashboard features will not work.');
}

// @supabase/supabase-js validates the URL/key at construction time, so empty
// strings throw (breaking builds/prerenders when env vars aren't set). Fall
// back to placeholders that pass validation but aren't real credentials.
const safeSupabaseUrl = supabaseUrl || 'https://placeholder.supabase.co';
const safeSupabaseAnonKey = supabaseAnonKey || 'placeholder-anon-key';

export const supabase = createClient(safeSupabaseUrl, safeSupabaseAnonKey);
