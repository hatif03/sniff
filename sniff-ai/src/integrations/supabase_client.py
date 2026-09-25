"""Supabase client for uploading sniff run artifacts and data.

Uploads:
- Screenshots, videos, traces to Supabase Storage
- Structured run data to Supabase Database (PostgreSQL)
- Real-time updates during run execution (optional)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

from ..core.models import Observation, ActionResult, DiagnosisResult

logger = logging.getLogger(__name__)


class SupabaseUploader:
    """Handles uploading sniff artifacts to Supabase."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        """Initialize Supabase uploader.

        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase anon/service key (defaults to SUPABASE_KEY env var)

        Raises:
            RuntimeError: If supabase-py is not installed or credentials missing
        """
        if not HAS_SUPABASE:
            raise RuntimeError(
                "supabase-py is not installed. Install with: pip install supabase"
            )

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError(
                "Supabase credentials not found. Set SUPABASE_URL and SUPABASE_KEY "
                "environment variables or pass them to the constructor."
            )

        # Initialize Supabase client
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Supabase client: {e}") from e

        # Storage bucket names
        self.screenshots_bucket = "sniff-screenshots"
        self.videos_bucket = "sniff-videos"
        self.traces_bucket = "sniff-traces"

    def upload_run(
        self,
        run_id: str,
        artifacts_dir: Path,
        goal: str,
        persona_name: str,
        outcome: str,
        start_time: datetime,
        end_time: datetime,
        observations: list[Observation],
        action_results: list[ActionResult],
        diagnosis: Optional[DiagnosisResult] = None,
        reasoning_timeline: Optional[list[dict]] = None,
        persona_review: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Upload complete run to Supabase.

        Args:
            run_id: Unique run identifier
            artifacts_dir: Path to artifacts directory
            goal: Run goal
            persona_name: Persona used
            outcome: Run outcome (success/failure/error)
            start_time: Run start time
            end_time: Run end time
            observations: All observations
            action_results: All action results
            diagnosis: Diagnosis result (if any)
            reasoning_timeline: Agent reasoning timeline (if any)
            persona_review: Persona review (if any)

        Returns:
            Dictionary with upload status and URLs
        """
        logger.info(f"Uploading run {run_id} to Supabase...")

        try:
            # 1. Upload artifacts to Storage
            screenshot_urls = self._upload_screenshots(run_id, artifacts_dir)
            video_urls = self._upload_videos(run_id, artifacts_dir)
            trace_url = self._upload_trace(run_id, artifacts_dir)

            # 2. Insert run record
            duration_seconds = (end_time - start_time).total_seconds()

            run_data = {
                "run_id": run_id,
                "goal": goal,
                "persona_name": persona_name,
                "outcome": outcome,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "total_steps": len(action_results),
                "successful_actions": len([r for r in action_results if r.success]),
                "failed_actions": len([r for r in action_results if not r.success]),
                "starting_url": observations[0].url if observations else None,
                "final_url": observations[-1].url if observations else None,
                "trace_url": trace_url,
                "created_at": datetime.utcnow().isoformat(),
            }

            result = self.client.table("runs").insert(run_data).execute()
            logger.info(f"Inserted run record: {run_id}")

            # 3. Upload observations
            self._upload_observations(run_id, observations, screenshot_urls)

            # 4. Upload action results
            self._upload_actions(run_id, action_results)

            # 5. Upload diagnosis (if present)
            if diagnosis:
                self._upload_diagnosis(run_id, diagnosis)

            # 6. Upload agent reasoning timeline (if present)
            if reasoning_timeline:
                self._upload_reasoning(run_id, reasoning_timeline)

            # 7. Upload persona review (if present)
            if persona_review:
                self._upload_persona_review(run_id, persona_review)

            logger.info(f"Successfully uploaded run {run_id} to Supabase")

            # Generate public URL for run
            public_url = f"{self.supabase_url.rstrip('/')}/runs/{run_id}"

            # Get latest screenshot URL (final state)
            latest_screenshot_url = None
            if screenshot_urls:
                max_step = max(screenshot_urls.keys())
                latest_screenshot_url = screenshot_urls.get(max_step)

            # Get first video URL if any
            first_video_url = video_urls[0] if video_urls else None

            return {
                "success": True,
                "run_id": run_id,
                "public_url": public_url,
                "screenshots_uploaded": len(screenshot_urls),
                "videos_uploaded": len(video_urls),
                "trace_uploaded": trace_url is not None,
                # URLs for Slack alert
                "screenshot_urls": screenshot_urls,  # All screenshots by step
                "latest_screenshot_url": latest_screenshot_url,  # Final screenshot
                "video_urls": video_urls,  # All video URLs
                "first_video_url": first_video_url,  # First video
                "trace_url": trace_url,  # Trace file URL
            }

        except Exception as e:
            logger.error(f"Failed to upload run {run_id}: {e}", exc_info=True)
            return {
                "success": False,
                "run_id": run_id,
                "error": str(e),
            }

    def _upload_screenshots(self, run_id: str, artifacts_dir: Path) -> dict[int, str]:
        """Upload screenshots to Supabase Storage.

        Args:
            run_id: Run identifier
            artifacts_dir: Artifacts directory

        Returns:
            Dictionary mapping step number to public URL
        """
        screenshot_urls = {}
        screenshots = sorted(artifacts_dir.glob("step_*.png"))

        for screenshot in screenshots:
            try:
                # Extract step number from filename
                step_num = int(screenshot.stem.split("_")[1])

                # Upload to Supabase Storage
                storage_path = f"{run_id}/{screenshot.name}"

                with open(screenshot, "rb") as f:
                    self.client.storage.from_(self.screenshots_bucket).upload(
                        path=storage_path,
                        file=f.read(),
                        file_options={"content-type": "image/png"}
                    )

                # Get public URL
                public_url = self.client.storage.from_(self.screenshots_bucket).get_public_url(storage_path)
                screenshot_urls[step_num] = public_url

                logger.debug(f"Uploaded screenshot for step {step_num}")

            except Exception as e:
                logger.warning(f"Failed to upload screenshot {screenshot.name}: {e}")

        logger.info(f"Uploaded {len(screenshot_urls)} screenshots")
        return screenshot_urls

    def _upload_videos(self, run_id: str, artifacts_dir: Path) -> list[str]:
        """Upload videos to Supabase Storage.

        Args:
            run_id: Run identifier
            artifacts_dir: Artifacts directory

        Returns:
            List of public URLs
        """
        video_urls = []
        videos_dir = artifacts_dir / "videos"

        if not videos_dir.exists():
            return video_urls

        videos = list(videos_dir.glob("*.webm"))

        for video in videos:
            try:
                storage_path = f"{run_id}/{video.name}"

                with open(video, "rb") as f:
                    self.client.storage.from_(self.videos_bucket).upload(
                        path=storage_path,
                        file=f.read(),
                        file_options={"content-type": "video/webm"}
                    )

                public_url = self.client.storage.from_(self.videos_bucket).get_public_url(storage_path)
                video_urls.append(public_url)

                logger.debug(f"Uploaded video {video.name}")

            except Exception as e:
                logger.warning(f"Failed to upload video {video.name}: {e}")

        logger.info(f"Uploaded {len(video_urls)} videos")
        return video_urls

    def _upload_trace(self, run_id: str, artifacts_dir: Path) -> Optional[str]:
        """Upload Playwright trace to Supabase Storage.

        Args:
            run_id: Run identifier
            artifacts_dir: Artifacts directory

        Returns:
            Public URL or None
        """
        trace_file = artifacts_dir / "trace.zip"

        if not trace_file.exists():
            return None

        try:
            storage_path = f"{run_id}/trace.zip"

            with open(trace_file, "rb") as f:
                self.client.storage.from_(self.traces_bucket).upload(
                    path=storage_path,
                    file=f.read(),
                    file_options={"content-type": "application/zip"}
                )

            public_url = self.client.storage.from_(self.traces_bucket).get_public_url(storage_path)
            logger.info(f"Uploaded trace file")
            return public_url

        except Exception as e:
            logger.warning(f"Failed to upload trace: {e}")
            return None

    def _upload_observations(
        self,
        run_id: str,
        observations: list[Observation],
        screenshot_urls: dict[int, str]
    ) -> None:
        """Upload observations to database.

        Args:
            run_id: Run identifier
            observations: List of observations
            screenshot_urls: Mapping of step to screenshot URL
        """
        observation_records = []

        for obs in observations:
            record = {
                "run_id": run_id,
                "step": obs.step,
                "timestamp": obs.timestamp,
                "url": obs.url,
                "screenshot_url": screenshot_urls.get(obs.step),
                "visible_text": obs.visibleText,
                "timing": obs.timing,
                "console_errors": obs.consoleErrors,
                "network_events": obs.networkEvents,
                "last_action_result": obs.lastActionResult,
            }
            observation_records.append(record)

        # Batch insert
        if observation_records:
            self.client.table("observations").insert(observation_records).execute()
            logger.info(f"Uploaded {len(observation_records)} observations")

    def _upload_actions(self, run_id: str, action_results: list[ActionResult]) -> None:
        """Upload action results to database.

        Args:
            run_id: Run identifier
            action_results: List of action results
        """
        action_records = []

        for i, action in enumerate(action_results, 1):
            record = {
                "run_id": run_id,
                "step": i,
                "action": action.action,
                "target": action.target,
                "success": action.success,
                "status": action.status,
                "error": action.error,
                "duration_ms": action.durationMs,
                "details": action.details,
                "timestamp": action.timestamp,
            }
            action_records.append(record)

        # Batch insert
        if action_records:
            self.client.table("actions").insert(action_records).execute()
            logger.info(f"Uploaded {len(action_records)} actions")

    def _upload_diagnosis(self, run_id: str, diagnosis: DiagnosisResult) -> None:
        """Upload diagnosis to database.

        Args:
            run_id: Run identifier
            diagnosis: Diagnosis result
        """
        diagnosis_record = {
            "run_id": run_id,
            "root_cause": diagnosis.rootCause,
            "severity": diagnosis.severity,
            "evidence": diagnosis.evidence,
            "likely_owner": diagnosis.likelyOwner,
            "repro_steps": diagnosis.reproSteps,
            "suggested_fix": diagnosis.suggestedFix,
            "created_at": datetime.utcnow().isoformat(),
        }

        self.client.table("diagnoses").insert(diagnosis_record).execute()
        logger.info(f"Uploaded diagnosis")

    def _upload_reasoning(self, run_id: str, reasoning_timeline: list[dict]) -> None:
        """Upload agent reasoning timeline to database.

        Args:
            run_id: Run identifier
            reasoning_timeline: Agent reasoning entries
        """
        reasoning_records = []

        for entry in reasoning_timeline:
            record = {
                "run_id": run_id,
                "step": entry.get("step"),
                "timestamp": entry.get("timestamp"),
                "url": entry.get("url"),
                "action": entry.get("action"),
                "target": entry.get("target"),
                "reasoning": entry.get("reasoning"),
                "confidence": entry.get("confidence"),
                "attempt": entry.get("attempt"),
                "repaired": entry.get("repaired"),
                "is_fallback": entry.get("is_fallback"),
            }
            reasoning_records.append(record)

        # Batch insert
        if reasoning_records:
            self.client.table("agent_reasoning").insert(reasoning_records).execute()
            logger.info(f"Uploaded {len(reasoning_records)} reasoning entries")

    def _upload_persona_review(self, run_id: str, persona_review: dict) -> None:
        """Upload persona review to database.

        Args:
            run_id: Run identifier
            persona_review: Persona review data
        """
        review_record = {
            "run_id": run_id,
            "persona_name": persona_review.get("persona_name"),
            "persona_display_name": persona_review.get("persona_display_name"),
            "overall_sentiment": persona_review.get("overall_sentiment"),
            "experience_rating": persona_review.get("experience_rating"),
            "friction_points": persona_review.get("friction_points", []),
            "positive_aspects": persona_review.get("positive_aspects", []),
            "abandonment_likelihood": persona_review.get("abandonment_likelihood"),
            "narrative": persona_review.get("narrative"),
            "recommendations": persona_review.get("recommendations", []),
            "timestamp": persona_review.get("timestamp"),
            "created_at": datetime.utcnow().isoformat(),
        }

        self.client.table("persona_reviews").insert(review_record).execute()
        logger.info(f"Uploaded persona review")

    def ensure_buckets_exist(self) -> bool:
        """Ensure required storage buckets exist.

        Returns:
            True if all buckets exist or were created successfully
        """
        buckets = [
            self.screenshots_bucket,
            self.videos_bucket,
            self.traces_bucket,
        ]

        try:
            logger.debug(f"Checking Supabase storage buckets: {', '.join(buckets)}")

            # Get existing buckets
            existing_buckets = self.client.storage.list_buckets()
            existing_names = {b.name for b in existing_buckets}

            # Check if all required buckets exist
            missing_buckets = [b for b in buckets if b not in existing_names]

            if not missing_buckets:
                logger.debug(f"✓ All required storage buckets exist: {', '.join(buckets)}")
                return True

            # Try to create missing buckets (may fail due to RLS policies)
            logger.debug(f"Attempting to create missing buckets: {', '.join(missing_buckets)}")
            created_count = 0
            for bucket_name in missing_buckets:
                try:
                    self.client.storage.create_bucket(
                        bucket_name,
                        options={"public": True}
                    )
                    logger.info(f"✓ Created bucket: {bucket_name}")
                    created_count += 1
                except Exception as create_error:
                    error_str = str(create_error)
                    # Check if error is due to bucket already existing or RLS policy
                    if "already exists" in error_str.lower() or "duplicate" in error_str.lower():
                        logger.debug(f"Bucket '{bucket_name}' already exists (expected)")
                    elif "row-level security" in error_str.lower() or "403" in error_str:
                        # RLS policy prevents creation - bucket likely exists but we can't create it
                        logger.debug(f"Cannot create bucket '{bucket_name}' due to RLS policy (bucket may already exist)")
                    else:
                        # Unexpected error
                        logger.warning(f"Unexpected error creating bucket '{bucket_name}': {create_error}")

            # Re-check bucket existence
            existing_buckets = self.client.storage.list_buckets()
            existing_names = {b.name for b in existing_buckets}
            still_missing = [b for b in buckets if b not in existing_names]

            if not still_missing:
                if created_count > 0:
                    logger.info(f"✓ All required buckets verified ({created_count} created, {len(buckets) - created_count} already existed)")
                else:
                    logger.info(f"✓ All required buckets verified (all existed)")
                return True
            else:
                # Buckets are still missing after creation attempt
                # Try to test if we can actually upload to them (they might exist but not show in list)
                logger.info(
                    f"Some buckets not visible in list: {still_missing}. "
                    f"This may be due to RLS policies. Continuing anyway - uploads will verify bucket existence."
                )
                # Return True to allow uploads to attempt - they'll fail if buckets truly don't exist
                return True

        except Exception as e:
            logger.error(f"Failed to check buckets: {e}")
            # Don't fail completely - buckets might exist but we can't list them
            logger.info("Continuing anyway - uploads will fail if buckets don't exist")
            return True  # Return True to allow uploads to attempt


def create_supabase_uploader(config) -> Optional[SupabaseUploader]:
    """Create Supabase uploader from configuration.

    Args:
        config: SniffConfig instance

    Returns:
        SupabaseUploader instance or None if disabled/not configured
    """
    # Check if Supabase integration is enabled
    if not hasattr(config, 'supabase') or not config.supabase.enabled:
        logger.info("Supabase integration disabled")
        return None

    try:
        uploader = SupabaseUploader(
            supabase_url=config.supabase.url,
            supabase_key=config.supabase.key,
        )

        # Ensure buckets exist
        uploader.ensure_buckets_exist()

        return uploader

    except Exception as e:
        logger.warning(f"Could not create Supabase uploader: {e}")
        return None
