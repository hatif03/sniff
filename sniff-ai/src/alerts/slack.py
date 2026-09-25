"""Slack alerting service with rich block formatting.

Sends structured alerts to Slack webhook with:
- Severity indicator
- Root cause classification
- Evidence links/paths
- Reproduction steps
- Owner tag for routing
"""

import logging
from typing import Any, Optional
from datetime import datetime

import httpx

from ..core.models import DiagnosisResult

logger = logging.getLogger(__name__)


class SlackAlert:
    """Slack webhook alert sender."""

    # Severity emoji mapping
    SEVERITY_EMOJI = {
        "P0": "🔴",
        "P1": "🟠",
        "P2": "🟡",
        "P3": "🔵",
    }

    # Root cause emoji mapping
    ROOT_CAUSE_EMOJI = {
        "Backend": "⚙️",
        "UX/Content": "🎨",
        "Performance": "⚡",
        "Integration": "🔌",
    }

    def __init__(self, webhook_url: Optional[str] = None, bot_name: str = "Sniff Alert Bot"):
        """Initialize Slack alert sender.

        Args:
            webhook_url: Slack webhook URL for posting messages
            bot_name: Bot display name
        """
        self.webhook_url = webhook_url
        self.bot_name = bot_name

    def send_alert(
        self,
        run_id: str,
        diagnosis: DiagnosisResult,
        run_goal: str,
        artifacts_path: Optional[str] = None,
        supabase_result: Optional[dict] = None,
    ) -> bool:
        """Send alert to Slack.

        Args:
            run_id: Unique run identifier
            diagnosis: Diagnosis result with classification
            run_goal: Original run goal
            artifacts_path: Path to run artifacts
            supabase_result: Supabase upload result with public URLs (optional)

        Returns:
            True if alert sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured, skipping alert")
            return False

        try:
            payload = self._build_payload(run_id, diagnosis, run_goal, artifacts_path, supabase_result)
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

            logger.info(f"Slack alert sent successfully for run {run_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _build_payload(
        self,
        run_id: str,
        diagnosis: DiagnosisResult,
        run_goal: str,
        artifacts_path: Optional[str] = None,
        supabase_result: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Build Slack message payload with rich blocks.

        Args:
            run_id: Unique run identifier
            diagnosis: Diagnosis result
            run_goal: Original run goal
            artifacts_path: Path to artifacts
            supabase_result: Supabase upload result with URLs (optional)

        Returns:
            Slack message payload
        """
        severity_emoji = self.SEVERITY_EMOJI.get(diagnosis.severity, "⚪")
        root_cause_emoji = self.ROOT_CAUSE_EMOJI.get(diagnosis.rootCause, "❓")

        blocks = []

        # Header block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{severity_emoji} sniff Alert: {diagnosis.severity} - {diagnosis.rootCause}",
            }
        })

        # Divider
        blocks.append({"type": "divider"})

        # Run details
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Run ID:*\n`{run_id}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Timestamp:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{severity_emoji} {diagnosis.severity}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Root Cause:*\n{root_cause_emoji} {diagnosis.rootCause}"
                },
            ]
        })

        # Goal
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Goal:*\n{run_goal}"
            }
        })

        # Divider
        blocks.append({"type": "divider"})

        # Suggested fix
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested Fix:*\n{diagnosis.suggestedFix}"
            }
        })

        # Owner
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Owner:*\n@{diagnosis.likelyOwner}"
            }
        })

        # Reproduction steps
        if diagnosis.reproSteps:
            repro_text = "\n".join([f"{i}. {step}" for i, step in enumerate(diagnosis.reproSteps, 1)])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reproduction Steps:*\n```{repro_text}```"
                }
            })

        # Evidence
        if diagnosis.evidence:
            evidence_items = []

            # Final URL
            if diagnosis.evidence.get('final_url'):
                evidence_items.append(f"🔗 URL: {diagnosis.evidence['final_url']}")

            # Error count
            error_count = len(diagnosis.evidence.get('error_messages', []))
            if error_count > 0:
                evidence_items.append(f"⚠️ {error_count} error(s) detected")

            # Failed actions
            failed_actions = diagnosis.evidence.get('failed_actions', 0)
            if failed_actions > 0:
                evidence_items.append(f"❌ {failed_actions} failed action(s)")

            if evidence_items:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Evidence:*\n" + "\n".join(evidence_items)
                    }
                })

        # Supabase links (if available) - clickable URLs
        if supabase_result and supabase_result.get("success"):
            supabase_items = []

            # Dashboard link
            if supabase_result.get("public_url"):
                supabase_items.append(f"📊 <{supabase_result['public_url']}|View Run Dashboard>")

            # Latest screenshot
            if supabase_result.get("latest_screenshot_url"):
                supabase_items.append(f"📸 <{supabase_result['latest_screenshot_url']}|View Final Screenshot>")

            # Video
            if supabase_result.get("first_video_url"):
                supabase_items.append(f"🎥 <{supabase_result['first_video_url']}|Watch Video Recording>")

            # Trace
            if supabase_result.get("trace_url"):
                supabase_items.append(f"🔍 <{supabase_result['trace_url']}|Download Playwright Trace>")

            # Screenshot count
            screenshot_count = supabase_result.get("screenshots_uploaded", 0)
            if screenshot_count > 0:
                supabase_items.append(f"📷 {screenshot_count} screenshot(s) uploaded")

            if supabase_items:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🌐 Supabase Artifacts:*\n" + "\n".join(supabase_items)
                    }
                })
        elif artifacts_path:
            # Fallback to local path if Supabase not available
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📁 Local Artifacts:*\n`{artifacts_path}`"
                }
            })

        # Divider
        blocks.append({"type": "divider"})

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🔍 Generated by {self.bot_name} | Run ID: {run_id}"
                }
            ]
        })

        return {
            "username": self.bot_name,
            "blocks": blocks,
        }

    def send_test_alert(self) -> bool:
        """Send test alert to verify webhook configuration.

        Returns:
            True if test alert sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        test_payload = {
            "username": self.bot_name,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🧪 sniff Test Alert",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This is a test alert from sniff. Your webhook is configured correctly!"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🔍 Generated by {self.bot_name}"
                        }
                    ]
                }
            ]
        }

        try:
            response = httpx.post(
                self.webhook_url,
                json=test_payload,
                timeout=10.0,
            )
            response.raise_for_status()

            logger.info("Slack test alert sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack test alert: {e}")
            return False


def create_slack_alert(webhook_url: Optional[str] = None, bot_name: str = "Sniff Alert Bot") -> SlackAlert:
    """Create SlackAlert instance with configuration.

    Args:
        webhook_url: Slack webhook URL
        bot_name: Bot display name

    Returns:
        Configured SlackAlert instance
    """
    return SlackAlert(webhook_url=webhook_url, bot_name=bot_name)
