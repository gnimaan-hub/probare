"""Tests M4 — assertions sur les contrôles et matrice de couverture (ISA 315 révisée)."""
from __future__ import annotations
import os
import uuid

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_m4/projets")

from probare_engine.controls.registry import REGISTRE, ASSERTIONS, controles_couvrant
from probare_engine.planning.couverture import matrice_couverture


# ─── Taggage des 52 contrôles ────────────────────────────────────────────────

class TestAssertionsRegistre:
    def test_tous_les_controles_ont_au_moins_une_assertion(self):
        sans = [ref for ref, c in REGISTRE.items() if not c.assertions]
        assert sans == [], f"Contrôles sans assertion : {sans}"

    def test_assertions_du_vocabulaire_canonique(self):
        for ref, c in REGISTRE.items():
            for a in c.assertions:
                assert a in ASSERTIONS, f"{ref} porte une assertion inconnue : {a}"

    def test_controles_couvrant(self):
        # Les contrôles de cut-off couvrent l'assertion cut_off
        refs = {c.ref for c in controles_couvrant("ventes", "cut_off")}
        assert "VENTE-CUT-OFF" in refs
        # Les séquences de factures couvrent l'exhaustivité
        refs = {c.ref for c in controles_couvrant("ventes", "exhaustivite")}
        assert "VENTE-SEQ-FACTURES" in refs

    def test_enregistrer_refuse_assertion_inconnue(self):
        from probare_engine.controls.registry import enregistrer, ControleDefinition
        with pytest.raises(ValueError, match="inconnue"):
            enregistrer(ControleDefinition(
                ref="TEST-BIDON", assertions=["inexistante"],
                libelle="x", nep_ref="NEP 500", cycle="tresorerie", description="x"))


# ─── Matrice de couverture ───────────────────────────────────────────────────

def _risque(cycle, assertions, niveau="moyen", libelle="Risque"):
    return {"id": str(uuid.uuid4()), "libelle": libelle, "cycle": cycle,
            "assertions": assertions, "niveau": niveau}


class TestMatriceCouverture:
    def test_cellule_couverte_par_un_controle(self):
        m = matrice_couverture([_risque("ventes", ["exhaustivite"])], [], [])
        assert m["nb_cellules"] == 1
        ligne = m["lignes"][0]
        assert ligne["couvert"] is True
        assert ligne["nb_procedures"] >= 1
        assert all(p["type"] == "controle" for p in ligne["procedures"])
        assert m["nb_trous"] == 0

    def test_trou_signale(self):
        # (ventes, droits) n'est couvert par aucun contrôle du registre
        m = matrice_couverture([_risque("ventes", ["droits"])], [], [])
        assert m["nb_trous"] == 1
        assert m["trous"][0]["assertion"] == "droits"
        assert m["lignes"][0]["couvert"] is False

    def test_sondage_couvre_existence_et_evaluation(self):
        # Un sondage sur le cycle ventes couvre existence/evaluation
        sondages = [{"id": "s1", "cycle": "ventes", "libelle": "Sondage ventes"}]
        m = matrice_couverture([_risque("ventes", ["existence"])], sondages, [])
        procs = m["lignes"][0]["procedures"]
        assert any(p["type"] == "sondage" for p in procs)

    def test_circularisation_couvre_droits(self):
        # (ventes, droits) sans contrôle, mais une circularisation le couvre
        circs = [{"id": "c1", "cycle": "ventes", "compte": "411000", "libelle": "Client X"}]
        m = matrice_couverture([_risque("ventes", ["droits"])], [], circs)
        assert m["nb_trous"] == 0
        assert any(p["type"] == "circularisation" for p in m["lignes"][0]["procedures"])

    def test_risque_sans_assertion_couvre_tout_le_cycle(self):
        # Un risque sans assertion explicite est éclaté sur les 6 assertions
        m = matrice_couverture([_risque("ventes", [])], [], [])
        assert m["nb_cellules"] == len(ASSERTIONS)

    def test_taux_couverture(self):
        m = matrice_couverture(
            [_risque("ventes", ["exhaustivite", "droits"])], [], [])
        # exhaustivite couverte, droits non → 1/2
        assert m["taux_couverture"] == 0.5

    def test_matrice_vide(self):
        m = matrice_couverture([], [], [])
        assert m["nb_cellules"] == 0 and m["taux_couverture"] is None


# ─── Routes API ──────────────────────────────────────────────────────────────

class TestRoutesCouverture:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def _projet(self, client):
        return client.post("/api/projets", json={
            "nom": "T-M4", "cycles_couverts": ["ventes"]}).json()["id"]

    def test_registre_expose_les_assertions(self, client):
        r = client.get("/api/projets/x/controles/registre")
        body = r.json()
        assert "assertions" in body
        assert all("assertions" in c for c in body["controles"])

    def test_matrice_via_api(self, client):
        pid = self._projet(client)
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        # Risque validé sur une assertion couverte, un autre sur un trou
        db.save_risque({"id": str(uuid.uuid4()), "projet_id": pid,
                        "libelle": "Ventes fictives", "cycle": "ventes",
                        "assertions": ["exhaustivite"], "valide_auditeur": 1})
        db.save_risque({"id": str(uuid.uuid4()), "projet_id": pid,
                        "libelle": "Propriété créances", "cycle": "ventes",
                        "assertions": ["droits"], "valide_auditeur": 1})
        # Un risque NON validé ne doit pas entrer dans la matrice
        db.save_risque({"id": str(uuid.uuid4()), "projet_id": pid,
                        "libelle": "Brouillon", "cycle": "ventes",
                        "assertions": ["evaluation"], "valide_auditeur": 0})
        r = client.get(f"/api/projets/{pid}/planification/couverture")
        body = r.json()
        assert body["nb_cellules"] == 2   # le risque non validé est exclu
        assert body["nb_trous"] == 1
        assert body["trous"][0]["assertion"] == "droits"

    def test_proposer_procedures_sans_cle(self, client):
        pid = self._projet(client)
        from probare_engine.api.routes import _get_db
        _get_db(pid).save_risque({"id": str(uuid.uuid4()), "projet_id": pid,
                                  "libelle": "Propriété", "cycle": "ventes",
                                  "assertions": ["droits"], "valide_auditeur": 1})
        # Trou présent, mais garde LLM (pas de clé) → 503
        r = client.post(f"/api/projets/{pid}/planification/couverture/proposer-procedures")
        assert r.status_code == 503
