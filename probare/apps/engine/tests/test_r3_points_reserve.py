"""R3 — points de réserve QUALITATIFS (ISA 705) et cohérence avec l'opinion.

Défaut corrigé, constaté au test de bout en bout ARULOS : une opinion « avec
réserve » adossée à un cumul ISA 450 de zéro. Les réserves étaient des
limitations d'étendue (provisions et dettes foncières non justifiées) — un
fondement bien réel, mais que le modèle purement quantitatif ne savait pas
représenter, donc invisible au dossier.
"""
from __future__ import annotations
import uuid
import pytest

from probare_engine.storage.db import ProjectDB
from probare_engine.reserves import (
    TYPE_LIMITATION, TYPE_INCERTITUDE, TYPE_DESACCORD,
    IMPACT_AUCUN, IMPACT_RESERVE, IMPACT_DEFAVORABLE, IMPACT_IMPOSSIBILITE,
    STATUT_OUVERT, STATUT_LEVE,
    opinion_minimale_requise, incoherences_opinion, synthese_points_reserve,
    points_impactants, valider_point,
)


@pytest.fixture
def db(tmp_path):
    d = ProjectDB(tmp_path / "audit.db")
    d.connect()
    yield d
    d.close()


def _projet(db, **kw):
    pid = str(uuid.uuid4())
    db.create_projet({"id": pid, "nom": "ARULOS", "client": "ARULOS SARL",
                      "exercice": "2024", "seuil_signification": 1_000_000, **kw})
    return pid


def _point(**kw):
    return {"id": str(uuid.uuid4()), "type": TYPE_LIMITATION, "libelle": "Provisions",
            "impact_opinion": IMPACT_RESERVE, "statut": STATUT_OUVERT, **kw}


# ─── Règle d'opinion minimale ────────────────────────────────────────────────

def test_sans_point_ni_anomalie_opinion_sans_reserve_suffit():
    assert opinion_minimale_requise([], {"cumul_non_corrigees": 0}) == "sans_reserve"


def test_limitation_ouverte_impose_une_reserve():
    """Le cas ARULOS : cumul chiffré nul, mais une limitation d'étendue ouverte."""
    points = [_point()]
    assert opinion_minimale_requise(points, {"cumul_non_corrigees": 0}) == "avec_reserve"


def test_le_point_le_plus_grave_lemporte():
    points = [_point(impact_opinion=IMPACT_RESERVE),
              _point(impact_opinion=IMPACT_IMPOSSIBILITE, type=TYPE_LIMITATION),
              _point(impact_opinion=IMPACT_AUCUN, type=TYPE_INCERTITUDE)]
    assert opinion_minimale_requise(points, {}) == "impossibilite"


def test_point_leve_ne_pese_plus():
    """Un point levé reste au dossier — il documente une diligence menée à son
    terme — mais il ne justifie plus de réserve."""
    points = [_point(statut=STATUT_LEVE, resolution="Attestation obtenue le 12/03.")]
    assert points_impactants(points) == []
    assert opinion_minimale_requise(points, {}) == "sans_reserve"


def test_impact_aucun_ne_declenche_pas_de_reserve():
    """Un point suivi mais jugé sans incidence relève de l'observation."""
    points = [_point(type=TYPE_INCERTITUDE, impact_opinion=IMPACT_AUCUN)]
    assert opinion_minimale_requise(points, {}) == "sans_reserve"


def test_cumul_450_seul_impose_toujours_une_reserve():
    """La règle quantitative existante n'est pas affaiblie par R3."""
    assert opinion_minimale_requise([], {"depasse_seuil_signification": True}) == "avec_reserve"


# ─── Cohérence opinion ↔ dossier, dans les deux sens ─────────────────────────

def test_incoherence_opinion_trop_clemente():
    ecarts = incoherences_opinion("sans_reserve", [_point(libelle="Dettes foncières")], {})
    assert len(ecarts) == 1
    assert "Dettes foncières" in ecarts[0] and "Opinion avec réserve" in ecarts[0]


