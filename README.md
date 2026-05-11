# Compas

Outil d'évaluation continue des compétences comportementales (*soft skills*) pour les étudiants de BTS SIO SISR.

---

## Table des matières

1. [Description du projet](#1-description-du-projet)
   - [Contexte et objectif](#contexte-et-objectif)
   - [Fonctionnement général](#fonctionnement-général)
   - [Stack technique](#stack-technique)
   - [Structure du projet](#structure-du-projet)
2. [Manuel utilisateur](#2-manuel-utilisateur)
   - [Installation](#installation)
   - [Préparer le fichier Excel](#préparer-le-fichier-excel)
   - [Commandes CLI](#commandes-cli)
   - [Le dashboard](#le-dashboard)

---

## 1. Description du projet

### Contexte et objectif

Dans les classes de BTS SIO SISR, l'évaluation des compétences techniques est bien balisée, mais celle des compétences comportementales — autonomie, rigueur, communication, engagement — reste souvent informelle. **Compas** structure cette évaluation continue tout au long d'un projet.

L'enseignant note ses observations sur une feuille papier en classe, les reporte dans un tableur Excel après la séance, puis génère un dashboard HTML projeté en classe lors du bilan suivant. Les étudiants voient leur progression séance après séance, par critère et globalement.

### Fonctionnement général

```
Feuille papier → Tableur Excel (.xlsx)
                       │
                  poetry run compas import
                       │
                       ▼
                  Base SQLite
                       │
                  poetry run compas dashboard
                       │
                       ▼
                  Dashboard HTML (fichier statique)
```

Chaque fichier Excel correspond à un **projet** (ex. « Infrastructure réseau PME »). Un même étudiant peut participer à plusieurs projets ; Compas dédoublonne automatiquement les entrées. L'import est **destructif** : la base est reconstruite intégralement à chaque exécution, garantissant toujours un état cohérent avec les fichiers source.

Les scores par séance sont lissés par une **moyenne mobile exponentielle (EMA)** qui donne plus de poids aux séances récentes, limitant l'effet des observations isolées. Une tendance (hausse / stable / baisse) et un rang (Or / Argent / Bronze / Alerte) sont calculés pour chaque étudiant.

### Stack technique

| Composant | Rôle |
|-----------|------|
| Python 3.12+ | Langage principal |
| [Poetry](https://python-poetry.org/) | Gestion des dépendances et environnement virtuel |
| [openpyxl](https://openpyxl.readthedocs.io/) | Lecture des fichiers `.xlsx` |
| sqlite3 | Base de données locale (bibliothèque standard Python) |
| [Jinja2](https://jinja.palletsprojects.com/) | Génération du template HTML |
| [Typer](https://typer.tiangolo.com/) | CLI avec complétion automatique |

Aucun serveur web, aucun framework : le résultat est un fichier HTML autonome, lisible hors ligne et projetable directement dans un navigateur.

### Structure du projet

```
compas/
├── pyproject.toml              # Dépendances et configuration
├── src/
│   └── compas/
│       ├── cli.py              # Point d'entrée CLI
│       ├── importer.py         # Lecture xlsx → SQLite
│       ├── ema.py              # Calcul EMA et tendances
│       ├── dashboard.py        # Génération HTML
│       ├── validator.py        # Validation de conformité xlsx
│       └── templates/
│           └── dashboard.html  # Template Jinja2
├── data/                       # Fichiers xlsx (non versionné)
├── output/                     # Fichiers générés (non versionné)
├── scripts/
│   └── generate_test_data.py   # Générateur de données de test
└── tests/
    ├── test_importer.py
    ├── test_ema.py
    ├── test_validator.py
    └── fixtures/
        └── test_projet.xlsx
```

---

## 2. Manuel utilisateur

### Installation

**Prérequis :** Python 3.12 ou supérieur, [Poetry](https://python-poetry.org/docs/#installation).

```bash
# Cloner le dépôt
git clone <url-du-depot>
cd compas

# Installer les dépendances dans un environnement virtuel local
poetry install
```

Vérifier que tout fonctionne :

```bash
poetry run compas --help
```

---

### Éviter de retaper `poetry run`

Toutes les commandes de ce manuel préfixent `poetry run compas …`. Il existe plusieurs façons de s'en affranchir.

#### Option 1 — Activer l'environnement virtuel (session en cours)

Le venv est créé localement dans `.venv/`. Pour l'activer dans votre terminal :

```bash
# Bash / Zsh — méthode directe (venv local)
source .venv/bin/activate

# Ou avec la commande Poetry 2.x (portable quel que soit l'emplacement du venv)
eval "$(poetry env activate)"
```

Une fois activé, `compas` est disponible directement :

```bash
compas build
compas validate data/
compas explain "Dupont"
```

Pour désactiver :

```bash
deactivate
```

#### Option 2 — Activation automatique avec direnv

[direnv](https://direnv.net/) active l'environnement dès que vous entrez dans le dossier du projet.

```bash
# Créer le fichier .envrc à la racine du projet
echo 'source .venv/bin/activate' > .envrc
direnv allow
```

> Nécessite `direnv` installé sur le système (`apt install direnv` / `brew install direnv`).

#### Option 3 — Makefile

Un `Makefile` est fourni avec les commandes courantes. Il s'utilise sans activation préalable :

```bash
make build      # importer + générer le dashboard (ouvre le navigateur)
make validate   # valider les fichiers xlsx
make import     # importer uniquement
make dashboard  # générer le dashboard uniquement
```

`make help` liste toutes les cibles disponibles.

---

### Complétion automatique

Installer la complétion pour bash, zsh ou fish — à faire une fois après avoir activé le venv :

```bash
compas --install-completion
```

---

### Préparer le fichier Excel

Chaque projet est décrit dans un fichier `.xlsx` placé dans le dossier `data/`. Un fichier contient au minimum deux types de feuilles : une feuille **Config** et une ou plusieurs **feuilles de séance**.

#### Feuille « Config »

Cette feuille décrit le projet et liste les étudiants participants.

| Cellule | Contenu |
|---------|---------|
| A1 | `Projet` (libellé fixe) |
| B1 | Nom du projet (ex. `Infrastructure réseau PME`) |
| A2 | `Groupe` (libellé fixe) |
| B2 | Identifiant du groupe (ex. `TP1`) |

**À partir de la ligne 5**, un tableau liste les étudiants (la ligne 4 contient les en-têtes) :

| Colonne | En-tête | Description |
|---------|---------|-------------|
| A | Nom | Nom complet de l'étudiant |
| B | INE | Identifiant national étudiant — clé de croisement entre projets (colonne masquée à l'impression) |
| C | Anonyme | `oui` ou `non` |
| D | Pseudo | Affiché à la place du nom si anonyme = `oui` |
| E | Date de départ | Date de fin de participation (`JJ/MM/AAAA`), laisser vide si l'étudiant est toujours actif |

La lecture s'arrête à la première ligne dont la colonne A est vide.

#### Feuilles de séance

Toute feuille dont le nom n'est pas `Config`, `Modele` / `Modèle` ou ne commence pas par `tmp-` est traitée comme une séance. Le nom est libre (`S1`, `2026-03-27`, `Séance 4`…).

**En-tête (lignes 1–2) :**

| Cellule | Contenu |
|---------|---------|
| A1 | Titre fusionné (ignoré) |
| B2 | Numéro de la séance (entier) |
| D2 | Date de la séance (`JJ/MM/AAAA`) |
| F2 | Heure de début (ex. `8h00`) |
| H2 | Nom de l'enseignant |
| J2 | Heure de fin (ex. `12h00`) |

La ligne 3 est vide. La ligne 4 contient les en-têtes du tableau. La ligne 5 est réservée au rappel des symboles (ignorée).

**À partir de la ligne 6**, un tableau liste les relevés :

| Colonne | Critère | Valeurs acceptées |
|---------|---------|-------------------|
| A | Étudiant | Nom exact (doit correspondre à la feuille Config) |
| B | Présence | voir tableau ci-dessous |
| C | Autonomie | −2, −1, 0, 1, 2 ou vide (non observé) |
| D | Rigueur | idem |
| E | Communication | idem |
| F | Engagement | idem |
| G | Commentaire | Texte libre, optionnel |

**Codes de présence** (syntaxe `TYPE:valeur:motif`, combinaisons par virgule) :

| Code | Signification |
|------|--------------|
| `P` ou vide | Présent toute la séance |
| `A` | Absent toute la séance |
| `A:medical` | Absent avec motif (un mot, sans espace) |
| `A:9h15-10h00` | Absent sur un créneau horaire (présent sinon) |
| `A:H1-H2` | Absent sur les créneaux H1 et H2 |
| `R:15` | Retard de 15 minutes en début de cours |
| `R:9h30` | Arrivée à 9h30 (retard calculé depuis l'heure de début) |
| `RR:10` | Retard de 10 minutes après la récréation |
| `D:10h15` | Départ définitif à 10h15 (présent au début) |
| `N` | Note sur la feuille papier — consulter le scan |
| `R:5,RR:10` | Combinaison : retard début + retard après récré |

Chaque token peut recevoir un motif optionnel : `R:9h30:transport`, `D:10h15:medical`.

**Échelle des scores :**

| Symbole papier | Valeur tableur | Interprétation |
| ------------- | ------------- | -------------- |
| `++` | `2` | Très au-dessus des attentes |
| `+` | `1` | Au-dessus des attentes |
| `=` | `0` | Conforme aux attentes |
| `-` | `−1` | En dessous des attentes |
| `--` | `−2` | Très en dessous des attentes |
| *(rien)* | vide | Non observé — la séance est ignorée dans le calcul de la moyenne |

#### Feuilles ignorées

Compas ignore silencieusement les feuilles suivantes :

- `Config` (réservée aux métadonnées)
- `Modele` et `Modèle` (feuille modèle, insensible aux accents)
- Toute feuille dont le nom commence par `tmp-` (insensible à la casse)

---

### Commandes CLI

#### Vérifier la conformité des fichiers Excel

```bash
poetry run compas validate data/
```

Analyse chaque fichier `.xlsx` et signale les erreurs (bloquantes) et avertissements (non bloquants) : colonnes manquantes, format d'INE incorrect, présence non reconnue, scores hors plage, etc. Code retour `0` si aucune erreur, `1` sinon.

| Option | Description |
|--------|-------------|
| `FILE_OR_DIR …` | Un ou plusieurs fichiers `.xlsx` ou dossiers à analyser |
| `--strict` | Traiter les avertissements comme des erreurs |

#### Importer les fichiers Excel dans la base

```bash
poetry run compas import
```

Lit tous les fichiers `.xlsx` du dossier `data/`, reconstruit la base SQLite et affiche un résumé sur la sortie d'erreur.

| Option | Défaut | Description |
|--------|--------|-------------|
| `--data DIR` | `data/` | Dossier contenant les fichiers `.xlsx` |
| `--db FILE` | `output/compas.db` | Chemin de la base SQLite à créer ou recréer |

L'option `-v / --verbose` est **globale** et se place avant la sous-commande :

```bash
poetry run compas -v import
```

#### Générer le dashboard HTML

```bash
poetry run compas dashboard
```

Lit la base SQLite, calcule les EMA, tendances et rangs, et écrit le fichier HTML.

| Option | Défaut | Description |
|--------|--------|-------------|
| `--db FILE` | `output/compas.db` | Chemin de la base SQLite |
| `--out FILE` | `output/dashboard.html` | Fichier HTML de sortie |
| `--alpha ALPHA` | `0.4` | Coefficient de lissage EMA (entre 0 et 1) |
| `--open` | — | Ouvrir le dashboard dans le navigateur après génération |

#### Tout en une commande

```bash
poetry run compas build
```

Enchaîne l'import et la génération du dashboard. Accepte les mêmes options que `import` et `dashboard`.

#### Expliquer le calcul EMA d'un étudiant

```bash
poetry run compas explain "Dupont"
```

Génère un rapport Markdown qui détaille pas à pas le calcul de l'EMA pour chaque critère d'un étudiant. Utile pour justifier un rang auprès de l'étudiant ou vérifier un calcul.

La recherche est insensible à la casse et accepte un fragment de nom :

```bash
# Fragment suffisant
poetry run compas explain "dup"

# Nom complet entre guillemets si le nom contient des espaces
poetry run compas explain "Dupont Arthur"
```

Si plusieurs étudiants correspondent au fragment, la commande liste les correspondances et s'arrête.

Le rapport est écrit dans `output/explain_<nom>.md` par défaut. Exemple de contenu :

```markdown
## Autonomie

| Séance | Date       | Valeur | Calcul                    | EMA       |
| ------ | ---------- | ------ | ------------------------- | --------- |
| S1     | 15/01/2026 | +1     | initialisation            | **1.000** |
| S2     | 22/01/2026 | —      | non observé               | 1.000     |
| S3     | 29/01/2026 | +2     | 0.4 × 2.00 + 0.6 × 1.000 | **1.400** |
| S4     | 05/02/2026 | 0      | 0.4 × 0.00 + 0.6 × 1.400 | **0.840** |

**EMA finale : 0.840**
```

| Option | Défaut | Description |
|--------|--------|-------------|
| `NOM` | — | Nom ou fragment de nom de l'étudiant |
| `--db FILE` | `output/compas.db` | Chemin de la base SQLite |
| `--out FILE` | `output/explain_<nom>.md` | Fichier Markdown de sortie |
| `--alpha ALPHA` | `0.4` | Coefficient de lissage EMA (entre 0 et 1) |

---

### Le dashboard

Ouvrir `output/dashboard.html` dans un navigateur — aucun serveur requis.

Les cartes sont affichées par **ordre alphabétique**. Le dashboard affiche une **carte par étudiant actif** avec :

- Son nom (ou pseudo si anonyme)
- Un histogramme vertical des 4 critères (Autonomie, Rigueur, Communication, Engagement) avec la valeur EMA courante
- Une flèche de tendance (↑ hausse / → stable / ↓ baisse) basée sur la comparaison avec la séance précédente
- Un **rang** calculé sur la moyenne des 4 EMA :

| Rang | Seuil (EMA moyen) |
|------|------------------|
| Or | ≥ 0,70 |
| Argent | ≥ 0,25 |
| Bronze | ≥ −0,25 |
| Alerte | < −0,25 |

- Des statistiques de présence (séances totales, absences, retards, cumul des minutes de retard)

Le thème clair/sombre suit automatiquement le réglage système de l'appareil (`prefers-color-scheme`).
