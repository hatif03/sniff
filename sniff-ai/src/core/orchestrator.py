"""Run orchestrator with state machine and guardrails.

Central runtime coordinator that:
- Maintains run state and transitions
- Calls Agent Service for decisions
- Calls Execution Worker to perform actions
- Triggers Diagnosis Engine on fail/stuck/timeout
- Emits report + alert

Architecture boundaries:
- Orchestrator owns state machine authority
- Agent returns decisions only (no direct execution)
- Worker executes tools only (no decision-making)
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime
import uuid

from .models import Observation, AgentDecision, ActionResult, DiagnosisResult
from .state_machine import StateMachine, RunState, RunOutcome
from .config import SniffConfig
from .persona import PersonaProfile
from .validation import DecisionSanitizer, create_default_sanitizer
from ..executor.playwright_worker import PlaywrightWorker
from ..diagnosis.classifier import DiagnosisClassifier, create_default_classifier
from ..alerts.slack import SlackAlert, create_slack_alert
from ..evidence.report_builder import ReportBuilder, RunReport, create_report_builder
from ..agent.persona_reviewer import PersonaReviewer, create_persona_reviewer

# Optional Supabase integration
try:
    from ..integrations.supabase_client import SupabaseUploader, create_supabase_uploader
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    SupabaseUploader = None
    create_supabase_uploader = None

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Raised when a guardrail is violated."""
    pass