def test_incoherence_reserve_sans_fondement_tracable():
    """Le défaut du test E2E : réserve exprimée, cumul nul, registre vide."""
    ecarts = incoherences_opinion("avec_reserve", [], {"cumul_non_corrigees": 0.0})
    assert len(ecarts) == 1
    assert "sans fondement traçable" in ecarts[0]


def test_reserve_justifiee_par_un_point_est_coherente():
    assert incoherences_opinion("avec_reserve", [_point()], {"cumul_non_corrigees": 0.0}) == []


def test_reserve_justifiee_par_le_cumul_seul_est_coherente():
    """Anomalies chiffrées non corrigées sous le seuil : l'auditeur peut juger
    qu'elles motivent tout de même une réserve — rien à redire."""
    assert incoherences_opinion("avec_reserve", [], {"cumul_non_corrigees": 250_000.0}) == []


def test_opinion_plus_severe_que_le_minimum_est_admise():
    """Le jugement de l'auditeur peut durcir l'opinion, jamais l'adoucir."""
    assert incoherences_opinion("defavorable", [_point()], {}) == []


def test_pas_de_verdict_sans_type_opinion():
    assert incoherences_opinion(None, [_point()], {}) == []
    assert incoherences_opinion("", [], {}) == []


# ─── Synthèse servie à côté du cumul 450 ─────────────────────────────────────

def test_synthese_separe_ouverts_leves_et_montants():
    points = [
        _point(montant_concerne=4_500_000, rubrique="Provisions pour risques"),
        _point(type=TYPE_DESACCORD, impact_opinion=IMPACT_AUCUN),
        _point(statut=STATUT_LEVE, resolution="Confirmation reçue."),
    ]
    syn = synthese_points_reserve(points, {"cumul_non_corrigees": 0})
    assert (syn["nb_total"], syn["nb_ouverts"], syn["nb_leves"]) == (3, 2, 1)
    assert syn["nb_impactants"] == 1
    assert syn["par_type"][TYPE_LIMITATION] == 1
    assert syn["montant_concerne_total"] == 4_500_000
    assert syn["opinion_minimale_requise"] == "avec_reserve"


# ─── Vocabulaire ─────────────────────────────────────────────────────────────

def test_valider_point_refuse_le_vocabulaire_inconnu():
    with pytest.raises(ValueError, match="Type de point de réserve inconnu"):
        valider_point({"libelle": "x", "type": "grave", "impact_opinion": IMPACT_RESERVE})
    with pytest.raises(ValueError, match="Impact sur l'opinion inconnu"):
        valider_point({"libelle": "x", "type": TYPE_LIMITATION, "impact_opinion": "beaucoup"})
    with pytest.raises(ValueError, match="libellé"):
        valider_point({"libelle": "  ", "type": TYPE_LIMITATION, "impact_opinion": IMPACT_RESERVE})


def test_point_leve_doit_documenter_sa_levee():
    """Lever un point sans dire comment reviendrait à effacer une limitation."""
    with pytest.raises(ValueError, match="documenter"):
        valider_point({"libelle": "x", "type": TYPE_LIMITATION,
                       "impact_opinion": IMPACT_RESERVE, "statut": STATUT_LEVE})
    valider_point({"libelle": "x", "type": TYPE_LIMITATION, "impact_opinion": IMPACT_RESERVE,
                   "statut": STATUT_LEVE, "resolution": "Attestation notariée obtenue."})


# ─── Persistance ─────────────────────────────────────────────────────────────

def test_crud_points_reserve(db):
    pid = _projet(db)
    p = db.save_point_reserve({**_point(projet_id=pid), "description": "Aucun justificatif."})
    assert p["statut"] == "ouvert" and p["source"] == "manuel" and p["cree_le"]

    maj = db.save_point_reserve({"id": p["id"], "projet_id": pid, "statut": STATUT_LEVE,
                                 "resolution": "Justificatifs produits."})
    assert maj["statut"] == STATUT_LEVE
    assert maj["libelle"] == "Provisions", "l'upsert ne doit pas perdre les champs non fournis"
    assert maj["cree_le"] == p["cree_le"]

    assert db.delete_point_reserve(p["id"]) is True
    assert db.list_points_reserve(pid) == []


