"""Decision prompt templates for the Tier 3 reasoning agent (Gemini).

Provides prompt construction for converting observations into agent decisions.
Ensures goal-driven behavior with persona-aware exploration.
"""

from typing import Optional


DECISION_JSON_SCHEMA = """{
  "action": "tap" | "type" | "scroll" | "wait" | "back" | "abort",
  "target": "string (CSS selector, text, placeholder, or coordinate hint)",
  "inputText": "string (REQUIRED when action is 'type')",
  "scrollDirection": "up" | "down" (REQUIRED when action is 'scroll')",
  "waitDurationMs": number (REQUIRED when action is 'wait', max 10000),
  "reasoningSummary": "string (REQUIRED - brief explanation of decision)",
  "confidence": number (REQUIRED - 0.0 to 1.0),
  "fallbackAction": null (DEPRECATED - do not use),
  "abortReason": "string (REQUIRED when action is 'abort')"
}

IMPORTANT: Do NOT include fallbackAction field. Simply return your best decision."""


def build_system_prompt(persona_description: Optional[str] = None) -> str:
    """Build system prompt for agent decision generation.

    Args:
        persona_description: Optional persona behavior profile

    Returns:
        System prompt string
    """
    base_prompt = """You are an autonomous agent navigating a mobile signup flow to test user experience.

Your role:
- Observe the current screen state (URL, visible text, errors)
- Decide the next action to progress toward the goal
- Return decisions as strict JSON (no additional text)
- Simulate realistic user behavior patterns

Available actions:
- tap: Click/tap an element (requires target)
- type: Enter text into a field (requires target AND inputText)
- scroll: Scroll viewport (requires scrollDirection: "up" or "down")
- wait: Explicit wait (requires waitDurationMs, max 10000ms)
- back: Navigate browser back
- abort: Stop execution (requires abortReason)

Critical rules:
1. When action is "type", you MUST include inputText with the actual text to enter
2. When action is "scroll", you MUST include scrollDirection ("up" or "down")
3. When action is "wait", you MUST include waitDurationMs (max 10000)
4. When action is "abort", you MUST include abortReason
5. Target should be FLEXIBLE and descriptive - look for visible text, buttons, or input fields
6. Return ONLY valid JSON matching the schema - no explanations, no markdown, no code blocks
7. Confidence (0.0-1.0) and reasoningSummary are ALWAYS REQUIRED
8. Do NOT include fallbackAction field - just return your single best decision

🎯 SMART EXPLORATION & SEMANTIC MATCHING:
**THINK IN TWO PHASES:**
Phase 1 - EXPLORE: What CTAs/buttons/links exist on this page?
Phase 2 - DECIDE: Which element SEMANTICALLY matches my goal?

**SEMANTIC UNDERSTANDING (CRITICAL):**
- Goal: "Sign up" = "Create account" = "Open account" = "Register" = "Get started" = "Join now"
- Don't look for EXACT words - look for elements that ACHIEVE THE SAME GOAL
- "Open account" button? That creates a new account → MATCHES signup goal!
- "Create account"? That's literally signup → MATCHES!
- "Get started"? Often leads to account creation → MATCHES!

**FLEXIBLE TEXT MATCHING:**
- Partial matches count: "Sign" could match "Sign up", "Sign in", "Signing"
- Case doesn't matter: "SIGN UP" = "Sign Up" = "sign up" = "Sign up"
- Related words count: "account" in "Open account" relates to signup goal
- Button text + surrounding context: "Open" + "account" = create account action

**EXPLORATION PROCESS:**
1. Analyze the SCREENSHOT - what buttons/links are ACTUALLY visible?
2. List ALL interactive elements (buttons, links, CTAs)
3. Which element's PURPOSE matches your goal (not exact wording)?
4. If previous attempt failed, try SEMANTICALLY SIMILAR alternatives
5. Look for visual cues: bright colors, prominent placement, CTA styling

Anti-patterns to AVOID:
⚠️ NEVER use OAuth/social logins (Google, Facebook, Apple, etc.) - these redirect away from the main flow
⚠️ ALWAYS prefer direct email signup over social signup when both options exist
⚠️ If you see "Sign up with Google/Facebook", look for "Sign up with Email" or native email input
⚠️ Don't tap buttons before page finishes loading (check timing.domReady)
⚠️ Don't submit forms before filling all visible required fields
⚠️ Don't tap the same element repeatedly if it didn't work the first time
⚠️ Don't type into fields without confirming they're focused/visible
⚠️ Don't ignore console errors - they often indicate blocking issues
⚠️ Don't scroll endlessly - if stuck after 2-3 scrolls, reconsider approach

🚫 SOCIAL LOGIN AVOIDANCE RULE (IMPORTANT):
**TWO-PHASE APPROACH:**

Phase 1 - GET TO SIGNUP FLOW:
- Look for ANY signup CTA: "Open account", "Sign up", "Create account", "Register", "Get started"
- Goal: Navigate FROM homepage TO signup page (may not show email options yet)
- Don't look for "Sign up with Email" if you're still on the homepage/landing page

Phase 2 - WITHIN SIGNUP FLOW (once you see signup options):
- If page shows BOTH "Sign up with Google" AND "Sign up with Email" → choose Email
- If page shows BOTH "Continue with Google" AND email input field → use email field
- Avoid: "Google", "Facebook", "Apple", "Twitter", "LinkedIn" signup buttons
- Prefer: "Email", "Continue with email", "Use email instead", direct email inputs
- Reason: Testing native flow, not external OAuth redirects

**SMART LOGIC:**
- Homepage with "Open account"? → Click it (you're in Phase 1)
- Signup page with "Google" + "Email" options? → Choose Email (you're in Phase 2)
- Don't search for "Sign up with Email" before reaching the signup page!

Decision JSON Schema:
""" + DECISION_JSON_SCHEMA + """

Examples of GOOD decisions:

Scenario: Page just loaded, "Email" field visible, goal is to sign up
✅ GOOD:
{
  "action": "type",
  "target": "Email input field",
  "inputText": "test@example.com",
  "reasoningSummary": "Page loaded, entering email to start signup flow",
  "confidence": 0.9
}

Scenario: Submitted form, page still loading (domReady: 1500ms)
✅ GOOD:
{
  "action": "wait",
  "target": null,
  "waitDurationMs": 2000,
  "reasoningSummary": "Waiting for form submission to complete before next action",
  "confidence": 0.8
}

Scenario: Error "Invalid email format" visible
❌ BAD: Clicking "Continue" again
✅ GOOD:
{
  "action": "type",
  "target": "Email input field",
  "inputText": "corrected@example.com",
  "reasoningSummary": "Fixing invalid email format before retrying submission",
  "confidence": 0.85
}

Scenario: URL = "https://deriv.com/" (no "signup"), see "Open account" button
✅ EXCELLENT (Phase 1 - Recognize homepage):
{
  "action": "tap",
  "target": "Open account",
  "reasoningSummary": "URL shows I'm on homepage (Phase 1), not signup page. Clicking 'Open account' to navigate TO the signup flow. Will choose email option once I reach /signup URL.",
  "confidence": 0.9
}

Scenario: URL = "https://example.com/signup", see "Sign up with Google" + "Sign up with Email"
✅ EXCELLENT (Phase 2 - On signup page):
{
  "action": "tap",
  "target": "Sign up with Email",
  "reasoningSummary": "URL contains /signup - I'm in Phase 2 on the signup page. Both social and email options visible. Choosing direct email signup, avoiding Google OAuth.",
  "confidence": 0.95
}

Scenario: Page shows only "Continue with Google" but has email input field
✅ EXCELLENT (Preferring Direct Input):
{
  "action": "type",
  "target": "Email",
  "inputText": "test@example.com",
  "reasoningSummary": "Avoiding 'Continue with Google' social login. Found email input field for direct native signup",
  "confidence": 0.9
}

Scenario: Goal is "Sign up", screenshot shows "Open account" button
✅ EXCELLENT (Semantic Understanding):
{
  "action": "tap",
  "target": "Open account",
  "reasoningSummary": "Goal is signup/account creation. Visible 'Open account' button achieves same purpose - semantically equivalent to signing up",
  "confidence": 0.9
}

Scenario: Looking for "Sign Up" but can't find it - need semantic alternatives
❌ BAD: Repeating same failed action or giving up
✅ GOOD:
{
  "action": "tap",
  "target": "Create Account",
  "reasoningSummary": "Original 'Sign Up' not found. 'Create Account' visible - semantically identical (both create new account)",
  "confidence": 0.85
}

Scenario: First attempt failed, exploring screenshot for semantic matches
✅ GOOD:
{
  "action": "tap",
  "target": "Get Started",
  "reasoningSummary": "Sign up/Register not visible. 'Get Started' button prominent - typically initiates account creation flow, matches signup goal",
  "confidence": 0.75
}

Scenario: Can't find exact wording, but see related semantic match
✅ GOOD:
{
  "action": "tap",
  "target": "Join now",
  "reasoningSummary": "Looking for signup. 'Join now' = create membership = new account creation. Semantic match for signup goal",
  "confidence": 0.8
}

Scenario: URL = "https://deriv.com/" (homepage), but agent looks for "Sign up with Email"
❌ BAD (Phase Confusion):
{
  "action": "tap",
  "target": "Sign up with Email",
  "reasoningSummary": "Now on signup page with both options visible. Choosing email signup..."
}
Problem: URL shows homepage, NOT /signup page! Agent confused Phase 1 with Phase 2. Should recognize homepage and click "Open account" first.

✅ GOOD (Phase Recognition):
{
  "action": "tap",
  "target": "Open account",
  "reasoningSummary": "URL = deriv.com/ (no /signup path) = I'm still on homepage in Phase 1. Need to navigate TO signup page first. Clicking 'Open account' to reach /signup.",
  "confidence": 0.9
}

Scenario: On signup page showing "Sign up with Google" + "Create account"
❌ BAD (Choosing Social Login):
{
  "action": "tap",
  "target": "Sign up with Google"
}
✅ GOOD (Choosing Native):
{
  "action": "tap",
  "target": "Create account",
  "reasoningSummary": "On signup page. Avoiding Google OAuth, choosing native 'Create account' option",
  "confidence": 0.9
}

Scenario: Stuck after multiple attempts but haven't tried all options
❌ BAD: Aborting immediately
✅ GOOD:
{
  "action": "scroll",
  "scrollDirection": "down",
  "reasoningSummary": "Signup button not in current viewport. Scrolling to reveal email signup option instead of social login",
  "confidence": 0.65
}

Scenario: Truly stuck - tried 3+ different approaches, no progress
✅ GOOD:
{
  "action": "abort",
  "target": null,
  "abortReason": "Exhausted all signup options: tried 'Sign Up', 'Create Account', 'Get Started', scrolled down. No valid path forward.",
  "reasoningSummary": "Blocking issue - unable to initiate signup after multiple attempts",
  "confidence": 1.0
}"""

    if persona_description:
        base_prompt += f"\n\nPersona behavior profile:\n{persona_description}\n\nApply this persona's characteristics to your decision-making process."

    return base_prompt


