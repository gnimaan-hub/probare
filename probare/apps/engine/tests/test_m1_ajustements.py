"""Tests M1 — écritures d'ajustement, balance ajustée, état récapitulatif ISA 450.

Tout le chiffrage est déterministe : équilibre de la partie double, effets sur
le résultat et les capitaux propres, construction de la balance ajustée.
"""
from __future__ import annotations
import os
import uuid

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_m1/projets")

from probare_engine.ajustements import (
    valider_lignes, effets_ecriture, synthese_ajustements, balance_ajustee,
    AjustementError,
)


def _l(compte, debit=0, credit=0):
    return {"compte": compte, "debit": debit, "credit": credit}


# ─── Validation des lignes (partie double) ───────────────────────────────────

class TestValiderLignes:
    def test_equilibre_ok(self):
        d, c = valider_lignes([_l("601000", debit=1000), _l("401000", credit=1000)])
        assert d == 1000 and c == 1000

    def test_desequilibre_refuse(self):
        with pytest.raises(AjustementError, match="déséquilibrée"):
            valider_lignes([_l("601000", debit=1000), _l("401000", credit=900)])

    def test_une_seule_ligne_refusee(self):
        with pytest.raises(AjustementError, match="deux lignes"):
            valider_lignes([_l("601000", debit=1000)])

    def test_ligne_double_sens_refusee(self):
        with pytest.raises(AjustementError, match="un seul sens"):
            valider_lignes([_l("601000", debit=1000, credit=1000), _l("401000", credit=0.0)])

    def test_montant_negatif_refuse(self):
        with pytest.raises(AjustementError, match="positifs"):
            valider_lignes([_l("601000", debit=-500), _l("401000", credit=-500)])

    def test_compte_manquant_refuse(self):
        with pytest.raises(AjustementError, match="compte"):
            valider_lignes([_l("", debit=100), _l("401000", credit=100)])

    def test_decomposition_multiligne(self):
        d, c = valider_lignes([
            _l("601000", debit=600), _l("445660", debit=400), _l("401000", credit=1000),
        ])
        assert d == 1000 and c == 1000


# ─── Effets sur le résultat et les capitaux propres ──────────────────────────

class TestEffets:
    def test_charge_supplementaire_diminue_le_resultat(self):
        # Dot. provision (681 débit) / provision (151 crédit) : résultat −5000
        eff = effets_ecriture([_l("681500", debit=5000), _l("151000", credit=5000)])
        assert eff["effet_resultat"] == -5000
        # 151 n'est pas 10x-14x : l'effet CP = effet résultat
        assert eff["effet_capitaux_propres"] == -5000

    def test_produit_supplementaire_augmente_le_resultat(self):
        # Client (411 débit) / vente omise (701 crédit) : résultat +8000
        eff = effets_ecriture([_l("411000", debit=8000), _l("701000", credit=8000)])
        assert eff["effet_resultat"] == 8000
        assert eff["effet_capitaux_propres"] == 8000

    def test_reclassement_bilan_sans_effet(self):
        # Reclassement fournisseur ↔ fournisseur : aucun effet résultat/CP
        eff = effets_ecriture([_l("401000", debit=3000), _l("404000", credit=3000)])
        assert eff["effet_resultat"] == 0
        assert eff["effet_capitaux_propres"] == 0

    def test_mouvement_direct_capitaux_propres(self):
        # Correction imputée directement en réserves (106 débit) / client (411 crédit)
        eff = effets_ecriture([_l("106000", debit=2000), _l("411000", credit=2000)])
        assert eff["effet_resultat"] == 0
        assert eff["effet_capitaux_propres"] == -2000


# ─── État récapitulatif (SUM) ────────────────────────────────────────────────

class TestSyntheseAjustements:
    def test_separation_passees_non_passees(self):
        ecritures = [
            {"statut": "passee", "total_debits": 1000,
             "lignes": [_l("601000", debit=1000), _l("401000", credit=1000)]},
            {"statut": "proposee", "total_debits": 8000,
             "lignes": [_l("411000", debit=8000), _l("701000", credit=8000)]},
            {"statut": "refusee", "total_debits": 5000,
             "lignes": [_l("681500", debit=5000), _l("151000", credit=5000)]},
        ]
        s = synthese_ajustements(ecritures)
        assert s["nb_passees"] == 1 and s["nb_non_passees"] == 2 and s["nb_refusees"] == 1
        # Non passées : +8000 (produit omis) − 5000 (provision refusée) = +3000
        assert s["non_passees"]["effet_resultat"] == 3000
        assert s["non_passees"]["montant_total"] == 13000
        # Passée : charge supplémentaire −1000
        assert s["passees"]["effet_resultat"] == -1000


# ─── Balance ajustée ─────────────────────────────────────────────────────────

class TestBalanceAjustee:
    def test_seules_les_passees_ajustent(self):
        bruts = {"601000": (10_000.0, ["src1"]), "401000": (-10_000.0, ["src2"])}
        ecritures = [
            {"statut": "passee",
             "lignes": [_l("601000", debit=500), _l("401000", credit=500)]},
            {"statut": "proposee",
             "lignes": [_l("601000", debit=9_999), _l("401000", credit=9_999)]},
        ]
        ba = balance_ajustee(bruts, ecritures)
        par_compte = {l["compte"]: l for l in ba["lignes"]}
        assert par_compte["601000"]["solde_brut"] == 10_000
        assert par_compte["601000"]["ajustement"] == 500      # la proposée est ignorée
        assert par_compte["601000"]["solde_ajuste"] == 10_500
        assert par_compte["401000"]["solde_ajuste"] == -10_500
        assert ba["nb_comptes_ajustes"] == 2
        # L'équilibre global est préservé (Σ nets = 0 avant et après)
        assert ba["total_brut"] == 0 and ba["total_ajuste"] == 0

    def test_compte_absent_de_la_balance(self):
        bruts = {"411000": (5_000.0, [])}
        ecritures = [{"statut": "passee",
                      "lignes": [_l("411000", debit=1000), _l("701000", credit=1000)]}]
        ba = balance_ajustee(bruts, ecritures)
        par_compte = {l["compte"]: l for l in ba["lignes"]}
        assert par_compte["701000"]["solde_brut"] == 0
        assert par_compte["701000"]["solde_ajuste"] == -1000


