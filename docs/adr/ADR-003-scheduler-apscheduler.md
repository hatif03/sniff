# ADR-003: Scheduler Approach — APScheduler In-Process Daemon

## Status
Accepted

## Date
2025-01-01

## Context

To enable continuous/scheduled testing (catch signup regressions before real users do), Sniff needs a mechanism to trigger runs on a schedule (e.g., every hour, after every deployment). Two broad options exist:

**Option A — OS cron integration**: Generate a crontab entry that calls `sniff run`. Simple, zero dependencies, works on any Unix system. Downside: not portable (doesn't work on Windows, in Docker containers without a cron daemon, or on cloud VMs without manual setup).

**Option B — In-process APScheduler daemon**: `sniff daemon start` runs a background process that holds an APScheduler instance. Schedules are stored in `sniff.json`; the daemon reads them on start. Works anywhere Python runs, including Docker and cloud VMs without OS cron.

**Option C — External task queue (Celery/Redis)**: Full-featured but adds Redis/RabbitMQ as infrastructure dependencies. Excessive for what is essentially a "run a CLI command on a schedule" use case.

## Decision

Use **APScheduler** (`apscheduler>=3.10`) as an in-process daemon, exposed via `sniff daemon start|stop|status`. This is the most portable approach and the right level of complexity for the use case.

The daemon uses **APScheduler's `BackgroundScheduler`** with a **SQLite job store** (`data/sniff_schedules.db`) so schedules survive restarts. On `sniff daemon start`, the process forks to the background (or runs in-foreground with `--foreground`), writes its PID to `.sniff_daemon.pid`, and begins executing scheduled jobs.

## Rationale

| Option | Considered | Rejected because |
|---|---|---|
| APScheduler daemon (chosen) | ✅ | — |
| OS cron | ✅ | Not portable; doesn't work in Docker/containers/Windows |
| Celery + Redis | ✅ | Excessive infrastructure for this scheduling use case |
| systemd timer | ✅ | Linux-only; no cross-platform support |
| GitHub Actions (CI/CD scheduled workflow) | ✅ | Viable for CI use case but doesn't serve local/self-hosted use |

## Consequences

**Positive:**
- Works identically on macOS, Linux, Windows, Docker, cloud VMs
- Schedules persist across restarts via SQLite job store
- `sniff daemon status` shows all scheduled jobs and next run times
- Can be run as a systemd/launchd service for production deployment

**Negative / Trade-offs:**
- Requires `apscheduler` as an additional dependency
- Process management (start/stop/PID file) adds code complexity
- SQLite job store means concurrent write contention is possible if multiple daemons start (mitigated by PID file lock)

**Neutral:**
- APScheduler v3.x is the stable version; v4 is in beta — we use v3.x

## Implementation Notes

- `src/scheduler/scheduler.py` — `SniffScheduler` class
- `src/cli/commands/daemon.py` — `sniff daemon start|stop|status`
- `src/cli/commands/schedule.py` — `sniff schedule add|list|remove|run-now`
- PID file: `.sniff_daemon.pid` in the working directory
- SQLite job store: `data/sniff_schedules.db`
- `SniffScheduler` wraps `BackgroundScheduler` with `SQLAlchemyJobStore`
