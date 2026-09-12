# self-checkout

Self-service ordering kiosk for a snack bar. Spec: [`self-checkout-spec.md`](self-checkout-spec.md).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose

## Quick start (Docker)

One command builds and starts everything — the PostgreSQL database and the
FastAPI server — with migrations applied automatically:

```bash
docker-compose up -d --build
```

The API is then available at <http://localhost:8000> (root returns a hello
message), and PostgreSQL listens on `localhost:5432`.

Useful commands:

```bash
docker-compose ps            # check service status
docker-compose logs -f api   # follow API logs
docker-compose down          # stop everything (data kept in the db volume)
docker-compose down -v       # stop and delete the database volume
```

## Local development (without Docker for the API)

If you want to run the API on the host (e.g. with `--reload`) while Postgres
stays in Docker:

```bash
docker-compose up -d db      # start only the database
cd backend
uv sync                      # install dependencies
uv run alembic upgrade head  # apply migrations
uv run uvicorn app.main:app --reload
```

The API reads `DATABASE_URL` (set by Docker Compose) or falls back to
`postgresql+psycopg2://selfcheckout:selfcheckout@localhost:5432/selfcheckout`.

### Migrations

```bash
cd backend
uv run alembic upgrade head                       # apply migrations
uv run alembic revision --autogenerate -m "..."   # generate from model changes
uv run alembic downgrade -1                       # roll back one migration
```

> Requires [uv](https://docs.astral.sh/uv/) for local development only; the
> Docker path needs nothing beyond Docker.
