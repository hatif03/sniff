# Sniff Experiments Guide

Experiments allow you to run the same test goal with multiple personas to compare how different user types experience your signup flow.

## What is an Experiment?

An **experiment** is a collection of test runs that:
- Share the same goal, URL, device, and network settings
- Use different personas to simulate different user types
- Produce comparable results for UX analysis

## Why Use Experiments?

Running experiments helps you:

1. **Identify persona-specific friction** - See which user types struggle the most
2. **Compare completion times** - Understand which personas abandon faster
3. **Find common pain points** - Discover issues that affect all user types
4. **Prioritize fixes** - Know which UX issues have the broadest impact

---

## Quick Start

### Run with Specific Personas

```bash
Sniff experiment run \
  --name "Signup Flow Test" \
  --goal "Complete signup with email" \
  --persona impatient_user \
  --persona confused_first_time_user \
  --persona careful_user
```

### Run with All Personas

```bash
Sniff experiment run \
  --name "Full UX Audit" \
  --goal "Complete onboarding" \
  --all
```

### Run in Parallel (Faster)

```bash
Sniff experiment run \
  --name "Quick Test" \
  --goal "Sign up and verify email" \
  --all \
  --parallel
```

---

## Command Reference

### `Sniff experiment run`

Run a new experiment with multiple personas.

**Required Options:**
- `--name`, `-n` - Experiment name
- `--goal`, `-g` - Test goal (what you want personas to accomplish)

**Persona Selection (choose one):**
- `--persona`, `-p` - Specify personas (can use multiple times)
- `--all` - Use all available personas

**Optional:**
- `--description`, `-d` - Experiment description
- `--url`, `-u` - Starting URL (overrides config)
- `--device` - Device profile (e.g., "iPhone 13")
- `--network` - Network throttling (4g, 3g, slow3g)
- `--max-steps` - Override max steps limit
- `--headless/--headed` - Browser visibility
- `--parallel/--sequential` - Execution mode (default: sequential)
- `--yes`, `-y` - Skip confirmation prompt

**Examples:**

```bash
# Basic experiment with 3 personas
Sniff experiment run \
  --name "Email Signup Test" \
  --goal "Complete email signup" \
  --persona impatient_user \
  --persona confused_first_time_user \
  --persona power_user

# Test on slow 3G network
Sniff experiment run \
  --name "Mobile Performance Test" \
  --goal "Complete signup" \
  --all \
  --network slow3g \
  --device "iPhone 13"

# Run in parallel for speed
Sniff experiment run \
  --name "Fast Audit" \
  --goal "Create account" \
  --all \
  --parallel

# Specific URL override
Sniff experiment run \
  --name "Checkout Flow" \
  --goal "Complete checkout" \
  --url https://staging.example.com/checkout \
  --persona impatient_user \
  --persona careful_user
```

---

### `Sniff experiment list`

List all experiments with summary results.

```bash
Sniff experiment list
```

**Output:**
```
                              Experiments
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ ID               ┃ Name             ┃ Personas ┃ Success Rate ┃ Created         ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ exp_20260207_... │ Signup Flow Test │ 3        │ 66.7%        │ 2026-02-07 14:30│
│ exp_20260207_... │ Full UX Audit    │ 4        │ 100.0%       │ 2026-02-07 12:15│
└──────────────────┴──────────────────┴──────────┴──────────────┴─────────────────┘
```

---

### `Sniff experiment show <experiment_id>`

Show detailed results for a specific experiment.

```bash
Sniff experiment show exp_20260207_143027_8a3f1b2c
```

**Output:**
```
✓ Experiment Complete: Signup Flow Test

                    Experiment Summary
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric          ┃ Value                                 ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Experiment ID   │ exp_20260207_143027_8a3f1b2c          │
│ Goal            │ Complete signup with email            │
│ Total Runs      │ 3                                     │
│ Successful      │ 2 ✓                                   │
│ Failed          │ 1 ✗                                   │
│ Success Rate    │ 66.7%                                 │
│ Total Duration  │ 245.3s                                │
│ Avg Duration    │ 81.8s                                 │
└─────────────────┴───────────────────────────────────────┘

                       Persona Results
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ Persona                   ┃ Status    ┃ Outcome    ┃ Duration ┃ Steps ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ impatient_user            │ completed │ success ✓  │ 65.2s    │ 8     │
│ confused_first_time_user  │ completed │ failure ✗  │ 102.5s   │ 12    │
│ careful_user              │ completed │ success ✓  │ 77.6s    │ 10    │
└───────────────────────────┴───────────┴────────────┴──────────┴───────┘

Insights:
  🏃 Fastest: impatient_user
  🐌 Slowest: confused_first_time_user
  🏆 Most Successful: impatient_user

Recommendations:
  ⚠️  Warning: Less than 50% success rate - significant friction points exist
```

