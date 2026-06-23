"""
Tests unitaires des contrôles déterministes — 27 contrôles, 3 cycles.
Aucun appel LLM dans ces tests (tout est déterministe).
"""
import pytest
from probare_engine.provenance.models import DonneeSourcee
from probare_engine.controls.engine import (
    controle_equilibre_balance,
    controle_coherence_gl_balance,
    controle_sequence_pieces,
    controle_variations,
    controle_rapprochement_bancaire,
    controle_soldes_anormaux_tresorerie,
    controle_coherence_cycle,
    controle_soldes_anormaux,
    controle_montants_ronds,
    controle_cut_off,
    controle_doublons_factures,
    controle_concentration_compte,
    controle_ratio_avoirs,
    controle_creances_echues,
    _group_rows,
    _filter_accounts,
)

PID = "test-projet-001"
FID = "fid-001"
FID2 = "fid-002"


# ─── Constructeurs de jeux de données ─────────────────────────────────────────

def _ds(id_: str, valeur, localisation: str, type_: str = "montant",
        fichier_id: str = FID) -> DonneeSourcee:
    return DonneeSourcee(
        id=id_, projet_id=PID, fichier_source_id=fichier_id,
        valeur=valeur, type=type_, localisation=localisation,
    )


def _ds_compte(id_: str, compte: str, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, compte, f"GL:{row}:Compte", "compte", fichier_id)


def _ds_debit(id_: str, montant: float, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, montant, f"GL:{row}:Débit", "montant", fichier_id)


def _ds_credit(id_: str, montant: float, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, montant, f"GL:{row}:Crédit", "montant", fichier_id)


def _ds_solde(id_: str, montant: float, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, montant, f"BAL:{row}:Solde", "montant", fichier_id)


def _ds_piece(id_: str, numero: str, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, numero, f"GL:{row}:Pièce", "numero_piece", fichier_id)


def _ds_date(id_: str, date_val: str, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, date_val, f"GL:{row}:Date", "date", fichier_id)


def _ds_libelle(id_: str, libelle: str, row: int, fichier_id: str = FID) -> DonneeSourcee:
    return _ds(id_, libelle, f"GL:{row}:Libelle", "texte", fichier_id)


def _make_row(compte: str, row: int, debit: float = 0, credit: float = 0,
              solde: float = 0, piece: str = "", date: str = "",
              libelle: str = "", fichier_id: str = FID) -> list:
    """Crée une liste de DonneeSourcees simulant une ligne de GL ou balance."""
    donnees = [_ds_compte(f"c{row}-{fichier_id}", compte, row, fichier_id)]
    if debit > 0:
        donnees.append(_ds_debit(f"d{row}-{fichier_id}", debit, row, fichier_id))
    if credit > 0:
        donnees.append(_ds_credit(f"cr{row}-{fichier_id}", credit, row, fichier_id))
    if solde != 0:
        donnees.append(_ds_solde(f"s{row}-{fichier_id}", solde, row, fichier_id))
    if piece:
        donnees.append(_ds_piece(f"p{row}-{fichier_id}", piece, row, fichier_id))
    if date:
        donnees.append(_ds_date(f"dt{row}-{fichier_id}", date, row, fichier_id))
    if libelle:
        donnees.append(_ds_libelle(f"l{row}-{fichier_id}", libelle, row, fichier_id))
    return donnees


def _rows(donnees: list) -> list:
    return _group_rows(donnees)


# ═══════════════════════════════════════════════════════════════════════════════
# TRÉSORERIE — contrôles existants
# ═══════════════════════════════════════════════════════════════════════════════

