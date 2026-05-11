"""Génération du dashboard HTML depuis la base SQLite."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from compas.ema import compute_ema, compute_rank

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


def _is_time_range(s: str) -> bool:
    """Retourne True si s ressemble à une plage horaire (H1-H2 ou XhYY-XhYY)."""
    return bool(re.match(r"^(?:H\d+|\d+h\d*)-(?:H\d+|\d+h\d*)$", s, re.IGNORECASE))


def _parse_one_token(
    token: str, heure_debut: str | None, label: str = ""
) -> tuple[str, int]:
    """Parse un token de présence unique (sans virgule) en (type, min_retard).

    Args:
        token: Fragment de présence (ex : 'R:15', 'A:H1-H2').
        heure_debut: Heure de début de séance pour calculer les retards en heures.
        label: Contexte optionnel (ex : nom étudiant) ajouté aux warnings.

    Returns:
        Tuple (type, min_retard) où type ∈ {'P', 'A', 'R'}.
    """
    t = token.strip()
    if not t or t.upper() == "P":
        return "P", 0

    parts = t.split(":", 2)
    code = parts[0].upper()

    if code == "A":
        if len(parts) == 1:
            return "A", 0
        val = parts[1]
        # A:H1-H2 ou A:9h15-10h00 = absence partielle → compté présent
        if _is_time_range(val):
            return "P", 0
        return "A", 0  # A:motif = absent toute la séance

    if code == "R":
        if len(parts) < 2:
            return "R", 0
        val = parts[1]
        if val.isdigit():
            return "R", int(val)
        arrive = _parse_heure(val)
        if arrive is not None:
            debut = _parse_heure(heure_debut)
            if debut is not None:
                return "R", max(0, arrive - debut)
            _warn_presence("Présence heure sans heure_debut, retard calculé à 0", token, label)
        return "R", 0

    if code == "RR":
        if len(parts) < 2:
            return "R", 0
        val = parts[1]
        if val.isdigit():
            return "R", int(val)
        return "R", 0

    if code == "D":
        return "P", 0  # départ anticipé, était présent au début

    if code == "N":
        return "P", 0  # note sur feuille papier, traité comme présent

    # Rétrocompatibilité : R15 (ancien format sans deux-points)
    m = re.match(r"^[Rr](\d+)$", t)
    if m:
        return "R", int(m.group(1))

    # Rétrocompatibilité : heure nue d'arrivée (ex : 9h30)
    arrive = _parse_heure(t)
    if arrive is not None:
        debut = _parse_heure(heure_debut)
        if debut is not None:
            return "R", max(0, arrive - debut)
        _warn_presence("Présence heure sans heure_debut, retard calculé à 0", token, label)
        return "R", 0

    _warn_presence("Format de présence non reconnu", token, label)
    return "P", 0


def _warn_presence(msg: str, token: str, label: str) -> None:
    """Émet un warning de présence avec contexte étudiant optionnel."""
    if label:
        logger.warning("%s [%s] : %r", msg, label, token)
    else:
        logger.warning("%s : %r", msg, token)


def _parse_presence(
    presence: str | None, heure_debut: str | None, label: str = ""
) -> tuple[str, int]:
    """Parse une valeur de présence et retourne (type, min_retard).

    Supporte la syntaxe TYPE:valeur:motif avec combinaisons par virgule.

    Args:
        presence: Valeur brute — syntaxe TYPE:valeur:motif, combinaisons par virgule.
        heure_debut: Heure de début de séance (ex : '8h00'), pour calculer R:XhYY.
        label: Contexte optionnel (ex : nom étudiant) ajouté aux warnings.

    Returns:
        Tuple (type, min_retard) où type ∈ {'P', 'A', 'R'}.
    """
    p = (presence or "").strip()
    if not p or p.upper() == "P":
        return "P", 0

    tokens = [tok.strip() for tok in p.split(",")]
    results = [_parse_one_token(tok, heure_debut, label) for tok in tokens]

    # Un token absent sans plage → absent toute la séance
    if any(r[0] == "A" for r in results):
        return "A", 0

    total_min = sum(r[1] for r in results)
    if any(r[0] == "R" for r in results):
        return "R", total_min
    return "P", 0


def _presence_stats(releves: list[dict], nom: str = "") -> dict:
    """Calcule les statistiques de présence d'un étudiant.

    Args:
        releves: Liste de relevés (dicts issus de la table releves).
        nom: Nom de l'étudiant, inclus dans les warnings de présence malformée.

    Returns:
        Dict avec les clés : total, present, absent, retards, min_retard.
    """
    total = len(releves)
    present = 0
    absent = 0
    retards = 0
    min_retard = 0
    for r in releves:
        ptype, mins = _parse_presence(r.get("presence"), r.get("heure_debut"), label=nom)
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
    # EMA par critère + score global cumulé par séance
    scores: dict[str, float | None] = {}
    for crit, key in zip(_CRITERIA, _CRITERIA_KEYS):
        obs: list[tuple[int, int | None]] = [(r["seance"], r[crit]) for r in releves]
        scores[key] = compute_ema(obs, alpha)

    # Tendance : compare le score global (moyenne des EMA par critère) entre
    # la séance courante et la précédente — même valeur que celle affichée.
    crit_running: dict[str, float | None] = {c: None for c in _CRITERIA}
    session_scores: list[float | None] = []
    for r in sorted(releves, key=lambda x: x["seance"]):
        for crit in _CRITERIA:
            val = r.get(crit)
            if val is not None:
                prev = crit_running[crit]
                crit_running[crit] = (
                    float(val) if prev is None
                    else alpha * float(val) + (1.0 - alpha) * prev
                )
        obs_vals = [v for v in crit_running.values() if v is not None]
        session_scores.append(sum(obs_vals) / len(obs_vals) if obs_vals else None)

    non_null = [v for v in session_scores if v is not None]
    if len(non_null) < 2:
        trend = "stable"
    else:
        delta = non_null[-1] - non_null[-2]
        trend = "up" if delta > 0.05 else "down" if delta < -0.05 else "stable"

    if etudiant.get("anonyme"):
        display_name = etudiant.get("pseudo") or "Étudiant anonyme"
    else:
        display_name = etudiant["nom"]

    return {
        "name": etudiant["nom"],
        "display_name": display_name,
        "anon": bool(etudiant.get("anonyme")),
        "scores": scores,
        "trend": trend,
        "rank": compute_rank(scores),
        "presence": _presence_stats(releves, nom=etudiant.get("nom", "")),
    }


def _slug(name: str) -> str:
    """Convertit un nom en slug ASCII pour les noms de fichiers."""
    norm = unicodedata.normalize("NFD", name.lower())
    ascii_name = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")


def _resolve_projets(
    conn: sqlite3.Connection, projet_filter: str | None
) -> list[sqlite3.Row]:
    """Retourne les projets correspondant au filtre, ou tous si filtre vide.

    Raises:
        ValueError: Si la base n'a aucun projet, ou si le filtre ne matche rien.
    """
    if projet_filter is None:
        rows = conn.execute(
            "SELECT id, nom, groupe FROM projets ORDER BY id"
        ).fetchall()
        if not rows:
            raise ValueError("Aucun projet dans la base")
        return rows

    rows = conn.execute(
        "SELECT id, nom, groupe FROM projets ORDER BY id"
    ).fetchall()
    if not rows:
        raise ValueError("Aucun projet dans la base")
    pf = projet_filter.lower()
    matches = [r for r in rows if pf in r["nom"].lower()]
    if not matches:
        noms = sorted(r["nom"] for r in rows)
        raise ValueError(
            f"Aucun projet ne correspond à « {projet_filter} ».\n"
            f"Projets disponibles : {', '.join(noms)}"
        )
    return matches


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
    at_seance: int | None = None,
    at_date: str | None = None,
    projet: str | None = None,
) -> None:
    """Lit la base SQLite, calcule les métriques et génère le dashboard HTML.

    Si `projet` est fourni, filtre par nom de projet (insensible à la casse).
    Sinon, prend le premier projet de la base (comportement historique).
    Pour générer un dashboard par projet quand la base en contient plusieurs,
    utiliser :func:`generate_all_projects`.

    Args:
        db_path: Chemin vers la base SQLite existante.
        out_path: Chemin du fichier HTML à écrire.
        alpha: Coefficient de lissage EMA (défaut 0.4).
        at_seance: Si fourni, n'inclut que les séances ≤ à ce numéro.
        at_date: Si fourni, n'inclut que les séances dont la date ≤ à cette
            date (format ISO YYYY-MM-DD).
        projet: Fragment de nom de projet pour filtrer (insensible à la casse).

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si la base ne contient aucun projet ou aucune séance.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if projet is not None:
            projets = _resolve_projets(conn, projet)
            if len(projets) > 1:
                noms = ", ".join(p["nom"] for p in projets)
                raise ValueError(
                    f"Plusieurs projets correspondent à « {projet} » : {noms}.\n"
                    "Précisez davantage le nom."
                )
            projet_row = projets[0]
        else:
            projet_row = conn.execute(
                "SELECT id, nom, groupe FROM projets ORDER BY id LIMIT 1"
            ).fetchone()
            if not projet_row:
                raise ValueError("Aucun projet dans la base")
            nb_projets = conn.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
            if nb_projets > 1:
                logger.warning(
                    "Plusieurs projets dans la base — seul « %s » sera affiché"
                    " (utiliser --projet ou generate_all_projects)",
                    projet_row["nom"],
                )
        projet_id = int(projet_row["id"])

        all_seances = conn.execute(
            "SELECT DISTINCT seance, date FROM releves WHERE projet_id=? ORDER BY seance",
            (projet_id,),
        ).fetchall()

        # Appliquer le filtre temporel
        seances = list(all_seances)
        if at_seance is not None:
            seances = [s for s in seances if int(s["seance"]) <= at_seance]
        if at_date is not None:
            seances = [s for s in seances if s["date"] <= at_date]

        if not seances:
            cutoff = f"séance {at_seance}" if at_seance else at_date
            raise ValueError(
                f"Aucune séance avant « {cutoff} »"
                f" pour le projet « {projet_row['nom']} »"
            )

        if at_seance is not None or at_date is not None:
            logger.info(
                "Vue historique : %d séance(s) sur %d", len(seances), len(all_seances)
            )

        seance_actuelle = int(seances[-1]["seance"])
        date_derniere: str = seances[-1]["date"]
        date_fmt = datetime.strptime(date_derniere, "%Y-%m-%d").strftime("%d/%m/%Y")

        # Heure début/fin de la dernière séance retenue
        last_hours = conn.execute(
            "SELECT heure_debut, heure_fin FROM releves WHERE projet_id=? AND seance=? LIMIT 1",
            (projet_id, seance_actuelle),
        ).fetchone()
        heure_debut_session: str | None = last_hours["heure_debut"] if last_hours else None
        heure_fin_session: str | None = last_hours["heure_fin"] if last_hours else None

        # Étudiants actifs à la date de la dernière séance retenue
        etudiants = conn.execute(
            """SELECT id, nom, groupe, anonyme, pseudo, date_depart
               FROM etudiants
               WHERE date_depart IS NULL OR date_depart > ?
               ORDER BY nom""",
            (date_derniere,),
        ).fetchall()

        releves_rows = conn.execute(
            """SELECT etudiant_id, seance, heure_debut, heure_fin,
                      presence, autonomie, rigueur, communication, engagement
               FROM releves WHERE projet_id=? AND seance <= ?""",
            (projet_id, seance_actuelle),
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

    # Tri alphabétique : pseudo pour les anonymes, nom réel sinon
    students.sort(key=lambda s: s["display_name"].casefold())

    compas_data = {
        "projet": projet_row["nom"],
        "groupe": projet_row["groupe"] or "",
        "seance_actuelle": seance_actuelle,
        "seances_total": len(seances),
        "date": date_fmt,
        "heure_debut": heure_debut_session,
        "heure_fin": heure_fin_session,
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


def generate_all_projects(
    db_path: Path,
    out_path: Path,
    alpha: float = 0.4,
    at_seance: int | None = None,
    at_date: str | None = None,
) -> list[tuple[str, Path]]:
    """Génère un dashboard HTML par projet présent dans la base.

    Si la base contient un seul projet, le fichier est écrit à `out_path`
    (comportement historique). S'il y en a plusieurs, le nom est suffixé
    avec un slug du nom de projet (ex : ``dashboard_infrastructure.html``).

    Args:
        db_path: Chemin vers la base SQLite existante.
        out_path: Chemin de référence (utilisé tel quel si un seul projet,
            sinon le suffixe ``_<slug>`` est inséré avant l'extension).
        alpha: Coefficient de lissage EMA (défaut 0.4).
        at_seance: Si fourni, n'inclut que les séances ≤ à ce numéro.
        at_date: Si fourni, n'inclut que les séances ≤ à cette date ISO.

    Returns:
        Liste de tuples (nom_projet, chemin_fichier).

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si la base ne contient aucun projet.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        projets = _resolve_projets(conn, None)
    finally:
        conn.close()

    multi = len(projets) > 1
    written: list[tuple[str, Path]] = []
    for p in projets:
        if multi:
            target = out_path.with_name(
                f"{out_path.stem}_{_slug(p['nom'])}{out_path.suffix}"
            )
        else:
            target = out_path
        try:
            generate(
                db_path, target, alpha=alpha,
                at_seance=at_seance, at_date=at_date, projet=p["nom"],
            )
            written.append((p["nom"], target))
        except ValueError as exc:
            logger.warning("Dashboard ignoré pour « %s » : %s", p["nom"], exc)
    return written
