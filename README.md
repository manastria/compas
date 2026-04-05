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
│       └── templates/
│           └── dashboard.html  # Template Jinja2
├── data/                       # Fichiers xlsx (non versionné)
├── output/                     # Fichiers générés (non versionné)
└── tests/
    ├── test_importer.py
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
| B | Anonyme | `oui` ou `non` |
| C | Pseudo | Affiché à la place du nom si anonyme = `oui` |
| D | Date de départ | Date de fin de participation (`JJ/MM/AAAA`), laisser vide si l'étudiant est toujours actif |

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

**Codes de présence :**

| Code | Signification |
|------|--------------|
| `P` ou vide | Présent |
| `A` | Absent |
| `R15` | Retard de 15 minutes |
| `9h30` | Arrivée à 9h30 (le retard est calculé depuis l'heure de début de séance) |

**Échelle des scores :**

| Valeur | Interprétation |
|--------|---------------|
| `2` | Très au-dessus des attentes |
| `1` | Au-dessus des attentes |
| `0` | Conforme aux attentes |
| `−1` | En dessous des attentes |
| `−2` | Très en dessous des attentes |
| vide | Non observé — la séance est ignorée dans le calcul de la moyenne |

#### Feuilles ignorées

Compas ignore silencieusement les feuilles suivantes :

- `Config` (réservée aux métadonnées)
- `Modele` et `Modèle` (feuille modèle, insensible aux accents)
- Toute feuille dont le nom commence par `tmp-` (insensible à la casse)

---

### Commandes CLI

#### Importer les fichiers Excel dans la base

```bash
poetry run compas import
```

Lit tous les fichiers `.xlsx` du dossier `data/`, reconstruit la base SQLite et affiche un résumé sur la sortie d'erreur.

| Option | Défaut | Description |
|--------|--------|-------------|
| `--data DIR` | `data/` | Dossier contenant les fichiers `.xlsx` |
| `--db FILE` | `output/compas.db` | Chemin de la base SQLite à créer ou recréer |
| `-v` | — | Mode verbeux (détail de chaque feuille traitée) |

#### Générer le dashboard HTML

```bash
poetry run compas dashboard
```

Lit la base SQLite, calcule les EMA, tendances et rangs, et écrit le fichier HTML.

| Option | Défaut | Description |
|--------|--------|-------------|
| `--db FILE` | `output/compas.db` | Chemin de la base SQLite |
| `--out FILE` | `output/dashboard.html` | Fichier HTML de sortie |

#### Tout en une commande

```bash
poetry run compas build
```

Enchaîne l'import et la génération du dashboard.

---

### Le dashboard

Ouvrir `output/dashboard.html` dans un navigateur — aucun serveur requis.

Le dashboard affiche une **carte par étudiant actif** avec :

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
