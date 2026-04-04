"""Tests du module compas.ema."""

import pytest

from compas.ema import compute_ema, compute_rank, compute_trend


# ---------------------------------------------------------------------------
# compute_ema
# ---------------------------------------------------------------------------


class TestComputeEma:
    def test_empty_returns_none(self):
        assert compute_ema([]) is None

    def test_all_null_returns_none(self):
        assert compute_ema([(1, None), (2, None)]) is None

    def test_single_observation_returns_value(self):
        assert compute_ema([(1, 2)]) == pytest.approx(2.0)

    def test_two_observations(self):
        # EMA(S1) = 1.0 ; EMA(S2) = 0.4*2 + 0.6*1 = 1.4
        assert compute_ema([(1, 1), (2, 2)]) == pytest.approx(1.4)

    def test_null_values_skipped(self):
        # None entre deux observations : résultat identique à deux observations directes
        assert compute_ema([(1, 1), (2, None), (3, 2)]) == pytest.approx(1.4)

    def test_sorted_by_seance_number(self):
        # Entrée dans l'ordre inverse : doit donner le même résultat
        assert compute_ema([(2, 2), (1, 1)]) == pytest.approx(1.4)

    def test_three_observations(self):
        # EMA(1)=1.0 ; EMA(2)=0.4*2+0.6*1=1.4 ; EMA(3)=0.4*0+0.6*1.4=0.84
        assert compute_ema([(1, 1), (2, 2), (3, 0)]) == pytest.approx(0.84)

    def test_negative_scores(self):
        # EMA(1)=-1.0 ; EMA(2)=0.4*(-2)+0.6*(-1)=-1.4
        assert compute_ema([(1, -1), (2, -2)]) == pytest.approx(-1.4)

    def test_custom_alpha(self):
        # alpha=1.0 : EMA = dernière valeur
        assert compute_ema([(1, 1), (2, 2)], alpha=1.0) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# compute_trend
# ---------------------------------------------------------------------------


class TestComputeTrend:
    def test_empty_is_stable(self):
        assert compute_trend([]) == "stable"

    def test_single_observation_is_stable(self):
        assert compute_trend([(1, 1)]) == "stable"

    def test_all_null_is_stable(self):
        assert compute_trend([(1, None), (2, None)]) == "stable"

    def test_increasing_is_up(self):
        # EMA(S1)=0, EMA(S2)=0.4*2+0.6*0=0.8 → 0.8 > 0+0.05
        assert compute_trend([(1, 0), (2, 2)]) == "up"

    def test_decreasing_is_down(self):
        # EMA(S1)=2.0, EMA(S2)=0.4*0+0.6*2=1.2 → 1.2 < 2.0-0.05
        assert compute_trend([(1, 2), (2, 0)]) == "down"

    def test_constant_is_stable(self):
        # EMA(S1)=1.0, EMA(S2)=0.4*1+0.6*1=1.0 → stable
        assert compute_trend([(1, 1), (2, 1)]) == "stable"

    def test_below_threshold_is_stable(self):
        # Variation de 0.04 < 0.05 → stable
        # EMA(S1)=1.0, EMA(S2)=1.04 → besoin : 0.4*x + 0.6 = 1.04 → x=1.1
        assert compute_trend([(1, 1), (2, 1)], threshold=0.05) == "stable"

    def test_null_between_observations_skipped(self):
        # S1=0, S2=None, S3=2 → même résultat que S1=0, S2=2
        assert compute_trend([(1, 0), (2, None), (3, 2)]) == "up"

    def test_custom_threshold(self):
        # Variation de 0.4 avec threshold=0.5 → stable
        assert compute_trend([(1, 0), (2, 1)], threshold=0.5) == "stable"
        # Même variation avec threshold=0.3 → up
        assert compute_trend([(1, 0), (2, 1)], threshold=0.3) == "up"


# ---------------------------------------------------------------------------
# compute_rank
# ---------------------------------------------------------------------------


class TestComputeRank:
    def test_empty_dict_is_alerte(self):
        assert compute_rank({}) == "alerte"

    def test_all_none_is_alerte(self):
        assert compute_rank({"auto": None, "rig": None, "com": None, "eng": None}) == "alerte"

    def test_high_scores_or(self):
        # Moyenne = 1.0 ≥ 0.70
        scores = {"auto": 1.0, "rig": 1.0, "com": 1.0, "eng": 1.0}
        assert compute_rank(scores) == "or"

    def test_at_seuil_or_is_or(self):
        scores = {"auto": 0.70, "rig": 0.70, "com": 0.70, "eng": 0.70}
        assert compute_rank(scores) == "or"

    def test_medium_scores_argent(self):
        # Moyenne = 0.5 → argent (0.25 ≤ 0.5 < 0.70)
        scores = {"auto": 0.5, "rig": 0.5, "com": 0.5, "eng": 0.5}
        assert compute_rank(scores) == "argent"

    def test_at_seuil_argent_is_argent(self):
        scores = {"auto": 0.25, "rig": 0.25, "com": 0.25, "eng": 0.25}
        assert compute_rank(scores) == "argent"

    def test_low_scores_bronze(self):
        # Moyenne = 0.0 → bronze (−0.25 ≤ 0.0 < 0.25)
        scores = {"auto": 0.0, "rig": 0.0, "com": 0.0, "eng": 0.0}
        assert compute_rank(scores) == "bronze"

    def test_at_seuil_bronze_is_bronze(self):
        scores = {"auto": -0.25, "rig": -0.25, "com": -0.25, "eng": -0.25}
        assert compute_rank(scores) == "bronze"

    def test_very_low_scores_alerte(self):
        # Moyenne = -1.0 < −0.25
        scores = {"auto": -1.0, "rig": -1.0, "com": -1.0, "eng": -1.0}
        assert compute_rank(scores) == "alerte"

    def test_none_excluded_from_mean(self):
        # Seul auto=1.0 est observé → moyenne = 1.0 → or
        scores = {"auto": 1.0, "rig": None, "com": None, "eng": None}
        assert compute_rank(scores) == "or"

    def test_mixed_with_none(self):
        # auto=0.5, rig=None, com=0.5, eng=None → moyenne = 0.5 → argent
        scores = {"auto": 0.5, "rig": None, "com": 0.5, "eng": None}
        assert compute_rank(scores) == "argent"

    def test_custom_thresholds(self):
        scores = {"auto": 0.5}
        assert compute_rank(scores, seuil_or=0.8, seuil_argent=0.3, seuil_bronze=0.0) == "argent"
        assert compute_rank(scores, seuil_or=0.8, seuil_argent=0.6, seuil_bronze=0.0) == "bronze"
