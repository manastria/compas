# Compas — Évaluation continue des soft skills

## Présentation

Compas est un outil d'évaluation continue des compétences comportementales (soft skills) pour les étudiants de BTS SIO SISR. L'enseignant saisit ses observations sur une feuille papier en classe, les reporte dans un tableur Excel, puis un script Python consolide les données dans une base SQLite et génère un dashboard HTML statique projeté en classe.

## Stack technique

- **Python 3.12+** avec Poetry pour la gestion des dépendances
- **openpyxl** : lecture des fichiers `.xlsx`
- **sqlite3** : base de données (bibliothèque standard)
- **Jinja2** : moteur de template pour la génération HTML
- **Typer** : CLI avec complétion automatique des sous-commandes
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
│       ├── validator.py        # Validation de conformité des fichiers xlsx
│       └── templates/
│           └── dashboard.html  # Template Jinja2
├── data/                       # Fichiers xlsx (non versionné, dans .gitignore)
│   └── *.xlsx
├── output/                     # Fichiers générés (non versionné)
│   ├── compas.db
│   └── dashboard.html
├── scripts/
│   └── generate_test_data.py   # Générateur de données de test (Faker)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_importer.py
    ├── test_ema.py
    ├── test_validator.py
    └── fixtures/
        └── test_projet.xlsx    # Fichier xlsx de test
```

## CLI

Le CLI est construit avec **Typer**. L'option globale `-v / --verbose` se place avant la sous-commande. La complétion automatique s'installe avec `--install-completion`.

Les chemins par défaut sont `data/` pour les xlsx, `output/compas.db` pour la base et `output/dashboard.html` pour le dashboard — les options restent disponibles pour surcharger :

```bash
# Installer la complétion automatique (à faire une fois, bash/zsh/fish)
compas --install-completion

# Vérifier la conformité des fichiers xlsx avant import
poetry run compas validate data/

# Importer tous les xlsx du dossier data/ dans la base SQLite
poetry run compas import

# Générer le dashboard HTML depuis la base
poetry run compas dashboard

# Les deux à la suite (raccourci)
poetry run compas build

# Mode verbeux (flag global avant la sous-commande)
poetry run compas -v build

# Exemple avec chemins personnalisés
poetry run compas build --data autre/dir --db autre/base.db --out autre/out.html
```

Le point d'entrée est défini dans `pyproject.toml` :

```toml
[project.scripts]
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
| B | INE | texte | Identifiant national étudiant (clé de croisement inter-projets, colonne masquée à l'impression) |
| C | Anonyme | texte | « oui » ou « non » |
| D | Pseudo | texte | Pseudo pour le dashboard (si anonyme = oui) |
| E | Date de départ | date ou texte | Date de démission, vide si actif |

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
| I2 | Libellé « Heure fin » |
| J2 | Heure de fin du cours (texte, ex : « 12h00 ») |

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
    ine TEXT UNIQUE,               -- identifiant national étudiant
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
    heure_fin TEXT,      -- ex : "12h00"
    enseignant TEXT,
    presence TEXT,        -- syntaxe TYPE:valeur:motif, combinaisons par virgule
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

Un même étudiant peut apparaître dans plusieurs fichiers xlsx (plusieurs projets). La table `etudiants` ne doit contenir qu'une seule entrée par nom. En cas de conflit sur les champs `ine`, `anonyme`, `pseudo` ou `date_depart`, la valeur la plus récente (dernier fichier lu) prévaut. L'INE sert de clé de croisement avec les autres projets (ex : Assiduité) ; son unicité est garantie par la contrainte `UNIQUE` SQLite.

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

Le pattern est uniforme : `LETTRE:valeur:motif`. Le `:` est le séparateur systématique entre le type, la valeur et le motif optionnel. Les combinaisons utilisent la virgule comme séparateur.

**Éléments simples :**

| Syntaxe | Signification |
|---------|---------------|
| *(vide)* ou `P` | Présent toute la séance |
| `A` | Absent toute la séance |
| `A:motif` | Absent toute la séance avec motif |
| `A:H1-H2` | Absent heures 1-2 |
| `A:H1-H2:motif` | Absent heures 1-2 avec motif |
| `A:9h15-10h00` | Absent de 9h15 à 10h00 (départ temporaire + retour) |
| `A:9h15-10h00:motif` | Idem avec motif |
| `R:15` | Retard de 15 min en début de cours |
| `R:9h30` | Arrivée tardive à 9h30 |
| `R:9h30:motif` | Arrivée tardive avec motif |
| `RR:10` | Retard de 10 min après la récréation |
| `RR:10:motif` | Idem avec motif |
| `D:10h15` | Départ définitif à 10h15 |
| `D:10h15:motif` | Départ définitif avec motif |
| `N` | Note sur la feuille papier — consulter le scan |

**Combinaisons (séparateur virgule) :**

| Syntaxe | Signification |
|---------|---------------|
| `R:5,RR:10` | Retard début + retard après récré |
| `R:10,D:11h30:medical` | Retard début + départ anticipé |
| `A:H1-H2,RR:5` | Absent H1-H2 + retard après récré |
| `R:5,N` | Retard de 5 min + note sur la feuille |

**Règles :** motif = un mot unique sans espace. Créneaux = `H1`, `H2`, `H3`, `H4` ou format `XhYY`. `N` peut apparaître seul ou combiné. Si la situation est trop complexe, `N` seul suffit.

**Interprétation pour les statistiques :**

- `A` ou `A:motif` (motif sans plage) → absent toute la séance
- `A:H1-H2` ou `A:XhYY-XhYY` → absence partielle, compté comme présent
- `R:N` ou `RR:N` → présent avec retard, N = minutes
- `R:XhYY` → retard calculé depuis `heure_debut`
- `D:XhYY` → présent (départ anticipé, était là au début)
- `N` → présent (détail sur la feuille papier)
- Combinaisons : absent si l'un des tokens donne `A` sans plage, sinon présent ; minutes de retard cumulées

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
4. Trie les étudiants par ordre alphabétique (`name.casefold()`).
5. Injecte les données dans le template Jinja2 sous forme de JSON dans une balise `<script>`.
6. Écrit le fichier HTML de sortie.

Le template HTML est celui du dashboard compact (grille responsive, cartes avec histogrammes verticaux). Le JavaScript dans le template lit le JSON et génère les cartes côté client.

### Données injectées

```javascript
var COMPAS_DATA = {
  projet: "Infrastructure réseau PME",
  groupe: "TP1",
  seance_actuelle: 4,
  seances_total: 6,
  date: "27/03/2026",
  heure_debut: "8h00",
  heure_fin: "12h00",
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

## Évolutions prévues

- **Projet Assiduité** : projet frère avec la même stack technique, syntaxe de présence partagée, croisement des données par INE
- **Dashboard compact vidéoprojeté** : grille de cartes avec histogrammes verticaux (en cours)
- **Fiche individuelle par étudiant** : vue détaillée avec historique des séances
- **Rangs gamifiés** : seuils et badges à définir

## Ce qui est hors scope pour la v1

- Interface web / serveur
- Commutateur dark mode dans le dashboard (utilise `prefers-color-scheme` du système)
- Fiche individuelle par étudiant
- Gamification avancée (badges spéciaux, objectifs de groupe)
- Traduction en note semestrielle
- Impact de la présence sur les scores