class TestEquilibreBalance:
    def test_balance_equilibree(self):
        debits = [_ds("d1", 1000.0, "Balance:2:Débit"), _ds("d2", 500.0, "Balance:3:Débit")]
        credits = [_ds("c1", 1200.0, "Balance:2:Crédit"), _ds("c2", 300.0, "Balance:3:Crédit")]
        res, exc = controle_equilibre_balance(PID, debits, credits)
        assert res["statut"] == "ok"
        assert exc is None

    def test_balance_desequilibree(self):
        debits = [_ds("d1", 1000.0, "Balance:2:Débit")]
        credits = [_ds("c1", 900.0, "Balance:2:Crédit")]
        res, exc = controle_equilibre_balance(PID, debits, credits)
        assert res["statut"] == "exception"
        assert exc is not None
        assert exc["nep_ref"] == "NEP 500"
        assert exc["severite"] == "critique"
        assert float(res["valeur"]) == pytest.approx(100.0)

    def test_balance_vide(self):
        res, exc = controle_equilibre_balance(PID, [], [])
        assert res["statut"] == "ok"
        assert exc is None

    def test_balance_tolerance(self):
        debits = [_ds("d1", 1000.005, "Balance:2:Débit")]
        credits = [_ds("c1", 1000.0, "Balance:2:Crédit")]
        res, exc = controle_equilibre_balance(PID, debits, credits, tolerance=0.01)
        assert res["statut"] == "ok"

    def test_ecart_large(self):
        debits = [_ds("d1", 50000.0, "Balance:2:Débit")]
        credits = [_ds("c1", 35000.0, "Balance:2:Crédit")]
        res, exc = controle_equilibre_balance(PID, debits, credits)
        assert res["statut"] == "exception"
        assert float(res["valeur"]) == pytest.approx(15000.0)

    def test_plusieurs_lignes(self):
        debits = [_ds(f"d{i}", float(i * 100), f"Balance:{i+1}:Débit") for i in range(1, 6)]
        credits = [_ds(f"c{i}", float(i * 100), f"Balance:{i+1}:Crédit") for i in range(1, 6)]
        res, exc = controle_equilibre_balance(PID, debits, credits)
        assert res["statut"] == "ok"


class TestSequencePieces:
    def test_sequence_continue(self):
        pieces = [_ds_piece(f"p{i}", str(i), i) for i in range(1, 11)]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "ok"
        assert exc is None

    def test_trou_dans_sequence(self):
        nums = [1, 2, 4, 5, 6]
        pieces = [_ds_piece(f"p{n}", str(n), n) for n in nums]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "exception"
        assert exc is not None
        assert "3" in exc["description"]

    def test_doublon_sequence(self):
        nums = [1, 2, 2, 3, 4]
        pieces = [_ds_piece(f"p{i}", str(n), i) for i, n in enumerate(nums, 1)]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "exception"

    def test_plusieurs_trous(self):
        nums = [1, 2, 5, 8, 9, 10]
        pieces = [_ds_piece(f"p{i}", str(n), i) for i, n in enumerate(nums, 1)]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "exception"

    def test_aucun_numero_numerique(self):
        pieces = [_ds_piece("p1", "FAC001", 1), _ds_piece("p2", "FAC002", 2)]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "ok"

    def test_floats_comme_entiers(self):
        nums = ["1.0", "2.0", "3.0"]
        pieces = [_ds_piece(f"p{i}", n, i) for i, n in enumerate(nums, 1)]
        res, exc = controle_sequence_pieces(PID, pieces)
        assert res["statut"] == "ok"

    def test_ref_alternatif(self):
        pieces = [_ds_piece(f"p{i}", str(i), i) for i in [1, 2, 4]]
        res, exc = controle_sequence_pieces(PID, pieces, controle_ref="ACHAT-SEQ-FACTURES")
        assert exc is not None
        assert exc["controle_ref"] == "ACHAT-SEQ-FACTURES"


