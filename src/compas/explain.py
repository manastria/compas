"""Génération de rapports markdown d'explication EMA pour un étudiant."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from compas.ema import compute_rank

_CRITERIA: list[tuple[str, str, str]] = [
    ("autonomie",     "auto", "Autonomie"),
    ("rigueur",       "rig",  "Rigueur"),
    ("communication", "com",  "Communication"),
    ("engagement",    "eng",  "Engagement"),
]

_RANK_LABELS = {
    "or":     "Or",
    "argent": "Argent",
    "bronze": "Bronze",
    "alerte": "Alerte",
}


def _slug(name: str) -> str:
    """Convertit un nom en slug ASCII pour les noms de fichiers."""
    norm = unicodedata.normalize("NFD", name.lower())
    ascii_name = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")


def _fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso


def _fmt_val(v: int | None) -> str:
    return "—" if v is None else f"{v:+d}"


def _ema_to_pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{round(max(0, min(100, ((v + 2) / 4) * 100))) } %"


def _resolve_projet(
    conn: sqlite3.Connection, projet_filter: str | None
) -> list[dict]:
    """Retourne la liste des projets correspondants (par nom, insensible à la casse).

    Args:
        conn: Connexion SQLite ouverte.
        projet_filter: Fragment de nom de projet, ou None pour tous les projets.

    Returns:
        Liste de dicts {id, nom, groupe}.

    Raises:
        ValueError: Si projet_filter ne correspond à aucun projet de la base.
    """
    projets = [
        dict(r) for r in conn.execute(
            "SELECT id, nom, groupe FROM projets ORDER BY id"
        ).fetchall()
    ]
    if not projets:
        return []
    if projet_filter is None:
        return projets
    pf = projet_filter.lower()
    matches = [p for p in projets if pf in p["nom"].lower()]
    if not matches:
        noms = sorted(p["nom"] for p in projets)
        raise ValueError(
            f"Aucun projet ne correspond à « {projet_filter} ».\n"
            f"Projets disponibles : {', '.join(noms)}"
        )
    return matches


def _render_explain(
    etudiant: dict,
    projet: dict,
    releves_list: list[dict],
    alpha: float,
) -> str:
    """Construit le contenu markdown d'un rapport explain pour un étudiant et un projet.

    Args:
        etudiant: Dict {id, nom, anonyme, pseudo}.
        projet: Dict {id, nom, groupe}.
        releves_list: Relevés de l'étudiant pour ce projet (triés par séance).
        alpha: Coefficient EMA.

    Returns:
        Contenu markdown.
    """
    nom = etudiant["nom"]
    pseudo = etudiant.get("pseudo") if etudiant.get("anonyme") else None
    display_name = f"{nom} ({pseudo})" if pseudo else nom
    projet_nom = projet["nom"]
    projet_groupe = projet.get("groupe") or "—"
    one_minus_alpha = round(1.0 - alpha, 10)

    lines: list[str] = [
        f"# Rapport EMA — {display_name}",
        "",
        f"**Projet :** {projet_nom}  ",
        f"**Groupe :** {projet_groupe}  ",
        f"**Coefficient $\\alpha$ :** {alpha}  ",
        f"**Généré le :** {datetime.now().strftime('%d/%m/%Y à %Hh%M')}  ",
        "",
        "---",
        "",
        "## Formule EMA",
        "",
        "La première séance observée initialise directement l'EMA :",
        "",
        "$$EMA_1 = v_1$$",
        "",
        "Pour chaque séance suivante :",
        "",
        "$$EMA_n = \\alpha \\times v_n + (1 - \\alpha) \\times EMA_{n-1}$$",
        "",
        f"Avec $\\alpha = {alpha}$, le complément $(1 - \\alpha)$ vaut"
        f" $1 - {alpha} = {one_minus_alpha:.10g}$.",
        "C'est le poids accordé à l'historique : plus $\\alpha$ est grand,"
        " plus les séances récentes priment sur l'historique.",
        "",
        "Les séances sans observation (—) ne modifient pas l'EMA.",
        "",
        "---",
        "",
    ]

    # --- Calcul de la progression séance par séance ---
    _THRESHOLD = 0.05
    _crit_emas: dict[str, float | None] = {sk: None for _, sk, _ in _CRITERIA}
    per_session: list[dict] = []

    for r in releves_list:
        raw = {dc: r[dc] for dc, _, _ in _CRITERIA}

        for dc, sk, _ in _CRITERIA:
            val = r[dc]
            if val is not None:
                _crit_emas[sk] = (
                    float(val) if _crit_emas[sk] is None
                    else alpha * float(val) + one_minus_alpha * _crit_emas[sk]
                )

        obs = [v for v in _crit_emas.values() if v is not None]
        score_global = sum(obs) / len(obs) if obs else None

        # Tendance : compare le score global avec celui de la séance précédente
        prev_scores = [ps["score_global"] for ps in per_session if ps["score_global"] is not None]
        prev_score = prev_scores[-1] if prev_scores else None

        if prev_score is None or score_global is None:
            tendency, variation_str = "—", "—"
        else:
            delta = score_global - prev_score
            delta_pct = delta * 25  # 1 unité [-2;+2] = 25 %
            variation_str = f"${delta_pct:+.1f}\\,\\%$"
            tendency = (
                "↑ hausse" if delta > _THRESHOLD
                else "↓ baisse" if delta < -_THRESHOLD
                else "→ stable"
            )

        per_session.append({
            "seance": r["seance"],
            "date": _fmt_date(r["date"]),
            "raw": raw,
            "emas": dict(_crit_emas),
            "score_global": score_global,
            "variation": variation_str,
            "tendency": tendency,
        })

    # --- Section : Évolution séance par séance ---
    lines += [
        "## Évolution séance par séance",
        "",
        "### Valeurs observées",
        "",
        "Valeurs brutes saisies sur la feuille de séance"
        " ($-2$ à $+2$, ou — si non observé).",
        "",
        "| Séance | Date | Autonomie | Rigueur | Communication | Engagement |",
        "| ------ | ---- | --------- | ------- | ------------- | ---------- |",
    ]
    for ps in per_session:
        cells = " | ".join(_fmt_val(ps["raw"][dc]) for dc, _, _ in _CRITERIA)
        lines.append(f"| S{ps['seance']} | {ps['date']} | {cells} |")

    threshold_pct = _THRESHOLD * 25
    lines += [
        "",
        "### Score par critère et tendance",
        "",
        "L'EMA de chaque critère est mise à jour après chaque séance observée."
        " Le **score global** est la moyenne des quatre EMA convertie en pourcentage."
        " La **tendance** (↑ ↓ →) compare le score global de la séance courante"
        " avec celui de la séance précédente.",
        "",
        f"Seuil : $|\\Delta| > {threshold_pct:.2g}\\,\\%$"
        f" (soit $\\pm {_THRESHOLD}$ sur l'échelle $[-2\\,;\\,+2]$).",
        "",
        "| Séance | Autonomie | Rigueur | Communication | Engagement"
        " | Score global | Variation | Tendance |",
        "| ------ | --------- | ------- | ------------- | ----------"
        " | ------------ | --------- | -------- |",
    ]
    for ps in per_session:
        pcts = " | ".join(_ema_to_pct(ps["emas"][sk]) for _, sk, _ in _CRITERIA)
        global_pct = _ema_to_pct(ps["score_global"])
        lines.append(
            f"| S{ps['seance']} | {pcts} | **{global_pct}**"
            f" | {ps['variation']} | {ps['tendency']} |"
        )

    lines += ["", "---", ""]

    # --- Détail par critère ---
    final_emas: dict[str, float | None] = {}

    for db_col, short_key, label in _CRITERIA:
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| Séance | Date | Valeur | Calcul | EMA |")
        lines.append("|--------|------|--------|--------|-----|")

        current_ema: float | None = None
        for r in releves_list:
            seance = r["seance"]
            date_str = _fmt_date(r["date"])
            val = r[db_col]
            val_str = _fmt_val(val)

            if val is None:
                ema_str = f"{current_ema:.3f}" if current_ema is not None else "—"
                lines.append(
                    f"| S{seance} | {date_str} | {val_str} | non observé | {ema_str} |"
                )
            elif current_ema is None:
                current_ema = float(val)
                lines.append(
                    f"| S{seance} | {date_str} | {val_str}"
                    f" | $EMA_1 = v_1$ | **{current_ema:.3f}** |"
                )
            else:
                prev = current_ema
                current_ema = alpha * float(val) + one_minus_alpha * prev
                calcul = (
                    f"${alpha} \\times {float(val):.2f}"
                    f" + {one_minus_alpha:.10g} \\times {prev:.3f}$"
                )
                lines.append(
                    f"| S{seance} | {date_str} | {val_str} | {calcul} | **{current_ema:.3f}** |"
                )

        final_emas[short_key] = current_ema
        lines.append("")
        if current_ema is not None:
            lines.append(f"**EMA finale : {current_ema:.3f}**")
        else:
            lines.append("**Aucune observation pour ce critère.**")
        lines.append("")

    lines += [
        "---",
        "",
        "## Récapitulatif",
        "",
        "Le score affiché aux étudiants convertit l'EMA (échelle $[-2 ; +2]$)"
        " en pourcentage entier :",
        "",
        "$$\\text{score (\\%)} ="
        " \\text{arrondi}\\!\\left(\\frac{EMA + 2}{4} \\times 100\\right)$$",
        "",
        "Cette formule ramène $-2 \\to 0\\,\\%$,"
        " $0 \\to 50\\,\\%$ et $+2 \\to 100\\,\\%$.",
        "",
        "| Critère | EMA finale | Score affiché |",
        "|---------|------------|---------------|",
    ]
    for _, short_key, label in _CRITERIA:
        v = final_emas[short_key]
        ema_str = f"{v:.3f}" if v is not None else "—"
        pct = (
            f"{round(max(0, min(100, ((v + 2) / 4) * 100))) } %"
            if v is not None else "—"
        )
        lines.append(f"| {label} | {ema_str} | {pct} |")

    observed = [v for v in final_emas.values() if v is not None]
    if observed:
        mean = sum(observed) / len(observed)
        mean_pct = round(max(0, min(100, ((mean + 2) / 4) * 100)))
        lines.append(f"| **Moyenne** | **{mean:.3f}** | **{mean_pct} %** |")
        lines.append("")
        rank = compute_rank(final_emas)
        lines.append(f"**Rang final : {_RANK_LABELS.get(rank, rank)}**")
    else:
        lines.append("")
        lines.append("**Aucune donnée disponible pour calculer un rang.**")

    lines.append("")

    return "\n".join(lines)


def _build_out_path(base: Path, projet_nom: str, multi: bool) -> Path:
    """Construit le chemin de sortie en suffixant le projet quand multi=True."""
    if not multi:
        return base
    suffix = base.suffix
    stem = base.stem
    return base.with_name(f"{stem}_{_slug(projet_nom)}{suffix}")


def generate_explain(
    db_path: Path,
    name_query: str,
    out_path: Path,
    alpha: float = 0.4,
    projet: str | None = None,
) -> list[tuple[str, Path]]:
    """Génère un rapport markdown d'explication EMA pour un étudiant.

    Si l'étudiant participe à plusieurs projets et qu'aucun filtre `projet`
    n'est fourni, un rapport est écrit par projet en suffixant `out_path`
    avec le slug du nom de projet.

    Args:
        db_path: Chemin vers la base SQLite existante.
        name_query: Nom ou fragment de nom de l'étudiant (insensible à la casse).
        out_path: Chemin du fichier markdown de sortie (suffixé en multi-projets).
        alpha: Coefficient de lissage EMA.
        projet: Fragment de nom de projet pour filtrer (insensible à la casse).

    Returns:
        Liste de tuples (nom_projet, chemin_fichier) des rapports générés.

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si l'étudiant n'est pas trouvé, si plusieurs correspondent,
            si le filtre projet ne correspond à rien, ou si l'étudiant n'a aucun
            relevé pour les projets retenus.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        etudiants = conn.execute(
            "SELECT id, nom, anonyme, pseudo FROM etudiants"
        ).fetchall()

        query_lower = name_query.lower()
        matches = [e for e in etudiants if query_lower in e["nom"].lower()]

        if not matches:
            noms = sorted(e["nom"] for e in etudiants)
            raise ValueError(
                f"Aucun étudiant ne correspond à « {name_query} ».\n"
                f"Étudiants disponibles : {', '.join(noms)}"
            )
        if len(matches) > 1:
            noms = [e["nom"] for e in matches]
            raise ValueError(
                f"Plusieurs étudiants correspondent à « {name_query} » : {', '.join(noms)}.\n"
                "Précisez davantage le nom."
            )

        etudiant = dict(matches[0])
        eid = int(etudiant["id"])

        projets = _resolve_projet(conn, projet)
        if not projets:
            raise ValueError("Aucun projet dans la base")

        # Restreindre aux projets où l'étudiant a au moins un relevé
        projet_ids = [p["id"] for p in projets]
        placeholders = ",".join("?" for _ in projet_ids)
        rows = conn.execute(
            f"""SELECT projet_id, seance, date,
                       autonomie, rigueur, communication, engagement
                FROM releves
                WHERE etudiant_id = ? AND projet_id IN ({placeholders})
                ORDER BY projet_id, seance""",
            (eid, *projet_ids),
        ).fetchall()
        releves_by_projet: dict[int, list[dict]] = {}
        for r in rows:
            releves_by_projet.setdefault(int(r["projet_id"]), []).append(dict(r))

        projets_avec_releves = [p for p in projets if p["id"] in releves_by_projet]
        if not projets_avec_releves:
            cible = (
                f"le projet « {projet} »" if projet
                else "les projets de la base"
            )
            raise ValueError(
                f"Aucun relevé pour {etudiant['nom']} dans {cible}."
            )
    finally:
        conn.close()

    multi = len(projets_avec_releves) > 1
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written: list[tuple[str, Path]] = []
    for projet_row in projets_avec_releves:
        content = _render_explain(
            etudiant, projet_row, releves_by_projet[projet_row["id"]], alpha
        )
        path = _build_out_path(out_path, projet_row["nom"], multi)
        path.write_text(content, encoding="utf-8")
        written.append((projet_row["nom"], path))

    return written
