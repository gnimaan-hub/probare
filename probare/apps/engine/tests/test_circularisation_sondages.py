"""Tests unitaires — Circularisation (NEP 505) et Sondages sur pièces (NEP 530)."""
import pytest
from probare_engine.provenance.models import DonneeSourcee
from probare_engine.controls.circularisation import proposer_tiers, calculer_ecart
from probare_engine.controls.sondages import (
    calculer_taille_echantillon,
    selectionner_echantillon,
    projeter_erreur,
)

PID = "test-projet-circ-001"
FID = "fid-001"


def _ds(id_: str, valeur, localisation: str, type_: str = "montant") -> DonneeSourcee:
    return DonneeSourcee(
        id=id_, projet_id=PID, fichier_source_id=FID,
        valeur=valeur, type=type_, localisation=localisation,
    )


def _row(compte: str, libelle: str, solde: float, i: int) -> dict:
    return {
        "compte": _ds(f"c{i}", compte, f"GL:{i}:Compte", "compte"),
        "libelle": _ds(f"l{i}", libelle, f"GL:{i}:Libelle", "texte"),
        "solde": _ds(f"s{i}", solde, f"GL:{i}:Solde"),
    }


# ─── Circularisation — proposer_tiers ─────────────────────────────────────────

class TestProposerTiers:
    def test_retourne_top_n_par_solde_absolu(self):
        rows = [
            _row("411001", "Client A", 100_000, 1),
            _row("411002", "Client B", 500_000, 2),
            _row("411003", "Client C", -300_000, 3),
            _row("512001", "Banque", 800_000, 4),  # hors préfixe
        ]
        result = proposer_tiers(rows, prefixes=["41"], n=2)
        assert len(result) == 2
        assert result[0]["compte"] == "411002"  # 500k absolu le plus élevé
        assert result[1]["compte"] == "411003"  # 300k

    def test_n_superieur_a_la_population(self):
        rows = [_row("411001", "Client X", 50_000, 1)]
        result = proposer_tiers(rows, prefixes=["41"], n=10)
        assert len(result) == 1

    def test_prefixe_vide_renvoie_liste_vide(self):
        rows = [_row("411001", "Client X", 50_000, 1)]
        result = proposer_tiers(rows, prefixes=["99"], n=5)
        assert result == []

    def test_solde_inclus_dans_resultat(self):
        rows = [_row("411001", "Client A", 123_456, 1)]
        result = proposer_tiers(rows, prefixes=["41"], n=1)
        assert result[0]["solde"] == pytest.approx(123_456.0)

    def test_sources_presentes(self):
        rows = [_row("411001", "Client A", 123_456, 1)]
        result = proposer_tiers(rows, prefixes=["41"], n=1)
        assert len(result[0]["sources"]) > 0


# ─── Circularisation — calculer_ecart ─────────────────────────────────────────

class TestCalculerEcart:
    def test_sans_ecart(self):
        res = calculer_ecart(100_000.0, 100_000.0)
        assert res["ecart"] == 0.0
        assert res["ecart_pct"] == 0.0
        assert res["est_significatif"] is False

    def test_ecart_significatif_par_pct(self):
        res = calculer_ecart(100_000.0, 90_000.0)
        assert res["ecart"] == pytest.approx(10_000.0)
        assert res["ecart_pct"] == pytest.approx(10.0, rel=0.01)
        assert res["est_significatif"] is True

    def test_ecart_faible_non_significatif(self):
        # ecart = 50 < 100 et pct < 5% → non significatif
        res = calculer_ecart(100_000.0, 99_950.0)
        assert abs(res["ecart_pct"]) < 5.0
        assert abs(res["ecart"]) < 100.0
        assert res["est_significatif"] is False

    def test_solde_comptable_zero(self):
        res = calculer_ecart(0.0, 5_000.0)
        assert res["ecart"] == pytest.approx(-5_000.0)
        assert res["ecart_pct"] == 0.0

    def test_ecart_negatif(self):
        res = calculer_ecart(80_000.0, 100_000.0)
        assert res["ecart"] < 0
        assert res["est_significatif"] is True


# ─── Sondages — calculer_taille_echantillon ──────────────────────────────────

