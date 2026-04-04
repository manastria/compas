# Compas — Évaluation continue des soft skills

## Présentation

Compas est un outil d'évaluation continue des compétences comportementales (soft skills) pour les étudiants de BTS SIO SISR. L'enseignant saisit ses observations sur une feuille papier en classe, les reporte dans un tableur Excel, puis un script Python consolide les données dans une base SQLite et génère un dashboard HTML statique projeté en classe.

## Stack technique

- **Python 3.12+** avec Poetry pour la gestion des dépendances
- **openpyxl** : lecture des fichiers `.xlsx`
- **sqlite3** : base de données (bibliothèque standard)
- **Jinja2** : moteur de template pour la génération HTML
- Aucun serveur web, aucun framework — fichiers statiques uniquement

## Structure du projet

```
compas/
├── CLAUDE.md
├── pyproject.toml
├── README.md
├── src/
│   └── compas/
│       ├── __init__.py
│       ├── cli.py              # Point d'entrée CLI
│       ├── importer.py         # Lecture xlsx → SQLite
│       ├── ema.py              # Calcul EMA et tendances
│       ├── dashboard.py        # Génération HTML depuis SQLite
│       └── templates/
│           └── dashboard.html  # Template Jinja2
├── data/                       # Fichiers xlsx (non versionné, dans .gitignore)
│   └── *.xlsx
├── output/                     # Fichiers générés (non versionné)
│   ├── compas.db
│   └── dashboard.html
└── tests/
    ├── __init__.py
    ├── test_importer.py
    ├── test_ema.py
    └── fixtures/
        └── test_projet.xlsx    # Fichier xlsx de test
```

## CLI

Deux commandes principales via un unique point d'entrée :

```bash
# Importer tous les xlsx du dossier data/ dans la base SQLite
poetry run compas import --data data/ --db output/compas.db

# Générer le dashboard HTML depuis la base
poetry run compas dashboard --db output/compas.db --out output/dashboard.html

# Les deux à la suite (raccourci)
poetry run compas build --data data/ --db output/compas.db --out output/dashboard.html
```

Le point d'entrée est défini dans `pyproject.toml` :

```toml
[tool.poetry.scripts]
compas = "compas.cli:main"
```

## Structure du fichier xlsx

### Feuille « Config »

Contient les métadonnées du projet et la liste des étudiants.

**Cellules d'en-tête :**

| Cellule | Contenu |
|---------|---------|
| A1 | Libellé « Projet » |
| B1 | Nom du projet (ex : « Infrastructure réseau PME ») |
| A2 | Libellé « Groupe » |
| B2 | Nom du groupe (ex : « TP1 ») |

**Table des étudiants** (à partir de la ligne 4) :

| Colonne | En-tête (ligne 4) | Type | Description |
|---------|-------------------|------|-------------|
| A | Nom | texte | Nom complet de l'étudiant |
| B | Anonyme | texte | « oui » ou « non » |
| C | Pseudo | texte | Pseudo pour le dashboard (si anonyme = oui) |
| D | Date de départ | date ou texte | Date de démission, vide si actif |

La lecture s'arrête à la première ligne où la colonne A est vide.

### Feuilles de séance

Toute feuille qui n'est **pas** nommée `Config`, `Modele`, `Modèle`, ou préfixée `tmp-` est considérée comme une feuille de séance. Le nom de la feuille est libre (ex : `S1`, `2026-03-27`, `Séance 4`).

**En-tête (lignes 1-2) :**

| Cellule | Contenu |
|---------|---------|
| A1:H1 | Titre fusionné « COMPAS — Relevé de séance » (ignoré par le parser) |
| A2 | Libellé « Séance n° » |
| B2 | Numéro de séance (entier) |
| C2 | Libellé « Date » |
| D2 | Date de la séance (date Excel ou texte DD/MM/YYYY) |
| E2 | Libellé « Heure début » |
| F2 | Heure de début du cours (texte, ex : « 8h00 ») |
| G2 | Libellé « Enseignant » |
| H2 | Nom de l'enseignant |

