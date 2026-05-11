"""Traduction des codes de présence bruts en descriptions lisibles en français."""

from __future__ import annotations

import re


def _is_time_range(s: str) -> bool:
    """Retourne True si s ressemble à une plage horaire (H1-H2 ou XhYY-XhYY)."""
    return bool(re.match(r"^(?:H\d+|\d+h\d*)-(?:H\d+|\d+h\d*)$", s, re.IGNORECASE))


def _describe_token(token: str) -> str:
    """Traduit un token de présence unique (sans virgule) en description française."""
    t = token.strip()
    if not t or t.upper() == "P":
        return "Présent"

    parts = t.split(":", 2)
    code = parts[0].upper()

    if code == "N":
        return "Note sur la feuille papier"

    if code == "D":
        if len(parts) < 2:
            return "Départ anticipé"
        desc = f"Départ définitif à {parts[1]}"
        if len(parts) == 3:
            desc += f" — motif : {parts[2]}"
        return desc

    if code == "A":
        if len(parts) == 1:
            return "Absent toute la séance"
        val = parts[1]
        motif = parts[2] if len(parts) == 3 else None

        if _is_time_range(val):
            m_h = re.match(r"^H(\d+)-H(\d+)$", val, re.IGNORECASE)
            if m_h:
                desc = f"Absent heures {m_h.group(1)}-{m_h.group(2)}"
            else:
                m_t = re.match(r"^(\d+h\d*)-(\d+h\d*)$", val, re.IGNORECASE)
                desc = (
                    f"Absent de {m_t.group(1)} à {m_t.group(2)}"
                    if m_t else f"Absent {val}"
                )
            if motif:
                desc += f" — motif : {motif}"
            return desc

        desc = "Absent toute la séance"
        if val:
            desc += f" — motif : {val}"
        return desc

    if code == "R":
        if len(parts) < 2:
            return "Retard en début de cours"
        val, motif = parts[1], (parts[2] if len(parts) == 3 else None)
        desc = (
            f"Retard de {val} min en début de cours"
            if val.isdigit()
            else f"Arrivée tardive à {val}"
        )
        if motif:
            desc += f" — motif : {motif}"
        return desc

    if code == "RR":
        if len(parts) < 2:
            return "Retard après la récréation"
        val, motif = parts[1], (parts[2] if len(parts) == 3 else None)
        desc = (
            f"Retard de {val} min après la récréation"
            if val.isdigit()
            else f"Arrivée après la récréation à {val}"
        )
        if motif:
            desc += f" — motif : {motif}"
        return desc

    return t


def describe_presence(code: str | None) -> str:
    """Traduit un code de présence brut en description lisible en français.

    Supporte la syntaxe TYPE:valeur:motif et les combinaisons par virgule.

    Args:
        code: Code brut de présence (ex : 'R:15', 'A:H1-H2', 'R:5,RR:10').

    Returns:
        Description lisible, ex : 'Retard de 15 min en début de cours'.
        Les combinaisons sont séparées par ' + '.
    """
    if not code or code.strip().upper() == "P":
        return "Présent"

    tokens = [tok.strip() for tok in code.split(",")]
    return " + ".join(_describe_token(tok) for tok in tokens)