---

### `Sniff experiment compare <experiment_id>`

Compare persona performance in detail.

```bash
Sniff experiment compare exp_20260207_143027_8a3f1b2c
```

**Output:**
```
Persona Comparison: Signup Flow Test

                        Persona Performance
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┓
┃ Persona                   ┃ Outcome    ┃ Duration ┃ Steps ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━┩
│ impatient_user            │ success ✓  │ 65.2s    │ 8     │ completed │
│ careful_user              │ success ✓  │ 77.6s    │ 10    │ completed │
│ confused_first_time_user  │ failure ✗  │ 102.5s   │ 12    │ completed │
└───────────────────────────┴────────────┴──────────┴───────┴───────────┘

Key Findings:
  🏃 Fastest completion: impatient_user
  🐌 Slowest completion: confused_first_time_user

Recommendations:
  ⚠️  Warning: Less than 50% success rate - significant friction points exist
```

---

## Execution Modes

### Sequential (Default)

Runs personas one after another.

**Pros:**
- Easier to debug (see each run in real-time)
- Lower system resource usage
- Clearer progress tracking

**Cons:**
- Slower total execution time

**Use when:**
- You want to watch each persona's behavior
- Running with `--headed` mode
- Debugging flow issues

**Example:**
```bash
Sniff experiment run \
  --name "Debug Test" \
  --goal "Complete signup" \
  --persona impatient_user \
  --persona careful_user \
  --headed  # Sequential is better for visibility
```

---

### Parallel

Runs all personas simultaneously.

**Pros:**
- Faster total execution time
- Efficient for large persona sets

**Cons:**
- Higher system resource usage (CPU, memory, network)
- Harder to debug (multiple browsers running)
- May hit rate limits on target site

**Use when:**
- Running with `--headless` mode
- You have many personas to test
- Speed is more important than visibility

**Example:**
```bash
Sniff experiment run \
  --name "Fast Audit" \
  --goal "Complete signup" \
  --all \
  --parallel \
  --headless  # Parallel works best headless
```

**⚠️ Warning:** Parallel mode may:
- Trigger rate limiting on the target site
- Use significant system resources
- Be harder to debug if runs fail

---

## Use Cases

### 1. UX Friction Analysis

**Goal:** Identify which user types struggle most with your flow.

```bash
Sniff experiment run \
  --name "Signup UX Audit" \
  --goal "Complete email signup and verify account" \
  --all \
  --device "iPhone 13" \
  --network 4g
```

**What to look for:**
- Which persona takes longest?
- Which persona abandons most often?
- Are there common failure points across all personas?

---

### 2. Performance Testing

**Goal:** Test flow under various network conditions.

```bash
# Test with slow 3G
Sniff experiment run \
  --name "3G Performance Test" \
  --goal "Complete signup" \
  --persona impatient_user \
  --network slow3g

# Compare with 4G
Sniff experiment run \
  --name "4G Performance Test" \
  --goal "Complete signup" \
  --persona impatient_user \
  --network 4g
```

**What to look for:**
- Does impatient_user abandon on slow 3G?
- How much longer does the flow take?
- Do loading spinners/feedback appear?

---

### 3. A/B Testing Flow Variants

**Goal:** Compare two different URLs/flows.

```bash
# Test variant A
Sniff experiment run \
  --name "Variant A Test" \
  --goal "Complete signup" \
  --url https://staging.example.com/signup-a \
  --all

# Test variant B
Sniff experiment run \
  --name "Variant B Test" \
  --goal "Complete signup" \
  --url https://staging.example.com/signup-b \
  --all
```

**What to look for:**
- Which variant has higher success rate?
- Which variant completes faster?
- Do different personas prefer different variants?

---

### 4. Regression Testing

**Goal:** Ensure changes don't break existing flows.

```bash
# Before deployment
Sniff experiment run \
  --name "Pre-Deploy Baseline" \
  --goal "Complete checkout" \
  --all

# After deployment
Sniff experiment run \
  --name "Post-Deploy Verification" \
  --goal "Complete checkout" \
  --all

# Compare results
Sniff experiment compare exp_BEFORE_ID
Sniff experiment compare exp_AFTER_ID
```

---

## Best Practices

### 1. Use Descriptive Names

```bash
# ❌ Bad
--name "Test 1"

# ✅ Good
--name "Signup Flow - Email Verification Test"
```

### 2. Define Clear Goals

```bash
# ❌ Too vague
--goal "Test the app"

# ✅ Specific and measurable
--goal "Complete signup, upload document, and reach dashboard"
```

### 3. Start Sequential, Then Parallel

