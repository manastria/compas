"""Tests pour presence_desc et fiche individuelle."""

from pathlib import Path

import pytest

from compas.presence_desc import describe_presence


class TestDescribePresence:
    """Tests unitaires de describe_presence."""

    def test_none(self) -> None:
        assert describe_presence(None) == "Présent"

    def test_empty(self) -> None:
        assert describe_presence("") == "Présent"

    def test_p(self) -> None:
        assert describe_presence("P") == "Présent"

    def test_p_lowercase(self) -> None:
        assert describe_presence("p") == "Présent"

    def test_absent(self) -> None:
        assert describe_presence("A") == "Absent toute la séance"

    def test_absent_motif(self) -> None:
        assert describe_presence("A:medical") == "Absent toute la séance — motif : medical"

    def test_absent_heures(self) -> None:
        assert describe_presence("A:H3-H4") == "Absent heures 3-4"

    def test_absent_heures_motif(self) -> None:
        result = describe_presence("A:H3-H4:infirmerie")
        assert result == "Absent heures 3-4 — motif : infirmerie"

    def test_absent_plage_horaire(self) -> None:
        assert describe_presence("A:9h15-10h00") == "Absent de 9h15 à 10h00"

    def test_absent_h1_h2(self) -> None:
        assert describe_presence("A:H1-H2") == "Absent heures 1-2"

    def test_retard_minutes(self) -> None:
        assert describe_presence("R:15") == "Retard de 15 min en début de cours"

    def test_retard_heure(self) -> None:
        assert describe_presence("R:9h30") == "Arrivée tardive à 9h30"

    def test_retard_heure_motif(self) -> None:
        result = describe_presence("R:9h30:transport")
        assert result == "Arrivée tardive à 9h30 — motif : transport"

    def test_retard_apres_recre_minutes(self) -> None:
        assert describe_presence("RR:10") == "Retard de 10 min après la récréation"

    def test_retard_apres_recre_motif(self) -> None:
        result = describe_presence("RR:10:discussion")
        assert result == "Retard de 10 min après la récréation — motif : discussion"

    def test_depart_definitif(self) -> None:
        assert describe_presence("D:10h15") == "Départ définitif à 10h15"

    def test_depart_definitif_motif(self) -> None:
        result = describe_presence("D:10h15:medical")
        assert result == "Départ définitif à 10h15 — motif : medical"

    def test_note(self) -> None:
        assert describe_presence("N") == "Note sur la feuille papier"

    # Combinaisons

    def test_combinaison_r_rr(self) -> None:
        result = describe_presence("R:5,RR:10")
        assert result == (
            "Retard de 5 min en début de cours + Retard de 10 min après la récréation"
        )

    def test_combinaison_r_depart_motif(self) -> None:
        result = describe_presence("R:10,D:11h30:medical")
        assert result == (
            "Retard de 10 min en début de cours + Départ définitif à 11h30 — motif : medical"
        )

    def test_combinaison_absence_partielle_rr(self) -> None:
        result = describe_presence("A:H1-H2,RR:5")
        assert result == "Absent heures 1-2 + Retard de 5 min après la récréation"

    def test_combinaison_r_note(self) -> None:
        result = describe_presence("R:5,N")
        assert result == "Retard de 5 min en début de cours + Note sur la feuille papier"

    def test_combinaison_retard_depart(self) -> None:
        result = describe_presence("R:10,D:11h30:medical")
        assert "Retard de 10 min en début de cours" in result
        assert "Départ définitif à 11h30" in result

    def test_absent_sans_motif_texte_vide(self) -> None:
        # A:H1 n'est pas une plage : absent toute la séance
        result = describe_presence("A:nonrange")
        assert result == "Absent toute la séance — motif : nonrange"