class TestVariations:
    def test_variation_sous_seuil(self):
        soldes_n = {"512000": (10000.0, ["s1"])}
        soldes_n1 = {"512000": (9500.0, ["s2"])}
        ress, excs = controle_variations(PID, soldes_n, soldes_n1, 1000.0)
        assert all(r["statut"] == "ok" for r in ress)
        assert not excs

    def test_variation_au_dessus_seuil(self):
        soldes_n = {"512000": (10000.0, ["s1"])}
        soldes_n1 = {"512000": (5000.0, ["s2"])}
        ress, excs = controle_variations(PID, soldes_n, soldes_n1, 1000.0)
        assert any(r["statut"] == "exception" for r in ress)
        assert len(excs) == 1

    def test_compte_nouveau_sans_n1(self):
        soldes_n = {"512000": (10000.0, ["s1"])}
        ress, excs = controle_variations(PID, soldes_n, {}, 1000.0)
        assert any(r["statut"] == "exception" for r in ress)

    def test_multiples_comptes(self):
        soldes_n = {
            "512000": (10000.0, ["s1"]),
            "514000": (500.0, ["s2"]),
            "530000": (200.0, ["s3"]),
        }
        soldes_n1 = {
            "512000": (9000.0, ["s4"]),
            "514000": (498.0, ["s5"]),
            "530000": (195.0, ["s6"]),
        }
        ress, excs = controle_variations(PID, soldes_n, soldes_n1, 500.0)
        # 512000 varie de 1000 > 500 → exception
        assert len(excs) == 1
        assert "512000" in excs[0]["description"]


class TestRapprochementBancaire:
    def test_rapprochement_ok(self):
        s_compta = _ds("sc", 5000.0, "Compta:2:Solde")
        s_releve = _ds("sr", 5000.0, "Banque:2:Solde")
        res, exc = controle_rapprochement_bancaire(PID, s_compta, s_releve)
        assert res["statut"] == "ok"
        assert exc is None

    def test_ecart_banque(self):
        s_compta = _ds("sc", 5000.0, "Compta:2:Solde")
        s_releve = _ds("sr", 4800.0, "Banque:2:Solde")
        res, exc = controle_rapprochement_bancaire(PID, s_compta, s_releve)
        assert res["statut"] == "exception"
        assert float(res["valeur"]) == pytest.approx(200.0)

    def test_ecart_zero(self):
        s_compta = _ds("sc", 0.0, "Compta:2:Solde")
        s_releve = _ds("sr", 0.0, "Banque:2:Solde")
        res, exc = controle_rapprochement_bancaire(PID, s_compta, s_releve)
        assert res["statut"] == "ok"


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRE _group_rows
# ═══════════════════════════════════════════════════════════════════════════════

