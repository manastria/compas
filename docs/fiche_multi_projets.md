# Fiches individuelles en contexte multi-projets

Ce document détaille deux évolutions candidates de la fiche individuelle
(`compas fiches`) à envisager quand la base contient plusieurs projets pour
un même étudiant (typiquement : `Infrastructure réseau PME` + `Assiduité`).

**Décision (2026-05-11)** : l'**évolution A** (fiche globale en complément
des fiches par projet) est **retenue** ; l'**évolution B** (fiche unifiée à
onglets) est **abandonnée**. Une fiche globale lisible est préférée à une
fiche unique compactée par onglets ou par listes empilées. Les fiches par
projet existantes restent disponibles pour « zoomer » sur un projet.

Voir aussi la section [Colonne Projet dans le tableau des séances](#colonne-projet-dans-le-tableau-des-séances-de-la-fiche-globale)
pour le seul point d'évolution restant à implémenter.

## État actuel (rappel)

Implémenté dans [src/compas/fiche.py](../src/compas/fiche.py) :

- Une fiche **par projet** par étudiant.
  - Mono-projet : `output/fiches/fiche_<slug>.html`.
  - Multi-projets : `output/fiches/<slug_projet>/fiche_<slug>.html`.
- L'EMA, l'historique, les stats de présence sont calculés sur les seuls
  relevés du projet ciblé (`compute_student_data(projet_id=…)`).
- La section « Projets » du template affiche un mini-tableau de rang/tendance
  par projet quand l'étudiant en a plusieurs (utile pour situer le projet
  courant par rapport aux autres).

CLI :

```bash
compas fiches                    # une fiche par projet, par étudiant
compas fiches --projet "Infra"   # uniquement le projet "Infra"
compas fiches --name Dupont      # uniquement Dupont (tous ses projets)
```

## Évolution A — Fiche individuelle globale

**Cas d'usage** : conseil de classe, entretien individuel, dossier de fin
d'année. On veut **un seul document** par étudiant qui rassemble toute
l'information disponible sur lui, tous projets confondus.

### Ce que c'est concrètement

Une fiche supplémentaire générée **en plus** des fiches par projet, où
toutes les métriques sont calculées sur l'ensemble des relevés de
l'étudiant (tous projets, triés chronologiquement par date).

Layout cible :

```text
output/fiches/
├── fiche_<slug>.html              ← global (toute l'année, tous projets)
├── infrastructure_reseau_pme/
│   └── fiche_<slug>.html          ← projet 1
└── assiduite/
    └── fiche_<slug>.html          ← projet 2
```

En mono-projet, rien ne change : la fiche unique au top-level *est* déjà la
fiche globale (puisque global = unique projet).

### Faisabilité

**Très faible coût**. La fonction `compute_student_data(projet_id=None)`
produit déjà exactement cet agrégat — c'était le comportement historique
avant l'option 1. Il suffit d'ajouter une passe au top-level dans
`generate_all_fiches()` quand on est en multi-projets sans filtre.

Le template `fiche.html` actuel marche tel quel :

