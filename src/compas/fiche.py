"""Génération des fiches individuelles HTML par étudiant."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from compas.ema import compute_ema, compute_rank, compute_trend
from compas.presence_desc import describe_presence

logger = logging.getLogger(__name__)

_CRITERIA = [
    ("autonomie", "auto", "Autonomie"),
    ("rigueur", "rig", "Rigueur"),
    ("communication", "com", "Communication"),
    ("engagement", "eng", "Engagement"),
]


def _is_time_range(s: str) -> bool:
    return bool(re.match(r"^(?:H\d+|\d+h\d*)-(?:H\d+|\d+h\d*)$", s, re.IGNORECASE))


def _parse_heure(s: str | None) -> int | None:
    if not s:
        return None
    m = re.match(r"^(\d+)h(\d*)$", s.strip(), re.IGNORECASE)
    return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0) if m else None


def _presence_detail(presence: str | None, heure_debut: str | None) -> dict:
    """Parse un code de présence en stats détaillées (R et RR séparés).

    Returns:
        Dict avec absent, has_r, r_min, has_rr, rr_min.
    """
    result: dict = {"absent": False, "has_r": False, "r_min": 0, "has_rr": False, "rr_min": 0}
    p = (presence or "").strip()
    if not p or p.upper() == "P":
        return result

    for token in p.split(","):
        t = token.strip()
        if not t:
            continue
        parts = t.split(":", 2)
        code = parts[0].upper()

        if code in ("P", "N", "D"):
            continue

        if code == "A":
            if len(parts) == 1:
                result["absent"] = True
            elif not _is_time_range(parts[1]):
                result["absent"] = True
            # plage horaire (A:H1-H2 ou A:9h15-10h00) → présent pour les stats

        elif code == "R":
            result["has_r"] = True
            if len(parts) >= 2:
                val = parts[1]
                if val.isdigit():
                    result["r_min"] += int(val)
                else:
                    arrive = _parse_heure(val)
                    debut = _parse_heure(heure_debut)
                    if arrive is not None and debut is not None:
                        result["r_min"] += max(0, arrive - debut)

        elif code == "RR":
            result["has_rr"] = True
            if len(parts) >= 2 and parts[1].isdigit():
                result["rr_min"] += int(parts[1])

    return result


def _fmt_short(iso: str) -> str:
    """Convertit 'YYYY-MM-DD' en 'DD/MM'."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m")
    except ValueError:
        return iso


def _presence_stats(releves: list[dict]) -> dict:
    """Calcule les stats de présence avec retards R et RR séparés."""
    total = len(releves)
    present = absent = retards_r = retards_rr = min_r = min_rr = 0

    for r in releves:
        det = _presence_detail(r.get("presence"), r.get("heure_debut"))
        if det["absent"]:
            absent += 1
        else:
            present += 1
            if det["has_r"]:
                retards_r += 1
                min_r += det["r_min"]
            if det["has_rr"]:
                retards_rr += 1
                min_rr += det["rr_min"]

    taux = round(present * 100 / total) if total > 0 else 0
    return {
        "total": total,
        "present": present,
        "absent": absent,
        "retards_r": retards_r,
        "retards_rr": retards_rr,
        "min_r": min_r,
        "min_rr": min_rr,
        "taux": taux,
    }


def _project_rank_trend(releves: list[dict], alpha: float) -> tuple[str, str]:
    """Calcule le rang et la tendance pour les relevés d'un projet."""
    ema_scores = {
        sk: compute_ema([(r["seance"], r.get(dc)) for r in releves], alpha)
        for dc, sk, _ in _CRITERIA
    }
    rank = compute_rank(ema_scores)

    crit_running: dict[str, float | None] = {sk: None for _, sk, _ in _CRITERIA}
    session_avgs: list[float] = []
    for r in sorted(releves, key=lambda x: x["seance"]):
        for dc, sk, _ in _CRITERIA:
            val = r.get(dc)
            if val is not None:
                prev = crit_running[sk]
                crit_running[sk] = (
                    float(val) if prev is None
                    else alpha * float(val) + (1.0 - alpha) * prev
                )
        obs = [v for v in crit_running.values() if v is not None]
        if obs:
            session_avgs.append(sum(obs) / len(obs))

    if len(session_avgs) < 2:
        trend = "stable"
    else:
        delta = session_avgs[-1] - session_avgs[-2]
        trend = "up" if delta > 0.05 else "down" if delta < -0.05 else "stable"

    return rank, trend


