# Session 06 Prompt: Scheduled Continuous Runs

**Session Type:** Agent Mode  
**Status:** ⬜ Pending  
**Reference:** Sub-Task 5 in `sniff-expansion-plan.md` | [ADR-003](../../docs/adr/ADR-003-scheduler-apscheduler.md)

---

## Prompt (to be given when this session starts)

> Sub-Task 5 from `sniff-expansion-plan.md`:
>
> Add APScheduler-backed continuous run scheduling to Sniff. Reference ADR-003 for the daemon approach decision.
>
> 1. Create `sniff-ai/src/scheduler/` directory with `__init__.py` and `scheduler.py`:
>    - `SniffScheduler` class wrapping APScheduler `BackgroundScheduler`
>    - SQLAlchemy job store backed by SQLite: `data/sniff_schedules.db`
>    - `add_schedule(goal, persona, cron_expression, url)` method
>    - `remove_schedule(schedule_id)` method
>    - `list_schedules()` method
>    - `run_now(schedule_id)` method (immediate one-off trigger)
>    - `start()` / `stop()` / `status()` methods
>    - PID file management: `.sniff_daemon.pid`
>    - Module docstring explaining APScheduler choice (reference ADR-003)
>
> 2. Add `ScheduleConfig` to `SniffConfig`:
>    - `schedules_db_path: str = "./data/sniff_schedules.db"`
>    - `daemon_pid_file: str = ".sniff_daemon.pid"`
>    - `webhook_port: int = 8765`
>
> 3. Create `sniff-ai/src/cli/commands/schedule.py`:
>    - `sniff schedule add --goal "..." --cron "0 * * * *" --persona careful_user --url https://...`
>    - `sniff schedule list` — show all schedules with next run time
>    - `sniff schedule remove <schedule_id>`
>    - `sniff schedule run-now <schedule_id>`
>
> 4. Create `sniff-ai/src/cli/commands/daemon.py`:
>    - `sniff daemon start` — fork daemon, write PID file, begin scheduler
>    - `sniff daemon stop` — read PID file, send SIGTERM
>    - `sniff daemon status` — show running/stopped + active schedules
>
> 5. Add minimal webhook endpoint using FastAPI (already in dependencies):
>    - POST `/trigger` — start a run immediately (for CI/CD or external triggers)
>    - GET `/health` — daemon health check
>    - The daemon starts this server on `localhost:SNIFF_WEBHOOK_PORT` (default 8765)
>
> 6. Update `sniff-ai/src/cli/main.py` to register the new commands
>
> 7. Update Slack alert builder to include schedule context when alert comes from a scheduled run:
>    - Add "Scheduled Run" badge to alert header
>    - Include schedule ID and cron expression in alert fields
>
> 8. Write tests for scheduler logic (use in-memory SQLite for tests):
>    - Schedule creation, listing, removal
>    - PID file creation and cleanup
>    - Run-now trigger

---

## Pre-Session Checklist

Before starting this session, verify:
- [ ] Session 05 is complete (three-tier architecture working)
- [ ] `apscheduler >=3.11.0` is in pyproject.toml (added in Session 03) ✅
- [ ] `fastapi >=0.115.0` and `uvicorn >=0.34.0` are in pyproject.toml ✅
