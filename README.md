# rental-manager

A web tool to manage tenants, contracts and data for calculating costs

## Backend

The backend uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
cd backend
uv sync          # create .venv and install all dependencies
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Add a new dependency:

```bash
cd backend
uv add <package>
```
