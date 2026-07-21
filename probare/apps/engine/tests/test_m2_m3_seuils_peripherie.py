"""Tests M2 (seuils complémentaires — ISA 320/450) et M3 (diligences ISA de périphérie).

M2 : seuil des anomalies manifestement insignifiantes, résolution 'insignifiante'
hors cumul mais documentée, seuils spécifiques par cycle (toujours plus stricts).
M3 : questionnaires de périphérie (patron QCI), score déterministe, indicateurs
de continuité calculés depuis la balance, garde pipeline ISA 570.
"""
from __future__ import annotations
import os
import uuid
from types import SimpleNamespace

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_m2m3/projets")

from probare_engine.storage.db import ProjectDB
from probare_engine.statemachine.pipeline import transition, PipelineError
from probare_engine.planning.thresholds import calculer_seuils, TAUX_INSIGNIFIANCE_DEFAUT
from probare_engine.controls.peripherie import (
    DILIGENCES, liste_diligences, calculer_niveau_diligence, indicateurs_continuite,
)


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


def _exception(db, pid, ref="TRESOR-BAL-EQUIL", desc="écart", severite="significative"):
    eid = str(uuid.uuid4())
    db.save_exception({
        "id": eid, "projet_id": pid, "controle_ref": ref,
        "nep_ref": "NEP 500", "severite": severite,
        "description": desc, "statut": "ouverte",
    })
    return eid


# ─── M2 : calcul des trois seuils ────────────────────────────────────────────

class TestSeuilsComplementaires:
    def test_seuil_insignifiance_calcule(self):
        r = calculer_seuils("total_bilan", 10_000_000, 0.01)
        assert r["seuil_signification"] == 100_000
        assert r["seuil_planification"] == 75_000
        assert r["taux_insignifiance"] == TAUX_INSIGNIFIANCE_DEFAUT
        assert r["seuil_insignifiance"] == 3_000  # 3 % du seuil

    def test_taux_insignifiance_personnalise(self):
        r = calculer_seuils("total_bilan", 10_000_000, 0.01, taux_insignifiance=0.05)
        assert r["seuil_insignifiance"] == 5_000


# ─── M2 : résolution 'insignifiante' hors cumul mais documentée ──────────────

class TestResolutionInsignifiante:
    def test_insignifiantes_hors_cumul_mais_listees(self, db):
        pid = _projet(db, seuil_signification=100_000)
        e1 = _exception(db, pid, desc="grosse anomalie")
        e2 = _exception(db, pid, desc="poussière")
        db.trancher_exception(e1, "Non corrigée", "Auditeur",
                              type_resolution="non_corrigee", montant_incidence=60_000)
        db.trancher_exception(e2, "Montant dérisoire", "Auditeur",
                              type_resolution="insignifiante", montant_incidence=1_500)
        s = db.synthese_anomalies(pid, 100_000, 75_000)
        # Hors cumul…
        assert s["cumul_non_corrigees"] == 60_000.0
        assert not s["depasse_seuil_signification"]
        # …mais comptée, chiffrée et listée (jamais silencieuse)
        assert s["nb_insignifiantes"] == 1
        assert s["total_insignifiantes"] == 1_500.0
        assert len(s["exceptions_insignifiantes"]) == 1
        assert s["exceptions_insignifiantes"][0]["montant_incidence"] == 1_500

    def test_montant_conserve_sur_exception(self, db):
        pid = _projet(db, seuil_signification=100_000)
        eid = _exception(db, pid)
        exc = db.trancher_exception(eid, "Insignifiante", "Auditeur",
                                    type_resolution="insignifiante", montant_incidence=900)
        assert exc["type_resolution"] == "insignifiante"
        assert exc["montant_incidence"] == 900


# ─── M2 : validations de la route trancher (insignifiante) ───────────────────