class RunOrchestrator:
    """Orchestrator for autonomous run execution with state machine and guardrails.

    Coordinates all components:
    - State machine for flow control
    - Agent service for decisions
    - Execution worker for browser actions
    - Diagnosis engine for failure classification
    - Alert service for escalation
    - Report builder for artifacts
    """

    def __init__(
        self,
        config: SniffConfig,
        agent_service: Optional[Any] = None,  # Will be provided by CLI/integration
        progress_callback: Optional[callable] = None,  # Callback for progress updates
    ):
        """Initialize orchestrator.

        Args:
            config: sniff configuration
            agent_service: Agent service instance (optional, for dependency injection)
            progress_callback: Optional callback(message: str) for progress updates
        """
        self.config = config
        self.agent_service = agent_service
        self.progress_callback = progress_callback

        # Initialize components
        self.sanitizer = create_default_sanitizer()
        self.diagnosis_classifier = create_default_classifier()
        self.slack_alert = create_slack_alert(
            webhook_url=config.slack.webhook_url,
            bot_name=config.slack.bot_name,
        )
        self.report_builder = create_report_builder(
            artifacts_base_path=Path(config.artifacts_path)
        )

        # Initialize persona reviewer (optional, may fail if Bedrock not configured)
        self.persona_reviewer: Optional[PersonaReviewer] = None
        try:
            self.persona_reviewer = create_persona_reviewer(config)
        except Exception as e:
            logger.warning(f"Could not create persona reviewer: {e}")

        # Initialize Supabase uploader (optional)
        self.supabase_uploader: Optional[Any] = None
        if HAS_SUPABASE and create_supabase_uploader:
            try:
                self.supabase_uploader = create_supabase_uploader(config)
            except Exception as e:
                logger.warning(f"Could not create Supabase uploader: {e}")

        # Initialize website analyzer, goal enhancer, and planner
        from ..agent.website_analyzer import create_website_analyzer
        from ..agent.goal_enhancer import create_goal_enhancer
        from ..agent.planner import create_planner

        self.website_analyzer = create_website_analyzer()
        self.goal_enhancer: Optional[Any] = None
        self.planner: Optional[Any] = None
        if self.agent_service:
            # DecisionService uses 'client' attribute for BedrockClient
            bedrock_client = getattr(self.agent_service, 'client', None) or getattr(self.agent_service, 'bedrock_client', None)
            if bedrock_client:
                try:
                    self.goal_enhancer = create_goal_enhancer(bedrock_client)
                    logger.info("Goal enhancer initialized successfully")
                except Exception as e:
                    logger.warning(f"Could not create goal enhancer: {e}")

                try:
                    self.planner = create_planner(bedrock_client)
                    logger.info("Planner initialized successfully")
                except Exception as e:
                    logger.warning(f"Could not create planner: {e}")

        # Run state
        self.run_id: Optional[str] = None
        self.state_machine: Optional[StateMachine] = None
        self.worker: Optional[PlaywrightWorker] = None

        # Run data
        self.observations: list[Observation] = []
        self.action_results: list[ActionResult] = []
        self.diagnosis: Optional[DiagnosisResult] = None
        self.report: Optional[RunReport] = None
        self.reasoning_timeline: list[dict] = []
        self.persona_review: Optional[dict] = None
        self.supabase_upload_result: Optional[dict] = None  # Store Supabase URLs for Slack alert

        # Run parameters
        self.goal: Optional[str] = None
        self.enhanced_goal: Optional[str] = None  # Context-enhanced version of goal
        self.goal_type: Optional[Any] = None  # GoalType (exploratory/action/unknown)
        self.persona: Optional[PersonaProfile] = None
        self.start_url: Optional[str] = None

        # Timing
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Guardrail tracking
        self.step_count = 0
        self.intent_retry_count = 0
        self.current_url_dwell_start: Optional[datetime] = None
        self.last_url: Optional[str] = None

    def _report_progress(self, message: str):
        """Report progress update to callback if available."""
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception as e:
                logger.debug(f"Progress callback failed: {e}")

    async def run(
        self,
        goal: str,
        start_url: str,
        persona_name: str,
        device_name: Optional[str] = None,
    ) -> RunReport:
        """Execute autonomous run with full state machine.

        Args:
            goal: Run goal (user-defined objective)
            start_url: Starting URL for navigation
            persona_name: Name of persona to use
            device_name: Device to emulate (default from config)

        Returns:
            RunReport with results and artifacts

        Raises:
            GuardrailViolation: If guardrails are exceeded
        """
        # Initialize run
        # Generate human-readable run ID: run_YYYYMMDD_HHMMSS_<short-uuid>
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]  # First 8 chars for readability
        self.run_id = f"run_{timestamp}_{short_uuid}"
        self.goal = goal
        self.start_url = start_url
        self.start_time = datetime.utcnow()

        # Detect goal type (exploratory vs action-oriented)
        if self.planner:
            self.goal_type = self.planner.detect_goal_type(goal)
            logger.info(f"Goal type detected: {self.goal_type.value if self.goal_type else 'unknown'}")
            goal_type_emoji = "🔍" if self.goal_type.value == "exploratory" else "✅" if self.goal_type.value == "action" else "❓"
            self._report_progress(f"{goal_type_emoji} Goal type: {self.goal_type.value}")

        # Load persona
        personas_path = Path(self.config.personas_path)
        self.persona = PersonaProfile.load(persona_name, personas_path)

        # Initialize state machine
        self.state_machine = StateMachine(initial_state=RunState.SETUP)

        logger.info(f"Starting run {self.run_id} with goal: {goal}")
        self._report_progress(f"🚀 Starting run {self.run_id}")
        self._report_progress(f"🎯 Goal: {goal}")
        self._report_progress(f"🎭 Persona: {self.persona.display_name}")

        try:
            # Execute state machine
            await self._execute_state_machine(device_name or self.config.defaults.device)

        except Exception as e:
            logger.error(f"Run failed with error: {e}", exc_info=True)
            # Ensure we transition to terminal state
            if self.state_machine and not self.state_machine.is_terminal():
                try:
                    self.state_machine.transition(RunState.DONE, f"Error: {e}")
                    self.state_machine.set_outcome(RunOutcome.ERROR)
                except ValueError:
                    # Already in terminal state or invalid transition
                    pass

        finally:
            # Cleanup
            self.end_time = datetime.utcnow()
            if self.worker:
                await self.worker.cleanup()

            # Capture agent reasoning timeline if agent service is available
            if self.agent_service and hasattr(self.agent_service, 'get_reasoning_timeline'):
                try:
                    self.reasoning_timeline = self.agent_service.get_reasoning_timeline()
                    logger.info(f"Captured agent reasoning timeline: {len(self.reasoning_timeline)} decisions")
                except Exception as e:
                    logger.warning(f"Failed to capture reasoning timeline: {e}")

            # Generate final report
            outcome = self.state_machine.outcome if self.state_machine else None
            if outcome is None:
                outcome = RunOutcome.ERROR

            self.report = self.report_builder.build_report(
                run_id=self.run_id,
                outcome=outcome,
                goal=self.goal,
                persona_name=self.persona.name,
                start_time=self.start_time,
                end_time=self.end_time,
                observations=self.observations,
                action_results=self.action_results,
                diagnosis=self.diagnosis,
            )

            # Generate persona review
            if self.persona_reviewer and self.persona:
                try:
                    duration_seconds = (self.end_time - self.start_time).total_seconds()
                    # Safely get outcome value
                    outcome_value = outcome.value if outcome else "ERROR"
                    self.persona_review = self.persona_reviewer.generate_review(
                        persona=self.persona,
                        goal=self.goal,
                        observations=self.observations,
                        action_results=self.action_results,
                        diagnosis=self.diagnosis,
                        outcome=outcome_value,
                        duration_seconds=duration_seconds,
                    )
                    logger.info(f"Generated persona review from {self.persona.name}'s perspective")
                except Exception as e:
                    logger.warning(f"Failed to generate persona review: {e}")

            # Save report and evidence
            self.report_builder.save_report(self.report)
            self.report_builder.save_evidence_bundle(
                run_id=self.run_id,
                observations=self.observations,
                action_results=self.action_results,
                diagnosis=self.diagnosis,
                reasoning_timeline=self.reasoning_timeline if self.reasoning_timeline else None,
                persona_review=self.persona_review,
            )

            # Upload to Supabase if configured and not already uploaded
            # (Upload happens in ALERT state for failures, here for successes/non-alerted runs)
            if self.supabase_uploader and not self.supabase_upload_result:
                try:
                    logger.info("Uploading to Supabase (not uploaded during alert)...")
                    artifacts_dir = Path(self.config.artifacts_path) / self.run_id
                    upload_result = self.supabase_uploader.upload_run(
                        run_id=self.run_id,
                        artifacts_dir=artifacts_dir,
                        goal=self.goal,
                        persona_name=self.persona.name,
                        outcome=outcome.value,
                        start_time=self.start_time,
                        end_time=self.end_time,
                        observations=self.observations,
                        action_results=self.action_results,
                        diagnosis=self.diagnosis,
                        reasoning_timeline=self.reasoning_timeline if self.reasoning_timeline else None,
                        persona_review=self.persona_review,
                    )

                    if upload_result.get("success"):
                        logger.info(f"Uploaded run to Supabase: {upload_result.get('public_url')}")
                        self.supabase_upload_result = upload_result
                    else:
                        logger.warning(f"Supabase upload failed: {upload_result.get('error')}")

                except Exception as e:
                    logger.warning(f"Failed to upload to Supabase: {e}")
            elif self.supabase_upload_result:
                logger.info("Supabase upload already completed during alert state")

        return self.report

    async def _execute_state_machine(self, device_name: str) -> None:
        """Execute state machine loop.

        Args:
            device_name: Device to emulate
        """
        while not self.state_machine.is_terminal():
            current_state = self.state_machine.current_state

            logger.info(f"State: {current_state.value}")

            # Execute state handler
            if current_state == RunState.SETUP:
                await self._handle_setup(device_name)
            elif current_state == RunState.NAVIGATE:
                await self._handle_navigate()
            elif current_state == RunState.ACTION_EXECUTION:
                await self._handle_action_execution()
            elif current_state == RunState.EVALUATE_PROGRESS:
                await self._handle_evaluate_progress()
            elif current_state == RunState.STUCK_DETECTED:
                await self._handle_stuck_detected()
            elif current_state == RunState.DIAGNOSE:
                await self._handle_diagnose()
            elif current_state == RunState.ALERT:
                await self._handle_alert()
            elif current_state == RunState.REPORT:
                await self._handle_report()

    async def _handle_setup(self, device_name: str) -> None:
        """Handle SETUP state: Initialize worker and components.

        Args:
            device_name: Device to emulate
        """
        self._report_progress("⚙️  Setting up browser environment...")
        try:
            # Create artifacts directory
            artifacts_dir = Path(self.config.artifacts_path) / self.run_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Initialize worker
            self.worker = PlaywrightWorker(
                run_id=self.run_id,
                artifacts_dir=artifacts_dir,
                device_name=device_name,
                headless=self.config.playwright.headless,
                slow_mo=self.config.playwright.slow_mo,
            )

            if not self.config.test_mode:
                await self.worker.initialize()

            logger.info("Setup complete, transitioning to NAVIGATE")
            self._report_progress("✓ Browser ready")
            self.state_machine.transition(RunState.NAVIGATE, "Setup complete")

        except Exception as e:
            logger.error(f"Setup failed: {e}")
            self.state_machine.transition(RunState.DONE, f"Setup failed: {e}")
            self.state_machine.set_outcome(RunOutcome.ERROR)

    async def _handle_navigate(self) -> None:
        """Handle NAVIGATE state: Navigate to start URL."""
        self._report_progress(f"🌐 Navigating to {self.start_url}...")
        try:
            # Navigate to start URL
            observation = await self.worker.navigate(self.start_url)
            self.observations.append(observation)

            # Update dwell tracking
            self.last_url = observation.url
            self.current_url_dwell_start = datetime.utcnow()

            logger.info(f"Navigated to {self.start_url}")
            self._report_progress(f"✓ Loaded {self.start_url}")

            # Enhance goal with website context (if goal enhancer available)
            if self.goal_enhancer and not self.enhanced_goal:
                self._report_progress("🔍 Analyzing website structure...")
                try:
                    # Analyze website from initial observation
                    website_context = self.website_analyzer.analyze_from_observation(observation)
                    logger.info(f"Website analyzed: {website_context.page_structure}")

                    # Enhance goal with context
                    self._report_progress("📋 Creating detailed execution plan...")
                    self.enhanced_goal = self.goal_enhancer.enhance_goal(
                        original_goal=self.goal,
                        website_context=website_context,
                        persona=self.persona,
                    )
                    logger.info(f"Goal enhanced ({len(self.enhanced_goal)} chars)")
                    self._report_progress("✓ Execution plan ready")
                except Exception as e:
                    logger.warning(f"Goal enhancement failed: {e}, using original goal")
                    self.enhanced_goal = self.goal

            self.state_machine.transition(RunState.ACTION_EXECUTION, "Navigation complete")

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self.state_machine.transition(RunState.STUCK_DETECTED, f"Navigation failed: {e}")

    async def _handle_action_execution(self) -> None:
        """Handle ACTION_EXECUTION state: Get decision and execute action."""
        self._report_progress(f"🤔 Step {self.step_count + 1}: Analyzing page...")
        try:
            # Check guardrails
            self._check_guardrails()

            # Get current observation
            current_observation = self.observations[-1] if self.observations else None

            if not current_observation:
                raise ValueError("No observation available for decision")

            # Get agent decision
            if self.agent_service:
                decision = await self._get_agent_decision(current_observation)
            else:
                # Fallback: abort if no agent service
                decision = AgentDecision(
                    action="abort",
                    abortReason="No agent service configured",
                    reasoningSummary="Cannot proceed without agent service",
                    confidence=0.0,
                )

            # Sanitize decision
            sanitized = self.sanitizer.sanitize(decision)
            if sanitized.wasSanitized:
                logger.warning(f"Decision sanitized: {sanitized.sanitizationReason}")

            # Execute action (returns observation, stores action_result in worker)
            action_desc = f"{sanitized.decision.action}"
            if sanitized.decision.target:
                action_desc += f" '{sanitized.decision.target}'"
            self._report_progress(f"✋ Step {self.step_count + 1}: {action_desc}")

            observation = await self._execute_action(sanitized.decision)
            self.observations.append(observation)

            # Get action result from worker
            if self.worker.last_action_result:
                self.action_results.append(self.worker.last_action_result)
                # Report action result
                if self.worker.last_action_result.success:
                    self._report_progress(f"   ✓ {action_desc} successful")
                else:
                    self._report_progress(f"   ✗ {action_desc} failed")

            self.step_count += 1

            # Update dwell tracking
            if observation.url != self.last_url:
                self.last_url = observation.url
                self.current_url_dwell_start = datetime.utcnow()
                self.intent_retry_count = 0  # Reset retry count on navigation

            # Handle abort action
            if sanitized.decision.action == "abort":
                self.state_machine.transition(RunState.STUCK_DETECTED, f"Agent aborted: {sanitized.decision.abortReason}")
                return

            # Transition to progress evaluation
            self.state_machine.transition(RunState.EVALUATE_PROGRESS, "Action executed")

        except GuardrailViolation as e:
            logger.warning(f"Guardrail violated: {e}")
            self.state_machine.transition(RunState.STUCK_DETECTED, str(e))

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            self.state_machine.transition(RunState.STUCK_DETECTED, f"Execution error: {e}")

    async def _handle_evaluate_progress(self) -> None:
        """Handle EVALUATE_PROGRESS state: Check if goal is reached or stuck."""
        try:
            # Check if goal is reached
            if await self._is_goal_reached():
                logger.info("Goal reached!")
                self._report_progress("🎉 Goal achieved!")
                self.state_machine.transition(RunState.DONE, "Goal reached")
                self.state_machine.set_outcome(RunOutcome.SUCCESS)
                return

            # Check for stuck conditions
            if self._is_stuck():
                stuck_reason = self._get_stuck_reason()
                logger.warning(f"Stuck detected: {stuck_reason}")
                self.state_machine.transition(RunState.STUCK_DETECTED, stuck_reason)
                return

            # Continue execution
            self.state_machine.transition(RunState.ACTION_EXECUTION, "Continuing execution")

        except Exception as e:
            logger.error(f"Progress evaluation failed: {e}")
            self.state_machine.transition(RunState.STUCK_DETECTED, f"Evaluation error: {e}")

    async def _handle_stuck_detected(self) -> None:
        """Handle STUCK_DETECTED state: Transition to diagnosis."""
        logger.info("Stuck detected, proceeding to diagnosis")
        self._report_progress("⚠️  Stuck condition detected, analyzing...")
        self.state_machine.transition(RunState.DIAGNOSE, "Stuck condition detected")

    async def _handle_diagnose(self) -> None:
        """Handle DIAGNOSE state: Run diagnosis engine."""
        self._report_progress("🔍 Diagnosing root cause...")
        try:
            # Get stuck reason from last transition
            last_transition = self.state_machine.transitions[-1] if self.state_machine.transitions else None
            stuck_reason = last_transition.reason if last_transition else "Unknown"

            # Run diagnosis
            self.diagnosis = self.diagnosis_classifier.classify(
                observations=self.observations,
                action_results=self.action_results,
                run_goal=self.goal,
                stuck_reason=stuck_reason,
            )

            logger.info(f"Diagnosis complete: {self.diagnosis.rootCause} ({self.diagnosis.severity})")

            # Transition to alert if webhook configured, otherwise skip to report
            if self.config.slack.webhook_url:
                self.state_machine.transition(RunState.ALERT, "Diagnosis complete, sending alert")
            else:
                logger.info("Slack webhook not configured, skipping alert")
                self.state_machine.transition(RunState.REPORT, "Diagnosis complete, no alert configured")

        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            self.state_machine.transition(RunState.REPORT, f"Diagnosis error: {e}")

    async def _handle_alert(self) -> None:
        """Handle ALERT state: Upload to Supabase (if configured), then send Slack alert."""
        try:
            # Upload to Supabase FIRST to get public URLs for Slack alert
            if self.supabase_uploader and self.diagnosis:
                try:
                    logger.info("Uploading artifacts to Supabase before sending alert...")
                    artifacts_dir = Path(self.config.artifacts_path) / self.run_id
                    outcome = self.state_machine.outcome if self.state_machine.outcome else RunOutcome.FAILURE

                    self.supabase_upload_result = self.supabase_uploader.upload_run(
                        run_id=self.run_id,
                        artifacts_dir=artifacts_dir,
                        goal=self.goal,
                        persona_name=self.persona.name,
                        outcome=outcome.value,
                        start_time=self.start_time,
                        end_time=datetime.utcnow(),
                        observations=self.observations,
                        action_results=self.action_results,
                        diagnosis=self.diagnosis,
                        reasoning_timeline=self.reasoning_timeline if self.reasoning_timeline else None,
                        persona_review=self.persona_review,
                    )

                    if self.supabase_upload_result.get("success"):
                        logger.info(f"Uploaded to Supabase: {self.supabase_upload_result.get('public_url')}")
                    else:
                        logger.warning(f"Supabase upload failed: {self.supabase_upload_result.get('error')}")

                except Exception as e:
                    logger.warning(f"Failed to upload to Supabase before alert: {e}")
                    # Continue anyway - alert can still be sent with local paths

            # Now send Slack alert with Supabase URLs (if available)
            if self.diagnosis:
                artifacts_path = str(Path(self.config.artifacts_path) / self.run_id)
                success = self.slack_alert.send_alert(
                    run_id=self.run_id,
                    diagnosis=self.diagnosis,
                    run_goal=self.goal,
                    artifacts_path=artifacts_path,
                    supabase_result=self.supabase_upload_result,  # Pass Supabase URLs
                )

                if success:
                    logger.info("Alert sent successfully")
                else:
                    logger.warning("Alert failed to send")

            self.state_machine.transition(RunState.REPORT, "Alert processing complete")

        except Exception as e:
            logger.error(f"Alert failed: {e}")
            self.state_machine.transition(RunState.REPORT, f"Alert error: {e}")

    async def _handle_report(self) -> None:
        """Handle REPORT state: Finalize and transition to DONE."""
        logger.info("Report preparation complete")

        # Set outcome if not already set
        if not self.state_machine.outcome:
            if self.diagnosis:
                self.state_machine.set_outcome(RunOutcome.FAILURE)
            else:
                self.state_machine.set_outcome(RunOutcome.ABORTED)

        self.state_machine.transition(RunState.DONE, "Report complete")

    async def _get_agent_decision(self, observation: Observation) -> AgentDecision:
        """Get decision from agent service.

        Args:
            observation: Current observation

        Returns:
            AgentDecision from agent

        Note: This is a placeholder. Actual implementation will use agent service.
        """
        # This will be implemented by agent service integration
        # For now, return a fallback decision
        if self.agent_service and hasattr(self.agent_service, 'get_decision'):
            # Generate rich persona prompt using enhanced context builder
            persona_description = None
            if self.persona:
                # Use the enhanced to_prompt_context() which includes behavioral modifiers
                persona_description = self.persona.to_prompt_context()
                logger.debug(f"Using enhanced persona prompt for {self.persona.name}")

            # Convert recent action results to history format
            recent_history = []
            for result in self.action_results[-5:]:
                recent_history.append({
                    "action": result.action,
                    "success": result.success,
                    "status": result.status,
                    "details": result.details,
                })

            # Get decision (synchronous call, run in executor to keep async)
            # Use enhanced goal if available, otherwise use original goal
            goal_to_use = self.enhanced_goal if self.enhanced_goal else self.goal

            # Get next-action planning guidance (if planner available and past first step)
            planning_guidance = None
            if self.planner and self.step_count > 0 and self.goal_type:
                try:
                    # Convert observation to dict (Pydantic v2 uses model_dump())
                    obs_dict = observation.model_dump() if hasattr(observation, 'model_dump') else observation.dict()

                    planning_guidance = self.planner.get_next_action_plan(
                        goal=goal_to_use,
                        goal_type=self.goal_type,
                        current_observation=obs_dict,
                        action_history=[{
                            "action": r.action,
                            "target": r.details.get("target", "") if r.details else "",
                        } for r in self.action_results],
                    )
                    logger.debug(f"Planning guidance: {planning_guidance}")

                    # Append planning guidance to goal
                    if planning_guidance:
                        goal_to_use = f"{goal_to_use}\n\n**Next Action Guidance:** {planning_guidance}"
                except Exception as e:
                    logger.warning(f"Planning failed: {e}, continuing without guidance")

            import asyncio
            loop = asyncio.get_event_loop()
            decision = await loop.run_in_executor(
                None,
                lambda: self.agent_service.get_decision(
                    observation=observation,
                    goal=goal_to_use,
                    persona_description=persona_description,
                    recent_history=recent_history,
                )
            )
            return decision

        # Fallback: abort
        return AgentDecision(
            action="abort",
            abortReason="Agent service not available",
            reasoningSummary="Cannot make decision without agent service",
            confidence=0.0,
        )

    async def _execute_action(self, decision: AgentDecision) -> Observation:
        """Execute agent decision using worker.

        Args:
            decision: Sanitized agent decision

        Returns:
            Observation from execution (ActionResult stored in worker.last_action_result)
        """
        if decision.action == "tap":
            return await self.worker.tap(decision.target)
        elif decision.action == "type":
            return await self.worker.type(decision.target, decision.inputText)
        elif decision.action == "scroll":
            return await self.worker.scroll(decision.scrollDirection)
        elif decision.action == "wait":
            return await self.worker.wait(decision.waitDurationMs)
        elif decision.action == "back":
            return await self.worker.back()
        else:
            # Abort action doesn't execute, just create result and return last observation
            self.worker.last_action_result = ActionResult(
                success=True,
                action="abort",
                status="success",
                durationMs=0,
                details={"reason": decision.abortReason},
            )
            # Return last observation or capture new one
            if self.observations:
                return self.observations[-1]
            else:
                return await self.worker.capture_observation()

    def _check_guardrails(self) -> None:
        """Check guardrail limits.

        Raises:
            GuardrailViolation: If any guardrail is exceeded
        """
        # Max steps
        if self.step_count >= self.config.guardrails.max_steps:
            raise GuardrailViolation(f"Exceeded max steps: {self.config.guardrails.max_steps}")

        # Hard timeout
        if self.start_time:
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()
            if elapsed >= self.config.guardrails.hard_timeout:
                raise GuardrailViolation(f"Exceeded hard timeout: {self.config.guardrails.hard_timeout}s")

        # Max dwell time (if on same URL)
        if self.current_url_dwell_start:
            dwell_seconds = (datetime.utcnow() - self.current_url_dwell_start).total_seconds()
            if dwell_seconds >= self.config.guardrails.max_dwell_time:
                raise GuardrailViolation(f"Exceeded max dwell time on URL: {self.config.guardrails.max_dwell_time}s")

    async def _is_goal_reached(self) -> bool:
        """Check if run goal is reached.

        Returns:
            True if goal reached, False otherwise

        Note: This is a placeholder. Actual implementation may use agent service.
        """
        # This is a simplified check - actual implementation may use agent service
        # to evaluate goal completion based on current state

        if not self.observations:
            return False

        # Check if we've reached a success state (e.g., confirmation page)
        current_obs = self.observations[-1]
        success_indicators = [
            'success', 'complete', 'confirmation', 'thank you', 'welcome'
        ]

        visible_text_lower = ' '.join(current_obs.visibleText).lower()
        return any(indicator in visible_text_lower for indicator in success_indicators)

    def _is_stuck(self) -> bool:
        """Check if execution is stuck.

        Returns:
            True if stuck, False otherwise
        """
        # Early detection: Check for same action/target failing repeatedly
        if len(self.action_results) >= 3:
            last_three = self.action_results[-3:]
            # If same action failed 3 times, check why
            if all(not r.success for r in last_three):
                # Check if targeting same element repeatedly
                targets = [r.details.get("target") if r.details else None for r in last_three]
                if targets[0] and targets[0] == targets[1] == targets[2]:
                    logger.warning(f"Same target '{targets[0]}' failed 3 times - stuck")
                    return True

                # Check for invalid element type errors (don't retry these)
                statuses = [r.status for r in last_three]
                if "invalid_element_type" in statuses:
                    logger.warning("Invalid element type detected - stopping retries")
                    return True

        # Only consider stuck if we have significant failures
        # Changed from 3 to 5 consecutive failures to allow more exploration
        if len(self.action_results) >= 5:
            recent_failures = [r for r in self.action_results[-5:] if not r.success]
            if len(recent_failures) >= 5:
                return True

        # Check for excessive dwell time on same URL
        # But be more lenient - only flag if really stuck
        if self.current_url_dwell_start:
            dwell_seconds = (datetime.utcnow() - self.current_url_dwell_start).total_seconds()
            # Use 90% threshold instead of 80% to give more time
            if dwell_seconds >= (self.config.guardrails.max_dwell_time * 0.9):
                return True

        return False

    def _get_stuck_reason(self) -> str:
        """Get reason for stuck detection.

        Returns:
            Description of why stuck was detected
        """
        # Check for same target failing repeatedly (early detection)
        if len(self.action_results) >= 3:
            last_three = self.action_results[-3:]
            if all(not r.success for r in last_three):
                targets = [r.details.get("target") if r.details else None for r in last_three]
                if targets[0] and targets[0] == targets[1] == targets[2]:
                    action = last_three[0].action
                    error = last_three[-1].error or "Unknown error"
                    return f"Same target '{targets[0]}' failed 3 times (action: {action}, error: {error})"

                # Check for invalid element type
                statuses = [r.status for r in last_three]
                if "invalid_element_type" in statuses:
                    failed_result = next(r for r in last_three if r.status == "invalid_element_type")
                    return f"Invalid element type: {failed_result.error}"

        # Check for repeated failures
        if len(self.action_results) >= 5:
            recent_failures = [r for r in self.action_results[-5:] if not r.success]
            if len(recent_failures) >= 5:
                # Show what failed to help with diagnosis
                failed_actions = [f"{r.action}" for r in self.action_results[-5:] if not r.success]
                return f"Repeated failures after 5 attempts: {', '.join(failed_actions)}"

        # Check for dwell time
        if self.current_url_dwell_start:
            dwell_seconds = (datetime.utcnow() - self.current_url_dwell_start).total_seconds()
            if dwell_seconds >= (self.config.guardrails.max_dwell_time * 0.9):
                attempts = len([r for r in self.action_results if self.observations and r.action])
                return f"Excessive dwell time ({dwell_seconds:.0f}s) after {attempts} attempts on same URL"

        return "Unknown stuck condition"