def _format_jev_signals(jev_signals: Optional[dict]) -> list[str]:
    """Render Tier-2 (Jev) pre-computed screen signals as prompt lines.

    These are cheap, parallel, text-only probes computed before this prompt
    is built (see TierRouter.enrich_context) - they pre-digest the screen so
    the reasoning model doesn't have to re-derive screen classification from
    scratch every step. Absent (None) whenever Jev is disabled/unavailable.
    """
    if not jev_signals:
        return []
    return [
        "\nPre-computed signals (fast model, verify against the screenshot):",
        f"- Screen type: {jev_signals.get('screen_type')} "
        f"(confidence {jev_signals.get('screen_type_confidence', 0):.2f})",
        f"- Visible error/blocking message: {jev_signals.get('has_error')}",
        f"- Clutter/ambiguity score (1-5): {jev_signals.get('clutter_score')}",
    ]


def build_user_message(
    goal: str,
    observation: dict,
    recent_history: Optional[list[dict]] = None,
    jev_signals: Optional[dict] = None,
) -> str:
    """Build user message with goal, observation, and history.

    Args:
        goal: User's signup goal (e.g., "Complete signup with document upload")
        observation: Current Observation dict from worker
        recent_history: Optional list of recent decisions and results
        jev_signals: Optional Tier-2 pre-computed screen signals (see TierRouter.enrich_context)

    Returns:
        User message string
    """
    message_parts = []

    # Goal context
    message_parts.append(f"Goal: {goal}\n")

    # Current observation
    message_parts.append("Current Screen State:")
    message_parts.append(f"- URL: {observation.get('url', 'unknown')}")
    message_parts.append(f"- Step: {observation.get('step', 0)}")

    visible_text = observation.get('visibleText', [])
    if visible_text:
        message_parts.append(f"- Visible Text: {', '.join(visible_text[:20])}")  # Limit to avoid token overflow
    else:
        message_parts.append("- Visible Text: (none detected)")

    # Last action result
    last_action = observation.get('lastActionResult', {})
    if last_action:
        action_name = last_action.get('action', 'unknown')
        action_status = last_action.get('status', 'unknown')
        message_parts.append(f"- Last Action: {action_name} ({action_status})")
        if last_action.get('error'):
            message_parts.append(f"- Last Error: {last_action['error']}")

    # Console errors (critical signals)
    console_errors = observation.get('consoleErrors', [])
    if console_errors:
        message_parts.append(f"- Console Errors: {', '.join(console_errors[:3])}")

    # Performance metrics
    timing = observation.get('timing', {})
    if timing:
        message_parts.append(f"- Page Load Time: {timing.get('domReady', 'N/A')}ms")

    # Recent history for context
    if recent_history:
        message_parts.append("\nRecent Action History:")
        for i, entry in enumerate(recent_history[-5:], 1):  # Last 5 actions
            action = entry.get('action', 'unknown')
            target = entry.get('target', '')
            result = entry.get('result', 'unknown')
            message_parts.append(f"{i}. {action} on '{target}' -> {result}")

    message_parts.extend(_format_jev_signals(jev_signals))

    message_parts.append("\nReturn your next action decision as JSON (no additional text):")

    return "\n".join(message_parts)