class TestGroupRows:
    def test_groupe_une_ligne(self):
        donnees = _make_row("512000", 2, debit=1000.0)
        grouped = _rows(donnees)
        assert len(grouped) == 1
        assert grouped[0]["compte"].valeur == "512000"
        assert grouped[0]["debit"].valeur == pytest.approx(1000.0)

    def test_groupe_plusieurs_lignes_meme_fichier(self):
        donnees = (
            _make_row("512000", 2, debit=1000.0) +
            _make_row("401000", 3, credit=1000.0)
        )
        grouped = _rows(donnees)
        assert len(grouped) == 2

    def test_filtre_5xx(self):
        donnees = (
            _make_row("512000", 2, debit=1000.0) +
            _make_row("401000", 3, credit=500.0) +
            _make_row("607000", 4, debit=500.0)
        )
        grouped = _rows(donnees)
        rows_5xx = _filter_accounts(grouped, ("5",))
        assert len(rows_5xx) == 1
        assert rows_5xx[0]["compte"].valeur == "512000"

    def test_filtre_multiple_prefixes(self):
        donnees = (
            _make_row("401000", 2, credit=1000.0) +
            _make_row("607000", 3, debit=1000.0) +
            _make_row("512000", 4, credit=1000.0)
        )
        grouped = _rows(donnees)
        rows_achats = _filter_accounts(grouped, ("40", "60"))
        assert len(rows_achats) == 2

    def test_colonne_solde_detectee(self):
        donnees = [
            _ds_compte("c2", "512000", 2),
            _ds_solde("s2", 3000.0, 2),
        ]
        grouped = _rows(donnees)
        assert len(grouped) == 1
        assert grouped[0].get("solde") is not None
        assert grouped[0]["solde"].valeur == pytest.approx(3000.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TRÉSORERIE — nouveaux contrôles
# ═══════════════════════════════════════════════════════════════════════════════

class TestSoldesAnomauxTresorerie:
    def test_solde_debiteur_normal(self):
        donnees = _make_row("512000", 2, debit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert not excs
        assert all(r["statut"] == "ok" for r in ress)

    def test_solde_crediteur_anormal(self):
        donnees = _make_row("512000", 2, credit=3000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert len(excs) == 1
        assert "solde créditeur anormal" in excs[0]["description"]

    def test_aucun_compte_5xx(self):
        donnees = _make_row("401000", 2, credit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert not excs
        assert "Aucun compte de trésorerie" in ress[0]["details"]

    def test_plusieurs_comptes_dont_un_anormal(self):
        donnees = (
            _make_row("512000", 2, debit=3000.0) +
            _make_row("514000", 3, credit=1500.0) +
            _make_row("530000", 4, debit=200.0)
        )
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert len(excs) == 1
        assert "514000" in excs[0]["description"]

    def test_deux_comptes_anormaux(self):
        donnees = (
            _make_row("512000", 2, credit=1000.0) +
            _make_row("514000", 3, credit=2000.0)
        )
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert len(excs) == 2


class TestMontantsRonds:
    def test_ratio_normal(self):
        donnees = (
            _make_row("512000", 2, debit=1234.56) +
            _make_row("512000", 3, credit=987.65) +
            _make_row("512000", 4, debit=543.21)
        )
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(PID, "TRESOR-ROUND", grouped, ("5",))
        assert exc is None

    def test_ratio_anormal_tout_ronds(self):
        donnees = (
            _make_row("512000", 2, debit=1000.0) +
            _make_row("512000", 3, debit=2000.0) +
            _make_row("512000", 4, credit=500.0) +
            _make_row("512000", 5, credit=1500.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(PID, "TRESOR-ROUND", grouped, ("5",), seuil_ratio=0.40)
        assert exc is not None

    def test_aucun_compte_correspondant(self):
        donnees = _make_row("401000", 2, credit=1000.0)
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(PID, "TRESOR-ROUND", grouped, ("5",))
        assert exc is None
        assert "Aucun compte" in res["details"]

    def test_mix_ronds_et_fractionnaires(self):
        # 2 ronds sur 5 = 40% → juste à la limite
        donnees = (
            _make_row("512000", 2, debit=1000.0) +
            _make_row("512000", 3, debit=1234.56) +
            _make_row("512000", 4, credit=2000.0) +
            _make_row("512000", 5, credit=876.54) +
            _make_row("512000", 6, debit=543.21)
        )
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(PID, "TRESOR-ROUND", grouped, ("5",), seuil_ratio=0.41)
        assert exc is None  # 40% < 41%


class TestCutOff:
    def test_sans_exercice(self):
        donnees = _make_row("512000", 2, debit=1000.0, date="2023-12-20")
        grouped = _rows(donnees)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), None)
        assert exc is None
        assert "Exercice non renseigné" in res["details"]

    def test_concentration_fin_exercice(self):
        # 4/5 écritures dans les 15 derniers jours = 80% > 30%
        donnees = (
            _make_row("512000", 2, debit=1000.0, date="2023-01-15") +
            _make_row("512000", 3, debit=2000.0, date="2023-12-18") +
            _make_row("512000", 4, debit=3000.0, date="2023-12-20") +
            _make_row("512000", 5, debit=4000.0, date="2023-12-25") +
            _make_row("512000", 6, credit=1000.0, date="2023-12-31")
        )
        grouped = _rows(donnees)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), "2023",
                                    nb_jours=15, seuil_ratio=0.30)
        assert exc is not None
        assert "cut-off" in exc["description"].lower()

    def test_distribution_normale(self):
        donnees = []
        for i, mois in enumerate(["01", "02", "03", "04", "05", "06",
                                   "07", "08", "09", "10", "11", "12"], 2):
            donnees += _make_row("512000", i, debit=1000.0, date=f"2023-{mois}-15")
        grouped = _rows(donnees)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), "2023",
                                    nb_jours=15, seuil_ratio=0.30)
        assert exc is None

    def test_sans_dates(self):
        donnees = _make_row("512000", 2, debit=1000.0)
        grouped = _rows(donnees)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), "2023")
        assert exc is None
        assert "Aucune date" in res["details"]

    def test_exercice_format_slash(self):
        donnees = (
            _make_row("512000", 2, debit=1000.0, date="2023/12/25") +
            _make_row("512000", 3, debit=2000.0, date="2023/01/10")
        )
        grouped = _rows(donnees)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), "2023",
                                    nb_jours=15, seuil_ratio=0.80)
        assert exc is None  # 1/2 = 50% < 80%


