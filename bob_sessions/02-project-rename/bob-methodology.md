# Session 02: Bob Methodology — Project Rename

## Bob Mode Used

**Agent Mode**

This was a pure implementation session — no planning needed, because the rename was completely specified in `sniff-expansion-plan.md` Sub-Task 1. Agent mode was used from the start.

---

## Bob Tools and Techniques

### Bulk Grep Before Any Write
Before changing a single file, Bob ran a repo-wide case-insensitive grep for the project's original internal name across all `.py`, `.ts`, `.json`, `.md`, and `.toml` files. This established the exact scope of the rename: 27 Python source files, 17 Markdown files, 2 config files, and 1 environment template.

This is standard Bob discipline: **never write before you know what you are changing**. A bulk rename without an upfront scope check risks missing occurrences or changing things that should not be changed.

### Shell-Backed Bulk Replacement
The rename was mechanically executed using PowerShell `Set-Content` with regex replacement across all files simultaneously for pure string patterns. This was chosen over file-by-file editing for three reasons:
1. The rename is purely mechanical — no logic changes
2. Bulk replacement is faster and produces fewer opportunities for human error
3. Every occurrence of the original name needed to be changed, not just some

Bob did not edit files by hand. It used shell tools to do the mechanical work, then read individual files to verify correctness.

### Verification Grep
After the bulk replacement, Bob ran a second repo-wide grep for any remaining occurrences. The result was zero hits in Python source files and `pyproject.toml`. This verification pass is standard practice — it confirms the work is complete rather than assuming it.

### Pre-Existing Bug Discovery
While reading test files as part of the rename scope check, Bob found a pre-existing import error: `tests/test_integration.py` imported `PersonaManager` which did not exist in `src/core/persona.py`. This was not introduced by the rename; it was already there.

Bob fixed it (removed the unused import) rather than leaving it. This is the standard practice: if a bug is found while doing other work, fix it if it is clearly correct and small-scope. The fix was noted in the session summary as a pre-existing issue, not presented as the session's primary work.

### Intentional Non-Change: `src.*` Import Paths
Bob deliberately did not rename the Python package path prefix (`from src.core.config import ...`) even though the original name appeared in the project brand. Rationale: `src` is the Python module structure, not the brand name. Changing it would require restructuring the entire package, which was out of scope and risky. This decision was documented inline.

### `.env.example` Enhancement
Since the rename already required editing `.env.example` for env var names, Bob added the Typesafe AI configuration variables (`TYPESAFE_API_KEY`, `TYPESAFE_MODEL_ID`, `SNIFF_JEV_ENABLED`) in the same pass. This avoids a second touch of the file in Session 04. The principle: if you are already editing a file, add related changes that are low-risk and clearly needed.

---

## Test Run
After all changes, Bob ran `uv run pytest` to verify all 67 tests still passed. This is the mandatory verification step for every Agent mode session that touches Python source files.

---

## Key Bob Discipline Applied

**Scope before touch.** The entire rename was scoped (via grep) before a single file was edited. This is the Bob "investigate before answering" principle applied to a large mechanical operation: know what you are changing, then change it, then verify you changed everything you needed to.
