"""Tests du processus d'audit : NEP 450 (cumul), gardes pipeline, NEP 505 (écart/seuil),
agrégats de seuil (NEP 320) et documentation des contrôles ignorés (NEP 230)."""
from __future__ import annotations
import uuid
import pytest

from probare_engine.storage.db import ProjectDB
from probare_engine.statemachine.pipeline import transition, peut_transitionner, PipelineError
from probare_engine.controls.circularisation import calculer_ecart


@pytest.fixture
def db(tmp_path):
    d = ProjectDB(tmp_path / "audit.db")
    d.connect()
    yield d
    d.close()


def _projet(db, **kw):
    pid = str(uuid.uuid4())
    db.create_projet({"id": pid, "nom": "Test", **kw})
    return pid


def _exception(db, pid, ref="TRESOR-BAL-EQUIL", desc="écart"):
    eid = str(uuid.uuid4())
    db.save_exception({
        "id": eid, "projet_id": pid, "controle_ref": ref,
        "nep_ref": "NEP 500", "severite": "significative",
        "description": desc, "statut": "ouverte",
    })
    return eid


# ─── NEP 450 : typologie et cumul ────────────────────────────────────────────

class TestSyntheseAnomalies:
    def test_cumul_vide(self, db):
        pid = _projet(db, seuil_signification=100_000)
        s = db.synthese_anomalies(pid, 100_000, 75_000)
        assert s["cumul_non_corrigees"] == 0.0
        assert not s["depasse_seuil_signification"]

    def test_cumul_non_corrigees(self, db):
        pid = _projet(db, seuil_signification=100_000)
        e1 = _exception(db, pid, desc="a")
        e2 = _exception(db, pid, desc="b")
        e3 = _exception(db, pid, desc="c")
        db.trancher_exception(e1, "Non corrigée", "Auditeur",
                              type_resolution="non_corrigee", montant_incidence=60_000)
        db.trancher_exception(e2, "Non corrigée", "Auditeur",
                              type_resolution="non_corrigee", montant_incidence=50_000)
        db.trancher_exception(e3, "Corrigée", "Auditeur", type_resolution="corrigee")
        s = db.synthese_anomalies(pid, 100_000, 75_000)
        assert s["cumul_non_corrigees"] == 110_000.0
        assert s["depasse_seuil_signification"] is True
        assert s["depasse_seuil_planification"] is True
        assert s["nb_non_corrigees"] == 2
        assert s["nb_corrigees"] == 1

    def test_cumul_sous_seuil(self, db):
        pid = _projet(db, seuil_signification=100_000)
        e1 = _exception(db, pid)
        db.trancher_exception(e1, "Non corrigée mineure", "Auditeur",
                              type_resolution="non_corrigee", montant_incidence=10_000)
        s = db.synthese_anomalies(pid, 100_000, 75_000)
        assert s["cumul_non_corrigees"] == 10_000.0
        assert not s["depasse_seuil_signification"]

    def test_tranchement_legacy_non_type(self, db):
        pid = _projet(db)
        e1 = _exception(db, pid)
        db.trancher_exception(e1, "Décision libre", "Auditeur")
        s = db.synthese_anomalies(pid, None, None)
        assert s["nb_non_typees"] == 1
        assert s["cumul_non_corrigees"] == 0.0


# ─── Gardes pipeline ─────────────────────────────────────────────────────────

class TestGardesPipeline:
    def test_travaux_sans_seuil_bloque(self, db):
        pid = _projet(db)
        db.update_projet(pid, {"etat_courant": "planification"})
        with pytest.raises(PipelineError, match="Seuil"):
            transition(db, pid, "travaux_substantifs")

    def test_travaux_avec_seuil_ok(self, db):
        pid = _projet(db, seuil_signification=50_000)
        db.update_projet(pid, {"etat_courant": "planification"})
        p = transition(db, pid, "travaux_substantifs")
        assert p["etat_courant"] == "travaux_substantifs"

    def test_revue_sans_controles_bloque(self, db):
        pid = _projet(db, seuil_signification=50_000)
        db.update_projet(pid, {"etat_courant": "travaux_substantifs"})
        with pytest.raises(PipelineError, match="Aucun contrôle"):
            transition(db, pid, "revue")

    def test_generation_bloquee_par_cumul_nep450(self, db):
        pid = _projet(db, seuil_signification=100_000)
        db.update_projet(pid, {"etat_courant": "revue"})
        e1 = _exception(db, pid)
        db.trancher_exception(e1, "Non corrigée", "Auditeur",
                              type_resolution="non_corrigee", montant_incidence=200_000)
        # Le message porte le code structuré (détecté par l'UI) et la référence 450
        # rendue dans le référentiel actif (ISA par défaut, NEP en option).
        with pytest.raises(PipelineError, match=r"ANOMALIES_SEUIL_DEPASSE.*450"):
            transition(db, pid, "generation")
        # Confirmation explicite → reste bloqué par la garde ISA 570 (M3) :
        # la conclusion sur la continuité d'exploitation doit être documentée.
        with pytest.raises(PipelineError, match="570"):
            transition(db, pid, "generation", confirmer_depassement_seuil=True)
        db.save_peripherie_evaluation(pid, "continuite", {"score": 1.0, "niveau": "favorable"})
        db.conclure_peripherie(pid, "continuite",
                               "La continuité d'exploitation n'appellerait pas de réserve.",
                               "Auditeur Test")
        # Confirmation explicite + continuité conclue → passe, journal en garde trace
        p = transition(db, pid, "generation", confirmer_depassement_seuil=True)
        assert p["etat_courant"] == "generation"

    def test_retour_arriere_autorise_et_journalise(self, db):
        pid = _projet(db, seuil_signification=50_000)
        db.update_projet(pid, {"etat_courant": "revue"})
        p = transition(db, pid, "ingestion", acteur="auditeur")
        assert p["etat_courant"] == "ingestion"
        journal = db.get_journal(pid)
        entry = next(j for j in journal if j["type"] == "transition_etat")
        assert entry["payload"].get("retour_arriere") is True

    def test_projet_archive_bloque(self, db):
        pid = _projet(db, seuil_signification=50_000)
        db.update_projet(pid, {"etat_courant": "cadrage", "archive": 1})
        with pytest.raises(PipelineError, match="archivé"):
            transition(db, pid, "evaluation_ci")
        ok, raison = peut_transitionner(db, pid, "evaluation_ci")
        assert not ok and "archivé" in raison


