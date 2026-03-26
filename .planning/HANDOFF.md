# Handoff — 2026-03-26

## Slutfört denna session

**Fas 1-4 komplett** — fullständigt backend + frontend för IT-systemregister.

### Genomfört:
1. **Fas 1 — Datamodell + API**: 8 SQLAlchemy-tabeller, CRUD för organizations/systems, sök/filter, audit trail
2. **Fas 2 — Kärnfunktionalitet**: Klassning (K/R/T), ägarskap, integrationer, multi-org RLS, import/export (Excel/CSV/JSON)
3. **Fas 3 — Frontend**: React 18 + shadcn/ui, systemlista, detaljvy med flikar, dashboard, SVG-beroendekarta
4. **Fas 4 — GDPR + compliance**: ROPA-koppling, avtal/leverantörer, NIS2-rapporter (JSON/Excel/HTML), compliance-gap-analys
5. **127 tester** — alla gröna (0.54s)

### Git-historik:
- `a2d7023` fas 1
- `21a41ed` fas 2
- `b476c8c` fas 3
- `21e3208` fas 4

## Nästa steg — Fas 5: K8s deploy

Kräver beslut:
- GitHub-repo (Hovhas/systemregister)
- Domän (t.ex. systemregister.tejpat.se)
- Databas: CNPG i klustret eller extern
- SOPS-secrets: DATABASE_URL, SECRET_KEY, OIDC-credentials
- Backup: CronJob till TrueNAS

Uppgifter:
- [ ] Skapa GitHub-repo och pusha
- [ ] Dockerfile multi-stage (prod)
- [ ] Kustomize overlays (dev/prod)
- [ ] Flux GitRepository + Kustomization
- [ ] Traefik IngressRoute
- [ ] SOPS-krypterade secrets
- [ ] CronJob: pg_dump till TrueNAS
- [ ] GitHub Actions CI/CD (build + push)

## Kända problem

- FK-violations ger 500 istf 422 (saknar validering i create_system)
- classified_at använder func.now() (transaktionsstid, inte klocktid)
- SAWarning "transaction already deassociated" i tester (ofarlig)
- Alembic-migrationer kräver att tabeller skapas med create_all först (RLS-migration)
- Frontend DashboardPage/DependenciesPage har inline-typer (bör använda @/types)

## Beslut fattade

| Beslut | Motivering |
|--------|------------|
| PostgreSQL RLS för multi-org | Dataisolering på databasnivå |
| X-Organization-Id header för RLS | Placeholder tills OIDC |
| HTML istället för PDF-rapport | Undviker tunga dependencies (weasyprint/reportlab) |
| after_flush för audit trail | Atomärt med original-transaktionen |
| Seed-data inline (inte scripts/seed.py) | Docker-containern monterar bara backend/ |

## Startkommando

```bash
cd ~/projekt/systemregister && claude --add-dir ../dev-team1 --dangerously-skip-permissions
```

Sedan: `/projekt:resume`
