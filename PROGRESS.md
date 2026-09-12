# Progress

- Created `self-checkout-spec.md` from a prompt (self-service snack bar kiosk).
- Iterated the spec to fix first-version gaps: added admin UI (as a route, no login), Start/Reset screens, stock, options, image_url, and idempotency.
- Built the backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL (docker-compose), with all spec routes, seeded menu, and a Postman collection.
