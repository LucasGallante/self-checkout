# Progress

- Created `self-checkout-spec.md` from a prompt (self-service snack bar kiosk).
- Iterated the spec to fix first-version gaps: added admin UI (as a route, no login), Start/Reset screens, stock, options, image_url, and idempotency.
- Built the backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL (docker-compose), with all spec routes, seeded menu, and a Postman collection.
- Built the frontend: React (Vite) customer flow + admin route, styled as a self-checkout kiosk.
- Dockerized the frontend (nginx) so a single `docker-compose up` runs the whole app.
- Polished the frontend: scrollable menu, responsive kiosk layout, full admin CRUD (incl. options), and fixed price/category bugs.
- Hardened the backend: fixed oversell/idempotency races, 500-on-delete, and added a pytest suite (29 tests, incl. concurrency).
- Expanded the test suite to 45 tests (~98% coverage), and made order history independent of the menu (snapshot-only, no item/option FKs).
