# Compas — Guide de l'enseignant

> **Document à l'usage des enseignants** — Version 1.0
> Guide pratique au fil de l'eau pour l'usage quotidien de Compas : codes à saisir, cas particuliers rencontrés en séance, gestion administrative des étudiants. Les informations détaillées (barème des critères, structure des fichiers, calculs) sont dans les autres documents — ce guide reste volontairement synthétique et sera complété au fur et à mesure de la mise en place du projet.
>
> Voir aussi : [`compas_guide_criteres.md`](compas_guide_criteres.md) pour le détail des critères d'évaluation.

---

## Codes de présence

### Rappel du principe

Le pattern est uniforme : `LETTRE:valeur:motif`. Le `:` sépare systématiquement le type, la valeur et le motif optionnel. Plusieurs codes peuvent être combinés avec une virgule.

Le motif est un mot unique, sans espace (ex. `medical`, `discussion`). Si la situation est trop complexe à coder, écris `N` seul et détaille sur la feuille papier — la note sera reprise lors de la saisie.

### Codes simples

| Syntaxe | Signification |
|---------|---------------|
| *(vide)* ou `P` | Présent toute la séance |
| `A` | Absent toute la séance |
| `A:motif` | Absent toute la séance, avec motif |
| `A:H1-H2` | Absent sur les heures 1-2 |
| `A:H1-H2:motif` | Absent heures 1-2, avec motif |
| `A:9h15-10h00` | Absent de 9h15 à 10h00 (départ temporaire + retour) |
| `A:9h15-10h00:motif` | Idem, avec motif |
| `R:15` | Retard de 15 min en début de cours |
| `R:9h30` | Arrivée tardive à 9h30 |
| `R:9h30:motif` | Arrivée tardive à 9h30, avec motif |
| `RR:10` | Retard de 10 min après la récréation |
| `RR:10:motif` | Idem, avec motif |
| `D:10h15` | Départ définitif à 10h15 (avant la fin du cours) |
| `D:10h15:motif` | Idem, avec motif |
| `N` | Note sur la feuille papier — se reporter au scan pour le détail |

**Créneaux acceptés :** `H1`, `H2`, `H3`, `H4` (heures de cours numérotées) ou format `XhYY` (heure précise, ex. `9h30`).

### Combinaisons

Plusieurs codes peuvent se cumuler sur une virgule :

| Syntaxe | Signification |
|---------|---------------|
| `R:5,RR:10` | Retard de 5 min en début de cours + retard de 10 min après la récréation |
| `R:10,D:11h30:medical` | Retard de 10 min en début de cours + départ anticipé à 11h30 pour motif médical |
| `A:H1-H2,RR:5` | Absent heures 1-2 + retard de 5 min après la récréation |
| `R:5,N` | Retard de 5 min + note complémentaire sur la feuille papier |

### Comment c'est compté dans les statistiques

| Code saisi | Comptabilisé comme |
|------------|---------------------|
| `A` ou `A:motif` (sans plage horaire) | Absent toute la séance |
| `A:H1-H2` ou `A:XhYY-XhYY` | Présent (absence partielle) |
| `R:N` ou `RR:N` | Présent, avec retard de N minutes |
| `R:XhYY` | Présent, retard calculé depuis l'heure de début de séance |
| `D:XhYY` | Présent (il était là en début de séance, parti avant la fin) |
| `N` | Présent (détail à consulter sur la feuille papier) |
| Combinaison | Absent si un des codes donne `A` sans plage horaire, sinon présent ; les minutes de retard se cumulent |

### Conseils de saisie

**En cas de doute, code `N`.** Une situation atypique mal codée fausse les statistiques. `N` seul + une note sur la feuille papier suffit toujours.

**Le motif reste facultatif.** Ne l'ajoute que s'il est utile pour comprendre la situation a posteriori (ex. `medical`, `stage`).

**Vide = présent.** Il n'est pas nécessaire de taper `P` à chaque séance : une cellule vide signifie déjà « présent toute la séance ».

---

## Gestion administrative des étudiants

### Départ d'un étudiant en cours d'année

Quand un étudiant démissionne ou quitte le groupe, deux réflexes différents selon la feuille :

**Dans la feuille « Config »** — ne le supprime pas. Renseigne simplement la colonne **E « Date de départ »** avec la date de son départ (format date ou texte `DD/MM/YYYY`). Cette date sert à :

- l'exclure automatiquement des étudiants « actifs » dans le dashboard et les fiches à partir de la séance suivante,
- conserver le lien avec son historique de séances déjà saisi (le rapprochement se fait par nom exact avec les feuilles de séance),
- préserver son INE, utilisé comme clé de croisement avec d'autres projets (ex. Assiduité).

Si tu le supprimes de Config, l'import perd la correspondance avec ses relevés déjà saisis dans les séances passées (un avertissement est émis, mais l'historique devient orphelin).

**Dans la feuille « Modele »/« Modèle »** — tu peux le retirer sans problème. Cette feuille sert uniquement de gabarit pour créer les nouvelles feuilles de séance par copier-coller — elle n'est jamais lue par le script d'import. La retirer évite simplement de le réintégrer par erreur dans les prochaines séances.

**Dans les feuilles de séance déjà créées** — ne touche pas aux séances passées où il apparaît déjà : son historique doit rester tel quel. Pour les séances futures, ne le fais simplement plus figurer dans le tableau (puisqu'il ne sera plus copié depuis le Modele mis à jour).

### Correspondance via l'INE (croisement inter-projets)

La colonne **B « INE »** de la feuille Config (colonne masquée à l'impression) n'est **pas** utilisée pour faire correspondre un étudiant d'une séance à sa fiche Config — ce rapprochement se fait par **nom exact**. L'INE sert à un autre usage : identifier de façon fiable un même étudiant **entre plusieurs projets** (ex. Compas et son projet frère Assiduité), même si son nom est saisi différemment d'un fichier à l'autre.

Ce qu'il faut retenir :

- **Un étudiant peut apparaître dans plusieurs fichiers xlsx** (plusieurs projets/groupes). Dans la base, il n'existe qu'**une seule fois** dans la table des étudiants, indexée par son nom.
- Si les fichiers se contredisent sur l'INE, l'anonymat, le pseudo ou la date de départ pour un même nom, c'est la valeur du **dernier fichier importé** qui l'emporte.
- L'INE est **unique** dans la base : deux étudiants ne peuvent pas partager le même INE. Si un INE est dupliqué par erreur entre deux noms différents, l'import échouera sur cette contrainte — vérifie la saisie de l'INE en priorité en cas d'erreur d'import.

Bonnes pratiques de saisie :

- **Toujours renseigner l'INE**, même si le projet en cours ne l'exploite pas encore : c'est cette valeur qui permettra plus tard de croiser les données avec d'autres projets (assiduité, autres groupes, etc.).
- **Recopier l'INE à l'identique** d'un fichier à l'autre pour un même étudiant — une faute de frappe crée deux identités différentes et casse le croisement.
- En revanche, le **nom** peut légèrement varier d'un fichier à l'autre à condition de rester rigoureusement identique aux endroits qui doivent se correspondre (Config ↔ feuilles de séance du même fichier) : c'est ce nom exact qui sert de clé de rapprochement à l'intérieur d'un même classeur.
- Si un étudiant change de nom (mariage, correction d'état civil), garde le même INE : c'est lui qui assure la continuité, pas le nom.

---

## Évolutions

Ce guide est un document vivant, complété au fil de la mise en place concrète du projet. Toute évolution de la syntaxe de présence doit être répercutée ici et dans `CLAUDE.md`.
