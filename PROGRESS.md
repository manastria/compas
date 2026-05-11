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

- [x] Renforcer les tests d’intégration de bout en bout (fixtures multi-fichiers)
- [x] Étendre les tests sur les cas limites de présence
- [x] Vérifier et documenter précisément la stratégie last file wins
- [x] Ajouter des tests de non-régression sur le JSON injecté au template
- [x] Clarifier les messages de warning sur formats inattendus

## P2 - Dashboard compact vidéoprojeté (en cours dans CLAUDE)

- [x] Stabiliser la grille responsive de cartes
- [x] Finaliser histogrammes verticaux et lisibilité en projection
- [x] Ajouter tests simples de structure HTML générée

## P3 - Évolutions prévues

- [x] Fiche individuelle par étudiant (historique détaillé)
- [x] Projet Assiduité (croisement via INE)
- [ ] Rangs gamifiés (seuils et badges)
- [ ] **Fiche multi-projets unifiée** (option 2 — non retenue pour l'instant) :
  remplacer l'EMA globale agrégée par une EMA **par projet** dans la fiche
  individuelle (`fiche.py`). La fiche présenterait alors une section /
  onglet par projet (scores, tendances, historique propres à chaque projet),
  plus une éventuelle vue de synthèse globale clairement marquée. Aujourd'hui
  l'option 1 a été retenue : `--projet` + génération d'un dashboard et d'un
  sous-dossier de fiches par projet quand la base en contient plusieurs.
  Déclencheurs pour réenvisager l'option 2 : besoin d'une vue « 360° » de
  l'étudiant en entretien individuel, sans avoir à ouvrir N fiches.

## Hors scope v1 (garde-fous)

- [ ] Pas de serveur web
- [ ] Pas de dark mode custom (prefers-color-scheme uniquement)
- [ ] Pas de traduction en note semestrielle
- [ ] Pas d’impact de la présence sur les scores

## Journal de session

## Session - 2026-05-11 (P3 — Fiche individuelle par étudiant)

- **Objectif** — Implémenter la commande `compas fiches` : fiche HTML individuelle par étudiant actif.
- **Réalisé** — `presence_desc.py` : `describe_presence()` traduit les codes présence en français (syntaxe TYPE:valeur:motif, combinaisons par virgule) ; `fiche.py` : `compute_student_data`, `generate_fiche`, `generate_all_fiches` avec EMA history, events, pres_events, inter-projets, stats présence R/RR séparées ; `templates/fiche.html` : template Jinja2 adapté du prototype (Chart.js CDN, `scorePct` corrigé en échelle [-2,+2], barColor aligné) ; `cli.py` : commande `fiches` + option `--skip-fiches` dans `build` ; `test_fiche.py` : 40 tests (23 presence_desc + 17 fiche).
- **Vérifications** — `ruff check` OK ; `pytest` 256 passed, 40 nouveaux, 2 échecs préexistants dans test_dashboard.py (non liés).
- **Risques/notes** — Pour un étudiant multi-projets, l'EMA globale est calculée sur la séquence ordonnée par date (index enuméré), pas par numéro de séance, pour éviter les doublons de numéros entre projets. La section inter-projets est masquée si l'étudiant n'a qu'un projet.
- **Prochaines actions** — Valider le rendu de la fiche en conditions réelles (projection) ; démarrer projet Assiduité ou gamification.

## Session - 2026-04-30 (suite — P2 Dashboard compact vidéoprojeté)

- **Objectif** — Stabiliser la grille, corriger le bug de l'histogramme, améliorer la lisibilité en projection, ajouter les tests de structure HTML.
- **Réalisé** — Bug `scoreToPercent` corrigé (clamp [-1,+1] → échelle [-2,+2] complète) ; grille `<div>` → `<ul>` natif (sémantique) avec `auto-fit` (cartes élargies si peu d'étudiants) ; bouton `type="button"` ; points de légende via classes CSS (`legend-dot--*`) au lieu de styles inline ; chart height 70→80 px, label 8→9 px, gap 5 px ; `data-rank`/`data-name` sur chaque `<li>` ; `escapeAttr()` pour sécuriser le HTML JS-généré ; classe `TestDashboardHTML` (13 tests : structure statique, formule JS, JSON).
- **Vérifications** — `ruff check src/ tests/` OK ; `pytest` 170 passed (+13 nouveaux).
- **Risques/notes** — Les tests de cartes vérifient le JSON (source de vérité) car le rendu DOM est JS-only ; pas de régression côté Python.
- **Prochaines actions** — Démarrer P3 ou affiner le dashboard (taille de police en projection à valider en conditions réelles).

## Session - 2026-04-30 (suite — P1 Robustesse et qualité)

- **Objectif** — Implémenter tous les items P1 : tests d'intégration, cas limites, last-file-wins, JSON non-régression, warnings.
- **Réalisé** — `conftest.py` fixture `populated_db` ; `TestLastFileWins` (5 tests, ine/anonyme/pseudo/date_depart/unicité) ; `TestGenerateJson` (11 tests, structure et valeurs JSON) ; `test_integration.py` (9 tests end-to-end, pipeline simple + multi-fichiers) ; `_parse_presence` avec `label` pour warnings contextuels ; fix ruff E501 dans importer.py.
- **Vérifications** — `ruff check src/ tests/` OK ; `pytest` 157 passed (+30 nouveaux).
- **Risques/notes** — last-file-wins sur INE (NULL écrase) documenté et testé ; `label=""` par défaut → rétrocompat totale.
- **Prochaines actions** — Démarrer P2 (dashboard compact vidéoprojeté).

## Session - 2026-04-30

- **Objectif** — Mettre en place la base de customisation agent et de suivi projet.
- **Réalisé** — Ajout de AGENTS.md, `.github/instructions/tests.instructions.md`, PROGRESS.md.
- **Vérifications** — Vérification structurelle des fichiers markdown ; pas de tests exécutés (changement documentaire uniquement).
- **Risques/notes** — Le plan P1/P2/P3 est une projection issue de CLAUDE.md, à ajuster selon les priorités réelles.
- **Prochaines actions** — Prioriser 2 à 3 items P1 ; ajouter une session à chaque fin de travail.

## Règle de mise à jour en fin de session

À la fin de chaque session, ajouter `## Session - YYYY-MM-DD` suivi d'une liste à puces :

```markdown
- **Objectif** — ...
- **Réalisé** — ...
- **Vérifications** — commandes exécutées et résultats.
- **Risques/notes** — ...
- **Prochaines actions** — ...
```

Conserver les anciennes sessions (historique append-only).