# ─── NEP 505 : écart de circularisation référencé au seuil ───────────────────

class TestEcartCircularisation:
    def test_ecart_avec_seuil_dossier(self, db):
        r = calculer_ecart(1_000_000, 940_000, seuil_reference=75_000)
        assert r["ecart"] == 60_000
        assert r["est_significatif"] is False  # 60k < 75k
        r2 = calculer_ecart(1_000_000, 900_000, seuil_reference=75_000)
        assert r2["est_significatif"] is True  # 100k > 75k

    def test_ecart_repli_sans_seuil(self, db):
        r = calculer_ecart(1_000, 850)
        assert r["est_significatif"] is True  # règle interne 5 % / 100


# ─── NEP 230 : contrôles ignorés persistés ───────────────────────────────────

class TestControlesIgnores:
    def test_persistance_et_remplacement(self, db):
        pid = _projet(db)
        db.save_controles_ignores(pid, "tresorerie", [
            {"controle_ref": "TRESOR-RAPPROCH", "raison": "Relevé bancaire manquant"},
        ])
        assert len(db.list_controles_ignores(pid)) == 1
        # Nouvelle passe : la liste du cycle est remplacée, pas cumulée
        db.save_controles_ignores(pid, "tresorerie", [
            {"controle_ref": "TRESOR-VARIATION", "raison": "Seuil non défini"},
        ])
        ignores = db.list_controles_ignores(pid)
        assert len(ignores) == 1
        assert ignores[0]["controle_ref"] == "TRESOR-VARIATION"


# ─── NEP 320 : agrégats de seuil sur les seuls comptes de bilan ─────────────

class TestAgregatsSeuil:
    def test_total_bilan_exclut_classes_6_7(self, db):
        from probare_engine.planning.analytical import calculer_agregats
        pid = _projet(db)
        fid = str(uuid.uuid4())
        db.save_fichier_source({"id": fid, "projet_id": pid, "nom": "bal.csv",
                                "type": "balance", "type_document": "balance"})
        lignes = [
            # (compte, solde) — actif 500k, passif 500k, charges 300k, produits 300k
            ("211000", 500_000.0),   # immobilisation (actif)
            ("101000", -200_000.0),  # capital (passif)
            ("401000", -300_000.0),  # fournisseurs (passif)
            ("601000", 300_000.0),   # charges (classe 6 — hors bilan)
            ("701000", -300_000.0),  # produits (classe 7 — hors bilan)
        ]
        donnees = []
        for i, (compte, solde) in enumerate(lignes, start=2):
            donnees.append({"id": str(uuid.uuid4()), "projet_id": pid,
                            "fichier_source_id": fid, "valeur": compte,
                            "type": "compte", "localisation": f"bal:{i}:Compte"})
            donnees.append({"id": str(uuid.uuid4()), "projet_id": pid,
                            "fichier_source_id": fid, "valeur": solde,
                            "type": "montant", "localisation": f"bal:{i}:Solde"})
        db.save_donnees_sourcees(donnees)

        ag = calculer_agregats(db.conn, pid, fid)
        # Total bilan = max(actif 500k, passif 500k) = 500k.
        # L'ancienne formule (max Σdébits/Σcrédits toute balance) donnait 800k.
        assert ag["total_bilan"] == pytest.approx(500_000.0)
        assert ag["charges_totales"] == pytest.approx(300_000.0)
        assert ag["produits_totaux"] == pytest.approx(300_000.0)