class Orchestrator:
    """Synchronous wrapper for RunOrchestrator.

    Provides the interface expected by the CLI run command.
    """

    def __init__(
        self,
        config: SniffConfig,
        run_id: str,
        goal: str,
        persona: PersonaProfile,
        starting_url: str,
        device: str,
        network: str,
        headless: bool,
        max_steps: int,
        progress_callback: Optional[callable] = None,
    ):
        """Initialize orchestrator with run parameters.

        Args:
            config: sniff configuration
            run_id: Unique run identifier
            goal: User-defined test goal
            persona: Persona profile to use
            starting_url: Starting URL for navigation
            device: Device profile name
            network: Network profile name
            headless: Run browser in headless mode
            max_steps: Maximum steps for this run
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.run_id = run_id
        self.goal = goal
        self.persona = persona
        self.starting_url = starting_url
        self.device = device
        self.network = network
        self.headless = headless
        self.max_steps = max_steps
        self.progress_callback = progress_callback

        # Update config overrides
        self.config.playwright.headless = headless
        self.config.guardrails.max_steps = max_steps

    def execute(self) -> dict:
        """Execute the run synchronously.

        Returns:
            Dictionary with run results
        """
        # Create async orchestrator
        from ..agent.decision_service import create_agent_service

        agent_service = None
        try:
            # Try to create agent service (may fail if Bedrock not configured)
            agent_service = create_agent_service(self.config)
        except Exception as e:
            logger.warning(f"Could not create agent service: {e}")
            logger.warning("Running in fallback mode without AI agent")

        orchestrator = RunOrchestrator(
            config=self.config,
            agent_service=agent_service,
            progress_callback=self.progress_callback,
        )

        # Run the async execution
        import asyncio

        try:
            # Run the orchestrator
            report = asyncio.run(
                orchestrator.run(
                    goal=self.goal,
                    start_url=self.starting_url,
                    persona_name=self.persona.name,
                    device_name=self.device,
                )
            )

            # Convert report to dict for CLI
            duration_seconds = (report.end_time - report.start_time).total_seconds()

            return {
                "success": report.outcome == RunOutcome.SUCCESS,
                "run_id": report.run_id,
                "outcome": report.outcome.value,
                "steps_executed": report.total_steps,
                "duration_seconds": duration_seconds,
                "diagnosis": {
                    "rootCause": report.diagnosis.rootCause if report.diagnosis else None,
                    "severity": report.diagnosis.severity if report.diagnosis else None,
                    "evidence": report.diagnosis.evidence if report.diagnosis else {},
                } if report.diagnosis else None,
            }

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "run_id": self.run_id,
                "outcome": "error",
                "steps_executed": orchestrator.step_count,
                "duration_seconds": (datetime.utcnow() - orchestrator.start_time).total_seconds() if orchestrator.start_time else 0,
                "error": str(e),
            }
