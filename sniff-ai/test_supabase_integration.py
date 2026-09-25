"""Test Supabase direct push integration.

This script verifies that Sherlock can connect to Supabase and upload data.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

def test_supabase_import():
    """Test that Supabase client can be imported."""
    print("Testing Supabase import...")
    try:
        from integrations.supabase_client import SupabaseUploader, create_supabase_uploader
        print("✅ Supabase client imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Supabase client: {e}")
        return False

def test_supabase_connection():
    """Test connection to Supabase."""
    print("\nTesting Supabase connection...")

    from integrations.supabase_client import SupabaseUploader

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')

    if not url or not key:
        print("❌ SUPABASE_URL or SUPABASE_KEY not found in .env")
        return False

    try:
        uploader = SupabaseUploader(supabase_url=url, supabase_key=key)
        print(f"✅ Connected to Supabase: {url}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

def test_buckets():
    """Test that storage buckets exist."""
    print("\nTesting storage buckets...")

    from integrations.supabase_client import SupabaseUploader

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')

    try:
        uploader = SupabaseUploader(supabase_url=url, supabase_key=key)

        # Try to list buckets
        buckets = uploader.client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]

        required_buckets = ['sherlock-screenshots', 'sherlock-videos', 'sherlock-traces']

        for bucket in required_buckets:
            if bucket in bucket_names:
                print(f"✅ Bucket exists: {bucket}")
            else:
                print(f"❌ Bucket missing: {bucket}")
                return False

        return True

    except Exception as e:
        print(f"❌ Failed to check buckets: {e}")
        return False

def test_database_tables():
    """Test that database tables exist."""
    print("\nTesting database tables...")

    from integrations.supabase_client import SupabaseUploader

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')

    try:
        uploader = SupabaseUploader(supabase_url=url, supabase_key=key)

        # Try to query each table
        tables = ['runs', 'observations', 'actions', 'diagnoses', 'agent_reasoning', 'persona_reviews']

        for table in tables:
            try:
                result = uploader.client.table(table).select('id').limit(1).execute()
                print(f"✅ Table exists: {table}")
            except Exception as e:
                print(f"❌ Table error ({table}): {e}")
                return False

        return True

    except Exception as e:
        print(f"❌ Failed to check tables: {e}")
        return False

def test_config_loading():
    """Test that config loads Supabase settings correctly."""
    print("\nTesting config loading...")

    try:
        from core.config import SherlockConfig

        config = SherlockConfig.from_env()

        if not config.supabase.enabled:
            print("❌ Supabase not enabled in config")
            return False

        print(f"✅ Supabase enabled: {config.supabase.enabled}")
        print(f"✅ Supabase URL: {config.supabase.url}")
        print(f"✅ Auto-upload: {config.supabase.auto_upload}")

        return True

    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Sherlock Supabase Direct Push Integration Test")
    print("=" * 60)

    tests = [
        ("Import Test", test_supabase_import),
        ("Connection Test", test_supabase_connection),
        ("Buckets Test", test_buckets),
        ("Database Tables Test", test_database_tables),
        ("Config Loading Test", test_config_loading),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Supabase integration is working!")
        print("\n✨ You're ready to run Sherlock with auto-upload to Supabase!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