class TestComputeStudentData:
    """Tests de compute_student_data sur la fixture populated_db."""

    def test_structure_cles(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.row_factory = sqlite3.Row
        eid = conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()["id"]
        conn.close()

        data = compute_student_data(populated_db, int(eid))
        expected = {
            "student", "scores", "history", "ema_history",
            "events", "pres_events", "projects",
        }
        assert set(data.keys()) == expected

    def test_student_info(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        conn.row_factory = sqlite3.Row
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()["id"])
        conn.close()

        data = compute_student_data(populated_db, eid)
        s = data["student"]
        assert s["name"] == "Dupont Alice"
        assert s["display_name"] == "Dupont Alice"
        assert s["rank"] in ("or", "argent", "bronze", "alerte")

    def test_scores_cles(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        assert set(data["scores"].keys()) == {"auto", "rig", "com", "eng"}
        for key, val in data["scores"].items():
            assert "ema" in val and "trend" in val
            assert val["trend"] in ("up", "down", "stable")

    def test_presence_stats(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        pres = data["student"]["presence"]
        assert set(pres.keys()) == {
            "total", "present", "absent", "retards_r", "retards_rr",
            "min_r", "min_rr", "taux"
        }
        assert pres["total"] == pres["present"] + pres["absent"]
        assert 0 <= pres["taux"] <= 100

    def test_retard_compte(self, populated_db: Path) -> None:
        """Martin Bob a R:15 en S1 → retards_r=1, min_r=15."""
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Martin Bob'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        pres = data["student"]["presence"]
        assert pres["retards_r"] == 1
        assert pres["min_r"] == 15
        assert pres["retards_rr"] == 0

    def test_history_non_vide(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        assert len(data["history"]) >= 1
        entry = data["history"][0]
        assert "date" in entry and "seance" in entry and "pres" in entry

    def test_ema_history_ne_contient_pas_absences(self, populated_db: Path) -> None:
        """Leclerc Eve (absente S1, pas de S2) → ema_history vide."""
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Leclerc Eve'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        # Leclerc Eve est absente S1 (aucune observation) → ema_history vide
        assert data["ema_history"] == []

    def test_db_inexistante(self, tmp_path: Path) -> None:
        from compas.fiche import compute_student_data

        with pytest.raises(FileNotFoundError):
            compute_student_data(tmp_path / "nonexistent.db", 1)

    def test_etudiant_inexistant(self, populated_db: Path) -> None:
        from compas.fiche import compute_student_data

        with pytest.raises(ValueError):
            compute_student_data(populated_db, 9999)

    def test_single_project_no_projects_section(self, populated_db: Path) -> None:
        """Un étudiant dans un seul projet → projects est vide."""
        from compas.fiche import compute_student_data
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        assert data["projects"] == []


class TestGenerateFiche:
    """Tests de generate_fiche : création du fichier HTML avec JSON correct."""

    def test_fichier_cree(self, populated_db: Path, tmp_path: Path) -> None:
        from compas.fiche import compute_student_data, generate_fiche
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        out = tmp_path / "fiche_dupont_alice.html"
        generate_fiche(data, out)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "COMPAS_FICHE_DATA" in content

    def test_json_contenu(self, populated_db: Path, tmp_path: Path) -> None:
        from compas.fiche import compute_student_data, generate_fiche
        import json
        import re
        import sqlite3

        conn = sqlite3.connect(populated_db)
        eid = int(conn.execute(
            "SELECT id FROM etudiants WHERE nom='Dupont Alice'"
        ).fetchone()[0])
        conn.close()

        data = compute_student_data(populated_db, eid)
        out = tmp_path / "fiche.html"
        generate_fiche(data, out)

        content = out.read_text(encoding="utf-8")
        m = re.search(r"var COMPAS_FICHE_DATA\s*=\s*(\{.*?\});", content, re.DOTALL)
        assert m is not None
        parsed = json.loads(m.group(1))
        assert parsed["student"]["name"] == "Dupont Alice"
        assert "scores" in parsed
        assert "history" in parsed


class TestGenerateAllFiches:
    """Tests de generate_all_fiches."""

    def test_genere_etudiants_actifs(self, populated_db: Path, tmp_path: Path) -> None:
        from compas.fiche import generate_all_fiches

        out_dir = tmp_path / "fiches"
        count = generate_all_fiches(populated_db, out_dir)
        # Les 3 étudiants sont actifs : date_depart de Leclerc Eve (2026-02-15)
        # est postérieure à la dernière séance (2026-01-22)
        assert count == 3
        assert out_dir.exists()
        html_files = list(out_dir.glob("*.html"))
        assert len(html_files) == 3

    def test_filtre_par_nom(self, populated_db: Path, tmp_path: Path) -> None:
        from compas.fiche import generate_all_fiches

        out_dir = tmp_path / "fiches"
        count = generate_all_fiches(populated_db, out_dir, name_filter="Dupont")
        assert count == 1

    def test_filtre_nom_inexistant(self, populated_db: Path, tmp_path: Path) -> None:
        from compas.fiche import generate_all_fiches

        with pytest.raises(ValueError, match="Aucun étudiant"):
            generate_all_fiches(populated_db, tmp_path / "fiches", name_filter="ZZZ")

    def test_db_inexistante(self, tmp_path: Path) -> None:
        from compas.fiche import generate_all_fiches

        with pytest.raises(FileNotFoundError):
            generate_all_fiches(tmp_path / "nonexistent.db", tmp_path / "fiches")
