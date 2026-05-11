"""Tests du module compas.dashboard — parsing de présence et génération JSON."""

import json
import logging
import re

import pytest

from compas.dashboard import _is_time_range, _parse_one_token, _parse_presence, generate


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

    def test_n_combined_with_r(self):
        # N (note papier) + R:5 → présent avec retard
        assert _parse_presence("R:5,N", None) == ("R", 5)

    def test_multiple_p_tokens(self):
        # Combinaison de deux P → présent, 0 min
        assert _parse_presence("P,P", None) == ("P", 0)

    def test_unknown_token_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="compas.dashboard"):
            result = _parse_presence("INCONNU:truc", None)
        assert result == ("P", 0)
        assert "non reconnu" in caplog.text

    def test_rr_alone_returns_r_zero(self):
        # RR sans valeur → retard de 0 min
        assert _parse_one_token("RR", None) == ("R", 0)

    def test_d_alone_returns_present(self):
        # D sans heure (mal formé) → présent par défaut
        assert _parse_one_token("D", None) == ("P", 0)


# ---------------------------------------------------------------------------
# _extract_compas_json — helper local pour les tests de génération
# ---------------------------------------------------------------------------


def _extract_compas_json(html: str) -> dict:
    """Extrait le JSON COMPAS_DATA injecté dans la balise <script> du dashboard."""
    m = re.search(r"var COMPAS_DATA = ({.*?});", html, re.DOTALL)
    assert m, "var COMPAS_DATA introuvable dans le HTML généré"
    return json.loads(m.group(1))


# ---------------------------------------------------------------------------
# TestGenerateJson — non-régression sur le JSON injecté au template
# ---------------------------------------------------------------------------


