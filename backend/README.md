# Yojaka Backend v2

## Requirements
- Python 3.11+
- Copy `.env.example` → `.env` and fill in API keys.

## Dev setup

```bash
cd backend
pip install -e ".[test]"
alembic upgrade head
uvicorn main:app --port 8000 --reload
```

## Run tests

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## Smoke test

```bash
curl http://localhost:8000/health
python tests/smoke_ws.py
```

## Environment

Set `YOJAKA_DEPLOYMENT=prod` to switch to Postgres + pgvector + Redis.
Required extra env vars: `DATABASE_URL`, `REDIS_URL`.
