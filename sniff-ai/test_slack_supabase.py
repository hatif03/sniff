#!/usr/bin/env python3
"""Test Slack-Supabase integration: verify alerts include Supabase URLs."""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.models import DiagnosisResult
from src.alerts.slack import SlackAlert
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_slack_with_supabase_urls():
    """Test that Slack alert properly formats Supabase URLs."""

    # Create mock Supabase result
    mock_supabase_result = {
        "success": True,
        "run_id": "test_run_12345",
        "public_url": "https://bmumkgbxobzavspbheij.supabase.co/runs/test_run_12345",
        "latest_screenshot_url": "https://bmumkgbxobzavspbheij.supabase.co/storage/v1/object/public/sniff-screenshots/test_run_12345/final.png",
        "first_video_url": "https://bmumkgbxobzavspbheij.supabase.co/storage/v1/object/public/sniff-videos/test_run_12345/recording.webm",
        "trace_url": "https://bmumkgbxobzavspbheij.supabase.co/storage/v1/object/public/sniff-traces/test_run_12345/trace.zip",
        "screenshots_uploaded": 5,
        "videos_uploaded": 1,
        "trace_uploaded": True,
    }

    # Create mock diagnosis
    mock_diagnosis = DiagnosisResult(
        rootCause="Backend",
        severity="P0",
        evidence={
            "final_url": "https://staging.example.com/signup",
            "error_messages": ["API returned 500", "Timeout after 30s"],
            "failed_actions": 3,
        },
        likelyOwner="backend-team",
        reproSteps=[
            "Navigate to signup page",
            "Click 'Upload Document' button",
            "Observe 500 error from API",
        ],
        suggestedFix="Check /api/upload endpoint - returning 500 errors consistently",
    )

    # Create Slack alert service
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL not configured in .env")
        return False

    slack = SlackAlert(webhook_url=webhook_url, bot_name="sniff Test Bot")

    print("\n🧪 Testing Slack alert with Supabase URLs...")
    print(f"   Webhook: {webhook_url[:50]}...")
    print(f"   Supabase: {mock_supabase_result['public_url']}")

    # Send alert with Supabase result
    success = slack.send_alert(
        run_id="test_run_12345",
        diagnosis=mock_diagnosis,
        run_goal="Complete signup with document upload",
        artifacts_path="/tmp/artifacts/test_run_12345",
        supabase_result=mock_supabase_result,
    )

    if success:
        print("\n✅ Alert sent successfully!")
        print("\n📱 Check your Slack channel. The alert should include:")
        print("   🌐 Supabase Artifacts section with:")
        print("      📊 View Run Dashboard (clickable link)")
        print("      📸 View Final Screenshot (clickable link)")
        print("      🎥 Watch Video Recording (clickable link)")
        print("      🔍 Download Playwright Trace (clickable link)")
        print("      📷 5 screenshot(s) uploaded")
        return True
    else:
        print("\n❌ Failed to send alert")
        return False


if __name__ == "__main__":
    result = test_slack_with_supabase_urls()
    sys.exit(0 if result else 1)