```bash
# First run: Debug with sequential + headed
Sniff experiment run --name "Debug" --goal "Sign up" --all --headed

# Once working: Run faster with parallel + headless
Sniff experiment run --name "Production" --goal "Sign up" --all --parallel
```

### 4. Use All Personas for Comprehensive Testing

```bash
# Tests all user types
Sniff experiment run --name "Full Audit" --goal "Complete flow" --all
```

### 5. Document Experiments

Use the `--description` flag:

```bash
Sniff experiment run \
  --name "Q1 2026 Signup Audit" \
  --goal "Complete signup" \
  --description "Testing new OAuth flow after redesign" \
  --all
```

---

## Interpreting Results

### Success Rate

- **100%**: All personas completed successfully - excellent UX!
- **75-99%**: Most personas succeed - minor friction exists
- **50-74%**: Significant friction - prioritize fixes
- **< 50%**: Critical issues - major UX problems
- **0%**: Complete failure - flow is broken

### Completion Time Variance

Large differences in completion times indicate:
- Some personas get confused more easily
- Flow complexity varies by user experience level
- Potential for optimization

**Example:**
```
impatient_user: 65s
careful_user: 78s
confused_first_time_user: 145s  ← 2x slower! Investigate why
```

### Common Patterns

**Pattern 1: All Personas Fail at Same Step**
→ Indicates a blocking bug or UX issue affecting everyone

**Pattern 2: Only Confused/Impatient Users Fail**
→ Flow works but has friction for less experienced users

**Pattern 3: Large Time Variance**
→ Flow clarity issues - some users understand quickly, others struggle

---

## Experiment Data Structure

Results are stored in `experiments/<experiment_id>/`:

```
experiments/
└── exp_20260207_143027_8a3f1b2c/
    ├── config.json         # Experiment configuration
    └── result.json         # Aggregated results + insights
```

Each persona run also generates standard artifacts in `artifacts/<run_id>/`.

---

## Troubleshooting

### All Runs Fail

**Check:**
1. Is the URL accessible?
2. Are allowed domains configured correctly?
3. Does `Sniff preflight` pass?

### Parallel Runs Fail

**Try:**
1. Reduce persona count
2. Use sequential mode
3. Check system resources (CPU, memory)

### Inconsistent Results

**Possible causes:**
1. Target site has dynamic content
2. Rate limiting triggered
3. Network instability

**Solutions:**
1. Run sequential for consistency
2. Add delays between runs
3. Use `--network` throttling

---

## Advanced Usage

### Custom Persona Sets

Create persona subsets for specific testing:

```bash
# Test only advanced users
Sniff experiment run \
  --name "Advanced User Test" \
  --goal "Use advanced features" \
  --persona power_user \
  --persona careful_user

# Test only struggling users
Sniff experiment run \
  --name "Struggling User Test" \
  --goal "Complete basic signup" \
  --persona confused_first_time_user \
  --persona impatient_user
```

### Combining with Other Tools

```bash
# Run experiment, then upload to Supabase
Sniff experiment run --name "Test" --goal "Signup" --all

# Results auto-upload if SUPABASE_ENABLED=true in .env
```

---

## FAQ

**Q: How many personas should I test?**
A: Start with 3-4 diverse personas (impatient, confused, careful, power). Use `--all` for comprehensive audits.

**Q: Should I use parallel or sequential?**
A: Sequential for debugging/visibility, parallel for speed when headless.

**Q: How long do experiments take?**
A: Depends on personas and flow complexity. Typical: 1-3 minutes per persona sequential, faster parallel.

**Q: Can I stop a running experiment?**
A: Yes, press Ctrl+C. Completed runs will be saved.

**Q: Can I re-run failed personas?**
A: Create a new experiment with only the failed personas using `--persona` flags.

**Q: Do experiments affect billing?**
A: Each persona run uses Bedrock API calls. More personas = higher cost.

---

## Examples

### Complete Workflow Example

```bash
# 1. Create personas
Sniff personas add  # Create custom personas

# 2. Run initial experiment
Sniff experiment run \
  --name "Initial Signup Test" \
  --goal "Complete signup with email verification" \
  --all \
  --sequential \
  --headed  # Watch it run

# 3. Review results
Sniff experiment list
Sniff experiment show exp_20260207_143027_8a3f1b2c

# 4. Compare personas
Sniff experiment compare exp_20260207_143027_8a3f1b2c

# 5. Run targeted follow-up with failing personas
Sniff experiment run \
  --name "Fix Verification - Confused Users" \
  --goal "Complete signup with email verification" \
  --persona confused_first_time_user \
  --headed

# 6. Run final validation with all personas
Sniff experiment run \
  --name "Final Validation" \
  --goal "Complete signup with email verification" \
  --all \
  --parallel  # Faster now that we're confident
```

---

Happy experimenting! 🧪