# ═══════════════════════════════════════════════════════════════════════════════
# ACHATS-FOURNISSEURS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoherenceCycle:
    def test_coherence_ok(self):
        donnees_gl = (
            _make_row("607000", 2, debit=1500.0) +
            _make_row("401000", 3, credit=1500.0)
        )
        donnees_bal = (
            _make_row("607000", 2, debit=1500.0, fichier_id=FID2) +
            _make_row("401000", 3, credit=1500.0, fichier_id=FID2)
        )
        rows_gl = _rows(donnees_gl)
        rows_bal = _rows(donnees_bal)
        ress, excs = controle_coherence_cycle(
            PID, "ACHAT-GL-COHER", rows_gl, rows_bal, ("40", "60")
        )
        assert not excs

    def test_incoherence_detectee(self):
        donnees_gl = _make_row("401000", 2, credit=1500.0)
        donnees_bal = _make_row("401000", 2, credit=1200.0, fichier_id=FID2)
        rows_gl = _rows(donnees_gl)
        rows_bal = _rows(donnees_bal)
        ress, excs = controle_coherence_cycle(
            PID, "ACHAT-GL-COHER", rows_gl, rows_bal, ("40",)
        )
        assert len(excs) == 1
        assert "Écart" in excs[0]["description"] or "écart" in excs[0]["description"]

    def test_compte_gl_seulement(self):
        rows_gl = _rows(_make_row("401000", 2, credit=1000.0))
        rows_bal = []
        ress, excs = controle_coherence_cycle(
            PID, "ACHAT-GL-COHER", rows_gl, rows_bal, ("40",)
        )
        assert len(excs) == 1

    def test_avec_colonne_solde_balance(self):
        donnees_gl = _make_row("607000", 2, debit=3000.0)
        donnees_bal = [
            _ds_compte("c2b", "607000", 2, FID2),
            _ds_solde("s2b", 3000.0, 2, FID2),
        ]
        rows_gl = _rows(donnees_gl)
        rows_bal = _rows(donnees_bal)
        ress, excs = controle_coherence_cycle(
            PID, "ACHAT-GL-COHER", rows_gl, rows_bal, ("60",)
        )
        assert not excs

    def test_aucun_compte_cycle(self):
        rows_gl = _rows(_make_row("512000", 2, debit=5000.0))
        rows_bal = _rows(_make_row("512000", 2, debit=5000.0, fichier_id=FID2))
        ress, excs = controle_coherence_cycle(
            PID, "ACHAT-GL-COHER", rows_gl, rows_bal, ("40", "60")
        )
        assert not excs
        assert "Aucun compte" in ress[0]["details"]


class TestSoldesAnormaux:
    def test_solde_crediteur_normal_fournisseur(self):
        donnees = _make_row("401000", 2, credit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "ACHAT-SOLDE-DEBITEUR", grouped, ("40",), "credit")
        assert not excs

    def test_solde_debiteur_anormal_fournisseur(self):
        donnees = _make_row("401000", 2, debit=2000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "ACHAT-SOLDE-DEBITEUR", grouped, ("40",), "credit")
        assert len(excs) == 1
        assert "débiteur anormal" in excs[0]["description"]

    def test_solde_debiteur_normal_client(self):
        donnees = _make_row("411000", 2, debit=3000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "VENTE-SOLDE-CREDITEUR", grouped, ("41",), "debit")
        assert not excs

    def test_solde_crediteur_anormal_client(self):
        donnees = _make_row("411000", 2, credit=1500.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "VENTE-SOLDE-CREDITEUR", grouped, ("41",), "debit")
        assert len(excs) == 1
        assert "créditeur anormal" in excs[0]["description"]

    def test_plusieurs_fourn_dont_un_anormal(self):
        donnees = (
            _make_row("401000", 2, credit=5000.0) +
            _make_row("401100", 3, debit=200.0) +
            _make_row("402000", 4, credit=3000.0)
        )
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "ACHAT-SOLDE-DEBITEUR", grouped, ("40",), "credit")
        assert len(excs) == 1
        assert "401100" in excs[0]["description"]

    def test_avec_colonne_solde(self):
        donnees = [
            _ds_compte("c2", "401000", 2),
            _ds_solde("s2", -3000.0, 2),  # solde négatif = créditeur (normal pour 401)
        ]
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(PID, "ACHAT-SOLDE-DEBITEUR", grouped, ("40",), "credit")
        assert not excs


