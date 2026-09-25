# Session 04 Prompt: Typesafe AI Jev Client Setup

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 3 in `sniff-expansion-plan.md` | [ADR-001](../../docs/adr/ADR-001-three-tier-architecture.md)

---

## Prompt (to be given when this session starts)

> Sub-Task 3 from `sniff-expansion-plan.md`:
>
> Integrate Typesafe AI's Jev model as Tier 2 in the three-tier intelligence architecture.
> Reference docs: https://docs.typesafe.ai/agent-skill
>
> 1. Read the Typesafe AI docs and understand:
>    - Skill spec format (inputs, outputs, schema)
>    - API authentication and invocation pattern
>
> 2. Add the Typesafe AI SDK to `sniff-ai/pyproject.toml`
>
> 3. Create `sniff-ai/src/agent/jev_client.py`:
>    - `JevClient` class wrapping the Typesafe AI API
>    - `invoke_skill(skill_name, inputs) -> SkillResult` method
>    - Auth via `TYPESAFE_API_KEY` env var
>    - Timeout handling + error types matching the BedrockClient pattern
>    - Module docstring explaining role in three-tier model
>
> 4. Create `sniff-ai/src/agent/skills/` directory with three skill definitions:
>    - `navigation_decision.skill` — given observation, choose next action type
>    - `stuck_detector.skill` — given recent action history, classify if stuck
>    - `element_selector.skill` — given visible text + goal, pick best target element
>    - Each skill file must include: description, input schema, output schema, examples
>
> 5. Add `TypesafeConfig` block to `SniffConfig` in `sniff-ai/src/core/config.py`:
>    - `api_key: Optional[str]`
>    - `model_id: str = "jev-v1"`
>    - `enabled: bool = True`
>    - `confidence_threshold: float = 0.75`
>    - Sourced from `TYPESAFE_API_KEY`, `TYPESAFE_MODEL_ID`, `SNIFF_JEV_ENABLED`, `SNIFF_JEV_CONFIDENCE_THRESHOLD`
>
> 6. Update `sniff-ai/.env.example` with the new Typesafe vars (they were pre-added in Session 02 as placeholders — verify they are correct)
>
> 7. Write unit tests for `JevClient` with mocked API responses:
>    - Successful skill invocation
>    - Low confidence response (below threshold)
>    - API error / timeout
>    - Missing API key handling
>
> Follow documentation discipline: every file must have module docstring, every class docstring, non-obvious logic inline commented.
> API key: already available (user confirmed in planning session).

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 03 is complete (Python deps installed, Tailwind v4 Node build verified)
- [ ] `sniff-ai/src/agent/bedrock_client.py` has been reviewed as the pattern to follow
- [ ] `TYPESAFE_API_KEY` is in local `.env` (not committed)
