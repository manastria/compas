"""Génération du dashboard HTML depuis la base SQLite."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from compas.ema import compute_ema, compute_rank, compute_trend

logger = logging.getLogger(__name__)

_CRITERIA = ["autonomie", "rigueur", "communication", "engagement"]
_CRITERIA_KEYS = ["auto", "rig", "com", "eng"]
_RANK_ORDER = {"or": 0, "argent": 1, "bronze": 2, "alerte": 3}


def _parse_heure(s: str | None) -> int | None:
    """Parse '8h00' ou '9h30' en minutes depuis minuit.

    Returns:
        Minutes depuis minuit, ou None si format non reconnu.
    """
    if not s:
        return None
    m = re.match(r"^(\d+)h(\d*)$", s.strip(), re.IGNORECASE)
    if m:
        return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
    return None


def _parse_presence(presence: str | None, heure_debut: str | None) -> tuple[str, int]:
    """Parse une valeur de présence et retourne (type, min_retard).

    Args:
        presence: Valeur brute (P, A, R15, 9h30, vide…).
        heure_debut: Heure de début de séance (ex : '8h00'), utilisée pour calculer
            le retard si la présence est une heure d'arrivée.

    Returns:
        Tuple (type, min_retard) où type ∈ {'P', 'A', 'R'}.
    """
    p = (presence or "").strip()
    if not p or p.upper() == "P":
        return "P", 0
    if p.upper() == "A":
        return "A", 0
    # R + chiffres : ex. R15, R5
    m = re.match(r"^[Rr](\d+)$", p)
    if m:
        return "R", int(m.group(1))
    # Format heure d'arrivée : ex. 9h30, 10h
    arrive = _parse_heure(p)
    if arrive is not None:
        debut = _parse_heure(heure_debut)
        if debut is not None:
            return "R", max(0, arrive - debut)
        logger.warning("Présence heure sans heure_debut, retard calculé à 0 : %r", presence)
        return "R", 0
    logger.warning("Format de présence non reconnu : %r", presence)
    return "P", 0


def _presence_stats(releves: list[dict]) -> dict:
    """Calcule les statistiques de présence d'un étudiant.

    Args:
        releves: Liste de relevés (dicts issus de la table releves).

    Returns:
        Dict avec les clés : total, present, absent, retards, min_retard.
    """
    total = len(releves)
    present = 0
    absent = 0
    retards = 0
    min_retard = 0
    for r in releves:
        ptype, mins = _parse_presence(r.get("presence"), r.get("heure_debut"))
        if ptype == "A":
            absent += 1
        else:
            present += 1
            if ptype == "R":
                retards += 1
                min_retard += mins
    return {
        "total": total,
        "present": present,
        "absent": absent,
        "retards": retards,
        "min_retard": min_retard,
    }


def _student_data(
    etudiant: dict,
    releves: list[dict],
    alpha: float,
) -> dict:
    """Calcule toutes les métriques d'un étudiant pour le dashboard.

    Args:
        etudiant: Dict issu de la table etudiants.
        releves: Liste des relevés de l'étudiant (toutes séances, tous projets).
        alpha: Coefficient EMA.

    Returns:
        Dict prêt pour injection dans le template JS.
    """
    # EMA par critère
    scores: dict[str, float | None] = {}
    for crit, key in zip(_CRITERIA, _CRITERIA_KEYS):
        obs: list[tuple[int, int | None]] = [(r["seance"], r[crit]) for r in releves]
        scores[key] = compute_ema(obs, alpha)

    # Tendance globale : calculée sur la moyenne des scores non-NULL par séance
    seance_means: list[tuple[int, float | None]] = []
    for r in releves:
        vals = [r[c] for c in _CRITERIA if r.get(c) is not None]
        seance_means.append((r["seance"], sum(vals) / len(vals) if vals else None))
    trend = compute_trend(seance_means, alpha)

    display_name = (
        etudiant["pseudo"]
        if etudiant.get("anonyme") and etudiant.get("pseudo")
        else etudiant["nom"]
    )

    return {
        "name": etudiant["nom"],
        "display_name": display_name,
        "anon": bool(etudiant.get("anonyme")),
        "scores": scores,
        "trend": trend,
        "rank": compute_rank(scores),
        "presence": _presence_stats(releves),
    }


def _safe_json(data: object) -> str:
    """Sérialise en JSON sûr pour injection inline dans un tag <script>.

    Remplace '</' par '<\\/' pour éviter de fermer prématurément la balise.
    """
    s = json.dumps(data, ensure_ascii=False, indent=2)
    return s.replace("</", r"<\/")


def generate(
    db_path: Path,
    out_path: Path,
    alpha: float = 0.4,
) -> None:
    """Lit la base SQLite, calcule les métriques et génère le dashboard HTML.

    Args:
        db_path: Chemin vers la base SQLite existante.
        out_path: Chemin du fichier HTML à écrire.
        alpha: Coefficient de lissage EMA (défaut 0.4).

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si la base ne contient aucun projet ou aucune séance.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        projet_row = conn.execute(
            "SELECT id, nom, groupe FROM projets ORDER BY id LIMIT 1"
        ).fetchone()
        if not projet_row:
            raise ValueError("Aucun projet dans la base")

        projet_id = int(projet_row["id"])
        nb_projets = conn.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
        if nb_projets > 1:
            logger.warning(
                "Plusieurs projets dans la base — seul « %s » sera affiché", projet_row["nom"]
            )

        seances = conn.execute(
            "SELECT DISTINCT seance, date FROM releves WHERE projet_id=? ORDER BY seance",
            (projet_id,),
        ).fetchall()
        if not seances:
            raise ValueError(f"Aucune séance pour le projet « {projet_row['nom']} »")

        seance_actuelle = int(seances[-1]["seance"])
        date_derniere: str = seances[-1]["date"]
        date_fmt = datetime.strptime(date_derniere, "%Y-%m-%d").strftime("%d/%m/%Y")

        # Étudiants actifs à la date de la dernière séance
        etudiants = conn.execute(
            """SELECT id, nom, groupe, anonyme, pseudo, date_depart
               FROM etudiants
               WHERE date_depart IS NULL OR date_depart > ?
               ORDER BY nom""",
            (date_derniere,),
        ).fetchall()

        releves_rows = conn.execute(
            """SELECT etudiant_id, seance, heure_debut,
                      presence, autonomie, rigueur, communication, engagement
               FROM releves WHERE projet_id=?""",
            (projet_id,),
        ).fetchall()

        releves_by_student: dict[int, list[dict]] = {}
        for row in releves_rows:
            eid = int(row["etudiant_id"])
            releves_by_student.setdefault(eid, []).append(dict(row))

        students = []
        for etudiant in etudiants:
            eid = int(etudiant["id"])
            data = _student_data(dict(etudiant), releves_by_student.get(eid, []), alpha)
            students.append(data)

    finally:
        conn.close()

    # Tri : Or → Argent → Bronze → Alerte, puis nom alphabétique
    students.sort(key=lambda s: (_RANK_ORDER.get(s["rank"], 99), s["name"]))

    compas_data = {
        "projet": projet_row["nom"],
        "groupe": projet_row["groupe"] or "",
        "seance_actuelle": seance_actuelle,
        "date": date_fmt,
        "alpha": alpha,
        "students": students,
    }

    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("dashboard.html").render(
        compas_data_json=_safe_json(compas_data)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    logger.info("Dashboard généré : %s (%d étudiant(s))", out_path, len(students))