class TestCalculerTailleEchantillon:
    def test_population_normale(self):
        res = calculer_taille_echantillon(500, 0.05, 95)
        assert res["taille_recommandee"] >= 1
        assert res["taille_recommandee"] <= 500
        assert res["population"] == 500

    def test_population_large_taux_faible(self):
        res1 = calculer_taille_echantillon(1000, 0.02, 95)
        res2 = calculer_taille_echantillon(1000, 0.10, 95)
        assert res1["taille_recommandee"] > res2["taille_recommandee"]

    def test_confiance_elevee_plus_grand_echantillon(self):
        res90 = calculer_taille_echantillon(500, 0.05, 90)
        res99 = calculer_taille_echantillon(500, 0.05, 99)
        assert res99["taille_recommandee"] >= res90["taille_recommandee"]

    def test_population_tres_petite(self):
        res = calculer_taille_echantillon(5, 0.05, 95)
        assert res["taille_recommandee"] <= 5
        assert res["taille_recommandee"] >= 1

    def test_population_zero(self):
        res = calculer_taille_echantillon(0, 0.05, 95)
        assert res["taille_recommandee"] >= 1


# ─── Sondages — selectionner_echantillon ────────────────────────────────────

class TestSelectionnerEchantillon:
    def _make_rows(self, n: int, prefix: str = "41") -> list:
        return [_row(f"{prefix}{i:04d}", f"Écriture {i}", float(i * 100), i) for i in range(1, n + 1)]

    def test_selectionne_n_elements(self):
        rows = self._make_rows(100)
        result = selectionner_echantillon(rows, ["41"], n=10, seed=42)
        assert len(result) == 10

    def test_deterministe_avec_seed(self):
        rows = self._make_rows(100)
        r1 = selectionner_echantillon(rows, ["41"], n=10, seed=42)
        r2 = selectionner_echantillon(rows, ["41"], n=10, seed=42)
        assert [e["compte"] for e in r1] == [e["compte"] for e in r2]

    def test_seed_different_donne_resultat_different(self):
        rows = self._make_rows(100)
        r1 = selectionner_echantillon(rows, ["41"], n=10, seed=42)
        r2 = selectionner_echantillon(rows, ["41"], n=10, seed=99)
        assert [e["compte"] for e in r1] != [e["compte"] for e in r2]

    def test_filtre_par_prefixe(self):
        rows = self._make_rows(50, prefix="41") + self._make_rows(50, prefix="51")
        result = selectionner_echantillon(rows, ["41"], n=20, seed=1)
        for e in result:
            assert e["compte"].startswith("41")

    def test_n_superieur_a_candidats(self):
        rows = self._make_rows(5)
        result = selectionner_echantillon(rows, ["41"], n=100, seed=1)
        assert len(result) == 5

    def test_provenance_dans_resultat(self):
        rows = self._make_rows(10)
        result = selectionner_echantillon(rows, ["41"], n=3, seed=7)
        for e in result:
            assert "sources" in e
            assert "montant" in e
            assert "compte" in e


# ─── Sondages — projeter_erreur ──────────────────────────────────────────────

class TestProjecterErreur:
    def test_sans_anomalie(self):
        res = projeter_erreur(0, 0.0, 1_000_000.0, 100)
        assert res["taux_anomalie"] == 0.0
        assert res["montant_projete_population"] == 0.0

    def test_projection_standard(self):
        # 2 anomalies / 100 échantillon, 500 Fdj anomalies, pop 1M
        # projection = (500/100) × 1_000_000 = 5_000_000
        res = projeter_erreur(2, 500.0, 1_000_000.0, 100)
        assert res["taux_anomalie"] == pytest.approx(0.02)
        assert res["montant_projete_population"] == pytest.approx(5_000_000.0, rel=0.01)

    def test_echantillon_zero(self):
        res = projeter_erreur(0, 0.0, 500_000.0, 0)
        assert res["taux_anomalie"] == 0.0
        assert res["montant_projete_population"] == 0.0

    def test_toutes_anomalies(self):
        # 10/10 anomalies, 10_000 Fdj / 10 × 100_000 = 100_000_000
        res = projeter_erreur(10, 10_000.0, 100_000.0, 10)
        assert res["taux_anomalie"] == pytest.approx(1.0)
        assert res["montant_projete_population"] == pytest.approx(100_000_000.0)

    def test_champs_retournes(self):
        res = projeter_erreur(1, 200.0, 50_000.0, 20)
        assert "taux_anomalie" in res
        assert "montant_anomalies_echantillon" in res
        assert "montant_projete_population" in res
        assert "nb_anomalies" in res
        assert "taille_echantillon" in res