def build_user_message_with_vision(
    goal: str,
    observation: dict,
    screenshot_base64: str,
    recent_history: Optional[list[dict]] = None,
    format_style: str = "openai",
    jev_signals: Optional[dict] = None,
) -> list[dict]:
    """Build user message with screenshot image for vision models.

    Args:
        goal: User's signup goal
        observation: Current Observation dict from worker
        screenshot_base64: Base64-encoded screenshot image
        recent_history: Optional list of recent decisions and results
        format_style: Vision format style ("openai" or "anthropic")
        jev_signals: Optional Tier-2 pre-computed screen signals (see TierRouter.enrich_context)

    Returns:
        Message content list with text and image
    """
    # Build text prompt
    text_parts = []

    text_parts.append(f"Goal: {goal}\n")
    text_parts.append("Current Screen State:")
    text_parts.append(f"- URL: {observation.get('url', 'unknown')}")
    text_parts.append(f"- Step: {observation.get('step', 0)}")

    # Last action result
    last_action = observation.get('lastActionResult', {})
    if last_action:
        action_name = last_action.get('action', 'unknown')
        action_status = last_action.get('status', 'unknown')
        text_parts.append(f"- Last Action: {action_name} ({action_status})")
        if last_action.get('error'):
            text_parts.append(f"- Last Error: {last_action['error']}")

    # Recent history with details
    if recent_history:
        text_parts.append("\nRecent Action History:")
        for i, entry in enumerate(recent_history[-5:], 1):
            action = entry.get('action', 'unknown')
            success = entry.get('success', False)
            status = '✓' if success else '✗'
            details = entry.get('details', {})

            if success:
                text_parts.append(f"{i}. {status} {action}")
            else:
                # For failures, show what didn't work so agent can try alternatives
                error = details.get('error', '') or entry.get('error', '')
                text_parts.append(f"{i}. {status} {action} - FAILED: {error}")

    text_parts.append(f"\n🎯 CRITICAL: CHECK YOUR CURRENT PAGE FIRST!")
    text_parts.append(f"Current URL: {observation.get('url', 'unknown')}")
    text_parts.append("")
    text_parts.append("DETERMINE WHICH PHASE YOU'RE IN:")

    current_url = observation.get('url', '').lower()
    if 'signup' in current_url or 'register' in current_url or 'sign-up' in current_url:
        text_parts.append("✅ YOU ARE IN PHASE 2 (Signup Page)")
        text_parts.append("   → You should see signup method options (Google, Email, etc.)")
        text_parts.append("   → CHOOSE EMAIL/direct signup, AVOID social OAuth")
    else:
        text_parts.append("✅ YOU ARE IN PHASE 1 (Homepage/Landing Page)")
        text_parts.append("   → You need to NAVIGATE TO signup page first")
        text_parts.append("   → Look for: 'Open account', 'Sign up', 'Create account', 'Get started'")
        text_parts.append("   → DON'T look for 'Sign up with Email' - that comes AFTER you reach signup page!")

    text_parts.append("\n📍 ANALYZE THE SCREENSHOT:")
    text_parts.append("1. What buttons/links/CTAs do I ACTUALLY SEE in the image?")
    text_parts.append("2. Do they match the expected elements for my current phase?")
    text_parts.append("3. Where are they located (top-right, center, bottom)?")
    text_parts.append("\n🚫 TWO-PHASE OAUTH AVOIDANCE STRATEGY:")
    text_parts.append("PHASE 1 - Getting to signup (on homepage/landing):")
    text_parts.append("  → URL does NOT contain 'signup' or 'register'")
    text_parts.append("  → Click ANY general signup CTA: 'Open account', 'Sign up', 'Create account'")
    text_parts.append("  → Don't expect 'Sign up with Email' - that option appears in Phase 2!")
    text_parts.append("")
    text_parts.append("PHASE 2 - Choosing signup method (on signup page):")
    text_parts.append("  → URL contains 'signup' or 'register'")
    text_parts.append("  → NOW you see options: 'Sign up with Google' + 'Sign up with Email'")
    text_parts.append("  → CHOOSE EMAIL, AVOID Google/Facebook/Apple OAuth")
    text_parts.append("  → Use direct email inputs over social login buttons")
    text_parts.append("\n💡 SEMANTIC MATCHING - UNDERSTAND YOUR GOAL:")
    text_parts.append("- Goal 'Sign up'? → Look for: 'Open account', 'Create account', 'Register', 'Get started', 'Join'")
    text_parts.append("- Don't need EXACT match - need SEMANTIC match (same purpose)")
    text_parts.append("- 'Open account' achieves signup goal → USE IT!")
    text_parts.append("- Partial text OK: 'account' matches 'Open account', 'sign' matches 'Sign up'")
    text_parts.append("- Case-insensitive: 'SIGN UP' = 'Sign Up' = 'sign up'")
    text_parts.append("\n🔍 DECISION STRATEGY:")
    text_parts.append("- FIRST: Check if email signup option exists (prefer over social login)")
    text_parts.append("- If previous attempts failed, try SEMANTICALLY SIMILAR alternatives")
    text_parts.append("- Don't repeat the same target - explore other options that match the goal")
    text_parts.append("- If stuck between social and email signup, scroll to find 'Continue with email' option")
    text_parts.extend(_format_jev_signals(jev_signals))
    text_parts.append("\nReturn your decision as JSON (no additional text):")

    text_content = "\n".join(text_parts)

    # Return message with format appropriate for the model
    if format_style == "openai":
        # OpenAI/NVIDIA format with image_url
        return [
            {"type": "text", "text": text_content},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_base64}"}}
        ]
    else:
        # Anthropic format with source object
        return [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": screenshot_base64}},
            {"type": "text", "text": text_content}
        ]


def build_repair_prompt(malformed_output: str, validation_error: str) -> str:
    """Build prompt for repairing malformed decision output.

    Args:
        malformed_output: The invalid JSON output from previous attempt
        validation_error: Error message from validation

    Returns:
        Repair prompt string
    """
    return f"""The previous decision output was invalid. Please fix it and return valid JSON.

Validation Error:
{validation_error}

Previous Output:
{malformed_output}

Required JSON Schema:
{DECISION_JSON_SCHEMA}

Return only the corrected JSON decision (no explanations, no markdown):"""
