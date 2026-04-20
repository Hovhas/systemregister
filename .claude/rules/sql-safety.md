---
paths: ["**/*.sql", "**/migration*", "**/schema*", "**/versions/*.py"]
---
# SQL-säkerhet

- ALDRIG UPDATE/DELETE utan WHERE-clause
- ALLTID backup före schema-migration
- Testa migrationer mot kopia först (i systemregister: kör Alembic först mot `docker compose exec backend` lokalt)
