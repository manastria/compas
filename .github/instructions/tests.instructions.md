---
description: "Utiliser cette instruction pour toute modification Python et imposer une validation pytest/ruff proportionnée aux fichiers touchés."
applyTo: "src/**/*.py,tests/**/*.py,pyproject.toml"
---
# Validation tests et qualité

Objectif: réduire les régressions et standardiser la routine de validation dans Compas.

## Routine minimale avant de conclure un changement

1. Exécuter les tests ciblés selon la zone modifiée.
2. Exécuter le lint ruff sur le périmètre modifié.
3. Si le changement touche plusieurs modules, exécuter la suite complète.
4. Rapporter ce qui a été exécuté et le résultat (succès/échec), sans masquer les limites.

## Matrice de tests ciblés

- Si modification de src/compas/importer.py ou parsing Excel/SQLite:
  - poetry run pytest tests/test_importer.py -q
- Si modification de src/compas/ema.py ou logique EMA/tendance/rang:
  - poetry run pytest tests/test_ema.py -q
- Si modification de src/compas/dashboard.py ou parsing présence/rendu:
  - poetry run pytest tests/test_dashboard.py -q
- Si modification transversale, CLI, schéma DB, ou plusieurs modules:
  - poetry run pytest -q

## Lint et format

- Lint recommandé:
  - poetry run ruff check src tests
- Si nécessaire pour corriger:
  - poetry run ruff format src tests

Ne jamais reformater des zones non liées à la demande.

## Règles de restitution dans la réponse finale

Toujours inclure:

- La liste des commandes réellement exécutées.
- Le statut de chaque commande (OK/échec).
- Les tests non exécutés (et pourquoi).
- Les risques résiduels si validation incomplète.

## En cas d’échec

- Ne pas ignorer un échec de tests ou lint.
- Corriger si possible dans la même session.
- Si blocage, expliquer brièvement la cause et proposer la prochaine action concrète.
