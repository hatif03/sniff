"""Configuration management for Sherlock.

Handles:
- .env loading and validation
- Config persistence (sherlock.json)
- Default values and overrides
- Pydantic models for type safety
"""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


class PlaywrightConfig(BaseModel):
    """Playwright browser automation configuration."""
    headless: bool = Field(default=True, description="Run browser in headless mode")
    screenshot_on_action: bool = Field(default=True, description="Capture screenshot on every action")
    slow_mo: int = Field(default=0, ge=0, description="Slow motion delay in ms")
    timeout: int = Field(default=30000, ge=1000, description="Default action timeout in ms")
    navigation_timeout: int = Field(default=60000, ge=1000, description="Navigation timeout in ms")


class BedrockConfig(BaseModel):
    """AWS Bedrock configuration for agent decisions."""
    model_id: str = Field(default="anthropic.claude-sonnet-4-5-20250929-v1:0", description="Primary Bedrock model ID")
    fallback_model_id: Optional[str] = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", description="Fallback model")
    region: str = Field(default="us-west-2", description="AWS region for Bedrock")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=60, ge=1, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
    anthropic_version: str = Field(default="bedrock-2023-05-31", description="Anthropic API version")


class SlackConfig(BaseModel):
    """Slack alerting configuration."""
    webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    channel: Optional[str] = Field(default=None, description="Override channel")
    bot_name: Optional[str] = Field(default="Sherlock Alert Bot", description="Bot display name")


class GuardrailsConfig(BaseModel):
    """Orchestrator guardrails and limits."""
    max_steps: int = Field(default=50, ge=1, description="Maximum steps per run")
    max_intent_retries: int = Field(default=3, ge=0, description="Max retries per intent")
    max_dwell_time: int = Field(default=30, ge=1, description="Max seconds per screen")
    hard_timeout: int = Field(default=600, ge=1, description="Hard timeout per run in seconds")
    max_run_duration: int = Field(default=300, ge=1, description="Maximum run duration in seconds")


class SecurityConfig(BaseModel):
    """Security and compliance settings."""
    allowed_domains: list[str] = Field(default_factory=list, description="Domain allowlist")
    redact_pii: bool = Field(default=True, description="Redact PII in logs")
    enforce_domain_allowlist: bool = Field(default=True, description="Enforce domain restrictions")

    @field_validator('allowed_domains', mode='before')
    @classmethod
    def parse_domains(cls, v):
        """Parse comma-separated domains from string."""
        if isinstance(v, str):
            return [d.strip() for d in v.split(',') if d.strip()]
        return v


class DefaultsConfig(BaseModel):
    """Default values for run parameters."""
    persona: Optional[str] = Field(default=None, description="Default persona")
    device: str = Field(default="iPhone 13", description="Default device profile")
    network: str = Field(default="4g", description="Default network profile (4g|3g|slow3g)")


class SupabaseConfig(BaseModel):
    """Supabase integration configuration."""
    enabled: bool = Field(default=False, description="Enable Supabase integration")
    url: Optional[str] = Field(default=None, description="Supabase project URL")
    key: Optional[str] = Field(default=None, description="Supabase anon/service key")
    auto_upload: bool = Field(default=True, description="Auto-upload runs after completion")
    screenshots_bucket: str = Field(default="sherlock-screenshots", description="Screenshots bucket name")
    videos_bucket: str = Field(default="sherlock-videos", description="Videos bucket name")
    traces_bucket: str = Field(default="sherlock-traces", description="Traces bucket name")


