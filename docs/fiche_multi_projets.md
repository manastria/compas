# Fiches individuelles en contexte multi-projets

Ce document détaille deux évolutions candidates de la fiche individuelle
(`compas fiches`) à envisager quand la base contient plusieurs projets pour
un même étudiant (typiquement : `Infrastructure réseau PME` + `Assiduité`).

Il sert de référence pour une décision ultérieure. Aucune des deux pistes
n'est implémentée à ce jour.

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

### Décision à prendre

- **Implémenter ?** Oui / Non / Plus tard.
- **Badge « Vue globale » dans le template ?** Oui / Non.
- **Page d'index par étudiant ?** Hors scope pour l'instant ?

## Évolution B — Fiche unifiée multi-projets (option 2 originelle)

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

### Décision à prendre

- **Implémenter ?** Oui / Non / Plus tard.
- **Onglets ou sections empilées ?** Onglets = plus compact à l'écran,
  moins pratique à l'impression. Empilées = inverse.
- **Conserver un onglet « Synthèse globale » ?** = recouvre l'évolution A
  partiellement.

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

**Les deux ne sont pas mutuellement exclusives** : on peut implémenter A
maintenant (très peu cher) et B plus tard si la demande émerge. Si on
implémente B, la fiche globale d'A devient redondante avec l'onglet
« Synthèse » de B et peut être supprimée à ce moment-là.

## Recommandation

Pour le besoin exprimé (conseil de classe, entretien individuel) :
**évolution A d'abord**. Coût marginal, résultat immédiat, pas de
régression. Évolution B à garder en réserve si une demande spécifique
émerge (par exemple « les étudiants veulent voir leur profil global en
ligne sans télécharger 3 fichiers »).
