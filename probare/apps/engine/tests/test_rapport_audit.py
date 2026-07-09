"""Tests de la phase Rapport d'audit : opinion (CRUD), référentiel comptable,
synthèse de mission et génération du rapport d'audit + mémorandum."""
from __future__ import annotations
import uuid
import pytest

from probare_engine.storage.db import ProjectDB
from probare_engine.normes import libelle_referentiel_comptable, REFERENTIELS_COMPTABLES
from probare_engine.reporting.export import (
    generer_rapport_audit, generer_memorandum_controle_comptes,
)


@pytest.fixture
def db(tmp_path):
    d = ProjectDB(tmp_path / "audit.db")
    d.connect()
    yield d
    d.close()


def _projet(db, **kw):
    pid = str(uuid.uuid4())
    db.create_projet({"id": pid, "nom": "HARBI MATERIAUX SARL",
                      "client": "HARBI MATERIAUX SARL", "exercice": "2025",
                      "cycles_couverts": ["tresorerie", "ventes"], **kw})
    return pid


# ─── Référentiel comptable ───────────────────────────────────────────────────

def test_referentiel_comptable_defaut(db):
    pid = _projet(db)
    assert db.get_projet(pid)["referentiel_comptable"] == "pcgd"


def test_referentiel_comptable_persiste(db):
    pid = _projet(db, referentiel_comptable="ifrs")
    assert db.get_projet(pid)["referentiel_comptable"] == "ifrs"
    updated = db.update_projet(pid, {"referentiel_comptable": "syscohada"})
    assert updated["referentiel_comptable"] == "syscohada"


def test_libelle_referentiel_comptable():
    assert "Djibouti" in libelle_referentiel_comptable("pcgd")
    assert "IFRS" in libelle_referentiel_comptable("ifrs")
    # code inconnu → défaut PCGD
    assert libelle_referentiel_comptable("xxx") == REFERENTIELS_COMPTABLES["pcgd"]
    assert libelle_referentiel_comptable(None) == REFERENTIELS_COMPTABLES["pcgd"]


# ─── Opinion : CRUD upsert ───────────────────────────────────────────────────

def test_opinion_absente_par_defaut(db):
    pid = _projet(db)
    assert db.get_opinion(pid) is None


def test_opinion_upsert_merge_preserve_champs(db):
    pid = _projet(db)
    op = db.save_opinion(pid, {
        "rigueur": "moderee", "type_opinion": "avec_reserve",
        "titre": "Opinion avec réserve", "texte_opinion": "À notre avis, sous réserve...",
        "fondement": "Selon les normes ISA.", "justification": "Cumul > seuil.",
        "proposee_par_ia": 1, "modele_ia": "claude-opus-4-8", "validee": 0,
    })
    assert op["type_opinion"] == "avec_reserve"
    assert op["validee"] == 0
    genere_le = op["genere_le"]

    # Mise à jour partielle : ne doit pas écraser les champs non fournis
    op2 = db.save_opinion(pid, {"validee": 1, "validee_par": "Auditeur"})
    assert op2["validee"] == 1
    assert op2["validee_par"] == "Auditeur"
    assert op2["texte_opinion"] == "À notre avis, sous réserve..."
    assert op2["type_opinion"] == "avec_reserve"
    assert op2["genere_le"] == genere_le  # date de création préservée


# ─── Synthèse de mission (récapitulatif déterministe) ────────────────────────

def test_synthese_mission_structure(db):
    from probare_engine.api.routes import _synthese_mission
    pid = _projet(db, seuil_signification=500_000, seuil_planification=375_000)
    db.save_resultat({"id": str(uuid.uuid4()), "projet_id": pid,
                      "controle_ref": "TRESOR-BAL-EQUIL", "valeur": 0.0,
                      "statut": "ok", "details": "OK", "sources": ["balance.csv"]})
    projet = db.get_projet(pid)
    recap = _synthese_mission(db, pid, projet)
    assert recap["projet"]["referentiel_comptable"] == "pcgd"
    assert "Djibouti" in recap["projet"]["referentiel_comptable_label"]
    ids_phases = {p["id"] for p in recap["phases"]}
    assert {"cadrage", "travaux_substantifs", "revue", "opinion"} <= ids_phases
    assert "ingérés" in recap["fichiers"] and "produits" in recap["fichiers"]
    assert recap["anomalies"]["cumul_non_corrigees"] == 0.0


