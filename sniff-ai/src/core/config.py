"""Configuration management for Sniff.

Handles:
- .env loading and validation
- Config persistence (sniff.json)
- Default values and overrides
- Pydantic models for type safety
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class PlaywrightConfig(BaseModel):
    """Playwright browser automation configuration."""
    headless: bool = Field(default=True, description="Run browser in headless mode")
    screenshot_on_action: bool = Field(default=True, description="Capture screenshot on every action")
    slow_mo: int = Field(default=0, ge=0, description="Slow motion delay in ms")
    timeout: int = Field(default=30000, ge=1000, description="Default action timeout in ms")
    navigation_timeout: int = Field(default=60000, ge=1000, description="Navigation timeout in ms")


class GeminiConfig(BaseModel):
    """Vertex AI Gemini configuration - the Tier 3 vision-capable reasoning model.

    Auth is via Application Default Credentials (`gcloud auth application-default
    login`), not an API key. Region/model are overridable because Gemini 3.x
    tiers aren't uniformly available in every regional Vertex location yet.
    """
    project_id: str | None = Field(default=None, description="GCP project ID (Vertex AI)")
    region: str = Field(default="us-central1", description="Vertex AI region")
    model_id: str = Field(default="gemini-3.5-flash-lite", description="Primary Gemini model ID")
    fallback_model_id: str = Field(default="gemini-2.5-flash-lite", description="Fallback model if primary unavailable in region")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens in response")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=60, ge=1, description="Request timeout")


class K2HorizonConfig(BaseModel):
    """ifm.ai k2-horizon configuration - the Tier 3 text-only reasoning model.

    OpenAI-compatible API, used for GoalEnhancer/Planner/PersonaReviewer
    (none of which need vision).
    """
    api_key: str | None = Field(default=None, description="ifm.ai API key")
    base_url: str = Field(default="https://api.ifm.ai/v1", description="ifm.ai API base URL")
    model_id: str = Field(default="IFM/K2-Horizon-375B-A23B", description="k2-horizon model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    timeout_seconds: int = Field(default=60, ge=1, description="Request timeout")


class SlackConfig(BaseModel):
    """Slack alerting configuration."""
    webhook_url: str | None = Field(default=None, description="Slack webhook URL")
    channel: str | None = Field(default=None, description="Override channel")
    bot_name: str | None = Field(default="Sniff Alert Bot", description="Bot display name")


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
    persona: str | None = Field(default=None, description="Default persona")
    device: str = Field(default="iPhone 13", description="Default device profile")
    network: str = Field(default="4g", description="Default network profile (4g|3g|slow3g)")


class SupabaseConfig(BaseModel):
    """Supabase integration configuration."""
    enabled: bool = Field(default=False, description="Enable Supabase integration")
    url: str | None = Field(default=None, description="Supabase project URL")
    key: str | None = Field(default=None, description="Supabase anon/service key")
    auto_upload: bool = Field(default=True, description="Auto-upload runs after completion")
    screenshots_bucket: str = Field(default="sniff-screenshots", description="Screenshots bucket name")
    videos_bucket: str = Field(default="sniff-videos", description="Videos bucket name")
    traces_bucket: str = Field(default="sniff-traces", description="Traces bucket name")


class TypesafeConfig(BaseModel):
    """Typesafe AI (Jev) configuration — the Tier 2 'System One' decision model.

    Disabled by default: every caller of JevClient/TierRouter degrades to
    today's deterministic/Bedrock-only behavior when this is False or no
    api_key is set. Typesafe's public docs don't publish exact endpoint
    paths/schemas as of this writing, so base_url/model_id are overridable
    once verified against the real API reference (console.typesafe.ai).
    """
    enabled: bool = Field(default=False, description="Enable Jev (Tier 2) decision calls")
    api_key: str | None = Field(default=None, description="Typesafe AI API key")
    base_url: str = Field(default="https://api.typesafe.ai/v1", description="Typesafe AI API base URL")
    model_id: str = Field(default="jev-latest", description="Jev model identifier")
    timeout_seconds: int = Field(default=5, ge=1, description="Request timeout (Jev is designed to respond in <1s)")


class ApiConfig(BaseModel):
    """FastAPI backend configuration (Phase 1: shared-secret gate).

    `token` gates POST/GET on /runs and /experiments via a static
    `Authorization: Bearer <token>` check - a deliberately minimal stand-in
    for real per-user auth, which is Phase 2 (see
    docs/product/SAAS_ROADMAP.md section 1).
    """
    token: str | None = Field(default=None, description="Shared bearer token required for API access (Phase 1 auth)")
    cors_origin: str = Field(default="http://localhost:3000", description="Allowed CORS origin for the web frontend (Next.js dev server by default)")


class SniffConfig(BaseModel):
    """Main Sniff configuration model."""

    # Application settings
    env: str = Field(default="development", description="Environment: development|staging|production")
    log_level: str = Field(default="INFO", description="Logging level")
    db_path: str = Field(default="./data/sniff.db", description="SQLite database path")
    artifacts_path: str = Field(default="./artifacts", description="Artifacts storage path")
    personas_path: str = Field(default="./src/personas", description="Persona storage path")
    primary_url: str | None = Field(default=None, description="Default staging URL for test runs")

    # Component configurations
    playwright: PlaywrightConfig = Field(default_factory=PlaywrightConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    k2horizon: K2HorizonConfig = Field(default_factory=K2HorizonConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    supabase: SupabaseConfig = Field(default_factory=SupabaseConfig)
    typesafe: TypesafeConfig = Field(default_factory=TypesafeConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)

    # Feature flags
    demo_mode: bool = Field(default=False, description="Enable deterministic demo mode")
    test_mode: bool = Field(default=False, description="Skip browser launch for tests")

    @classmethod
    def from_env(cls) -> 'SniffConfig':
        """Load configuration from environment variables.

        Loads .env file if present, then constructs config from environment.
        """
        # Load .env file
        load_dotenv()

        return cls(
            env=os.getenv('SNIFF_ENV', 'development'),
            log_level=os.getenv('SNIFF_LOG_LEVEL', 'INFO'),
            db_path=os.getenv('SNIFF_DB_PATH', './data/sniff.db'),
            artifacts_path=os.getenv('SNIFF_ARTIFACTS_PATH', './artifacts'),
            personas_path=os.getenv('SNIFF_PERSONAS_PATH', './src/personas'),
            primary_url=os.getenv('SNIFF_PRIMARY_URL'),

            playwright=PlaywrightConfig(
                headless=os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
                screenshot_on_action=os.getenv('PLAYWRIGHT_SCREENSHOT_ON_ACTION', 'true').lower() == 'true',
                slow_mo=int(os.getenv('PLAYWRIGHT_SLOW_MO', '0')),
                timeout=int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000')),
                navigation_timeout=int(os.getenv('PLAYWRIGHT_NAVIGATION_TIMEOUT', '60000')),
            ),

            gemini=GeminiConfig(
                project_id=os.getenv('GEMINI_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT'),
                region=os.getenv('GEMINI_REGION', 'us-central1'),
                model_id=os.getenv('GEMINI_MODEL_ID', 'gemini-3.5-flash-lite'),
                fallback_model_id=os.getenv('GEMINI_FALLBACK_MODEL_ID', 'gemini-2.5-flash-lite'),
                max_tokens=int(os.getenv('GEMINI_MAX_TOKENS', '4096')),
                temperature=float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
                timeout_seconds=int(os.getenv('GEMINI_TIMEOUT_SECONDS', '60')),
            ),

            k2horizon=K2HorizonConfig(
                api_key=os.getenv('IFM_API_KEY'),
                base_url=os.getenv('IFM_BASE_URL', 'https://api.ifm.ai/v1'),
                model_id=os.getenv('IFM_MODEL_ID', 'IFM/K2-Horizon-375B-A23B'),
                temperature=float(os.getenv('IFM_TEMPERATURE', '0.7')),
                timeout_seconds=int(os.getenv('IFM_TIMEOUT_SECONDS', '60')),
            ),

            slack=SlackConfig(
                webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
                channel=os.getenv('SLACK_CHANNEL'),
                bot_name=os.getenv('SLACK_BOT_NAME', 'Sniff Alert Bot'),
            ),

            guardrails=GuardrailsConfig(
                max_steps=int(os.getenv('SNIFF_MAX_STEPS', '50')),
                max_intent_retries=int(os.getenv('SNIFF_MAX_INTENT_RETRIES', '3')),
                max_dwell_time=int(os.getenv('SNIFF_MAX_DWELL_TIME', '30')),
                hard_timeout=int(os.getenv('SNIFF_HARD_TIMEOUT', '600')),
                max_run_duration=int(os.getenv('SNIFF_MAX_RUN_DURATION', '300')),
            ),

            security=SecurityConfig(
                allowed_domains=os.getenv('SNIFF_ALLOWED_DOMAINS', ''),
                redact_pii=os.getenv('SNIFF_REDACT_PII', 'true').lower() == 'true',
                enforce_domain_allowlist=os.getenv('SNIFF_ENFORCE_DOMAIN_ALLOWLIST', 'true').lower() == 'true',
            ),

            defaults=DefaultsConfig(
                persona=os.getenv('SNIFF_DEFAULT_PERSONA'),
                device=os.getenv('SNIFF_DEFAULT_DEVICE', 'iPhone 13'),
                network=os.getenv('SNIFF_DEFAULT_NETWORK', '4g'),
            ),

            supabase=SupabaseConfig(
                enabled=os.getenv('SUPABASE_ENABLED', 'false').lower() == 'true',
                url=os.getenv('SUPABASE_URL'),
                key=os.getenv('SUPABASE_KEY'),
                auto_upload=os.getenv('SUPABASE_AUTO_UPLOAD', 'true').lower() == 'true',
                screenshots_bucket=os.getenv('SUPABASE_SCREENSHOTS_BUCKET', 'sniff-screenshots'),
                videos_bucket=os.getenv('SUPABASE_VIDEOS_BUCKET', 'sniff-videos'),
                traces_bucket=os.getenv('SUPABASE_TRACES_BUCKET', 'sniff-traces'),
            ),

            typesafe=TypesafeConfig(
                enabled=os.getenv('TYPESAFE_ENABLED', 'false').lower() == 'true',
                api_key=os.getenv('TYPESAFE_API_KEY'),
                base_url=os.getenv('TYPESAFE_BASE_URL', 'https://api.typesafe.ai/v1'),
                model_id=os.getenv('TYPESAFE_MODEL_ID', 'jev-latest'),
                timeout_seconds=int(os.getenv('TYPESAFE_TIMEOUT_SECONDS', '5')),
            ),

            api=ApiConfig(
                token=os.getenv('SNIFF_API_TOKEN'),
                cors_origin=os.getenv('SNIFF_API_CORS_ORIGIN', 'http://localhost:3000'),
            ),

            demo_mode=os.getenv('SNIFF_DEMO_MODE', 'false').lower() == 'true',
            test_mode=os.getenv('SNIFF_TEST_MODE', 'false').lower() == 'true',
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> 'SniffConfig':
        """Load configuration from JSON file or create default.

        Args:
            config_path: Path to sniff.json config file. Defaults to ./data/sniff.json

        Returns:
            SniffConfig instance
        """
        # ALWAYS load .env file first (contains AWS credentials, etc.)
        # This is needed even when loading from JSON because validation
        # checks environment variables like AWS_ACCESS_KEY_ID
        load_dotenv()

        if config_path is None:
            config_path = Path('./data/sniff.json')

        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return cls(**data)

        # Return default config from environment
        return cls.from_env()

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to JSON file.

        Args:
            config_path: Path to save config. Defaults to ./data/sniff.json
        """
        if config_path is None:
            config_path = Path('./data/sniff.json')

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

        # Check Gemini (Vertex AI) auth - Application Default Credentials,
        # not an API key. Also require a project ID since ADC alone doesn't
        # imply which GCP project to bill/run against.
        if not self.gemini.project_id:
            errors.append("Gemini project not configured. Set GEMINI_PROJECT_ID (or GOOGLE_CLOUD_PROJECT)")
        else:
            try:
                import google.auth
                google.auth.default()
            except Exception as e:
                errors.append(
                    f"Google Cloud Application Default Credentials not available: {e}. "
                    "Run `gcloud auth application-default login`"
                )

        # Check k2-horizon (ifm.ai) API key presence
        if not self.k2horizon.api_key:
            errors.append("k2-horizon API key not configured. Set IFM_API_KEY")

        # Check domain allowlist if enforcement enabled
        if self.security.enforce_domain_allowlist and not self.security.allowed_domains:
            errors.append("Domain allowlist enforcement enabled but no domains configured. Set SNIFF_ALLOWED_DOMAINS")

        return errors


def get_config(config_path: Path | None = None) -> SniffConfig:
    """Get sniff configuration singleton.

    Args:
        config_path: Optional path to config file

    Returns:
        SniffConfig instance
    """
    return SniffConfig.load(config_path)
