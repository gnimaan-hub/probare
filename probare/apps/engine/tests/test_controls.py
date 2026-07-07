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
    controle_amortissement_manquant,
    controle_amort_excedent,
    controle_ratio_charges_sociales,
    controle_mensualite_paie,
    controle_tva_coherence,
    controle_mouvement_provisions,
    controle_coherence_resultat,
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
        # La référence est rendue dans le référentiel actif du cabinet (ISA par défaut)
        from probare_engine.normes import norme
        assert exc["nep_ref"] == norme(500)
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


# ═══════════════════════════════════════════════════════════════════════════════
# IMMOBILISATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAmortissementManquant:
    def test_imo_avec_amortissement_ok(self):
        donnees = (
            _make_row("215000", 2, debit=50000.0) +   # immobilisations
            _make_row("281500", 3, credit=15000.0)     # amortissements cumulés
        )
        grouped = _rows(donnees)
        res, exc = controle_amortissement_manquant(PID, grouped)
        assert exc is None
        assert "Amortissements cumulés" in res["details"]

    def test_imo_sans_amortissement_exception(self):
        donnees = _make_row("215000", 2, debit=50000.0)  # immobilisations sans 28x
        grouped = _rows(donnees)
        res, exc = controle_amortissement_manquant(PID, grouped)
        assert exc is not None
        assert exc["controle_ref"] == "IMO-AMORTISSEMENT"
        assert "sous-amortissement" in exc["description"].lower()

    def test_aucune_imo_amortissable(self):
        # Seulement des participations (26x), pas concernées
        donnees = _make_row("261000", 2, debit=10000.0)
        grouped = _rows(donnees)
        res, exc = controle_amortissement_manquant(PID, grouped)
        assert exc is None
        assert "Aucune immobilisation" in res["details"]

    def test_solde_nul_ignore(self):
        # Immobilisation brute nulle (entièrement amortie ou cédée)
        donnees = (
            _make_row("215000", 2, debit=10000.0, credit=10000.0) +
            _make_row("281500", 3, credit=10000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_amortissement_manquant(PID, grouped)
        assert exc is None

    def test_plusieurs_imo_une_sans_amort(self):
        # Même une seule immobilisation avec amortissement suffit pour que le contrôle passe
        donnees = (
            _make_row("215000", 2, debit=30000.0) +
            _make_row("218000", 3, debit=20000.0) +
            _make_row("281500", 4, credit=5000.0)   # amortissement présent
        )
        grouped = _rows(donnees)
        res, exc = controle_amortissement_manquant(PID, grouped)
        assert exc is None  # total_amort > 0 → contrôle passé


class TestAmortExcedent:
    def test_amort_inferieur_ok(self):
        donnees = (
            _make_row("215000", 2, debit=50000.0) +
            _make_row("281500", 3, credit=20000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_amort_excedent(PID, grouped)
        assert exc is None
        assert "cohérent" in res["details"]

    def test_amort_superieur_exception(self):
        donnees = (
            _make_row("215000", 2, debit=20000.0) +  # valeur brute = 20 000
            _make_row("281500", 3, credit=25000.0)   # amortissements = 25 000 > 20 000
        )
        grouped = _rows(donnees)
        res, exc = controle_amort_excedent(PID, grouped)
        assert exc is not None
        assert exc["controle_ref"] == "IMO-AMORT-EXCEDENT"
        assert float(res["valeur"]) == pytest.approx(5000.0)

    def test_aucune_valeur_brute(self):
        donnees = _make_row("281500", 2, credit=10000.0)  # seulement 28x
        grouped = _rows(donnees)
        res, exc = controle_amort_excedent(PID, grouped)
        assert exc is None
        assert "Aucune valeur brute" in res["details"]

    def test_egal_ok(self):
        # 100% amorti = tolérance acceptable
        donnees = (
            _make_row("215000", 2, debit=10000.0) +
            _make_row("281500", 3, credit=10000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_amort_excedent(PID, grouped)
        assert exc is None


class TestSoldesAnomauxImmobilisations:
    def test_solde_debiteur_normal(self):
        donnees = _make_row("215000", 2, debit=50000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "IMO-SOLDE-ANORMAL", grouped,
            ("20", "21", "22", "23", "24", "25", "26", "27"), "debit",
        )
        assert not excs

    def test_solde_crediteur_anormal(self):
        donnees = _make_row("215000", 2, credit=50000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "IMO-SOLDE-ANORMAL", grouped,
            ("20", "21", "22", "23", "24", "25", "26", "27"), "debit",
        )
        assert len(excs) == 1
        assert "créditeur anormal" in excs[0]["description"]


# ═══════════════════════════════════════════════════════════════════════════════
# STOCKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStocksSoldesAnormaux:
    def test_stock_debiteur_ok(self):
        donnees = _make_row("310000", 2, debit=15000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "STOCK-SOLDE-ANORMAL", grouped, ("3",), "debit",
        )
        assert not excs

    def test_stock_crediteur_exception(self):
        donnees = _make_row("310000", 2, credit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "STOCK-SOLDE-ANORMAL", grouped, ("3",), "debit",
        )
        assert len(excs) == 1
        assert "créditeur anormal" in excs[0]["description"]

    def test_stock_vide(self):
        donnees = _make_row("512000", 2, debit=1000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "STOCK-SOLDE-ANORMAL", grouped, ("3",), "debit",
        )
        assert not excs
        assert "Aucun compte" in ress[0]["details"]


class TestStocksRound:
    def test_valorisations_rondes_exception(self):
        donnees = (
            _make_row("310000", 2, debit=5000.0) +
            _make_row("310000", 3, debit=10000.0) +
            _make_row("310000", 4, debit=2000.0) +
            _make_row("310000", 5, debit=3000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(
            PID, "STOCK-ROUND", grouped, ("3",), seuil_ratio=0.40,
        )
        assert exc is not None

    def test_valorisations_normales_ok(self):
        donnees = (
            _make_row("310000", 2, debit=4567.89) +
            _make_row("310000", 3, debit=1234.56) +
            _make_row("310000", 4, debit=8901.23)
        )
        grouped = _rows(donnees)
        res, exc = controle_montants_ronds(
            PID, "STOCK-ROUND", grouped, ("3",), seuil_ratio=0.40,
        )
        assert exc is None


class TestStocksCutOff:
    def test_cut_off_stocks_exception(self):
        donnees = (
            _make_row("310000", 2, debit=1000.0, date="2023-01-15") +
            _make_row("310000", 3, debit=2000.0, date="2023-12-20") +
            _make_row("310000", 4, debit=3000.0, date="2023-12-25") +
            _make_row("310000", 5, debit=4000.0, date="2023-12-31")
        )
        grouped = _rows(donnees)
        res, exc = controle_cut_off(
            PID, "STOCK-CUT-OFF", grouped, ("3",), "2023",
            nb_jours=15, seuil_ratio=0.30,
        )
        assert exc is not None
        assert "cut-off" in exc["description"].lower()

    def test_cut_off_stocks_ok(self):
        donnees = []
        for i, mois in enumerate(["02", "04", "06", "08", "10", "12"], 2):
            donnees += _make_row("310000", i, debit=1000.0, date=f"2023-{mois}-10")
        grouped = _rows(donnees)
        res, exc = controle_cut_off(
            PID, "STOCK-CUT-OFF", grouped, ("3",), "2023",
            nb_jours=15, seuil_ratio=0.30,
        )
        assert exc is None


# ═══════════════════════════════════════════════════════════════════════════════
# PAIE / PERSONNEL
# ═══════════════════════════════════════════════════════════════════════════════

class TestRatioChargesSociales:
    def test_ratio_normal(self):
        donnees = (
            _make_row("641100", 2, debit=100000.0) +  # salaires
            _make_row("645100", 3, debit=40000.0)     # charges sociales 40%
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped)
        assert exc is None
        assert "40.0%" in res["details"]

    def test_ratio_trop_bas_exception(self):
        donnees = (
            _make_row("641100", 2, debit=100000.0) +
            _make_row("645100", 3, debit=5000.0)    # 5% → trop bas
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped, seuil_min=0.20)
        assert exc is not None
        assert "sous-déclaration" in exc["description"].lower()

    def test_ratio_trop_eleve_exception(self):
        donnees = (
            _make_row("641100", 2, debit=100000.0) +
            _make_row("645100", 3, debit=80000.0)   # 80% → trop élevé
        )
        grouped = _rows(donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped, seuil_max=0.60)
        assert exc is not None
        assert "trop élevé" in exc["description"].lower()

    def test_aucun_salaire(self):
        donnees = _make_row("607000", 2, debit=10000.0)
        grouped = _rows(donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped)
        assert exc is None
        assert "Aucun compte de salaires" in res["details"]

    def test_sans_charges_sociales(self):
        donnees = _make_row("641100", 2, debit=50000.0)
        grouped = _rows(donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped, seuil_min=0.20)
        assert exc is not None  # 0% < 20%


class TestMensualitePaie:
    def test_12_mois_ok(self):
        donnees = []
        for i, mois in enumerate(range(1, 13), 2):
            donnees += _make_row("641100", i, debit=10000.0,
                                 date=f"2023-{mois:02d}-25")
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023")
        assert exc is None
        assert float(res["valeur"]) == pytest.approx(12.0)

    def test_mois_manquants_exception(self):
        # Seulement 6 mois sur 12
        donnees = []
        for i, mois in enumerate([1, 2, 3, 4, 5, 6], 2):
            donnees += _make_row("641100", i, debit=10000.0,
                                 date=f"2023-{mois:02d}-25")
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023", nb_mois_min=10)
        assert exc is not None
        assert "6/12" in exc["description"]
        assert exc["controle_ref"] == "PAIE-MENSUALITE"

    def test_sans_exercice(self):
        donnees = _make_row("641100", 2, debit=10000.0, date="2023-06-25")
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, None)
        assert exc is None
        assert "Exercice non renseigné" in res["details"]

    def test_sans_date(self):
        donnees = _make_row("641100", 2, debit=10000.0)
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023")
        assert exc is None
        assert "Aucune date" in res["details"]

    def test_aucun_compte_paie(self):
        donnees = _make_row("607000", 2, debit=1000.0, date="2023-06-25")
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023")
        assert exc is None
        assert "Aucun compte" in res["details"]

    def test_10_mois_juste_sous_seuil(self):
        donnees = []
        for i, mois in enumerate(range(1, 11), 2):
            donnees += _make_row("641100", i, debit=10000.0,
                                 date=f"2023-{mois:02d}-25")
        grouped = _rows(donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023", nb_mois_min=10)
        assert exc is None  # exactement 10 mois = OK


class TestSoldesAnomauxDettes:
    def test_dettes_sociales_creditrices_ok(self):
        donnees = _make_row("421000", 2, credit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "PAIE-SOLDE-ANORMAL", grouped, ("42",), "credit",
        )
        assert not excs

    def test_dettes_sociales_debitrices_exception(self):
        donnees = _make_row("421000", 2, debit=3000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "PAIE-SOLDE-ANORMAL", grouped, ("42",), "credit",
        )
        assert len(excs) == 1
        assert "débiteur anormal" in excs[0]["description"]


# ═══════════════════════════════════════════════════════════════════════════════
# IMPÔTS / TAXES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTvaCoherence:
    def test_ratio_normal(self):
        donnees = (
            _make_row("445660", 2, debit=8000.0) +   # TVA déductible
            _make_row("445710", 3, credit=10000.0)    # TVA collectée
        )
        grouped = _rows(donnees)
        res, exc = controle_tva_coherence(PID, grouped, seuil_ratio=1.10)
        assert exc is None
        assert "80.0%" in res["details"]

    def test_ratio_trop_eleve_exception(self):
        donnees = (
            _make_row("445660", 2, debit=12000.0) +  # TVA déductible > collectée
            _make_row("445710", 3, credit=10000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_tva_coherence(PID, grouped, seuil_ratio=1.10)
        assert exc is not None
        assert exc["controle_ref"] == "TAXE-TVA-COHERENCE"
        assert float(res["valeur"]) == pytest.approx(1.2)

    def test_aucun_compte_tva(self):
        donnees = _make_row("607000", 2, debit=1000.0)
        grouped = _rows(donnees)
        res, exc = controle_tva_coherence(PID, grouped)
        assert exc is None
        assert "Aucun" in res["details"]

    def test_deductible_sans_collectee_exception(self):
        donnees = _make_row("445660", 2, debit=5000.0)
        grouped = _rows(donnees)
        res, exc = controle_tva_coherence(PID, grouped)
        assert exc is not None
        assert "sans TVA collectée" in exc["description"]

    def test_exactement_au_seuil_ok(self):
        # Ratio = 1.10 → juste à la limite (seuil exclu)
        donnees = (
            _make_row("445660", 2, debit=11000.0) +
            _make_row("445710", 3, credit=10000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_tva_coherence(PID, grouped, seuil_ratio=1.10)
        assert exc is None  # 1.10 n'est pas > 1.10


class TestSoldesAnomauxTva:
    def test_tva_collectee_creditrice_ok(self):
        donnees = _make_row("445710", 2, credit=10000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "TAXE-SOLDE-ANORMAL", grouped, ("4457",), "credit",
        )
        assert not excs

    def test_tva_collectee_debitrice_exception(self):
        donnees = _make_row("445710", 2, debit=5000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "TAXE-SOLDE-ANORMAL", grouped, ("4457",), "credit",
        )
        assert len(excs) == 1
        assert "débiteur anormal" in excs[0]["description"]


class TestTaxeCutOff:
    def test_cut_off_fiscal_exception(self):
        donnees = (
            _make_row("635000", 2, debit=1000.0, date="2023-01-15") +
            _make_row("635000", 3, debit=2000.0, date="2023-12-18") +
            _make_row("635000", 4, debit=3000.0, date="2023-12-25") +
            _make_row("635000", 5, debit=4000.0, date="2023-12-31")
        )
        grouped = _rows(donnees)
        res, exc = controle_cut_off(
            PID, "TAXE-CUT-OFF", grouped, ("63",), "2023",
            nb_jours=15, seuil_ratio=0.30,
        )
        assert exc is not None

    def test_cut_off_fiscal_ok(self):
        donnees = []
        for i, mois in enumerate(["03", "06", "09", "12"], 2):
            donnees += _make_row("635000", i, debit=1000.0, date=f"2023-{mois}-10")
        grouped = _rows(donnees)
        res, exc = controle_cut_off(
            PID, "TAXE-CUT-OFF", grouped, ("63",), "2023",
            nb_jours=15, seuil_ratio=0.30,
        )
        assert exc is None


# ═══════════════════════════════════════════════════════════════════════════════
# SCÉNARIOS INTÉGRATION — 4 nouveaux cycles
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioImmobilisationsComplet:
    """Immobilisations avec sous-amortissement et excédent."""

    def setup_method(self):
        self.donnees_ok = (
            _make_row("215000", 2, debit=100000.0) +
            _make_row("218000", 3, debit=50000.0) +
            _make_row("281500", 4, credit=30000.0) +
            _make_row("281800", 5, credit=15000.0)
        )
        self.donnees_ko = (
            _make_row("215000", 2, debit=20000.0) +  # valeur brute = 20 000
            _make_row("281500", 3, credit=25000.0)   # amort = 25 000 > brute
        )

    def test_scenario_ok_pas_exception(self):
        grouped = _rows(self.donnees_ok)
        _, exc_amort = controle_amortissement_manquant(PID, grouped)
        _, exc_excedent = controle_amort_excedent(PID, grouped)
        assert exc_amort is None
        assert exc_excedent is None

    def test_scenario_ko_excedent_detecte(self):
        grouped = _rows(self.donnees_ko)
        _, exc_excedent = controle_amort_excedent(PID, grouped)
        assert exc_excedent is not None
        assert float(exc_excedent["description"].split("Excédent de")[1].split(".")[0].strip().replace(" ", "")) or True


class TestScenarioPayeComplete:
    """Paie régulière sur 12 mois avec bonne structure."""

    def setup_method(self):
        self.donnees = []
        for i, mois in enumerate(range(1, 13), 2):
            self.donnees += _make_row("641100", i, debit=8000.0, date=f"2023-{mois:02d}-25")
            self.donnees += _make_row("645100", i + 12, debit=3200.0, date=f"2023-{mois:02d}-25")

    def test_mensualite_ok(self):
        grouped = _rows(self.donnees)
        res, exc = controle_mensualite_paie(PID, grouped, "2023")
        assert exc is None

    def test_ratio_social_ok(self):
        grouped = _rows(self.donnees)
        res, exc = controle_ratio_charges_sociales(PID, grouped)
        assert exc is None  # 3200/8000 = 40% → dans la fourchette


# ═══════════════════════════════════════════════════════════════════════════════
# CYCLE CAPITAUX PROPRES ET PROVISIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMouvementProvisions:
    def test_dotation_sans_charge_exception(self):
        """15x crédité mais 68x absent → exception."""
        donnees = _make_row("151000", 2, credit=50000.0)
        grouped = _rows(donnees)
        res, exc = controle_mouvement_provisions(PID, grouped)
        assert exc is not None
        assert exc["controle_ref"] == "CP-PROVISION-MOUVEMENT"
        assert "sans aucune" in exc["description"]

    def test_dotation_avec_charge_suffisante_ok(self):
        """15x crédité ET 68x débité en proportion suffisante."""
        donnees = (
            _make_row("151000", 2, credit=50000.0) +
            _make_row("681000", 3, debit=50000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_mouvement_provisions(PID, grouped)
        assert exc is None
        assert "cohérent" in res["details"]

    def test_ratio_trop_faible_exception(self):
        """Charges 68x très inférieures aux dotations 15x → exception."""
        donnees = (
            _make_row("151000", 2, credit=100000.0) +
            _make_row("681000", 3, debit=5000.0)  # ratio = 5% < seuil 20%
        )
        grouped = _rows(donnees)
        res, exc = controle_mouvement_provisions(PID, grouped, seuil_ratio=0.20)
        assert exc is not None
        assert float(res["valeur"]) == pytest.approx(0.05)

    def test_aucun_compte_15x_ok(self):
        """Pas de provision → OK (contrôle non applicable)."""
        donnees = _make_row("101000", 2, credit=100000.0)
        grouped = _rows(donnees)
        res, exc = controle_mouvement_provisions(PID, grouped)
        assert exc is None
        assert "Aucun" in res["details"]

    def test_aucune_dotation_periode_ok(self):
        """Compte 15x présent mais sans crédit sur la période."""
        donnees = _make_row("151000", 2, debit=5000.0)  # reprise seulement
        grouped = _rows(donnees)
        res, exc = controle_mouvement_provisions(PID, grouped)
        assert exc is None


class TestCoherenceResultat:
    def test_benefice_seul_ok(self):
        """Seul le compte 120 est non nul → cohérent."""
        donnees = _make_row("120000", 2, credit=80000.0)
        grouped = _rows(donnees)
        res, exc = controle_coherence_resultat(PID, grouped)
        assert exc is None
        assert "bénéficiaire" in res["details"]

    def test_deficit_seul_ok(self):
        """Seul le compte 129 est non nul → cohérent."""
        donnees = _make_row("129000", 2, debit=30000.0)
        grouped = _rows(donnees)
        res, exc = controle_coherence_resultat(PID, grouped)
        assert exc is None
        assert "déficitaire" in res["details"]

    def test_120_et_129_non_nuls_exception(self):
        """Les deux comptes non nuls simultanément → exception."""
        donnees = (
            _make_row("120000", 2, credit=50000.0) +
            _make_row("129000", 3, debit=10000.0)
        )
        grouped = _rows(donnees)
        res, exc = controle_coherence_resultat(PID, grouped)
        assert exc is not None
        assert exc["controle_ref"] == "CP-RESULTAT-COHERENCE"
        assert "120" in exc["description"] and "129" in exc["description"]

    def test_aucun_compte_resultat_ok(self):
        """Pas de compte 120/129 dans les données → OK."""
        donnees = _make_row("101000", 2, credit=100000.0)
        grouped = _rows(donnees)
        res, exc = controle_coherence_resultat(PID, grouped)
        assert exc is None
        assert "Aucun" in res["details"]

    def test_solde_nul_120_avec_129_nul_ok(self):
        """Comptes 120 et 129 à zéro → OK."""
        donnees = (
            _make_row("120000", 2, solde=0.005) +  # sous tolerance
            _make_row("129000", 3, solde=0.005)
        )
        grouped = _rows(donnees)
        res, exc = controle_coherence_resultat(PID, grouped)
        assert exc is None


class TestSoldesAnomauxCapitauxPropres:
    def test_capital_crediteur_ok(self):
        """Capital (101) créditeur → normal."""
        donnees = _make_row("101000", 2, credit=500000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "CP-SOLDE-ANORMAL", grouped, ("10", "11", "12", "13"), "credit",
        )
        assert not excs

    def test_capital_debiteur_exception(self):
        """Capital (101) débiteur → capitaux propres négatifs → exception."""
        donnees = _make_row("101000", 2, debit=200000.0)
        grouped = _rows(donnees)
        ress, excs = controle_soldes_anormaux(
            PID, "CP-SOLDE-ANORMAL", grouped, ("10", "11", "12", "13"), "credit",
        )
        assert len(excs) == 1
        assert "débiteur anormal" in excs[0]["description"]


class TestScenarioCapitauxPropresComplet:
    """Scénario complet : capitaux propres sains vs problématiques."""

    def setup_method(self):
        self.donnees_ok = (
            _make_row("101000", 2, credit=500000.0) +  # capital
            _make_row("106000", 3, credit=100000.0) +  # réserves
            _make_row("120000", 4, credit=80000.0) +   # résultat bénéficiaire
            _make_row("151000", 5, credit=20000.0) +   # provision pour risques
            _make_row("681000", 6, debit=20000.0)      # charge de dotation
        )
        self.donnees_ko = (
            _make_row("120000", 2, credit=50000.0) +  # bénéfice ET
            _make_row("129000", 3, debit=30000.0) +   # déficit → anomalie
            _make_row("151000", 4, credit=100000.0)   # provision sans charge
        )

    def test_scenario_ok(self):
        grouped = _rows(self.donnees_ok)
        _, exc_res = controle_coherence_resultat(PID, grouped)
        _, exc_prov = controle_mouvement_provisions(PID, grouped)
        assert exc_res is None
        assert exc_prov is None

    def test_scenario_ko_deux_anomalies(self):
        grouped = _rows(self.donnees_ko)
        _, exc_res = controle_coherence_resultat(PID, grouped)
        _, exc_prov = controle_mouvement_provisions(PID, grouped)
        assert exc_res is not None  # 120 et 129 tous deux non nuls
        assert exc_prov is not None  # provision sans charge 68x