class SherlockConfig(BaseModel):
    """Main Sherlock configuration model."""

    # Application settings
    env: str = Field(default="development", description="Environment: development|staging|production")
    log_level: str = Field(default="INFO", description="Logging level")
    db_path: str = Field(default="./data/sherlock.db", description="SQLite database path")
    artifacts_path: str = Field(default="./artifacts", description="Artifacts storage path")
    personas_path: str = Field(default="./src/personas", description="Persona storage path")
    primary_url: Optional[str] = Field(default=None, description="Default staging URL for test runs")

    # Component configurations
    playwright: PlaywrightConfig = Field(default_factory=PlaywrightConfig)
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)

    # Feature flags
    demo_mode: bool = Field(default=False, description="Enable deterministic demo mode")
    test_mode: bool = Field(default=False, description="Skip browser launch for tests")

    @classmethod
    def from_env(cls) -> 'SherlockConfig':
        """Load configuration from environment variables.

        Loads .env file if present, then constructs config from environment.
        """
        # Load .env file
        load_dotenv()

        return cls(
            env=os.getenv('SHERLOCK_ENV', 'development'),
            log_level=os.getenv('SHERLOCK_LOG_LEVEL', 'INFO'),
            db_path=os.getenv('SHERLOCK_DB_PATH', './data/sherlock.db'),
            artifacts_path=os.getenv('SHERLOCK_ARTIFACTS_PATH', './artifacts'),
            personas_path=os.getenv('SHERLOCK_PERSONAS_PATH', './src/personas'),
            primary_url=os.getenv('SHERLOCK_PRIMARY_URL'),

            playwright=PlaywrightConfig(
                headless=os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
                screenshot_on_action=os.getenv('PLAYWRIGHT_SCREENSHOT_ON_ACTION', 'true').lower() == 'true',
                slow_mo=int(os.getenv('PLAYWRIGHT_SLOW_MO', '0')),
                timeout=int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000')),
                navigation_timeout=int(os.getenv('PLAYWRIGHT_NAVIGATION_TIMEOUT', '60000')),
            ),

            bedrock=BedrockConfig(
                model_id=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-5-20250929-v1:0'),
                fallback_model_id=os.getenv('BEDROCK_MODEL_FALLBACK'),
                region=os.getenv('BEDROCK_REGION', os.getenv('AWS_REGION', 'us-west-2')),
                max_tokens=int(os.getenv('BEDROCK_MAX_TOKENS', '4096')),
                temperature=float(os.getenv('BEDROCK_TEMPERATURE', '0.7')),
                timeout_seconds=int(os.getenv('BEDROCK_TIMEOUT_SECONDS', '60')),
                max_retries=int(os.getenv('BEDROCK_MAX_RETRIES', '3')),
                anthropic_version=os.getenv('BEDROCK_ANTHROPIC_VERSION', 'bedrock-2023-05-31'),
            ),

            slack=SlackConfig(
                webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
                channel=os.getenv('SLACK_CHANNEL'),
                bot_name=os.getenv('SLACK_BOT_NAME', 'Sherlock Alert Bot'),
            ),

            guardrails=GuardrailsConfig(
                max_steps=int(os.getenv('SHERLOCK_MAX_STEPS', '50')),
                max_intent_retries=int(os.getenv('SHERLOCK_MAX_INTENT_RETRIES', '3')),
                max_dwell_time=int(os.getenv('SHERLOCK_MAX_DWELL_TIME', '30')),
                hard_timeout=int(os.getenv('SHERLOCK_HARD_TIMEOUT', '600')),
                max_run_duration=int(os.getenv('SHERLOCK_MAX_RUN_DURATION', '300')),
            ),

            security=SecurityConfig(
                allowed_domains=os.getenv('SHERLOCK_ALLOWED_DOMAINS', ''),
                redact_pii=os.getenv('SHERLOCK_REDACT_PII', 'true').lower() == 'true',
                enforce_domain_allowlist=os.getenv('SHERLOCK_ENFORCE_DOMAIN_ALLOWLIST', 'true').lower() == 'true',
            ),

            defaults=DefaultsConfig(
                persona=os.getenv('SHERLOCK_DEFAULT_PERSONA'),
                device=os.getenv('SHERLOCK_DEFAULT_DEVICE', 'iPhone 13'),
                network=os.getenv('SHERLOCK_DEFAULT_NETWORK', '4g'),
            ),

            supabase=SupabaseConfig(
                enabled=os.getenv('SUPABASE_ENABLED', 'false').lower() == 'true',
                url=os.getenv('SUPABASE_URL'),
                key=os.getenv('SUPABASE_KEY'),
                auto_upload=os.getenv('SUPABASE_AUTO_UPLOAD', 'true').lower() == 'true',
                screenshots_bucket=os.getenv('SUPABASE_SCREENSHOTS_BUCKET', 'sherlock-screenshots'),
                videos_bucket=os.getenv('SUPABASE_VIDEOS_BUCKET', 'sherlock-videos'),
                traces_bucket=os.getenv('SUPABASE_TRACES_BUCKET', 'sherlock-traces'),
            ),

            demo_mode=os.getenv('SHERLOCK_DEMO_MODE', 'false').lower() == 'true',
            test_mode=os.getenv('SHERLOCK_TEST_MODE', 'false').lower() == 'true',
        )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'SherlockConfig':
        """Load configuration from JSON file or create default.

        Args:
            config_path: Path to sherlock.json config file. Defaults to ./data/sherlock.json

        Returns:
            SherlockConfig instance
        """
        # ALWAYS load .env file first (contains AWS credentials, etc.)
        # This is needed even when loading from JSON because validation
        # checks environment variables like AWS_ACCESS_KEY_ID
        load_dotenv()

        if config_path is None:
            config_path = Path('./data/sherlock.json')

        if config_path.exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                return cls(**data)

        # Return default config from environment
        return cls.from_env()

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to JSON file.

        Args:
            config_path: Path to save config. Defaults to ./data/sherlock.json
        """
        if config_path is None:
            config_path = Path('./data/sherlock.json')

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)

    def validate_required(self) -> list[str]:
        """Validate that required configuration is present.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check AWS configuration - test if credentials actually work
        # instead of just checking environment variables
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            from botocore.config import Config

            try:
                # Use short timeout to avoid hanging on network issues
                sts_config = Config(
                    connect_timeout=3,
                    read_timeout=5,
                    retries={'max_attempts': 1}
                )
                sts = boto3.client('sts', config=sts_config)
                sts.get_caller_identity()
                # Credentials are valid
            except NoCredentialsError:
                errors.append("AWS credentials not configured. Set AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")
            except Exception as e:
                # Handle timeouts and other errors gracefully
                if 'timeout' in str(e).lower() or 'timed out' in str(e).lower() or '408' in str(e):
                    # Timeout is not a credential issue - just log warning
                    import logging
                    logging.getLogger(__name__).warning(f"AWS credential validation timed out: {e}. Assuming credentials are valid.")
                    # Don't add error - allow run to continue
                elif isinstance(e, ClientError):
                    error_code = e.response.get('Error', {}).get('Code', '')
                    if error_code == 'ExpiredToken':
                        errors.append("AWS credentials expired. Run 'aws sso login' or refresh your credentials")
                    else:
                        errors.append(f"AWS credentials error: {error_code}")
                else:
                    # Other errors - log but don't block
                    import logging
                    logging.getLogger(__name__).warning(f"AWS credential validation failed: {e}. Continuing anyway.")

        except ImportError:
            # boto3 not available, fall back to environment variable check
            if not os.getenv('AWS_PROFILE') and not os.getenv('AWS_ACCESS_KEY_ID'):
                errors.append("AWS credentials not configured. Set AWS_PROFILE or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")

        # Check domain allowlist if enforcement enabled
        if self.security.enforce_domain_allowlist and not self.security.allowed_domains:
            errors.append("Domain allowlist enforcement enabled but no domains configured. Set SHERLOCK_ALLOWED_DOMAINS")

        return errors


def get_config(config_path: Optional[Path] = None) -> SherlockConfig:
    """Get Sherlock configuration singleton.

    Args:
        config_path: Optional path to config file

    Returns:
        SherlockConfig instance
    """
    return SherlockConfig.load(config_path)
