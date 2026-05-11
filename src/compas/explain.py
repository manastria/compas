"""Génération de rapports markdown d'explication EMA pour un étudiant."""

from __future__ import annotations

import sqlite3
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


def _fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso


def _fmt_val(v: int | None) -> str:
    return "—" if v is None else f"{v:+d}"


def generate_explain(
    db_path: Path,
    name_query: str,
    out_path: Path,
    alpha: float = 0.4,
) -> str:
    """Génère un rapport markdown d'explication EMA pour un étudiant.

    Args:
        db_path: Chemin vers la base SQLite existante.
        name_query: Nom ou fragment de nom de l'étudiant (insensible à la casse).
        out_path: Chemin du fichier markdown à écrire.
        alpha: Coefficient de lissage EMA.

    Returns:
        Nom réel de l'étudiant trouvé.

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si l'étudiant n'est pas trouvé ou si plusieurs correspondent.
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

        projet_row = conn.execute(
            "SELECT nom, groupe FROM projets ORDER BY id LIMIT 1"
        ).fetchone()
        projet_nom = projet_row["nom"] if projet_row else "—"
        projet_groupe = projet_row["groupe"] if projet_row else "—"

        releves = conn.execute(
            """SELECT seance, date, autonomie, rigueur, communication, engagement
               FROM releves
               WHERE etudiant_id = ?
               ORDER BY seance""",
            (eid,),
        ).fetchall()
        releves_list = [dict(r) for r in releves]
    finally:
        conn.close()

    nom = etudiant["nom"]
    display_name = (
        etudiant["pseudo"]
        if etudiant.get("anonyme") and etudiant.get("pseudo")
        else nom
    )
    one_minus_alpha = round(1.0 - alpha, 10)

    lines: list[str] = [
        f"# Rapport EMA — {display_name}",
        "",
        f"**Projet :** {projet_nom}  ",
        f"**Groupe :** {projet_groupe}  ",
        f"**Coefficient α :** {alpha}  ",
        f"**Généré le :** {datetime.now().strftime('%d/%m/%Y à %Hh%M')}  ",
        "",
        "---",
        "",
        "## Formule EMA",
        "",
        f"> EMA(1) = valeur de la première séance observée  ",
        f"> EMA(n) = {alpha} × valeur(n) + {one_minus_alpha:.10g} × EMA(n−1)",
        "",
        "Les séances sans observation (—) ne modifient pas l'EMA.",
        "",
        "---",
        "",
    ]

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
                    f"| S{seance} | {date_str} | {val_str} | initialisation | **{current_ema:.3f}** |"
                )
            else:
                prev = current_ema
                current_ema = alpha * float(val) + one_minus_alpha * prev
                calcul = (
                    f"{alpha} × {float(val):.2f} + "
                    f"{one_minus_alpha:.10g} × {prev:.3f}"
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
        "| Critère | EMA finale |",
        "|---------|------------|",
    ]
    for _, short_key, label in _CRITERIA:
        v = final_emas[short_key]
        lines.append(f"| {label} | {f'{v:.3f}' if v is not None else '—'} |")

    observed = [v for v in final_emas.values() if v is not None]
    if observed:
        mean = sum(observed) / len(observed)
        lines.append(f"| **Moyenne** | **{mean:.3f}** |")
        lines.append("")
        rank = compute_rank(final_emas)
        lines.append(f"**Rang final : {_RANK_LABELS.get(rank, rank)}**")
    else:
        lines.append("")
        lines.append("**Aucune donnée disponible pour calculer un rang.**")

    lines.append("")

    content = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return nom
