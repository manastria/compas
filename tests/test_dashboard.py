"""Tests du module compas.dashboard — parsing de présence."""

import pytest

from compas.dashboard import _is_time_range, _parse_one_token, _parse_presence


# ---------------------------------------------------------------------------
# _is_time_range
# ---------------------------------------------------------------------------


class TestIsTimeRange:
    def test_h1_h2(self):
        assert _is_time_range("H1-H2") is True

    def test_h3_h4(self):
        assert _is_time_range("H3-H4") is True

    def test_heure_heure(self):
        assert _is_time_range("9h15-10h00") is True

    def test_heure_sans_minutes(self):
        assert _is_time_range("9h-10h") is True

    def test_motif_word(self):
        assert _is_time_range("medical") is False

    def test_bare_absence(self):
        assert _is_time_range("A") is False

    def test_single_heure(self):
        assert _is_time_range("9h30") is False


# ---------------------------------------------------------------------------
# _parse_one_token
# ---------------------------------------------------------------------------


class TestParseOneToken:
    def test_empty_is_present(self):
        assert _parse_one_token("", None) == ("P", 0)

    def test_p_is_present(self):
        assert _parse_one_token("P", None) == ("P", 0)

    def test_a_is_absent(self):
        assert _parse_one_token("A", None) == ("A", 0)

    def test_a_with_motif_is_absent(self):
        assert _parse_one_token("A:medical", None) == ("A", 0)

    def test_a_with_time_range_h_is_present(self):
        # Absence partielle H1-H2 → présent pour les stats
        assert _parse_one_token("A:H1-H2", None) == ("P", 0)

    def test_a_with_time_range_h_and_motif(self):
        assert _parse_one_token("A:H1-H2:exam", None) == ("P", 0)

    def test_a_with_heure_range_is_present(self):
        assert _parse_one_token("A:9h15-10h00", None) == ("P", 0)

    def test_a_with_heure_range_and_motif(self):
        assert _parse_one_token("A:9h15-10h00:medical", None) == ("P", 0)

    def test_r_minutes(self):
        assert _parse_one_token("R:15", None) == ("R", 15)

    def test_r_zero_minutes(self):
        assert _parse_one_token("R:0", None) == ("R", 0)

    def test_r_heure_with_debut(self):
        # Arrivée à 9h30, début 8h00 → 90 min de retard
        assert _parse_one_token("R:9h30", "8h00") == ("R", 90)

    def test_r_heure_with_motif(self):
        assert _parse_one_token("R:9h30:medical", "8h00") == ("R", 90)

    def test_r_heure_without_debut(self):
        # Pas d'heure de début → retard calculé à 0
        assert _parse_one_token("R:9h30", None) == ("R", 0)

    def test_rr_minutes(self):
        assert _parse_one_token("RR:10", None) == ("R", 10)

    def test_rr_with_motif(self):
        assert _parse_one_token("RR:10:fatigue", None) == ("R", 10)

    def test_d_is_present(self):
        # Départ anticipé : était là au début
        assert _parse_one_token("D:10h15", None) == ("P", 0)

    def test_d_with_motif(self):
        assert _parse_one_token("D:10h15:medical", None) == ("P", 0)

    def test_n_is_present(self):
        assert _parse_one_token("N", None) == ("P", 0)

    # --- Rétrocompatibilité ---

    def test_retrocompat_r15(self):
        assert _parse_one_token("R15", None) == ("R", 15)

    def test_retrocompat_bare_heure(self):
        assert _parse_one_token("9h30", "8h00") == ("R", 90)


# ---------------------------------------------------------------------------
# _parse_presence — combinaisons et cas dégénérés
# ---------------------------------------------------------------------------


class TestParsePresence:
    def test_none_is_present(self):
        assert _parse_presence(None, None) == ("P", 0)

    def test_empty_is_present(self):
        assert _parse_presence("", None) == ("P", 0)

    def test_p_is_present(self):
        assert _parse_presence("P", None) == ("P", 0)

    def test_a_is_absent(self):
        assert _parse_presence("A", None) == ("A", 0)

    def test_a_with_motif_is_absent(self):
        assert _parse_presence("A:medical", None) == ("A", 0)

    def test_r_minutes(self):
        assert _parse_presence("R:15", None) == ("R", 15)

    def test_r_heure(self):
        assert _parse_presence("R:9h30", "8h00") == ("R", 90)

    def test_rr_minutes(self):
        assert _parse_presence("RR:10", None) == ("R", 10)

    def test_d_is_present(self):
        assert _parse_presence("D:10h15", None) == ("P", 0)

    def test_n_is_present(self):
        assert _parse_presence("N", None) == ("P", 0)

    def test_combination_r_rr(self):
        # R:5 + RR:10 → présent, 15 min de retard cumulés
        assert _parse_presence("R:5,RR:10", None) == ("R", 15)

    def test_combination_r_d(self):
        # R:10 + D:11h30 → présent avec retard, départ anticipé ne compte pas
        assert _parse_presence("R:10,D:11h30:medical", None) == ("R", 10)

    def test_combination_partial_absence_rr(self):
        # A:H1-H2 (absent partiel = présent) + RR:5
        assert _parse_presence("A:H1-H2,RR:5", None) == ("R", 5)

    def test_combination_r_n(self):
        # R:5 + N → présent avec retard, note sur feuille
        assert _parse_presence("R:5,N", None) == ("R", 5)

    def test_full_absent_overrides_combination(self):
        # A (absent total) + RR:5 → absent
        assert _parse_presence("A,RR:5", None) == ("A", 0)

    def test_a_motif_overrides_combination(self):
        # A:medical (absent total) → absent
        assert _parse_presence("A:medical,R:5", None) == ("A", 0)

    def test_partial_absence_not_absent(self):
        # A:H1-H2 seul → présent pour les stats
        assert _parse_presence("A:H1-H2", None) == ("P", 0)

    def test_retrocompat_r15(self):
        assert _parse_presence("R15", None) == ("R", 15)

    def test_retrocompat_bare_heure(self):
        assert _parse_presence("9h30", "8h00") == ("R", 90)