class TestDoublonsFactures:
    def test_aucun_doublon(self):
        donnees = (
            _make_row("401000", 2, credit=1500.0, piece="FAC001") +
            _make_row("401000", 3, credit=2000.0, piece="FAC002") +
            _make_row("401000", 4, credit=800.0, piece="FAC003")
        )
        grouped = _rows(donnees)
        res, exc = controle_doublons_factures(PID, "ACHAT-DOUBLON", grouped, ("40",))
        assert exc is None

    def test_doublon_exact(self):
        donnees = (
            _make_row("401000", 2, credit=1500.0, piece="FAC001") +
            _make_row("401000", 3, credit=1500.0, piece="FAC001")
        )
        grouped = _rows(donnees)
        res, exc = controle_doublons_factures(PID, "ACHAT-DOUBLON", grouped, ("40",))
        assert exc is not None
        assert "FAC001" in exc["description"]

    def test_doublon_different_fournisseur(self):
        # Même montant, même pièce, mais DEUX fournisseurs différents → deux doublons
        donnees = (
            _make_row("401000", 2, credit=1500.0, piece="FAC001") +
            _make_row("401000", 3, credit=1500.0, piece="FAC001") +
            _make_row("401100", 4, credit=1500.0, piece="FAC001") +
            _make_row("401100", 5, credit=1500.0, piece="FAC001")
        )
        grouped = _rows(donnees)
        res, exc = controle_doublons_factures(PID, "ACHAT-DOUBLON", grouped, ("40",))
        assert exc is not None

    def test_aucun_compte_40x(self):
        donnees = _make_row("607000", 2, debit=1500.0)
        grouped = _rows(donnees)
        res, exc = controle_doublons_factures(PID, "ACHAT-DOUBLON", grouped, ("40",))
        assert exc is None

    def test_doublon_clients(self):
        donnees = (
            _make_row("411000", 2, debit=5000.0, piece="FACT2023-001") +
            _make_row("411000", 3, debit=5000.0, piece="FACT2023-001")
        )
        grouped = _rows(donnees)
        res, exc = controle_doublons_factures(PID, "VENTE-DOUBLON", grouped, ("41",))
        assert exc is not None