# ─── Routes API (cycle de vie, provenance) ───────────────────────────────────

class TestRoutesAjustements:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def _projet(self, client):
        r = client.post("/api/projets", json={"nom": "T-M1"})
        return r.json()["id"]

    def _ecriture(self, client, pid, **extra):
        r = client.post(f"/api/projets/{pid}/ajustements", json={
            "libelle": "Charge omise sur facture fournisseur",
            "lignes": [
                {"compte": "601000", "libelle": "Achats", "debit": 1000, "credit": 0},
                {"compte": "401000", "libelle": "Fournisseur", "debit": 0, "credit": 1000},
            ],
            **extra,
        })
        assert r.status_code == 200, r.text
        return r.json()

    def test_creation_et_effets(self, client):
        pid = self._projet(client)
        e = self._ecriture(client, pid)
        assert e["statut"] == "proposee"
        assert e["total_debits"] == 1000
        assert e["effet_resultat"] == -1000       # charge supplémentaire
        assert len(e["lignes"]) == 2
        # Provenance : chaque ligne porte sa DonneeSourcee
        assert all(l["donnee_id"] for l in e["lignes"])

    def test_desequilibre_refuse(self, client):
        pid = self._projet(client)
        r = client.post(f"/api/projets/{pid}/ajustements", json={
            "libelle": "Écriture bancale",
            "lignes": [
                {"compte": "601000", "debit": 1000, "credit": 0},
                {"compte": "401000", "debit": 0, "credit": 700},
            ],
        })
        assert r.status_code == 400
        assert "déséquilibrée" in r.json()["detail"]

    def test_cycle_de_vie(self, client):
        pid = self._projet(client)
        e = self._ecriture(client, pid)
        eid = e["id"]
        # proposée → acceptée client → passée
        r = client.patch(f"/api/projets/{pid}/ajustements/{eid}", json={"statut": "acceptee_client"})
        assert r.status_code == 200 and r.json()["statut"] == "acceptee_client"
        r = client.patch(f"/api/projets/{pid}/ajustements/{eid}", json={"statut": "passee"})
        assert r.status_code == 200 and r.json()["statut"] == "passee"
        # passée est terminal
        r = client.patch(f"/api/projets/{pid}/ajustements/{eid}", json={"statut": "proposee"})
        assert r.status_code == 400 and "interdite" in r.json()["detail"]
        # contenu gelé une fois passée
        r = client.patch(f"/api/projets/{pid}/ajustements/{eid}", json={"libelle": "Nouveau libellé"})
        assert r.status_code == 400
        # suppression interdite une fois passée
        r = client.delete(f"/api/projets/{pid}/ajustements/{eid}")
        assert r.status_code == 400

    def test_suppression_possible_si_proposee(self, client):
        pid = self._projet(client)
        e = self._ecriture(client, pid)
        r = client.delete(f"/api/projets/{pid}/ajustements/{e['id']}")
        assert r.status_code == 200
        r = client.get(f"/api/projets/{pid}/ajustements")
        assert r.json()["ecritures"] == []

    def test_balance_ajustee_endpoint(self, client):
        pid = self._projet(client)
        e = self._ecriture(client, pid)
        # Non passée : aucun ajustement dans la balance
        r = client.get(f"/api/projets/{pid}/balance-ajustee")
        assert r.status_code == 200
        assert r.json()["nb_comptes_ajustes"] == 0
        # Passée : les deux comptes sont ajustés
        client.patch(f"/api/projets/{pid}/ajustements/{e['id']}", json={"statut": "passee"})
        r = client.get(f"/api/projets/{pid}/balance-ajustee", params={"seulement_ajustes": True})
        body = r.json()
        assert body["nb_comptes_ajustes"] == 2
        comptes = {l["compte"]: l for l in body["lignes"]}
        assert comptes["601000"]["ajustement"] == 1000
        assert comptes["401000"]["ajustement"] == -1000
        # Provenance conservée sur les lignes ajustées
        assert comptes["601000"]["sources"]

    def test_synthese_dans_liste(self, client):
        pid = self._projet(client)
        self._ecriture(client, pid)
        r = client.get(f"/api/projets/{pid}/ajustements")
        s = r.json()["synthese"]
        assert s["nb_total"] == 1 and s["nb_non_passees"] == 1
        assert s["non_passees"]["effet_resultat"] == -1000

    def test_proposition_ia_sans_cle_api(self, client):
        pid = self._projet(client)
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        eid = str(uuid.uuid4())
        db.save_exception({
            "id": eid, "projet_id": pid, "controle_ref": "VENTE-DOUBLON",
            "nep_ref": "NEP 330", "severite": "significative",
            "description": "doublon", "statut": "ouverte", "montant_estime": 2500,
        })
        r = client.post(f"/api/projets/{pid}/ajustements/proposer/{eid}")
        assert r.status_code == 503  # garde LLM : clé absente / consentement