**Ligne 3** : vide (espacement).

**Ligne 4** : en-têtes du tableau (Étudiant, Présence, Autonomie, Rigueur, Communication, Engagement, Commentaire).

**Ligne 5** : rappel des symboles (ignoré par le parser).

**Lignes 6+** : données étudiants.

| Colonne | En-tête | Type | Valeurs possibles |
|---------|---------|------|-------------------|
| A | Étudiant | texte | Nom de l'étudiant |
| B | Présence | texte | `P`, `A`, `R` + minutes (ex : `R15`), heure (ex : `9h30`), vide = présent |
| C | Autonomie | entier ou vide | −2, −1, 0, 1, 2 ou vide (non observé) |
| D | Rigueur | entier ou vide | idem |
| E | Communication | entier ou vide | idem |
| F | Engagement | entier ou vide | idem |
| G | Commentaire | texte ou vide | Texte libre |

La lecture des lignes étudiants s'arrête à la première ligne où la colonne A est vide.

### Feuilles ignorées

Le script d'import ignore silencieusement :

- La feuille nommée exactement `Config`
- La feuille nommée `Modele` ou `Modèle` (insensible aux accents)
- Toute feuille dont le nom commence par `tmp-` (insensible à la casse)

## Schéma SQLite

```sql
CREATE TABLE IF NOT EXISTS etudiants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    groupe TEXT,
    anonyme INTEGER NOT NULL DEFAULT 0,  -- 0 = non, 1 = oui
    pseudo TEXT,
    date_depart TEXT  -- format ISO YYYY-MM-DD, NULL si actif
);

CREATE TABLE IF NOT EXISTS projets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    groupe TEXT
);

CREATE TABLE IF NOT EXISTS releves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    etudiant_id INTEGER NOT NULL REFERENCES etudiants(id),
    projet_id INTEGER NOT NULL REFERENCES projets(id),
    seance INTEGER NOT NULL,
    date TEXT NOT NULL,  -- format ISO YYYY-MM-DD
    heure_debut TEXT,    -- ex : "8h00"
    enseignant TEXT,
    presence TEXT,        -- P, A, R15, 9h30, etc.
    autonomie INTEGER,   -- -2 à +2, NULL si non observé
    rigueur INTEGER,
    communication INTEGER,
    engagement INTEGER,
    commentaire TEXT,
    UNIQUE(etudiant_id, projet_id, seance)
);
```

### Import destructif

L'import reconstruit intégralement la base à chaque exécution :

1. Supprimer les tables existantes (`DROP TABLE IF EXISTS`).
2. Recréer le schéma.
3. Lire chaque fichier `.xlsx` du dossier `data/`.
4. Pour chaque fichier : lire Config → créer le projet et les étudiants, puis lire les feuilles de séance → insérer les relevés.

La correspondance étudiant se fait par **nom exact** entre la feuille Config et les feuilles de séance. Si un nom de séance ne correspond à aucun étudiant de Config, émettre un avertissement sur stderr sans interrompre l'import.

### Dédoublonnage des étudiants

Un même étudiant peut apparaître dans plusieurs fichiers xlsx (plusieurs projets). La table `etudiants` ne doit contenir qu'une seule entrée par nom. En cas de conflit sur les champs `anonyme`, `pseudo` ou `date_depart`, la valeur la plus récente (dernier fichier lu) prévaut.

## Calcul EMA (Exponential Moving Average)

Pour chaque étudiant et chaque critère, la moyenne est calculée avec une pondération exponentielle qui donne plus de poids aux séances récentes.

### Formule

```
EMA(1) = valeur de la première séance observée
EMA(n) = α × valeur(n) + (1 − α) × EMA(n−1)
```

