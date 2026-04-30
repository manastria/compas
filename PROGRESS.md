# PROGRESS - Compas

Ce document suit l’avancement du projet et sert de journal de session.

Référence de cadrage: [CLAUDE.md](CLAUDE.md)

## État global

- Statut actuel: v1 fonctionnelle en CLI (import xlsx -> SQLite -> dashboard HTML statique)
- Stack: Python 3.12+, Poetry, openpyxl, sqlite3, Jinja2
- Entrée CLI: compas

## Plan de développement déduit de CLAUDE

## P0 - Socle v1 (essentiel)

- [x] CLI unifiée: import, dashboard, build
- [x] Import destructif depuis data/*.xlsx vers SQLite
- [x] Schéma SQLite et contraintes d’unicité
- [x] Parsing Config + feuilles de séance
- [x] Ignorer Config/Modele/Modèle/tmp-*
- [x] Dédoublonnage étudiants inter-projets
- [x] Calcul EMA, tendance et rangs
- [x] Parsing présence (syntaxe normalisée + combinaisons)
- [x] Dashboard HTML statique généré par Jinja2
- [x] Base de tests pytest (importer, ema, dashboard)

## P1 - Robustesse et qualité (court terme)

- [ ] Renforcer les tests d’intégration de bout en bout (fixtures multi-fichiers)
- [ ] Étendre les tests sur les cas limites de présence
- [ ] Vérifier et documenter précisément la stratégie last file wins
- [ ] Ajouter des tests de non-régression sur le JSON injecté au template
- [ ] Clarifier les messages de warning sur formats inattendus

## P2 - Dashboard compact vidéoprojeté (en cours dans CLAUDE)

- [ ] Stabiliser la grille responsive de cartes
- [ ] Finaliser histogrammes verticaux et lisibilité en projection
- [ ] Ajouter tests simples de structure HTML générée

## P3 - Évolutions prévues

- [ ] Fiche individuelle par étudiant (historique détaillé)
- [ ] Projet Assiduité (croisement via INE)
- [ ] Rangs gamifiés (seuils et badges)

## Hors scope v1 (garde-fous)

- [ ] Pas de serveur web
- [ ] Pas de dark mode custom (prefers-color-scheme uniquement)
- [ ] Pas de traduction en note semestrielle
- [ ] Pas d’impact de la présence sur les scores

## Journal de session

## Session - 2026-04-30

### Objectif

- Mettre en place la base de customisation agent et de suivi projet.

### Réalisé

- Ajout de AGENTS.md (guide minimal pour agents)
- Ajout de .github/instructions/tests.instructions.md (routine tests/lint)
- Création de PROGRESS.md (plan et journal)

### Vérifications

- Vérification structurelle des fichiers markdown créés
- Pas de commande de tests exécutée (changement documentaire uniquement)

### Risques/notes

- Le plan P1/P2/P3 est une projection issue de CLAUDE.md et devra être ajusté selon les priorités réelles.

### Prochaines actions proposées

- Prioriser 2 à 3 items P1 et les transformer en tâches testables
- Ajouter une session à chaque fin de travail

## Règle de mise à jour en fin de session

À la fin de chaque session, ajouter une nouvelle section sous Journal de session avec:

1. Date
2. Objectif
3. Réalisé
4. Vérifications (commandes exécutées et résultats)
5. Risques/notes
6. Prochaines actions

Conserver les anciennes sessions (historique append-only).