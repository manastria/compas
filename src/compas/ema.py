"""Calcul EMA (Exponential Moving Average), tendances et rangs."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_DEFAULT_ALPHA = 0.4
_DEFAULT_THRESHOLD = 0.05
_DEFAULT_SEUIL_OR = 0.70
_DEFAULT_SEUIL_ARGENT = 0.25
_DEFAULT_SEUIL_BRONZE = -0.25


def _ema_sequence(
    observations: list[tuple[int, int | None]],
    alpha: float,
) -> list[float]:
    """Calcule la séquence d'EMAs pour une liste d'observations triées par séance.

    Les séances sont triées par numéro croissant. Les valeurs None sont ignorées :
    on passe à l'observation suivante sans mettre à jour l'EMA.

    Args:
        observations: Liste de tuples (numéro_séance, score). Score peut être None.
        alpha: Coefficient de lissage (0 < alpha ≤ 1).

    Returns:
        Liste des EMAs calculées, une par observation non-None.
    """
    emas: list[float] = []
    for _, value in sorted(observations, key=lambda x: x[0]):
        if value is None:
            continue
        if not emas:
            emas.append(float(value))
        else:
            emas.append(alpha * float(value) + (1.0 - alpha) * emas[-1])
    return emas


def compute_ema(
    observations: list[tuple[int, int | None]],
    alpha: float = _DEFAULT_ALPHA,
) -> float | None:
    """Calcule l'EMA courante d'une séquence d'observations.

    Args:
        observations: Liste de tuples (numéro_séance, score). Score peut être None.
        alpha: Coefficient de lissage (défaut 0.4).

    Returns:
        EMA courante ou None si aucune observation non-None.
    """
    seq = _ema_sequence(observations, alpha)
    return seq[-1] if seq else None


def compute_trend(
    observations: list[tuple[int, int | None]],
    alpha: float = _DEFAULT_ALPHA,
    threshold: float = _DEFAULT_THRESHOLD,
) -> str:
    """Détermine la tendance en comparant les deux dernières EMAs.

    La tendance est calculée entre l'EMA courante et l'EMA de la séance précédente
    ayant une valeur observée.

    Args:
        observations: Liste de tuples (numéro_séance, score).
        alpha: Coefficient de lissage (défaut 0.4).
        threshold: Variation minimale pour déclarer une tendance (défaut 0.05).

    Returns:
        'up' si hausse, 'down' si baisse, 'stable' sinon.
    """
    seq = _ema_sequence(observations, alpha)
    if len(seq) < 2:
        return "stable"
    current, previous = seq[-1], seq[-2]
    if current > previous + threshold:
        return "up"
    if current < previous - threshold:
        return "down"
    return "stable"


def compute_rank(
    ema_scores: dict[str, float | None],
    seuil_or: float = _DEFAULT_SEUIL_OR,
    seuil_argent: float = _DEFAULT_SEUIL_ARGENT,
    seuil_bronze: float = _DEFAULT_SEUIL_BRONZE,
) -> str:
    """Détermine le rang d'un étudiant selon la moyenne de ses EMAs.

    Les critères à EMA None sont exclus du calcul de la moyenne.

    Args:
        ema_scores: Dictionnaire critère → EMA (None si aucune observation).
        seuil_or: Seuil minimal pour le rang Or (défaut 0.70).
        seuil_argent: Seuil minimal pour le rang Argent (défaut 0.25).
        seuil_bronze: Seuil minimal pour le rang Bronze (défaut −0.25).

    Returns:
        'or', 'argent', 'bronze' ou 'alerte'.
    """
    values = [v for v in ema_scores.values() if v is not None]
    if not values:
        return "alerte"
    mean = sum(values) / len(values)
    if mean >= seuil_or:
        return "or"
    if mean >= seuil_argent:
        return "argent"
    if mean >= seuil_bronze:
        return "bronze"
    return "alerte"