def compute_student_data(
    db_path: Path,
    etudiant_id: int,
    alpha: float = 0.4,
) -> dict:
    """Calcule toutes les données d'un étudiant pour sa fiche individuelle.

    Args:
        db_path: Chemin vers la base SQLite existante.
        etudiant_id: Identifiant de l'étudiant dans la table etudiants.
        alpha: Coefficient de lissage EMA (défaut 0.4).

    Returns:
        Dict structuré pour injection dans le template (COMPAS_FICHE_DATA).

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si l'étudiant n'est pas trouvé dans la base.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        etudiant_row = conn.execute(
            "SELECT id, nom, groupe, anonyme, pseudo, date_depart FROM etudiants WHERE id=?",
            (etudiant_id,),
        ).fetchone()
        if not etudiant_row:
            raise ValueError(f"Étudiant introuvable : id={etudiant_id}")
        etudiant = dict(etudiant_row)

        projets_rows = conn.execute(
            """SELECT DISTINCT p.id, p.nom, p.groupe
               FROM projets p
               INNER JOIN releves r ON r.projet_id = p.id
               WHERE r.etudiant_id = ?
               ORDER BY p.id""",
            (etudiant_id,),
        ).fetchall()
        projets = [dict(p) for p in projets_rows]

        releves_rows = conn.execute(
            """SELECT r.*, p.id as projet_id
               FROM releves r
               JOIN projets p ON p.id = r.projet_id
               WHERE r.etudiant_id = ?
               ORDER BY r.date, r.seance""",
            (etudiant_id,),
        ).fetchall()
        releves = [dict(r) for r in releves_rows]
    finally:
        conn.close()

    nom = etudiant["nom"]
    pseudo = etudiant.get("pseudo") if etudiant.get("anonyme") else None
    display_name = nom  # le pseudo est rendu séparément dans le template
    groupe = etudiant.get("groupe") or ""

    # EMA et tendance globales (tous projets, séquence par date)
    ema_scores: dict[str, float | None] = {}
    trends: dict[str, str] = {}
    for dc, sk, _ in _CRITERIA:
        obs = [(i, r.get(dc)) for i, r in enumerate(releves)]
        ema_scores[sk] = compute_ema(obs, alpha)
        trends[sk] = compute_trend(obs, alpha)

    rank = compute_rank(ema_scores)

    # Historique brut
    multi = len(projets) > 1
    history = [
        {
            "date": _fmt_short(r["date"]),
            "seance": f"S{r['seance']}",
            "pres": r.get("presence") or "P",
            "auto": r.get("autonomie"),
            "rig": r.get("rigueur"),
            "com": r.get("communication"),
            "eng": r.get("engagement"),
            "comment": r.get("commentaire") or "",
        }
        for r in releves
    ]

    # Historique EMA séance par séance (uniquement quand au moins un critère observé)
    crit_running: dict[str, float | None] = {sk: None for _, sk, _ in _CRITERIA}
    ema_history = []
    for i, r in enumerate(releves):
        any_obs = False
        for dc, sk, _ in _CRITERIA:
            val = r.get(dc)
            if val is not None:
                any_obs = True
                prev = crit_running[sk]
                crit_running[sk] = (
                    float(val) if prev is None
                    else alpha * float(val) + (1.0 - alpha) * prev
                )
        if any_obs:
            label = f"S{i + 1}" if multi else f"S{r['seance']}"
            ema_history.append({
                "seance": label,
                "auto": crit_running["auto"],
                "rig": crit_running["rig"],
                "com": crit_running["com"],
                "eng": crit_running["eng"],
            })

    # Événements remarquables (+2 ou −2)
    events = [
        {
            "date": _fmt_short(r["date"]),
            "criteria": label,
            "value": int(r[dc]),
            "comment": r.get("commentaire") or "",
        }
        for r in releves
        for dc, sk, label in _CRITERIA
        if r.get(dc) in (2, -2)
    ]

    # Détail des présences anormales
    pres_events = [
        {
            "date": _fmt_short(r["date"]),
            "code": code,
            "desc": describe_presence(code),
        }
        for r in releves
        if (code := (r.get("presence") or "").strip()) and code.upper() != "P"
    ]

    # Comparaison inter-projets (masqué si un seul projet)
    projet_releves: dict[int, list[dict]] = {}
    for r in releves:
        projet_releves.setdefault(int(r["projet_id"]), []).append(r)

    projects = []
    if multi:
        for p in projets:
            pid = int(p["id"])
            p_rank, p_trend = _project_rank_trend(projet_releves.get(pid, []), alpha)
            projects.append({"name": p["nom"], "rank": p_rank, "trend": p_trend})

    return {
        "student": {
            "name": nom,
            "display_name": display_name,
            "pseudo": pseudo,
            "groupe": groupe,
            "rank": rank,
            "presence": _presence_stats(releves),
        },
        "scores": {
            sk: {"ema": ema_scores[sk], "trend": trends[sk]}
            for _, sk, _ in _CRITERIA
        },
        "history": history,
        "ema_history": ema_history,
        "events": events,
        "pres_events": pres_events,
        "projects": projects,
    }


def _safe_json(data: object) -> str:
    """Sérialise en JSON sûr pour injection inline dans un tag <script>."""
    s = json.dumps(data, ensure_ascii=False, indent=2)
    return s.replace("</", r"<\/")


def _slug(name: str) -> str:
    """Convertit un nom en slug ASCII pour les noms de fichiers."""
    norm = unicodedata.normalize("NFD", name.lower())
    ascii_name = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")


def generate_fiche(student_data: dict, output_path: Path) -> None:
    """Rend le template Jinja2 fiche.html et écrit le fichier HTML.

    Args:
        student_data: Dict issu de compute_student_data.
        output_path: Chemin du fichier HTML à écrire.
    """
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("fiche.html").render(
        fiche_data_json=_safe_json(student_data)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("Fiche générée : %s", output_path)


def generate_all_fiches(
    db_path: Path,
    output_dir: Path,
    alpha: float = 0.4,
    name_filter: str | None = None,
) -> int:
    """Génère une fiche HTML pour chaque étudiant actif.

    Args:
        db_path: Chemin vers la base SQLite existante.
        output_dir: Dossier de sortie pour les fiches.
        alpha: Coefficient de lissage EMA (défaut 0.4).
        name_filter: Fragment de nom pour filtrer (insensible à la casse).

    Returns:
        Nombre de fiches générées.

    Raises:
        FileNotFoundError: Si db_path n'existe pas.
        ValueError: Si name_filter ne correspond à aucun étudiant actif.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        last_row = conn.execute("SELECT MAX(date) FROM releves").fetchone()
        last_date = last_row[0] if last_row else None

        if last_date:
            rows = conn.execute(
                "SELECT id, nom FROM etudiants WHERE date_depart IS NULL OR date_depart > ?",
                (last_date,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, nom FROM etudiants WHERE date_depart IS NULL"
            ).fetchall()
    finally:
        conn.close()

    etudiants = list(rows)
    if name_filter:
        nf = name_filter.lower()
        etudiants = [e for e in etudiants if nf in e["nom"].lower()]
        if not etudiants:
            raise ValueError(
                f"Aucun étudiant actif ne correspond à « {name_filter} »."
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for etudiant in etudiants:
        eid = int(etudiant["id"])
        nom = etudiant["nom"]
        try:
            data = compute_student_data(db_path, eid, alpha)
            filename = f"fiche_{_slug(nom)}.html"
            generate_fiche(data, output_dir / filename)
            count += 1
        except Exception as exc:
            logger.warning("Fiche ignorée pour %s : %s", nom, exc)

    logger.info("Fiches générées : %d/%d dans %s", count, len(etudiants), output_dir)
    return count