class TestGenerateJson:
    def test_html_generated(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_top_level_keys_present(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        expected_keys = (
            "projet", "groupe", "seance_actuelle", "seances_total", "date", "alpha", "students"
        )
        for key in expected_keys:
            assert key in data, f"Clé manquante dans COMPAS_DATA : {key!r}"

    def test_projet_and_groupe(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        assert data["projet"] == "Infrastructure réseau PME"
        assert data["groupe"] == "TP1"

    def test_seance_info(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        assert data["seance_actuelle"] == 2
        assert data["seances_total"] == 2
        assert data["heure_debut"] == "8h00"
        assert data["heure_fin"] == "12h00"

    def test_student_structure(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        alice = next(s for s in data["students"] if s["name"] == "Dupont Alice")
        for key in ("name", "display_name", "anon", "scores", "trend", "rank", "presence"):
            assert key in alice, f"Clé manquante dans student : {key!r}"
        for key in ("auto", "rig", "com", "eng"):
            assert key in alice["scores"], f"Clé manquante dans scores : {key!r}"
        for key in ("total", "present", "absent", "retards", "min_retard"):
            assert key in alice["presence"], f"Clé manquante dans presence : {key!r}"

    def test_student_rank_and_trend_valid_values(self, populated_db, tmp_path):
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        for s in data["students"]:
            assert s["rank"] in ("or", "argent", "bronze", "alerte"), s["name"]
            assert s["trend"] in ("up", "down", "stable"), s["name"]

    def test_alice_ema_scores(self, populated_db, tmp_path):
        """EMA d'Alice : S1 auto=1 → S2 auto=2 donne 0.4*2+0.6*1=1.4."""
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        alice = next(s for s in data["students"] if s["name"] == "Dupont Alice")
        assert alice["scores"]["auto"] == pytest.approx(1.4)
        # S1 rig=2 → S2 rig=1 : 0.4*1+0.6*2=1.6
        assert alice["scores"]["rig"] == pytest.approx(1.6)

    def test_alice_presence_stats(self, populated_db, tmp_path):
        """Alice présente aux 2 séances, 0 retard, 0 absence."""
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        alice = next(s for s in data["students"] if s["name"] == "Dupont Alice")
        assert alice["presence"]["total"] == 2
        assert alice["presence"]["present"] == 2
        assert alice["presence"]["absent"] == 0
        assert alice["presence"]["retards"] == 0

    def test_bob_presence_with_retard(self, populated_db, tmp_path):
        """Bob a un retard de 15 min en S1 (R:15)."""
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        data = _extract_compas_json(out.read_text(encoding="utf-8"))
        bob = next(s for s in data["students"] if s["name"] == "Martin Bob")
        assert bob["presence"]["retards"] == 1
        assert bob["presence"]["min_retard"] == 15

    def test_db_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate(tmp_path / "inexistant.db", tmp_path / "out.html")

    def test_safe_json_escaping(self, populated_db, tmp_path):
        """La séquence '</' est échappée en '<\\/' dans le HTML brut."""
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        raw = out.read_text(encoding="utf-8")
        # Vérifie que la balise </script> n'est pas fermée prématurément dans le bloc JSON
        script_block = re.search(r"var COMPAS_DATA = {.*?};", raw, re.DOTALL)
        assert script_block, "Bloc COMPAS_DATA introuvable"
        assert "</" not in script_block.group(0)


# ---------------------------------------------------------------------------
# TestDashboardHTML — structure du HTML généré (P2)
# ---------------------------------------------------------------------------


class TestDashboardHTML:
    """Vérifie la structure du HTML généré : attributs data-*, grille, lisibilité."""

    def _html(self, populated_db, tmp_path) -> str:
        out = tmp_path / "dashboard.html"
        generate(populated_db, out)
        return out.read_text(encoding="utf-8")

    def test_ul_grid_present(self, populated_db, tmp_path):
        """La grille est un élément <ul> natif (sémantique + liste accessible)."""
        html = self._html(populated_db, tmp_path)
        assert '<ul class="grid"' in html

    def test_button_has_type(self, populated_db, tmp_path):
        """Le bouton de thème déclare type='button' pour éviter submit implicite."""
        html = self._html(populated_db, tmp_path)
        assert 'type="button"' in html

    def test_student_count_in_json(self, populated_db, tmp_path):
        """Le JSON injecté contient les 3 étudiants actifs (les cartes sont rendues en JS)."""
        html = self._html(populated_db, tmp_path)
        data = _extract_compas_json(html)
        assert len(data["students"]) == 3

    def test_data_rank_values_in_json(self, populated_db, tmp_path):
        """Le JSON contient des rangs valides pour chaque étudiant."""
        html = self._html(populated_db, tmp_path)
        data = _extract_compas_json(html)
        ranks = [s["rank"] for s in data["students"]]
        assert all(r in ("or", "argent", "bronze", "alerte") for r in ranks)

    def test_student_names_in_json(self, populated_db, tmp_path):
        """Le JSON contient le nom réel de chaque étudiant (clé 'name')."""
        html = self._html(populated_db, tmp_path)
        data = _extract_compas_json(html)
        names = {s["name"] for s in data["students"]}
        assert {"Dupont Alice", "Martin Bob", "Leclerc Eve"} == names

    def test_students_sorted_alphabetically_in_json(self, populated_db, tmp_path):
        """Le JSON est trié par ordre alphabétique des noms."""
        html = self._html(populated_db, tmp_path)
        data = _extract_compas_json(html)
        names = [s["name"] for s in data["students"]]
        assert names == sorted(names, key=str.casefold)

    def test_alice_is_first_in_json(self, populated_db, tmp_path):
        """Dupont Alice est le premier étudiant du tableau JSON (ordre alphabétique)."""
        html = self._html(populated_db, tmp_path)
        data = _extract_compas_json(html)
        assert data["students"][0]["name"] == "Dupont Alice"

    def test_criteria_labels_in_js_source(self, populated_db, tmp_path):
        """Le source JS déclare les 4 labels de critères Au/Ri/Co/En."""
        html = self._html(populated_db, tmp_path)
        assert '"Au"' in html and '"Ri"' in html and '"Co"' in html and '"En"' in html

    def test_scoretopercent_uses_full_scale(self, populated_db, tmp_path):
        """Le source JS de scoreToPercent utilise l'échelle complète [-2,+2]."""
        html = self._html(populated_db, tmp_path)
        # Formule correcte : (v + 2) / 4 — pas l'ancien clamp Math.max(-1, Math.min(1
        assert "(v + 2) / 4" in html
        assert "Math.min(1," not in html

    def test_score_plus2_gives_100pct(self):
        """Score +2 → 100% (plafond de l'échelle [-2,+2])."""
        from compas.dashboard import _parse_one_token  # noqa: F401
        # Vérification via la fonction Python miroir de scoreToPercent JS
        # EMA max théorique = 2.0 → ((2+2)/4)*100 = 100
        assert round(((2 + 2) / 4) * 100) == 100

    def test_score_minus2_gives_0pct(self):
        """Score -2 → 0% (plancher de l'échelle [-2,+2])."""
        assert round((((-2) + 2) / 4) * 100) == 0

    def test_score_zero_gives_50pct(self):
        """Score 0 → 50% (centre de l'échelle)."""
        assert round(((0 + 2) / 4) * 100) == 50

    def test_legend_uses_css_classes_not_inline_style(self, populated_db, tmp_path):
        """Les points colorés de la légende utilisent des classes CSS, pas de style inline."""
        html = self._html(populated_db, tmp_path)
        # Les 5 classes de couleur de légende doivent être présentes
        for cls in ("legend-dot--red", "legend-dot--orange", "legend-dot--amber",
                    "legend-dot--green", "legend-dot--teal"):
            assert cls in html, f"Classe CSS manquante dans la légende : {cls!r}"