- **α = 0.4** par défaut (configurable via `--alpha` en CLI)
- Les séances sont triées par numéro croissant
- Les valeurs NULL (non observé) sont **ignorées** : on passe à la séance suivante sans mettre à jour l'EMA
- Si un étudiant n'a aucune valeur observée pour un critère, l'EMA est NULL

### Tendance

La tendance compare l'EMA actuelle à l'EMA de la séance précédente (qui avait une valeur observée) :

- **up** : EMA actuelle > EMA précédente + 0.05 (seuil pour éviter le bruit)
- **down** : EMA actuelle < EMA précédente − 0.05
- **stable** : sinon

### Rangs

Calculés sur la moyenne des 4 EMA (autonomie, rigueur, communication, engagement) :

| Rang | Condition | Seuil par défaut |
|------|-----------|-----------------|
| Or | moyenne ≥ seuil_or | 0.70 |
| Argent | moyenne ≥ seuil_argent | 0.25 |
| Bronze | moyenne ≥ seuil_bronze | −0.25 |
| Alerte | moyenne < seuil_bronze | — |

Les seuils sont configurables. Si un critère a un EMA NULL, il est exclu du calcul de la moyenne globale.

## Présence

### Parsing

| Valeur brute | Interprétation |
|-------------|----------------|
| `P` ou vide | Présent, 0 min de retard |
| `A` | Absent |
| `R` suivi de chiffres (ex : `R15`, `R5`) | Retard, extraire les minutes |
| Format heure `Xh`, `XhYY` (ex : `9h30`, `10h`) | Retard, calculer les minutes depuis l'heure de début de la séance |

### Statistiques affichées

Pour chaque étudiant sur un projet :

- Nombre de séances total
- Nombre de présences (P + retards)
- Nombre d'absences
- Nombre de retards
- Cumul des minutes de retard

## Génération du dashboard

### Template Jinja2

Le script `dashboard.py` :

1. Lit la base SQLite.
2. Filtre les étudiants actifs (date_depart NULL ou date_depart > date de la dernière séance).
3. Calcule les EMA, tendances, rangs, statistiques de présence.
4. Injecte les données dans le template Jinja2 sous forme de JSON dans une balise `<script>`.
5. Écrit le fichier HTML de sortie.

Le template HTML est celui du dashboard compact (grille responsive, cartes avec histogrammes verticaux). Le JavaScript dans le template lit le JSON et génère les cartes côté client.

### Données injectées

```javascript
var COMPAS_DATA = {
  projet: "Infrastructure réseau PME",
  groupe: "TP1",
  seance_actuelle: 4,
  seances_total: 6,
  date: "27/03/2026",
  alpha: 0.4,
  students: [
    {
      name: "Dupont A.",
      display_name: "Dupont A.",  // pseudo si anonyme
      anon: false,
      scores: { auto: 0.6, rig: 0.4, com: 0.8, eng: 0.5 },
      trend: "up",
      rank: "or",
      presence: { total: 4, present: 4, absent: 0, retards: 0, min_retard: 0 }
    }
  ]
};
```

## Conventions de code

- **Langue du code** : noms de variables et fonctions en anglais, commentaires en français si nécessaire
- **Docstrings** : en français, format Google style
- **Type hints** : obligatoires sur toutes les fonctions publiques
- **Logging** : utiliser le module `logging` standard, pas de `print`
- **Erreurs** : les erreurs de parsing (cellule inattendue, format inconnu) émettent un warning et continuent. Seules les erreurs structurelles (fichier illisible, Config manquante) sont fatales.
- **Tests** : pytest, un fichier xlsx de fixture dans `tests/fixtures/`
- **Formatage** : ruff (lint + format)

## Ce qui est hors scope pour la v1

- Interface web / serveur
- Commutateur dark mode dans le dashboard (utilise `prefers-color-scheme` du système)
- Fiche individuelle par étudiant
- Gamification avancée (badges spéciaux, objectifs de groupe)
- Traduction en note semestrielle
- Impact de la présence sur les scores