- `student.presence` agrège les présences de tous les projets.
- Les EMA et tendances suivent la séquence chronologique de tous les
  relevés (un mauvais score en projet A pèse sur l'EMA suivante observée en
  projet B — c'est le sens même de la vue « globale »).
- La section « Projets » (qui existe déjà côté template) se peuple
  automatiquement avec le rang et la tendance par projet, exactement ce
  qu'on veut en conseil de classe.

### Limites / questions ouvertes

1. **Sens de l'EMA globale** : agréger un projet « Infrastructure » et un
   projet « Assiduité » dans une même EMA suppose que les critères mesurés
   sont commensurables d'un projet à l'autre. C'est probablement OK pour
   les 4 critères soft skills (Autonomie/Rigueur/Communication/Engagement),
   moins évident si un futur projet introduit des critères différents.
2. **Identification visuelle** : rien dans le template ne dit « ceci est
   la vue globale ». On distingue par le chemin de fichier seulement.
   Si on imprime la fiche pour un conseil de classe, le lecteur ne saura
   pas qu'elle agrège plusieurs projets. Pistes : ajouter un badge
   « Vue globale » / « Projet : X » dans l'en-tête, ou laisser tel quel
   et différencier par le titre de l'onglet du navigateur.
3. **Numéros de séance** : actuellement, en mode multi-projets,
   `compute_student_data(projet_id=None)` utilise l'index énuméré
   (`S1`, `S2`, …) au lieu du numéro de séance brut, pour éviter les
   doublons (deux projets ayant chacun une `S1`). Garder ce comportement.
4. **Volume** : un étudiant participant à N projets aura N+1 fiches. Pour
   une promo de 30 étudiants × 3 projets, ça fait ~120 fichiers HTML.
   Pas un problème technique mais une éventuelle source de confusion en
   classe (« quelle fiche je projette ? »). Une mini-page d'index par
   étudiant listant ses fiches pourrait aider (hors scope ici).

### Décisions arrêtées (2026-05-11)

- **Implémenter ?** **Oui** — retenue comme l'évolution principale.
- **Badge « Vue globale » dans l'en-tête du template ?** **Oui**.
- **Page d'index par étudiant ?** **Non**.
- **Colonne « Projet » dans le tableau « Détail des séances » de la fiche
  globale, avec lien vers la fiche individuelle du projet** : **Oui** —
  voir la section dédiée ci-dessous.

## Colonne Projet dans le tableau des séances de la fiche globale

Sur la fiche globale uniquement (pas les fiches par projet, où l'info serait
redondante), ajouter une colonne « Projet » dans le tableau « Détail des
séances ». L'objectif : pouvoir « zoomer » sur la fiche par projet
correspondant à une séance donnée d'un simple clic.

### Comportement attendu

- La fiche globale liste toutes les séances de l'étudiant, tous projets
  confondus, triées chronologiquement.
- Chaque ligne du tableau « Détail des séances » porte une nouvelle colonne
  « Projet » indiquant le nom du projet de la séance.
- Le nom du projet est rendu comme un lien hypertexte vers la fiche
  individuelle de cet étudiant dans ce projet, soit
  `./<slug_projet>/fiche_<slug_etudiant>.html` (chemin relatif depuis
  `output/fiches/`).
- Sur les fiches par projet, le tableau reste inchangé (pas de colonne
  « Projet », puisque toutes les séances appartiennent au même projet).

### Implications côté données et template

- `compute_student_data(projet_id=None)` doit propager le `projet_id` (et
  un slug ou nom utilisable comme libellé / pour construire l'URL) sur
  chaque entrée de `history`.
- Le slug du projet doit être identique à celui utilisé par
  `generate_all_fiches()` pour nommer le sous-dossier de la fiche par
  projet, afin que le lien tombe juste.
- Le template `fiche.html` doit conditionner l'affichage de la colonne
  « Projet » sur la présence d'un drapeau « vue globale » dans le JSON
  (par exemple `is_global: true`), pour éviter de polluer les fiches par
  projet.

### Limites / questions ouvertes

- Si l'étudiant n'a participé qu'à un seul projet, la fiche globale n'est
  pas générée (mono-projet = la fiche unique top-level *est* déjà la fiche
  globale), donc la question ne se pose pas.
- Si un projet est ultérieurement supprimé de la base mais que la fiche
  HTML correspondante n'est pas régénérée, les liens vers ce projet
  pointeraient vers un fichier obsolète. Acceptable : `compas build`
  régénère toute la sortie, et l'utilisateur reconstruit l'ensemble en une
  commande.

## Évolution B — Fiche unifiée multi-projets (option 2 originelle, abandonnée)

**Cas d'usage** : on veut **une seule fiche par étudiant**, qui présente
proprement les données projet par projet à l'intérieur du même document
(scores, tendances, historique propres à chaque projet), plus une
synthèse globale clairement marquée. Pas de duplication de fichiers.

### Ce que c'est concrètement

Restructurer `COMPAS_FICHE_DATA` pour que les sections principales (scores,
tendances, history, ema_history, events, pres_events) soient **indexées par
projet** plutôt que mises à plat. Le template devient « à onglets » ou
« à sections empilées » avec un onglet par projet, et éventuellement un
onglet « Synthèse globale ».

Nouvelle forme indicative du JSON :

```javascript
var COMPAS_FICHE_DATA = {
  student: { /* identique : nom, groupe, anonyme, pseudo */ },
  global: {
    rank: "or",
    presence: { /* stats agrégées */ },
    scores: { auto: {ema, trend}, rig: {…}, … }
  },
  per_project: [
    {
      name: "Infrastructure réseau PME",
      rank: "or",
      presence: { /* stats projet */ },
      scores: { auto: {ema, trend}, … },
      history: [ /* relevés du projet */ ],
      ema_history: [ /* EMA séance par séance, du projet */ ],
      events: [ /* +2 / -2 du projet */ ],
      pres_events: [ /* présences anormales du projet */ ]
    },
    /* … autres projets */
  ]
};
```

### Faisabilité

**Coût modéré**. Côté Python : refactoriser `compute_student_data` pour
qu'elle retourne cette structure, en réutilisant la logique de filtrage par
projet déjà en place. Côté template : refactor non négligeable de
`fiche.html` (passer de sections plates à un système d'onglets ou de
sections collapsibles, gérer les graphiques Chart.js par projet).

### Limites / questions ouvertes

1. **Complexité visuelle** : une fiche à 3 projets avec onglets est moins
   lisible en impression qu'une fiche plate. Pour un conseil de classe sur
   papier, l'évolution A (fichiers séparés) est probablement plus simple.
2. **Compatibilité template** : casse la rétrocompatibilité du JSON
   `COMPAS_FICHE_DATA`. Si un autre outil (script externe, vue parente,
   etc.) consomme ce JSON, il faudra migrer.
3. **Synthèse globale dans l'onglet « Global »** : même question
   d'agrégation cross-projets que pour l'évolution A.

### Décision arrêtée (2026-05-11)

- **Implémenter ?** **Non — piste abandonnée.**
- Raison : on préfère une fiche globale lisible (évolution A) à une fiche
  unique compactée par onglets ou par sections empilées. Pour « zoomer »
  sur un projet, les fiches par projet existantes (ouvertes depuis le lien
  de la colonne « Projet » de la fiche globale) suffisent.
- Si le besoin réapparaît (par exemple une demande explicite de profil
  global consultable sans télécharger plusieurs fichiers), cette section
  reste comme référence pour ré-instruire la décision.

## Comment elles se recouvrent

| Critère                          | Évolution A (fiche globale) | Évolution B (fiche unifiée) |
| -------------------------------- | --------------------------- | --------------------------- |
| Nombre de fichiers HTML/étudiant | N+1                         | 1                           |
| Lisibilité écran                 | Bonne (1 fiche = 1 vue)     | Dépend du système d'onglets |
| Lisibilité impression            | Excellente                  | Médiocre (onglets cachés)   |
| Coût d'implémentation            | Très faible                 | Modéré                      |
| Casse l'API `COMPAS_FICHE_DATA`  | Non                         | Oui                         |
| Adapté conseil de classe         | Oui (fiche globale dédiée)  | Oui (onglet « Synthèse »)   |
| Adapté entretien individuel      | Oui                         | Oui                         |

**Les deux ne sont pas mutuellement exclusives en théorie**, mais en
pratique la décision retenue est l'évolution A seule. L'évolution B reste
documentée à titre historique mais n'est plus envisagée à court terme.

## Décision retenue (2026-05-11)

**Évolution A retenue, évolution B abandonnée.**

À implémenter :

1. Génération d'une fiche globale supplémentaire par étudiant participant
   à plusieurs projets, au top-level de `output/fiches/`.
2. Badge « Vue globale » dans l'en-tête du template `fiche.html` (visible
   uniquement sur la fiche globale).
3. Colonne « Projet » dans le tableau « Détail des séances » de la fiche
   globale, avec le nom du projet rendu comme lien vers la fiche
   individuelle de l'étudiant dans ce projet
   (`./<slug_projet>/fiche_<slug_etudiant>.html`).

Non retenu :

- Page d'index par étudiant listant ses fiches.
- Fiche unifiée à onglets / sections empilées (évolution B).
