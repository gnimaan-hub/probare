"""Tests du référentiel de normes ISA/NEP (module normes + configuration cabinet)."""
from __future__ import annotations
import json
import uuid
import pytest

from probare_engine import normes
from probare_engine.normes import norme, reformater_refs, charger_referentiel


class TestFormatage:
    def test_defaut_isa(self):
        # Sans configuration, le référentiel par défaut est ISA
        assert normes.REFERENTIEL_DEFAUT == "isa"

    def test_norme_referentiel_actif(self, monkeypatch):
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "isa")
        assert norme(505) == "ISA 505"
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "nep")
        assert norme(505) == "NEP 505"

    def test_reformater_refs_nep_vers_isa(self, monkeypatch):
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "isa")
        assert reformater_refs("NEP 500") == "ISA 500"
        assert reformater_refs("Conforme aux NEP 320 et NEP 450.") == \
            "Conforme aux ISA 320 et ISA 450."

    def test_reformater_refs_isa_vers_nep(self, monkeypatch):
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "nep")
        assert reformater_refs("ISA 230") == "NEP 230"

    def test_reformater_refs_idempotent_et_none(self, monkeypatch):
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "isa")
        assert reformater_refs("ISA 505") == "ISA 505"
        assert reformater_refs(None) is None
        assert reformater_refs("") == ""
        # Ne touche pas les nombres hors référence
        assert reformater_refs("Compte 505000 : solde 450") == "Compte 505000 : solde 450"


class TestConfiguration:
    def test_lecture_ecriture_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROBARE_DATA_DIR", str(tmp_path / "projets"))
        assert charger_referentiel() == "isa"  # défaut sans fichier
        normes.ecrire_config({"referentiel_normes": "nep"})
        assert charger_referentiel() == "nep"
        # Fichier bien formé
        data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert data["referentiel_normes"] == "nep"

    def test_valeur_invalide_retombe_sur_isa(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROBARE_DATA_DIR", str(tmp_path / "projets"))
        normes.ecrire_config({"referentiel_normes": "ifrs"})
        assert charger_referentiel() == "isa"


class TestRenduDonneesStockees:
    """Les données écrites sous un référentiel sont re-rendues dans l'actif."""

    def test_exception_stockee_en_nep_rendue_en_isa(self, tmp_path, monkeypatch):
        monkeypatch.setattr(normes, "REFERENTIEL_ACTIF", "isa")
        from probare_engine.storage.db import ProjectDB
        db = ProjectDB(tmp_path / "audit.db")
        db.connect()
        pid = str(uuid.uuid4())
        db.create_projet({"id": pid, "nom": "Test"})
        eid = str(uuid.uuid4())
        db.save_exception({
            "id": eid, "projet_id": pid, "controle_ref": "TRESOR-BAL-EQUIL",
            "nep_ref": "NEP 500",  # écrite lors d'une session NEP
            "severite": "critique", "description": "x", "statut": "ouverte",
        })
        exc = db.get_exception(eid)
        assert exc["nep_ref"] == "ISA 500"
        db.close()

    def test_registre_rendu_dans_referentiel_actif(self):
        # Le registre est normalisé au chargement du module (défaut ISA en test)
        from probare_engine.controls.registry import REGISTRE
        prefixes = {c.nep_ref.split()[0] for c in REGISTRE.values()}
        assert prefixes == {normes.prefixe_actif()}


class TestEndpointsConfig:
    def test_get_et_patch_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROBARE_DATA_DIR", str(tmp_path / "projets"))
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        c = TestClient(app)

        r = c.get("/api/config")
        assert r.status_code == 200
        body = r.json()
        assert body["referentiel_normes"] == "isa"
        assert {x["id"] for x in body["referentiels_disponibles"]} == {"isa", "nep"}

        # Bascule vers NEP : enregistrée, mais redémarrage requis
        r = c.patch("/api/config", json={"referentiel_normes": "nep"})
        assert r.status_code == 200
        body = r.json()
        assert body["referentiel_normes"] == "nep"
        assert body["redemarrage_requis"] is True  # l'actif reste celui du démarrage
        assert "Redémarrez" in body["message"]

        # Valeur inconnue refusée
        r = c.patch("/api/config", json={"referentiel_normes": "ifrs"})
        assert r.status_code == 400