class TestRouteTrancherInsignifiante:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def _projet_api(self, client, **extra):
        r = client.post("/api/projets", json={"nom": "T-M2", **extra})
        assert r.status_code == 200
        return r.json()["id"]

    def _exception_api(self, pid, severite="significative"):
        # Injection directe en base (la création d'exception passe par les contrôles)
        from probare_engine.api.routes import _get_db
        db = _get_db(pid)
        return _exception(db, pid, severite=severite)

    def test_refus_sans_seuil_insignifiance(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        eid = self._exception_api(pid)
        r = client.post(f"/api/projets/{pid}/exceptions/{eid}/trancher", json={
            "decision_humaine": "x" * 25, "decideur": "Auditeur",
            "type_resolution": "insignifiante", "montant_incidence": 100,
        })
        assert r.status_code == 400
        assert "insignifiantes" in r.json()["detail"]

    def test_refus_montant_au_dessus_du_seuil(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        from probare_engine.api.routes import _get_db
        _get_db(pid).update_projet(pid, {"seuil_insignifiance": 3_000})
        eid = self._exception_api(pid)
        r = client.post(f"/api/projets/{pid}/exceptions/{eid}/trancher", json={
            "decision_humaine": "x" * 25, "decideur": "Auditeur",
            "type_resolution": "insignifiante", "montant_incidence": 10_000,
        })
        assert r.status_code == 400
        assert "dépasse" in r.json()["detail"]

    def test_refus_exception_critique(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        from probare_engine.api.routes import _get_db
        _get_db(pid).update_projet(pid, {"seuil_insignifiance": 3_000})
        eid = self._exception_api(pid, severite="critique")
        r = client.post(f"/api/projets/{pid}/exceptions/{eid}/trancher", json={
            "decision_humaine": "x" * 25, "decideur": "Auditeur",
            "type_resolution": "insignifiante", "montant_incidence": 100,
        })
        assert r.status_code == 400
        assert "critique" in r.json()["detail"]

    def test_acceptation_cas_nominal(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        from probare_engine.api.routes import _get_db
        _get_db(pid).update_projet(pid, {"seuil_insignifiance": 3_000})
        eid = self._exception_api(pid)
        r = client.post(f"/api/projets/{pid}/exceptions/{eid}/trancher", json={
            "decision_humaine": "Montant manifestement insignifiant, écarté du cumul.",
            "decideur": "Auditeur",
            "type_resolution": "insignifiante", "montant_incidence": 1_200,
        })
        assert r.status_code == 200
        assert r.json()["type_resolution"] == "insignifiante"


# ─── M2 : seuils spécifiques par cycle ───────────────────────────────────────

class TestSeuilsSpecifiques:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def _projet_api(self, client, **extra):
        r = client.post("/api/projets", json={
            "nom": "T-SS", "cycles_couverts": ["tresorerie", "achats"], **extra})
        return r.json()["id"]

    def test_refus_sans_seuil_global(self, client):
        pid = self._projet_api(client)
        r = client.put(f"/api/projets/{pid}/planification/seuils-specifiques", json={
            "seuils": {"tresorerie": {"seuil": 10_000, "justification": "zone sensible"}}})
        assert r.status_code == 400

    def test_refus_superieur_au_global(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        r = client.put(f"/api/projets/{pid}/planification/seuils-specifiques", json={
            "seuils": {"tresorerie": {"seuil": 200_000, "justification": "zone sensible"}}})
        assert r.status_code == 400
        assert "inférieur" in r.json()["detail"]

    def test_refus_cycle_hors_perimetre(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        r = client.put(f"/api/projets/{pid}/planification/seuils-specifiques", json={
            "seuils": {"paie": {"seuil": 10_000, "justification": "zone sensible"}}})
        assert r.status_code == 400

    def test_refus_sans_justification(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        r = client.put(f"/api/projets/{pid}/planification/seuils-specifiques", json={
            "seuils": {"tresorerie": {"seuil": 10_000, "justification": "ras"}}})
        assert r.status_code == 400
        assert "Justifiez" in r.json()["detail"]

    def test_enregistrement_et_application_au_cycle(self, client):
        pid = self._projet_api(client, seuil_signification=100_000)
        r = client.put(f"/api/projets/{pid}/planification/seuils-specifiques", json={
            "seuils": {"tresorerie": {"seuil": 10_000,
                                      "justification": "Cycle sensible aux détournements"}}})
        assert r.status_code == 200
        assert r.json()["seuils_specifiques"]["tresorerie"]["seuil"] == 10_000

        from probare_engine.api.routes import _get_db, _seuil_cycle
        db = _get_db(pid)
        projet = db.get_projet(pid)
        seuil, note = _seuil_cycle(db, projet, "tresorerie")
        assert seuil == 10_000 and note and "spécifique" in note
        seuil, note = _seuil_cycle(db, projet, "achats")
        assert seuil == 100_000 and note is None


# ─── M3 : questionnaires et score des diligences ─────────────────────────────

class TestDiligencesPeripherie:
    def test_sept_diligences_definies(self):
        codes = {d["code"] for d in liste_diligences()}
        assert codes == {"acceptation", "fraude", "parties_liees", "evenements_posterieurs",
                         "continuite", "declarations_ecrites", "gouvernance"}
        # Seule la continuité (ISA 570) exige une conclusion avant génération
        assert DILIGENCES["continuite"]["conclusion_requise"] is True
        # Les deux lettres : affirmation (580) et gouvernance (260/265)
        assert DILIGENCES["declarations_ecrites"]["lettre"] == "affirmation"
        assert DILIGENCES["gouvernance"]["lettre"] == "gouvernance"

    def test_questions_completes(self):
        for d in liste_diligences():
            assert len(d["questions"]) >= 5
            for q in d["questions"]:
                assert q["id"] and q["question"] and q["risque_si_non"]

    def test_bareme_prudent(self):
        # favorable exige un score élevé ET zéro non
        rep = [{"reponse": "oui"}] * 6
        assert calculer_niveau_diligence(rep)["niveau"] == "favorable"
        rep = [{"reponse": "oui"}] * 6 + [{"reponse": "non"}]
        assert calculer_niveau_diligence(rep)["niveau"] == "attention"
        rep = [{"reponse": "oui"}] * 2 + [{"reponse": "non"}] * 3
        assert calculer_niveau_diligence(rep)["niveau"] == "defavorable"
        # na neutralisé
        rep = [{"reponse": "oui"}] * 3 + [{"reponse": "na"}] * 4
        info = calculer_niveau_diligence(rep)
        assert info["niveau"] == "favorable" and info["nb_na"] == 4
        assert calculer_niveau_diligence([])["niveau"] == "defavorable"


# ─── M3 : indicateurs de continuité (ISA 570) ────────────────────────────────

def _row(compte: str, solde: float):
    return {
        "compte": SimpleNamespace(id=f"c-{compte}", valeur=compte),
        "solde": SimpleNamespace(id=f"s-{compte}", valeur=solde),
    }


class TestIndicateursContinuite:
    def test_calculs_et_alertes(self):
        # Capital 1 000 000 (créditeur), perte 600 000 (compte 129 débiteur),
        # immobilisations 300 000, trésorerie 50 000.
        rows = [
            _row("101000", -1_000_000),
            _row("129000", 600_000),
            _row("215000", 300_000),
            _row("512000", 50_000),
        ]
        ind = indicateurs_continuite(rows, seuil=100_000)
        assert ind["capital_social"] == 1_000_000
        assert ind["resultat_exercice"] == -600_000
        assert ind["capitaux_propres"] == 400_000          # 1 000 000 − 600 000
        # Ressources stables 1xx = 400 000 ; FR = 400 000 − 300 000
        assert ind["fonds_roulement"] == 100_000
        assert ind["tresorerie_nette"] == 50_000
        assert "Capitaux propres inférieurs à la moitié du capital social." in ind["alertes"]
        assert "Résultat de l'exercice déficitaire." in ind["alertes"]
        assert ind["nb_alertes"] == 2
        assert ind["sources"]  # provenance conservée

    def test_situation_saine_sans_alerte(self):
        rows = [
            _row("101000", -1_000_000),
            _row("120000", -200_000),   # bénéfice (créditeur)
            _row("215000", 500_000),
            _row("512000", 400_000),
        ]
        ind = indicateurs_continuite(rows)
        assert ind["capitaux_propres"] == 1_200_000
        assert ind["resultat_exercice"] == 200_000
        assert ind["alertes"] == []


# ─── M3 : routes périphérie (mode dégradé sans clé API) ─────────────────────

class TestRoutesPeripherie:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    def _projet_api(self, client):
        r = client.post("/api/projets", json={"nom": "T-M3"})
        return r.json()["id"]

    def test_get_peripherie_liste_les_sept(self, client):
        pid = self._projet_api(client)
        r = client.get(f"/api/projets/{pid}/peripherie")
        assert r.status_code == 200
        diligences = r.json()["diligences"]
        assert len(diligences) == 7
        assert all(d["statut"] == "non_commencee" for d in diligences)

    def test_cycle_complet_reponses_evaluation_conclusion(self, client):
        pid = self._projet_api(client)
        # Moins de 3 réponses → refus d'évaluer
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/reponses", json={
            "reponses": [{"question_id": "CNT-01", "reponse": "oui"}]})
        assert r.status_code == 200
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/evaluer")
        assert r.status_code == 400

        # Conclure avant d'évaluer → refus
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/conclure", json={
            "conclusion": "Conclusion suffisamment argumentée ici.", "conclu_par": "Auditeur"})
        assert r.status_code == 400

        # 3 réponses → évaluation (mode dégradé : pas de clé API)
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/reponses", json={
            "reponses": [
                {"question_id": "CNT-01", "reponse": "oui"},
                {"question_id": "CNT-02", "reponse": "non", "commentaire": "pertes récurrentes"},
                {"question_id": "CNT-03", "reponse": "oui"},
            ]})
        assert r.status_code == 200
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/evaluer")
        assert r.status_code == 200
        body = r.json()
        assert body["score_info"]["niveau"] in ("attention", "defavorable")
        assert body["evaluation"]["evalue_le"]

        # Conclusion trop courte → refus ; puis conclusion valide signée
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/conclure", json={
            "conclusion": "court", "conclu_par": "Auditeur"})
        assert r.status_code == 400
        r = client.post(f"/api/projets/{pid}/peripherie/continuite/conclure", json={
            "conclusion": "La continuité serait assurée sous réserve des diligences listées.",
            "conclu_par": "Auditeur Test"})
        assert r.status_code == 200
        assert r.json()["evaluation"]["conclusion"]

        # Statut consolidé
        r = client.get(f"/api/projets/{pid}/peripherie")
        cnt = next(d for d in r.json()["diligences"] if d["code"] == "continuite")
        assert cnt["statut"] == "conclue"

    def test_lettre_refusee_pour_diligence_sans_lettre(self, client):
        pid = self._projet_api(client)
        r = client.post(f"/api/projets/{pid}/peripherie/fraude/generer-lettre")
        # 400 : la fraude ne produit pas de lettre (ou 403/503 selon garde LLM,
        # mais la garde LLM passe après la vérification du consentement client)
        assert r.status_code in (400, 403)

    def test_diligence_inconnue(self, client):
        pid = self._projet_api(client)
        assert client.post(f"/api/projets/{pid}/peripherie/inconnue/evaluer").status_code == 400


# ─── M3 : garde pipeline ISA 570 ─────────────────────────────────────────────

class TestGardeContinuite:
    def test_generation_bloquee_sans_conclusion_570(self, db):
        pid = _projet(db, seuil_signification=100_000)
        db.update_projet(pid, {"etat_courant": "revue"})
        with pytest.raises(PipelineError, match="570"):
            transition(db, pid, "generation")
        # Évaluée mais non conclue → toujours bloqué
        db.save_peripherie_evaluation(pid, "continuite", {"score": 1.0, "niveau": "favorable"})
        with pytest.raises(PipelineError, match="570"):
            transition(db, pid, "generation")
        # Conclue et signée → passe
        db.conclure_peripherie(pid, "continuite",
                               "La continuité d'exploitation n'appellerait pas de réserve.",
                               "Auditeur Test")
        p = transition(db, pid, "generation")
        assert p["etat_courant"] == "generation"