# ─── Génération des livrables finaux ─────────────────────────────────────────

def _docx_text(path):
    import docx
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


CABINET = {
    "nom": "Cabinet NIMAAN & Associés", "forme_juridique": "SARL",
    "adresse_ville": "Djibouti", "adresse_pays": "Djibouti",
    "numero_ordre": "CAC-DJ-042", "responsable_nom": "Gouled Ahmed",
    "responsable_titre": "Commissaire aux comptes",
}


def test_generer_rapport_audit(db, tmp_path):
    pid = _projet(db, referentiel_comptable="pcgd")
    db.update_planification(pid, {"forme_juridique": "SARL",
                                  "dirigeants": [{"nom": "M. X", "fonction": "Gérant"}]})
    projet = db.get_projet(pid)
    opinion = {"type_opinion": "sans_reserve", "titre": "Opinion sans réserve",
               "texte_opinion": "À notre avis, les comptes présentent sincèrement...",
               "fondement": "Selon les normes ISA.", "observations": "", "validee": 1}
    out = generer_rapport_audit(projet, opinion, tmp_path / "rapport.docx",
                                cabinet=CABINET, plan=db.get_or_create_planification(pid))
    assert out.exists() and out.stat().st_size > 5000
    txt = _docx_text(out)
    for needle in ["Cabinet NIMAAN", "Opinion sans réserve", "Fondement de l'opinion",
                   "Plan Comptable Général de Djibouti", "M. X, Gérant",
                   "Responsabilités de la direction", "Commissaire aux comptes"]:
        assert needle in txt, f"absent du rapport : {needle}"


def test_generer_memorandum_triptyque(db, tmp_path):
    pid = _projet(db)
    db.save_resultat({"id": str(uuid.uuid4()), "projet_id": pid,
                      "controle_ref": "VENTE-CUT-OFF", "valeur": 0.42,
                      "statut": "exception", "details": "42% en fin d'exercice",
                      "sources": ["gl.csv"]})
    eid = str(uuid.uuid4())
    db.save_exception({"id": eid, "projet_id": pid, "controle_ref": "VENTE-CUT-OFF",
                       "nep_ref": "NEP 330", "severite": "significative",
                       "description": "Concentration ventes décembre", "statut": "ouverte"})
    db.trancher_exception(eid, "Non corrigée", "Auditeur",
                          type_resolution="non_corrigee", montant_incidence=120_000)
    db.save_feuille_travail({"id": str(uuid.uuid4()), "projet_id": pid, "cycle": "ventes",
                             "contenu_redige": "Conclusion : anomalie non corrigée.",
                             "sources": ["VENTE-CUT-OFF"], "nep_ref": "NEP 330"})
    projet = db.get_projet(pid)
    out = generer_memorandum_controle_comptes(
        projet, db.list_resultats(pid), db.list_exceptions(pid), db.list_feuilles(pid),
        tmp_path / "memo.docx", plan=db.get_or_create_planification(pid),
        controles_ignores=[{"controle_ref": "TRESOR-RAPPROCH", "cycle": "tresorerie",
                            "raison": "Relevé bancaire non fourni"}],
        cabinet=CABINET)
    assert out.exists() and out.stat().st_size > 5000
    txt = _docx_text(out)
    for needle in ["MÉMORANDUM", "Cycle Ventes-Clients", "Objectifs", "Travaux effectués",
                   "Commentaires de l'auditeur", "VENTE-CUT-OFF", "non corrigée",
                   "Contrôles prévus non exécutés"]:
        assert needle in txt, f"absent du mémorandum : {needle}"
