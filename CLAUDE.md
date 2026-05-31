# Proiect Abc — Mod de lucru

## Skill-uri active

Toate cele 30 de skill-uri din `.claude/skills/` sunt active pe toată durata
proiectului. Claude le încarcă automat în fiecare sesiune (sunt project-level,
comise în repo).

**Regulă:** apelează skill-ul potrivit **automat, după context**, fără să fie
nevoie de o cerere explicită. La nevoie, folosește oricare dintre celelalte
după necesitate.

### Mapare context → skill (orientativ)

| Situație | Skill |
|---|---|
| Cod nou / bugfix | `tdd` (test-first) |
| Bug greu / regresie de performanță | `diagnose` |
| Finalizare feature / înainte de merge | `review` |
| Cod care se complică | `karpathy-guidelines` (simplitate, modificări chirurgicale) |
| Planificare / spec / RFC | `grill-me`, `grill-with-docs`, `to-prd`, `to-issues` |
| Refactor planificat | `request-refactor-plan`, `improve-codebase-architecture` |
| Predare conversație / pauză | `handoff` |
| Comunicare scurtă | `caveman` |
| Siguranță git | `git-guardrails-claude-code` |
| Setup repo (hooks, pre-commit) | `setup-pre-commit` |

Lista completă a skill-urilor este în `.claude/skills/`.

## Git

- Dezvoltare pe branch-ul desemnat al sesiunii.
- Commit-uri clare; push doar când lucrarea e completă.
- Fără PR decât la cerere explicită.
