# Sniff FastAPI backend (src/api/main.py), containerized for Fly.io/Railway/
# any host that runs a long-lived container (see docs/product/SAAS_ROADMAP.md
# section 5 - Playwright needs real compute + browser binaries, not serverless).
#
# Base image: Playwright's own official Python image, which ships Chromium/
# Firefox/WebKit already installed - avoids a slow `playwright install` in a
# generic python:3.11 image. Tag matches the exact playwright version this
# project pins (see pyproject.toml / uv.lock: playwright==1.63.0). "-noble"
# is the Ubuntu 24.04 variant of that tag (the other option is "-jammy",
# Ubuntu 22.04); either works, noble is current.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app

# Install this project's dependencies. uv.lock already pins everything the
# project needs (including `fastapi`/`uvicorn`), so `uv sync` matches the
# same dev workflow used locally instead of a hand-rolled pip install list.
# (No --extra dev: pytest/ruff/mypy aren't needed to run the API.)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
