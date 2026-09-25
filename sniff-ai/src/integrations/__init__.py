"""Sherlock integrations with external services.

Available integrations:
- Supabase: Upload artifacts and run data to Supabase
"""

__all__ = []

# Optional integrations
try:
    from .supabase_client import SupabaseUploader, create_supabase_uploader
    __all__.extend(['SupabaseUploader', 'create_supabase_uploader'])
except ImportError:
    pass
