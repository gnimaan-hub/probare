"""Balances à quatre colonnes : soldes ≠ mouvements.

Régression constatée sur données réelles (projet ARULOS 2024, BG_2024.xlsx) :
la balance porte « mvt débit », « mvt crédit », « solde débit », « solde
crédit ». Les colonnes de solde étaient classées comme des mouvements (les
deux contiennent « débit »), la dernière écrasant la première, puis le solde
net était calculé en retranchant un mouvement d'un solde. Des rubriques
d'actif (disponibilités, VMP, clients) ressortaient créditrices.

Compte témoin 512120 : mvt débit 243 838 141, mvt crédit 237 870 637,
solde débit 5 967 504 → le solde net doit valoir 5 967 504.
"""
import pandas as pd
import pytest

from probare_engine.colonnes import classer_colonne_montant
from probare_engine.ingestion.excel_csv import _detect_column_mapping, lire_fichier
from probare_engine.controls.engine import (
    _group_rows,
    _solde_net,
    controle_soldes_anormaux,
    controle_coherence_cycle,
)
from probare_engine.api.routes import _aggreger_soldes_nets
from probare_engine.provenance.models import DonneeSourcee

PID = "test-projet-bal"
FID = "fid-bal"

# Chiffres réels du compte 512120 (ARULOS 2024)
MVT_DEBIT_512120 = 243_838_141.0
MVT_CREDIT_512120 = 237_870_637.0
SOLDE_DEBIT_512120 = 5_967_504.0


def _ds(id_: str, valeur, colonne: str, type_: str = "montant") -> DonneeSourcee:
    return DonneeSourcee(
        id=id_, projet_id=PID, fichier_source_id=FID,
        valeur=valeur, type=type_, localisation=f"BG_2024!Balance:2:{colonne}",
    )


def _row_512120() -> list[DonneeSourcee]:
    """Ligne 512120 telle qu'ingérée depuis une balance à quatre colonnes."""
    return [
        _ds("c1", "512120", "N° compte", "compte"),
        _ds("m1", MVT_DEBIT_512120, "Mvt Débit"),
        _ds("m2", MVT_CREDIT_512120, "Mvt Crédit"),
        _ds("s1", SOLDE_DEBIT_512120, "Solde Débit"),
    ]


# ─── Classification des colonnes ──────────────────────────────────────────────

class TestClassementColonnes:
    @pytest.mark.parametrize("nom,attendu", [
        ("Mvt Débit", "debit"),
        ("mvt crédit", "credit"),
        ("Débit", "debit"),
        ("Crédit", "credit"),
        ("Mouvement debit", "debit"),
        ("Solde Débit", "solde_debit"),
        ("solde crédit", "solde_credit"),
        ("Solde Débiteur", "solde_debit"),
        ("Solde Créditeur", "solde_credit"),
        ("Solde", "solde"),
        ("Solde net", "solde"),
        ("Balance", "solde"),
        ("Libellé", None),
        ("N° compte", None),
    ])
    def test_classement(self, nom, attendu):
        assert classer_colonne_montant(nom) == attendu


# ─── Ingestion : mapping des colonnes ─────────────────────────────────────────

class TestMappingColonnes:
    def test_balance_quatre_colonnes(self):
        """Mouvements et soldes sont mappés sur des champs distincts."""
        df = pd.DataFrame(columns=[
            "N° Compte", "Intitulé", "Mvt Débit", "Mvt Crédit",
            "Solde Débit", "Solde Crédit",
        ])
        m = _detect_column_mapping(df)
        assert m["debit"] == "Mvt Débit"
        assert m["credit"] == "Mvt Crédit"
        assert m["solde_debit"] == "Solde Débit"
        assert m["solde_credit"] == "Solde Crédit"
        assert m["solde"] is None
        # Aucune colonne n'alimente deux champs à la fois
        prises = [v for v in m.values() if v]
        assert len(prises) == len(set(prises))

    def test_grand_livre_colonnes_simples(self):
        """Cas majoritaire : Débit / Crédit sans colonne de solde."""
        df = pd.DataFrame(columns=["Compte", "Libellé", "Date", "Débit", "Crédit"])
        m = _detect_column_mapping(df)
        assert m["debit"] == "Débit"
        assert m["credit"] == "Crédit"
        assert m["solde"] is None
        assert m["solde_debit"] is None and m["solde_credit"] is None

    def test_balance_colonne_solde_seule(self):
        df = pd.DataFrame(columns=["Compte", "Libellé", "Solde"])
        m = _detect_column_mapping(df)
        assert m["solde"] == "Solde"
        assert m["debit"] is None and m["credit"] is None

    def test_balance_solde_debiteur_crediteur(self):
        """Ancienne balance « Solde Débiteur / Solde Créditeur » : ce sont des soldes."""
        df = pd.DataFrame(columns=["Compte", "Solde Débiteur", "Solde Créditeur"])
        m = _detect_column_mapping(df)
        assert m["solde_debit"] == "Solde Débiteur"
        assert m["solde_credit"] == "Solde Créditeur"

    def test_ingestion_fichier_reel(self, tmp_path):
        """Bout en bout : les quatre montants de 512120 sont ingérés distinctement."""
        chemin = tmp_path / "BG_2024.xlsx"
        pd.DataFrame([
            {"N° Compte": "512120", "Intitulé": "Banque X",
             "Mvt Débit": MVT_DEBIT_512120, "Mvt Crédit": MVT_CREDIT_512120,
             "Solde Débit": SOLDE_DEBIT_512120, "Solde Crédit": 0.0},
        ]).to_excel(chemin, index=False)

        donnees, meta = lire_fichier(chemin, PID, FID)
        mapping = meta["mapping_detecte"]
        assert mapping["debit"] == "Mvt Débit"
        assert mapping["solde_debit"] == "Solde Débit"

        rows = _group_rows(donnees)
        assert len(rows) == 1
        assert _solde_net(rows[0]) == pytest.approx(SOLDE_DEBIT_512120)


