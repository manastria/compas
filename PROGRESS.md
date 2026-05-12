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
- [ ] **Fiche globale par étudiant** (évolution A — décision tranchée le
  2026-05-11, voir [docs/fiche_multi_projets.md](docs/fiche_multi_projets.md)) :
  - Génération d'une fiche globale supplémentaire au top-level de
    `output/fiches/` pour les étudiants participant à plusieurs projets.
  - Badge « Vue globale » dans l'en-tête du template `fiche.html`.
  - Colonne « Projet » dans le tableau « Détail des séances » de la fiche
    globale, avec le nom du projet rendu comme lien vers la fiche
    individuelle de l'étudiant dans ce projet
    (`./<slug_projet>/fiche_<slug_etudiant>.html`).
  - L'évolution B (fiche unifiée à onglets / sections empilées) est
    **abandonnée**.

## Hors scope v1 (garde-fous)

- [ ] Pas de serveur web
- [ ] Pas de dark mode custom (prefers-color-scheme uniquement)
- [ ] Pas de traduction en note semestrielle
- [ ] Pas d’impact de la présence sur les scores

## Journal de session

## Session - 2026-05-12

- **Objectif** — Étendre `scripts/git-publish.sh` pour exclure aussi des fichiers et permettre une inspection avant commit.
- **Réalisé** — Ajout du parsing d'options `--exclude`/`-x` répétable pour exclure fichiers ou répertoires ; ajout de `--stop-before-commit` qui quitte après les exclusions et affiche les commandes pour abandonner la publication puis revenir à `dev` ; conservation du message de publication en argument positionnel.
- **Vérifications** — `bash -n scripts/git-publish.sh` OK ; `bash scripts/git-publish.sh --help` OK.
- **Risques/notes** — Le script n'a pas été exécuté en publication réelle pour éviter tout changement de branche/commit/push.
- **Prochaines actions** — Tester `--stop-before-commit` lors de la prochaine publication réelle avec un fichier exclu.

## Session - 2026-05-11 (P3 — Décision fiche globale multi-projets)

- **Objectif** — Trancher entre les deux pistes documentées dans `docs/fiche_multi_projets.md` (fiche globale vs fiche unifiée à onglets).
- **Réalisé** — Mise à jour de [docs/fiche_multi_projets.md](docs/fiche_multi_projets.md) : évolution A retenue (fiche globale lisible + badge « Vue globale »), évolution B abandonnée (onglets/sections empilées jugés moins lisibles, surtout à l'impression) ; ajout d'une nouvelle section dédiée à la colonne « Projet » à insérer dans le tableau « Détail des séances » de la fiche globale, avec lien vers `./<slug_projet>/fiche_<slug_etudiant>.html` pour permettre le « zoom » sur une fiche projet ; mise à jour de la rubrique P3 du PROGRESS.md.
- **Vérifications** — Pas de tests exécutés (changement documentaire uniquement) ; lecture croisée du doc et du PROGRESS.md.
- **Risques/notes** — Implémentation déléguée à une session ultérieure (Sonnet) ; côté code, `compute_student_data(projet_id=None)` devra propager le projet sur chaque entrée de `history`, et le template `fiche.html` devra conditionner la colonne « Projet » sur un drapeau `is_global` pour ne pas polluer les fiches par projet ; le slug doit rester aligné avec celui de `generate_all_fiches()` pour que les liens tombent juste.
- **Prochaines actions** — Implémenter la fiche globale + colonne « Projet » avec lien (session ultérieure).

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