def test_liste_ouverts_avant_leves_puis_ordre_didentification(db):
    """Les points ouverts passent devant ; à l'intérieur d'un groupe, l'ordre
    est celui de l'identification — c'est l'ordre rendu au fondement du rapport."""
    pid = _projet(db)
    db.save_point_reserve(_point(projet_id=pid, libelle="Levé", statut=STATUT_LEVE,
                                 resolution="ok"))
    db.save_point_reserve(_point(projet_id=pid, libelle="Ouvert 1"))
    db.save_point_reserve(_point(projet_id=pid, libelle="Ouvert 2"))
    assert [p["libelle"] for p in db.list_points_reserve(pid)] == [
        "Ouvert 1", "Ouvert 2", "Levé"]


# ─── Bout en bout : API et livrables ─────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PROBARE_DATA_DIR", str(tmp_path / "projets"))
    import importlib
    from probare_engine.api import routes as routes_mod
    importlib.reload(routes_mod)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(routes_mod.router)
    return TestClient(app)


def _creer_projet_api(client) -> str:
    r = client.post("/projets", json={"nom": "ARULOS", "client": "ARULOS SARL",
                                      "exercice": "2024", "nif": "123"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_api_registre_et_garde_de_validation(client):
    pid = _creer_projet_api(client)

    # L'opinion doit exister avant toute validation.
    from probare_engine.api.routes import _get_db
    db = _get_db(pid)
    db.save_opinion(pid, {"type_opinion": "avec_reserve", "titre": "Opinion avec réserve",
                          "texte_opinion": "À notre avis, sous réserve...",
                          "fondement": "Limitation sur les provisions."})

    # 1. Registre vide + réserve → la validation est refusée, avec le motif.
    r = client.put(f"/projets/{pid}/opinion", json={"validee": True})
    assert r.status_code == 400
    assert "sans fondement traçable" in r.json()["detail"]

    # 2. L'auditeur enregistre le point de réserve qui la motive.
    r = client.post(f"/projets/{pid}/points-reserve", json={
        "type": "limitation", "libelle": "Provisions pour risques non justifiées",
        "description": "Aucun élément probant sur le mode de calcul.",
        "rubrique": "Provisions pour risques et charges",
        "montant_concerne": 4_500_000, "impact_opinion": "reserve"})
    assert r.status_code == 200, r.text
    point_id = r.json()["point"]["id"]

    # 3. La même validation passe désormais.
    r = client.put(f"/projets/{pid}/opinion", json={"validee": True})
    assert r.status_code == 200, r.text
    assert r.json()["opinion"]["validee"] == 1

    # 4. La synthèse sert le qualitatif à côté du cumul 450.
    syn = client.get(f"/projets/{pid}/synthese-mission").json()
    assert syn["anomalies"]["cumul_non_corrigees"] == 0.0
    assert syn["points_reserve"]["nb_ouverts"] == 1
    assert syn["points_reserve"]["opinion_minimale_requise"] == "avec_reserve"
    assert syn["coherence_opinion"] == []

    # 5. Une opinion sans réserve devient à son tour incohérente.
    r = client.put(f"/projets/{pid}/opinion",
                   json={"type_opinion": "sans_reserve", "validee": True})
    assert r.status_code == 400
    assert "Provisions pour risques non justifiées" in r.json()["detail"]

    # 6. Le point levé cesse de peser.
    r = client.put(f"/projets/{pid}/points-reserve/{point_id}", json={
        "type": "limitation", "libelle": "Provisions pour risques non justifiées",
        "impact_opinion": "reserve", "statut": "leve",
        "resolution": "Détail du calcul et attestation d'avocat obtenus."})
    assert r.status_code == 200, r.text
    r = client.put(f"/projets/{pid}/opinion",
                   json={"type_opinion": "sans_reserve", "validee": True})
    assert r.status_code == 200, r.text


def test_api_vocabulaire_reserves(client):
    voc = client.get("/vocabulaire-reserves").json()
    assert {t["id"] for t in voc["types"]} == {"limitation", "incertitude", "desaccord"}
    assert {i["id"] for i in voc["impacts"]} == {"aucun", "reserve", "defavorable",
                                                 "impossibilite"}


def test_api_candidats_depuis_les_controles_non_executes(client):
    """Une limitation déjà établie par le dossier est proposée, pas inventée."""
    pid = _creer_projet_api(client)
    from probare_engine.api.routes import _get_db
    db = _get_db(pid)
    db.save_controles_ignores(pid, "tresorerie", [
        {"controle_ref": "TRESOR-RAPPROCH", "raison": "Relevé bancaire non fourni"}])

    cands = client.get(f"/projets/{pid}/points-reserve/candidats").json()["candidats"]
    assert len(cands) == 1
    assert cands[0]["type"] == "limitation"
    assert "TRESOR-RAPPROCH" in cands[0]["libelle"]
    assert "Relevé bancaire non fourni" in cands[0]["description"]

    # Une fois enregistré, le candidat ne se represente plus.
    client.post(f"/projets/{pid}/points-reserve", json={
        **{k: v for k, v in cands[0].items()}, "impact_opinion": "reserve"})
    assert client.get(f"/projets/{pid}/points-reserve/candidats").json()["candidats"] == []


def test_rapport_expose_les_points_de_reserve_dans_le_fondement(db, tmp_path):
    """R1 + R3 — le fondement porte la base de la réserve, les points qualitatifs
    puis le paragraphe normatif, dans cet ordre."""
    from probare_engine.reporting.export import generer_rapport_audit, fondement_complet
    pid = _projet(db)
    projet = db.get_projet(pid)
    points = [db.save_point_reserve(_point(
        projet_id=pid, libelle="Provisions pour risques non justifiées",
        description="Aucun élément probant sur le mode de calcul.",
        rubrique="Provisions pour risques et charges", montant_concerne=4_500_000))]
    opinion = {"type_opinion": "avec_reserve", "titre": "Opinion avec réserve",
               "texte_opinion": "À notre avis, sous réserve...",
               "fondement": "Nos travaux ont été limités.", "validee": 1}

    texte = fondement_complet(opinion["fondement"], points)
    i_base = texte.index("Nos travaux ont été limités.")
    i_point = texte.index("Provisions pour risques non justifiées")
    i_norme = texte.index("indépendants de l'entité")
    assert i_base < i_point < i_norme, "ordre ISA 705 : base, points, paragraphe normatif"

    cabinet = {"nom": "Cabinet NIMAAN & Associés", "responsable_nom": "Gouled Ahmed",
               "responsable_titre": "Commissaire aux comptes", "adresse_ville": "Djibouti"}
    out = generer_rapport_audit(projet, opinion, tmp_path / "rapport.docx", cabinet=cabinet,
                                plan=db.get_or_create_planification(pid), points_reserve=points)
    import docx
    txt = "\n".join(p.text for p in docx.Document(str(out)).paragraphs)
    assert "Limitation de l'étendue des travaux" in txt
    assert "Provisions pour risques non justifiées" in txt
    assert "4 500 000 FDJ" in txt
    assert "n'entre pas au cumul des anomalies non corrigées" in txt


def test_point_leve_absent_du_fondement_du_rapport(db):
    """Un point levé ne doit plus motiver la réserve dans le rapport."""
    from probare_engine.reporting.export import fondement_complet
    points = [_point(libelle="Stock non observé", statut=STATUT_LEVE,
                     resolution="Inventaire tournant exploité.")]
    assert "Stock non observé" not in fondement_complet("Base.", points)
