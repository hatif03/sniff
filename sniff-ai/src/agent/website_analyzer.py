"""Website analyzer for extracting context from initial page load.

This module helps the agent understand the website structure before making decisions.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WebsiteContext:
    """Extracted context from website analysis."""

    url: str
    page_title: str
    visible_text_sample: str  # First 1000 chars of visible text
    detected_buttons: List[str]
    detected_links: List[str]
    detected_form_fields: List[str]
    signup_indicators: List[str]  # Patterns suggesting signup flow
    oauth_providers: List[str]  # Detected OAuth providers
    page_structure: str  # High-level description

    def to_context_string(self) -> str:
        """Convert to formatted string for LLM context."""
        parts = [
            f"URL: {self.url}",
            f"Page Title: {self.page_title}",
            "",
            "Detected Interactive Elements:",
        ]

        if self.detected_buttons:
            parts.append(f"  Buttons: {', '.join(self.detected_buttons[:10])}")

        if self.detected_links:
            parts.append(f"  Links: {', '.join(self.detected_links[:10])}")

        if self.detected_form_fields:
            parts.append(f"  Form Fields: {', '.join(self.detected_form_fields[:10])}")

        if self.oauth_providers:
            parts.append(f"  OAuth Providers: {', '.join(self.oauth_providers)}")

        if self.signup_indicators:
            parts.append(f"\nSignup Flow Indicators: {', '.join(self.signup_indicators)}")

        parts.append(f"\nPage Structure: {self.page_structure}")

        parts.append(f"\nVisible Text Sample:")
        parts.append(f"{self.visible_text_sample[:500]}...")

        return "\n".join(parts)


class WebsiteAnalyzer:
    """Analyzes website structure to provide context for agent decisions."""

    def __init__(self):
        """Initialize website analyzer."""
        self.signup_keywords = [
            "sign up", "signup", "register", "create account",
            "get started", "join", "new account", "create demo"
        ]

        self.oauth_providers = [
            "google", "facebook", "apple", "github", "microsoft",
            "twitter", "linkedin"
        ]

    def analyze_from_observation(self, observation) -> WebsiteContext:
        """Analyze website from an observation.

        Args:
            observation: Observation object from PlaywrightWorker

        Returns:
            WebsiteContext with extracted information
        """
        url = observation.url
        visible_text = "\n".join(observation.visibleText) if observation.visibleText else ""

        # Extract page title from visible text (usually first line or in caps)
        page_title = self._extract_page_title(visible_text, url)

        # Detect buttons and links (from visible text patterns)
        detected_buttons = self._detect_buttons(visible_text)
        detected_links = self._detect_links(visible_text)

        # Detect form fields (look for field-like patterns)
        detected_form_fields = self._detect_form_fields(visible_text)

        # Detect signup indicators
        signup_indicators = self._detect_signup_indicators(visible_text)

        # Detect OAuth providers
        oauth_providers = self._detect_oauth_providers(visible_text)

        # Generate page structure description
        page_structure = self._analyze_page_structure(
            visible_text, detected_buttons, detected_links, detected_form_fields
        )

        return WebsiteContext(
            url=url,
            page_title=page_title,
            visible_text_sample=visible_text[:1000],
            detected_buttons=detected_buttons,
            detected_links=detected_links,
            detected_form_fields=detected_form_fields,
            signup_indicators=signup_indicators,
            oauth_providers=oauth_providers,
            page_structure=page_structure,
        )

    def _extract_page_title(self, visible_text: str, url: str) -> str:
        """Extract page title from visible text."""
        lines = visible_text.split('\n')

        # Look for title-like patterns in first few lines
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100:  # Titles are usually short
                # Skip navigation items
                if line.lower() not in ['home', 'about', 'contact', 'menu']:
                    return line

        # Fallback to domain name
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '').split('.')[0].title()
        except:
            return url

    def _detect_buttons(self, visible_text: str) -> List[str]:
        """Detect button-like text."""
        buttons = []
        lines = visible_text.split('\n')

        button_patterns = [
            'sign up', 'log in', 'login', 'register', 'submit', 'continue',
            'next', 'get started', 'create', 'join', 'start', 'go', 'send',
            'confirm', 'verify', 'accept', 'agree', 'buy', 'subscribe'
        ]

        for line in lines:
            line_lower = line.strip().lower()
            # Buttons are usually short
            if len(line) < 50 and line.strip():
                for pattern in button_patterns:
                    if pattern in line_lower:
                        buttons.append(line.strip())
                        break

        return list(set(buttons))[:20]  # Unique, limited to 20

    def _detect_links(self, visible_text: str) -> List[str]:
        """Detect link-like text."""
        links = []
        lines = visible_text.split('\n')

        link_patterns = [
            'learn more', 'read more', 'click here', 'view', 'see',
            'about', 'help', 'support', 'faq', 'terms', 'privacy'
        ]

        for line in lines:
            line_lower = line.strip().lower()
            if len(line) < 80 and line.strip():
                for pattern in link_patterns:
                    if pattern in line_lower:
                        links.append(line.strip())
                        break

        return list(set(links))[:15]

    def _detect_form_fields(self, visible_text: str) -> List[str]:
        """Detect form field labels."""
        fields = []
        lines = visible_text.split('\n')

        field_patterns = [
            'email', 'password', 'name', 'first name', 'last name',
            'username', 'phone', 'address', 'city', 'country',
            'zip', 'postal', 'date', 'birth'
        ]

        for line in lines:
            line_lower = line.strip().lower()
            if len(line) < 50 and line.strip():
                for pattern in field_patterns:
                    if pattern in line_lower:
                        fields.append(line.strip())
                        break

        return list(set(fields))[:15]

    def _detect_signup_indicators(self, visible_text: str) -> List[str]:
        """Detect indicators of signup flow."""
        indicators = []
        text_lower = visible_text.lower()

        for keyword in self.signup_keywords:
            if keyword in text_lower:
                indicators.append(keyword)

        return indicators

    def _detect_oauth_providers(self, visible_text: str) -> List[str]:
        """Detect OAuth provider options."""
        providers = []
        text_lower = visible_text.lower()

        for provider in self.oauth_providers:
            if provider in text_lower:
                providers.append(provider.title())

        return providers

    def _analyze_page_structure(
        self,
        visible_text: str,
        buttons: List[str],
        links: List[str],
        form_fields: List[str]
    ) -> str:
        """Generate high-level page structure description."""
        parts = []

        # Estimate page type
        text_lower = visible_text.lower()

        if any(kw in text_lower for kw in self.signup_keywords):
            if form_fields:
                parts.append("Signup page with form")
            else:
                parts.append("Signup landing page")
        elif 'login' in text_lower or 'sign in' in text_lower:
            parts.append("Login page")
        elif 'dashboard' in text_lower or 'account' in text_lower:
            parts.append("User dashboard or account page")
        else:
            parts.append("Informational page")

        # Add component counts
        if buttons:
            parts.append(f"with {len(buttons)} interactive buttons")
        if form_fields:
            parts.append(f"and {len(form_fields)} form fields")

        return ", ".join(parts)


def create_website_analyzer() -> WebsiteAnalyzer:
    """Create website analyzer instance.

    Returns:
        WebsiteAnalyzer instance
    """
    return WebsiteAnalyzer()
