# Alembic barrins_api

Single-database Alembic configuration for barrins_api.

Common usage:

- Apply all migrations: `alembic upgrade head`
- Roll back one migration: `alembic downgrade -1`
- Generate a migration: `alembic revision --autogenerate -m "message"`

Project reminders:

- Always review the generated SQL before applying it.
- Avoid any dynamic SQL interpolation in migration scripts.
- Prefer `sa.text(...).bindparams(...)` when parameters are needed.
