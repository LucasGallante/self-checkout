# self-checkout

Self-service ordering kiosk for a snack bar. Spec: [`self-checkout-spec.md`](self-checkout-spec.md).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose
- [uv](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/) for local
  development only; the Docker path needs nothing else.

## Quick start (Docker)

One command builds and starts everything — PostgreSQL, the FastAPI server, and
the React frontend — with migrations applied automatically:

```bash
docker-compose up -d --build
```

- App (kiosk + admin): <http://localhost:5173> (admin at `/admin`)
- API: <http://localhost:8000> (root returns a hello message)
- PostgreSQL: `localhost:5432`

Useful commands:

```bash
docker-compose ps            # check service status
docker-compose logs -f api   # follow API logs
docker-compose down          # stop everything (data kept in the db volume)
docker-compose down -v       # stop and delete the database volume
```

## Backend (local development)

Run the API on the host (e.g. with `--reload`) while Postgres stays in Docker:

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

### Tests

Tests run against a dedicated `selfcheckout_test` database on the Postgres
container. Start it and create the test DB once:

```bash
docker-compose up -d db
docker exec self-checkout-db-1 psql -U selfcheckout -c "CREATE DATABASE selfcheckout_test"
```

Then run the suite from `backend/`:

```bash
uv run pytest                 # all tests
uv run pytest -q              # compact output
uv run pytest tests/test_checkout.py          # one file
uv run pytest -k "concurrency"                # just the concurrency tests
uv run pytest --cov=app --cov-report=term-missing   # with coverage
```

## Frontend (local development)

Run the Vite dev server (proxies API calls to `:8000` automatically):

```bash
docker-compose up -d db api  # backend must be up for the proxy
cd frontend
npm install                  # first time only
npm run dev                  # http://localhost:5173
```

Other frontend commands:

```bash
npm run build   # production build into dist/
npm run preview # serve the production build locally
```
