"""Unit tests for Agent Service decision generation.

Tests:
- Bedrock client invocation
- Decision schema validation
- Malformed output repair logic
- Fallback decision generation
- Reasoning timeline tracking
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

from src.core.models import Observation, AgentDecision
from src.agent.bedrock_client import BedrockClient, BedrockInvocationError, BedrockTimeoutError
from src.agent.decision_service import (
    DecisionService,
    DecisionGenerationError,
    DecisionValidationError,
    DecisionTimeoutError
)


@pytest.fixture
def sample_observation():
    """Sample observation for testing."""
    return Observation(
        runId="test_run_001",
        step=1,
        url="https://example.com/signup",
        screenshotPath="/tmp/test_screenshot.png",
        visibleText=["Email", "Password", "Sign Up"],
        timing={"ttfb": 200, "domReady": 400},
        consoleErrors=[],
        networkEvents=[],
        lastActionResult={}
    )


@pytest.fixture
def valid_decision_json():
    """Valid decision JSON response."""
    return {
        "action": "type",
        "target": "Email input field",
        "inputText": "test@example.com",
        "reasoningSummary": "User needs to enter email to proceed",
        "confidence": 0.85,
        "fallbackAction": None
    }


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client."""
    return Mock(spec=BedrockClient)


class TestBedrockClient:
    """Tests for BedrockClient wrapper."""

    @patch('boto3.client')
    def test_client_initialization(self, mock_boto_client):
        """Test Bedrock client initializes correctly."""
        client = BedrockClient(region="us-west-2")
        assert client.region == "us-west-2"
        assert "claude" in client.model_id.lower()
        mock_boto_client.assert_called_once()

    @patch('boto3.client')
    def test_invoke_success(self, mock_boto_client):
        """Test successful model invocation."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        # Mock response
        mock_response = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': 'Test response'}]
            }).encode())
        }
        mock_client_instance.invoke_model.return_value = mock_response

        client = BedrockClient()
        response = client.invoke(
            system_prompt="Test system",
            user_message="Test user"
        )

        assert response == "Test response"

    @patch('boto3.client')
    def test_invoke_with_json_response(self, mock_boto_client):
        """Test JSON response parsing."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        json_response = {"key": "value"}
        mock_response = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': json.dumps(json_response)}]
            }).encode())
        }
        mock_client_instance.invoke_model.return_value = mock_response

        client = BedrockClient()
        response = client.invoke_with_json_response(
            system_prompt="Return JSON",
            user_message="Test"
        )

        assert response == json_response

    @patch('boto3.client')
    def test_invoke_with_markdown_json(self, mock_boto_client):
        """Test JSON extraction from markdown code blocks."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        json_data = {"action": "tap"}
        markdown_response = f"```json\n{json.dumps(json_data)}\n```"
        mock_response = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': markdown_response}]
            }).encode())
        }
        mock_client_instance.invoke_model.return_value = mock_response

        client = BedrockClient()
        response = client.invoke_with_json_response(
            system_prompt="Return JSON",
            user_message="Test"
        )

        assert response == json_data


class TestDecisionService:
    """Tests for DecisionService."""

    def test_service_initialization(self):
        """Test service initializes with correct defaults."""
        service = DecisionService(max_repair_retries=3)
        assert service.max_repair_retries == 3
        assert len(service.reasoning_timeline) == 0

    def test_successful_decision_generation(
        self,
        mock_bedrock_client,
        sample_observation,
        valid_decision_json
    ):
        """Test successful decision generation."""
        mock_bedrock_client.invoke_with_json_response.return_value = valid_decision_json

        service = DecisionService(bedrock_client=mock_bedrock_client)
        decision = service.get_decision(
            observation=sample_observation,
            goal="Complete signup"
        )

        assert isinstance(decision, AgentDecision)
        assert decision.action == "type"
        assert decision.inputText == "test@example.com"
        assert decision.confidence == 0.85

        # Check reasoning timeline
        timeline = service.get_reasoning_timeline()
        assert len(timeline) == 1
        assert timeline[0]['action'] == 'type'
        assert timeline[0]['repaired'] is False

    def test_validation_error_triggers_repair(
        self,
        mock_bedrock_client,
        sample_observation
    ):
        """Test malformed output triggers repair attempts."""
        # First attempt: invalid JSON (missing required field)
        invalid_json = {
            "action": "type",
            "target": "Email field",
            # Missing inputText - should fail validation
            "reasoningSummary": "Enter email",
            "confidence": 0.8
        }

        # Second attempt: valid JSON
        valid_json = {
            "action": "type",
            "target": "Email field",
            "inputText": "test@example.com",
            "reasoningSummary": "Enter email",
            "confidence": 0.8
        }

        mock_bedrock_client.invoke_with_json_response.side_effect = [
            invalid_json,  # First attempt fails validation
            valid_json     # Repair succeeds
        ]

        service = DecisionService(
            bedrock_client=mock_bedrock_client,
            max_repair_retries=2
        )

        decision = service.get_decision(
            observation=sample_observation,
            goal="Complete signup"
        )

        # Should succeed after repair
        assert decision.action == "type"
        assert decision.inputText == "test@example.com"

        # Check that repair was attempted
        assert mock_bedrock_client.invoke_with_json_response.call_count == 2

        # Check timeline shows repair
        timeline = service.get_reasoning_timeline()
        assert timeline[0]['repaired'] is True
        assert timeline[0]['attempt'] == 2

    def test_max_repair_retries_exceeded_returns_fallback(
        self,
        mock_bedrock_client,
        sample_observation
    ):
        """Test fallback decision when all repair attempts fail."""
        # All attempts return invalid JSON
        invalid_json = {
            "action": "type",
            # Missing required fields
            "confidence": 0.8
        }

        mock_bedrock_client.invoke_with_json_response.return_value = invalid_json

        service = DecisionService(
            bedrock_client=mock_bedrock_client,
            max_repair_retries=2
        )

        decision = service.get_decision(
            observation=sample_observation,
            goal="Complete signup"
        )

        # Should return safe fallback (abort)
        assert decision.action == "abort"
        assert "failed after" in decision.abortReason.lower()
        assert decision.confidence == 0.0

        # Check timeline shows fallback
        timeline = service.get_reasoning_timeline()
        assert timeline[0]['is_fallback'] is True

    def test_bedrock_timeout_raises_exception(
        self,
        mock_bedrock_client,
        sample_observation
    ):
        """Test timeout exception is raised and handled."""
        mock_bedrock_client.invoke_with_json_response.side_effect = (
            BedrockTimeoutError("Request timed out")
        )

        service = DecisionService(bedrock_client=mock_bedrock_client)

        with pytest.raises(DecisionTimeoutError):
            service.get_decision(
                observation=sample_observation,
                goal="Complete signup"
            )

    def test_reasoning_timeline_tracking(self, mock_bedrock_client):
        """Test reasoning timeline accumulates correctly."""
        valid_decision = {
            "action": "tap",
            "target": "Sign Up button",
            "reasoningSummary": "Initiate signup",
            "confidence": 0.9
        }

        mock_bedrock_client.invoke_with_json_response.return_value = valid_decision

        service = DecisionService(bedrock_client=mock_bedrock_client)

        # Generate multiple decisions
        for step in range(1, 4):
            obs = Observation(
                runId="test_run",
                step=step,
                url=f"https://example.com/step{step}",
                screenshotPath=f"/tmp/step{step}.png",
                visibleText=["Content"],
                timing={},
                consoleErrors=[],
                networkEvents=[],
                lastActionResult={}
            )

            service.get_decision(observation=obs, goal="Test goal")

        # Check timeline
        timeline = service.get_reasoning_timeline()
        assert len(timeline) == 3
        assert timeline[0]['step'] == 1
        assert timeline[1]['step'] == 2
        assert timeline[2]['step'] == 3

        # Test clear
        service.clear_timeline()
        assert len(service.get_reasoning_timeline()) == 0

    def test_decision_with_persona(
        self,
        mock_bedrock_client,
        sample_observation,
        valid_decision_json
    ):
        """Test persona description is included in prompt."""
        mock_bedrock_client.invoke_with_json_response.return_value = valid_decision_json

        service = DecisionService(bedrock_client=mock_bedrock_client)
        service.get_decision(
            observation=sample_observation,
            goal="Complete signup",
            persona_description="Confused first-time user"
        )

        # Check that invoke was called (persona is in system prompt)
        assert mock_bedrock_client.invoke_with_json_response.called

    def test_decision_with_recent_history(
        self,
        mock_bedrock_client,
        sample_observation,
        valid_decision_json
    ):
        """Test recent history is included in prompt."""
        mock_bedrock_client.invoke_with_json_response.return_value = valid_decision_json

        history = [
            {"action": "tap", "target": "Sign Up", "result": "success"}
        ]

        service = DecisionService(bedrock_client=mock_bedrock_client)
        service.get_decision(
            observation=sample_observation,
            goal="Complete signup",
            recent_history=history
        )

        # Check that invoke was called with history context
        assert mock_bedrock_client.invoke_with_json_response.called


class TestAgentDecisionValidation:
    """Tests for AgentDecision schema validation."""

    def test_type_action_requires_input_text(self):
        """Test that type action requires inputText."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="type",
                target="Email field",
                # Missing inputText
                reasoningSummary="Enter email",
                confidence=0.8
            )

        assert "inputText is REQUIRED" in str(exc_info.value)

    def test_scroll_action_requires_direction(self):
        """Test that scroll action requires scrollDirection."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="scroll",
                # Missing scrollDirection
                reasoningSummary="Scroll down",
                confidence=0.8
            )

        assert "scrollDirection is REQUIRED" in str(exc_info.value)

    def test_wait_action_requires_duration(self):
        """Test that wait action requires waitDurationMs."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="wait",
                # Missing waitDurationMs
                reasoningSummary="Wait for load",
                confidence=0.8
            )

        assert "waitDurationMs is REQUIRED" in str(exc_info.value)

    def test_abort_action_requires_reason(self):
        """Test that abort action requires abortReason."""
        with pytest.raises(ValidationError) as exc_info:
            AgentDecision(
                action="abort",
                # Missing abortReason
                reasoningSummary="Cannot proceed",
                confidence=0.8
            )

        assert "abortReason is REQUIRED" in str(exc_info.value)

    def test_valid_type_decision(self):
        """Test valid type decision passes validation."""
        decision = AgentDecision(
            action="type",
            target="Email field",
            inputText="test@example.com",
            reasoningSummary="Enter email address",
            confidence=0.85
        )

        assert decision.action == "type"
        assert decision.inputText == "test@example.com"

    def test_valid_tap_decision(self):
        """Test valid tap decision passes validation."""
        decision = AgentDecision(
            action="tap",
            target="Sign Up button",
            reasoningSummary="Click sign up",
            confidence=0.9
        )

        assert decision.action == "tap"
        assert decision.target == "Sign Up button"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