# ─── Regroupement et solde net ────────────────────────────────────────────────

class TestSoldeNet:
    def test_balance_quatre_colonnes_512120(self):
        """Le solde net vient des colonnes de SOLDE, pas des mouvements."""
        rows = _group_rows(_row_512120())
        assert len(rows) == 1
        row = rows[0]
        # Les quatre montants coexistent : aucun n'en écrase un autre
        assert float(row["debit"].valeur) == MVT_DEBIT_512120
        assert float(row["credit"].valeur) == MVT_CREDIT_512120
        assert float(row["solde_debit"].valeur) == SOLDE_DEBIT_512120
        assert _solde_net(row) == pytest.approx(SOLDE_DEBIT_512120)
        # Et surtout : pas le solde diminué d'un mouvement
        assert _solde_net(row) != pytest.approx(
            SOLDE_DEBIT_512120 - MVT_CREDIT_512120
        )

    def test_solde_crediteur_quatre_colonnes(self):
        """Un fournisseur créditeur ressort négatif (sens créditeur)."""
        donnees = [
            _ds("c1", "401000", "N° compte", "compte"),
            _ds("m1", 500_000.0, "Mvt Débit"),
            _ds("m2", 800_000.0, "Mvt Crédit"),
            _ds("s2", 300_000.0, "Solde Crédit"),
        ]
        row = _group_rows(donnees)[0]
        assert _solde_net(row) == pytest.approx(-300_000.0)

    def test_colonnes_simples_debit_credit(self):
        """Sans colonne de solde, le net reste débit − crédit."""
        donnees = [
            _ds("c1", "606000", "N° compte", "compte"),
            _ds("d1", 1_200.0, "Débit"),
            _ds("cr1", 200.0, "Crédit"),
        ]
        row = _group_rows(donnees)[0]
        assert _solde_net(row) == pytest.approx(1_000.0)

    def test_colonne_solde_signee_seule(self):
        donnees = [
            _ds("c1", "411000", "N° compte", "compte"),
            _ds("s1", -4_500.0, "Solde"),
        ]
        row = _group_rows(donnees)[0]
        assert _solde_net(row) == pytest.approx(-4_500.0)

    def test_solde_prime_sur_mouvements(self):
        """Colonne solde signée + mouvements : le solde l'emporte."""
        donnees = [
            _ds("c1", "512000", "N° compte", "compte"),
            _ds("d1", 900.0, "Débit"),
            _ds("cr1", 400.0, "Crédit"),
            _ds("s1", 120.0, "Solde"),
        ]
        row = _group_rows(donnees)[0]
        assert _solde_net(row) == pytest.approx(120.0)


# ─── Agrégation et contrôles en aval ──────────────────────────────────────────

class TestAgregationEtControles:
    def test_aggreger_soldes_nets_512120(self):
        rows = _group_rows(_row_512120())
        soldes = _aggreger_soldes_nets(rows, ("5",))
        montant, sources = soldes["512120"]
        assert montant == pytest.approx(SOLDE_DEBIT_512120)
        assert sources  # provenance conservée

    def test_disponibilites_non_signalees_creditrices(self):
        """La régression observée : 512120 ressortait créditeur (sens inhabituel)."""
        rows = _group_rows(_row_512120())
        resultats, exceptions = controle_soldes_anormaux(
            PID, "TRESOR-SOLDE-ANORMAL", rows, ("5",), sens_normal="debit",
        )
        assert exceptions == []
        assert all(r["statut"] == "ok" for r in resultats)

    def test_coherence_gl_balance_utilise_le_solde(self):
        """Le GL (mouvements cumulés) est confronté au SOLDE de la balance."""
        rows_balance = _group_rows(_row_512120())
        rows_gl = _group_rows([
            _ds("gc1", "512120", "N° compte", "compte"),
            _ds("gd1", MVT_DEBIT_512120, "Débit"),
            _ds("gc2", MVT_CREDIT_512120, "Crédit"),
        ])
        resultats, exceptions = controle_coherence_cycle(
            PID, "TRESOR-GL-COHER", rows_gl, rows_balance, ("5",),
        )
        # GL net = 243 838 141 − 237 870 637 = 5 967 504 = solde balance
        assert exceptions == []
        assert all(r["statut"] == "ok" for r in resultats)
