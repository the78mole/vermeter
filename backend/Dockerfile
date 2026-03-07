FROM python:3.12-slim

# uv-Binary aus dem offiziellen Astral-Image kopieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# System-Build-Abhängigkeiten für asyncpg / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# uv-Umgebungsvariablen: Bytecode kompilieren + Copy-Link-Modus für Performance
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Abhängigkeiten installieren (Cache-Layer: wird nur neu gebaut, wenn sich
# pyproject.toml oder uv.lock ändern, nicht bei Code-Änderungen)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Anwendungscode kopieren und Projekt installieren
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