class TestConcentrationCompte:
    def test_concentration_normale(self):
        # 4 fournisseurs à 25% chacun → aucun ne dépasse 30%
        donnees = (
            _make_row("401000", 2, credit=2500.0) +
            _make_row("401100", 3, credit=2500.0) +
            _make_row("401200", 4, credit=2500.0) +
            _make_row("401300", 5, credit=2500.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_concentration_compte(PID, "ACHAT-CONCENTRATION", grouped, ("40",), "credit")
        assert exc is None

    def test_concentration_elevee_fournisseur(self):
        donnees = (
            _make_row("401000", 2, credit=8000.0) +
            _make_row("401100", 3, credit=1000.0) +
            _make_row("401200", 4, credit=1000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_concentration_compte(PID, "ACHAT-CONCENTRATION", grouped, ("40",), "credit")
        assert exc is not None
        assert "401000" in exc["description"]
        assert "80.0%" in exc["description"]

    def test_un_seul_fournisseur(self):
        donnees = _make_row("401000", 2, credit=5000.0)
        grouped = _rows(donnees)
        res, exc = controle_concentration_compte(PID, "ACHAT-CONCENTRATION", grouped, ("40",), "credit")
        assert exc is not None

    def test_concentration_client_elevee(self):
        donnees = (
            _make_row("411000", 2, debit=9000.0) +
            _make_row("411100", 3, debit=1000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_concentration_compte(PID, "VENTE-CONCENTRATION", grouped, ("41",), "debit")
        assert exc is not None
        assert "411000" in exc["description"]

    def test_seuil_custom(self):
        # 50% → exception avec seuil=40%, ok avec seuil=60%
        donnees = (
            _make_row("401000", 2, credit=5000.0) +
            _make_row("401100", 3, credit=5000.0)
        )
        grouped = _rows(donnees)
        _, exc_40 = controle_concentration_compte(PID, "ACHAT-CONCENTRATION", grouped, ("40",),
                                                  "credit", seuil_concentration=0.40)
        assert exc_40 is not None

        _, exc_60 = controle_concentration_compte(PID, "ACHAT-CONCENTRATION", grouped, ("40",),
                                                  "credit", seuil_concentration=0.60)
        assert exc_60 is None


class TestRatioAvoirs:
    def test_ratio_normal_achats(self):
        donnees = (
            _make_row("401000", 2, credit=5000.0) +
            _make_row("401000", 3, debit=200.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", grouped, ("40",), "debit")
        assert exc is None

    def test_ratio_anormal_achats(self):
        donnees = (
            _make_row("401000", 2, credit=3000.0) +
            _make_row("401000", 3, debit=500.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", grouped, ("40",), "debit",
                                         seuil_ratio=0.05)
        assert exc is not None
        assert "avoirs" in exc["description"].lower()

    def test_ratio_anormal_ventes(self):
        donnees = (
            _make_row("411000", 2, debit=4000.0) +
            _make_row("411000", 3, credit=800.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "VENTE-AVOIR", grouped, ("41",), "credit",
                                         seuil_ratio=0.05)
        assert exc is not None

    def test_aucun_avoir(self):
        donnees = (
            _make_row("401000", 2, credit=5000.0) +
            _make_row("401000", 3, credit=3000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", grouped, ("40",), "debit")
        assert exc is None

    def test_libelle_avoir(self):
        donnees = (
            _make_row("401000", 2, credit=5000.0) +
            _make_row("401000", 3, debit=300.0, libelle="AVOIR FAC-2023-001")
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", grouped, ("40",), "debit",
                                         seuil_ratio=0.05)
        assert exc is not None

    def test_aucun_compte_correspondant(self):
        donnees = _make_row("607000", 2, debit=1000.0)
        grouped = _rows(donnees)
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", grouped, ("40",), "debit")
        assert exc is None


# ═══════════════════════════════════════════════════════════════════════════════
# VENTES-CLIENTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreancesEchues:
    def test_pas_de_creances_echues(self):
        donnees = (
            _make_row("411000", 2, debit=5000.0, date="2023-11-01") +
            _make_row("411000", 3, debit=3000.0, date="2023-12-01")
        )
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, "2023",
                                            nb_jours_seuil=90, seuil_ratio=0.10)
        assert exc is None

    def test_creances_echues_significatives(self):
        donnees = (
            _make_row("411000", 2, debit=5000.0, date="2023-06-01") +
            _make_row("411000", 3, debit=3000.0, date="2023-11-15")
        )
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, "2023",
                                            nb_jours_seuil=90, seuil_ratio=0.10)
        assert exc is not None
        assert "irrécouvrabilité" in exc["description"]

    def test_aucune_date(self):
        donnees = _make_row("411000", 2, debit=5000.0)
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, "2023")
        assert exc is None

    def test_pas_d_exercice(self):
        donnees = _make_row("411000", 2, debit=5000.0, date="2023-01-01")
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, None)
        assert exc is None
        assert "Exercice non renseigné" in res["details"]

    def test_aucune_creance_client(self):
        donnees = _make_row("607000", 2, debit=1000.0, date="2023-01-01")
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, "2023")
        assert exc is None

    def test_toutes_echues(self):
        # 100% des créances > 90j → exception forte
        donnees = (
            _make_row("411000", 2, debit=3000.0, date="2023-01-15") +
            _make_row("411100", 3, debit=2000.0, date="2023-02-20") +
            _make_row("411200", 4, debit=5000.0, date="2023-03-10")
        )
        grouped = _rows(donnees)
        res, exc = controle_creances_echues(PID, grouped, "2023",
                                            nb_jours_seuil=90, seuil_ratio=0.10)
        assert exc is not None
        assert float(res["valeur"]) == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS D'INTÉGRATION — scénarios complets
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioAchatsFrauduleux:
    """Grand livre achats avec doublon, concentration et avoirs anormaux."""

    def setup_method(self):
        self.donnees = (
            # Fournisseur principal 401000 = 85% + doublon FAC001
            _make_row("401000", 2, credit=8500.0, piece="FAC001") +
            _make_row("401000", 3, credit=8500.0, piece="FAC001") +
            # Fournisseur secondaire 401100 = 15%
            _make_row("401100", 4, credit=1500.0, piece="FAC020") +
            # Avoir important : 2000 sur 18500 = 10.8% > 5%
            _make_row("401000", 5, debit=2000.0, libelle="AVOIR FAC-OLD") +
            # Charges correspondantes
            _make_row("607000", 6, debit=10000.0) +
            _make_row("607000", 7, debit=8500.0)
        )
        self.grouped = _rows(self.donnees)

    def test_doublon_detecte(self):
        res, exc = controle_doublons_factures(PID, "ACHAT-DOUBLON", self.grouped, ("40",))
        assert exc is not None

    def test_concentration_detectee(self):
        res, exc = controle_concentration_compte(PID, "ACHAT-CONCENTRATION",
                                                  self.grouped, ("40",), "credit")
        assert exc is not None

    def test_avoir_anormal_detecte(self):
        res, exc = controle_ratio_avoirs(PID, "ACHAT-AVOIR", self.grouped, ("40",), "debit",
                                         seuil_ratio=0.05)
        assert exc is not None


class TestScenarioVentesRisquees:
    """Grand livre ventes avec créances anciennes et concentration client."""

    def setup_method(self):
        self.donnees = (
            # Client principal 411000 = 70% avec créance ancienne
            _make_row("411000", 2, debit=7000.0, date="2023-03-01", piece="FACT001") +
            # Client secondaire 411100 = 30%
            _make_row("411100", 3, debit=3000.0, date="2023-10-01", piece="FACT002") +
            # Produits
            _make_row("707000", 4, credit=7000.0) +
            _make_row("707000", 5, credit=3000.0)
        )
        self.grouped = _rows(self.donnees)

    def test_concentration_detectee(self):
        res, exc = controle_concentration_compte(PID, "VENTE-CONCENTRATION",
                                                  self.grouped, ("41",), "debit")
        assert exc is not None

    def test_creances_echues_detectees(self):
        res, exc = controle_creances_echues(PID, self.grouped, "2023",
                                             nb_jours_seuil=90, seuil_ratio=0.10)
        assert exc is not None

    def test_sequence_ok(self):
        pieces = [d for d in self.donnees if d.type == "numero_piece"]
        res, exc = controle_sequence_pieces(PID, pieces, "VENTE-SEQ-FACTURES")
        assert res is not None  # FACT001, FACT002 = non numériques → OK


class TestScenarieTresorerieClean:
    """Trésorerie sans anomalie."""

    def test_tout_normal(self):
        donnees = (
            _make_row("512000", 2, debit=5000.0, date="2023-03-15") +
            _make_row("512000", 3, credit=2000.0, date="2023-06-20") +
            _make_row("530000", 4, debit=500.0, date="2023-09-10") +
            _make_row("512000", 5, debit=3000.0, date="2023-11-05")
        )
        grouped = _rows(donnees)

        # Soldes normaux
        ress, excs = controle_soldes_anormaux_tresorerie(PID, grouped)
        assert not excs

        # Pas de cut-off (distribution sur l'année)
        res, exc = controle_cut_off(PID, "TRESOR-CUT-OFF", grouped, ("5",), "2023",
                                    nb_jours=15, seuil_ratio=0.30)
        assert exc is None
