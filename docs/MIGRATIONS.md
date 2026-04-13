# Databasmigrationer — Systemregister

## Skapa ny migration

```bash
docker compose exec backend alembic revision --autogenerate -m "beskrivning av ändring"
```

Granska alltid den genererade filen i `backend/alembic/versions/` innan du committar.

## Kör migrationer lokalt

```bash
docker compose exec backend alembic upgrade head
```

## Kör i produktion

Migrationer körs automatiskt via `entrypoint.sh` vid container-start:

```bash
alembic upgrade head
```

Om detta INTE är konfigurerat i din Dokploy-setup, kör manuellt via Dokploy terminal.

## Rollback

```bash
# Till specifik revision
docker compose exec backend alembic downgrade <revision>

# Ett steg tillbaka
docker compose exec backend alembic downgrade -1
```

## Visa nuvarande revision

```bash
docker compose exec backend alembic current
```

## Visa migrationshistorik

```bash
docker compose exec backend alembic history --verbose
```

## Vanliga problem

### Enum-konflikter

PostgreSQL enums kan inte utökas i en transaktion tillsammans med andra DDL-satser. Lösning: skapa separata migrationer för enum-ändringar.

```python
# I migrationen:
from alembic import op
op.execute("ALTER TYPE lifecyclestatus ADD VALUE 'ny_status'")
```

### Circular foreign keys

Om två tabeller refererar varandra, skapa FK-constraints i en separat migration efter att båda tabeller skapats:

```python
op.create_foreign_key("fk_name", "table_a", "table_b", ["col"], ["id"])
```

### Data-loss-varning

Alembic-autogenerate kan generera `drop_column` eller `drop_table` för kolumner/tabeller som tagits bort i modellerna. Granska ALLTID att detta är avsiktligt innan du kör migrationen.

### Migrationen misslyckas i produktion

1. Kontrollera Dokploy runtime-loggar
2. Koppla upp manuellt: `alembic current` for att se var migrationen stannade
3. Fixa problemet, skapa ny migration, eller rollback: `alembic downgrade <revision>`
4. Pusha fix -> ny deploy
