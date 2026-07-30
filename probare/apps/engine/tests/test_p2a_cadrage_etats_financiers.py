"""P2-a — cadrage des états financiers PRÉSENTÉS avec la balance auditée.

C'est la diligence d'audit réelle sur les états financiers : vérifier que le
bilan et le compte de résultat publiés par l'entité se raccordent, poste par
poste, à la comptabilité auditée. Le pivot est la feuille maîtresse (M5).
"""
from __future__ import annotations
import uuid
import pytest

from probare_engine.storage.db import ProjectDB
from probare_engine.rubriques import plan_rubriques, rubrique_as_dict
from probare_engine.etats_financiers import (
    COTE_ACTIF, COTE_PASSIF, COTE_CHARGES, COTE_PRODUITS,
    STATUT_CONCORDANT, STATUT_ECART, STATUT_ECART_SIGNIFICATIF,
    STATUT_NON_RATTACHE, TOLERANCE_ARRONDI,
    rapprocher, suggerer_rubrique, montant_audite_pour, valider_poste,
)


@pytest.fixture
def db(tmp_path):
    d = ProjectDB(tmp_path / "audit.db")
    d.connect()
    yield d
    d.close()


RUBRIQUES = [rubrique_as_dict(r) for r in plan_rubriques("pcgd")]


def _matrice(**montants_par_ref) -> dict:
    """Feuille maîtresse minimale : {ref: montant_ajusté} en solde net débiteur."""
    index = {r["ref"]: r for r in RUBRIQUES}
    rubriques = []
    for ref, montant in montants_par_ref.items():
        r = dict(index[ref])
        r["montant_ajuste"] = float(montant)
        r["montant_presente"] = round(float(montant) * r["signe_presentation"], 2)
        rubriques.append(r)
    charges = sum(r["montant_ajuste"] for r in rubriques if r["type"] == "resultat_charges")
    produits = sum(-r["montant_ajuste"] for r in rubriques if r["type"] == "resultat_produits")
    return {"rubriques": rubriques, "totaux": {"resultat": round(produits - charges, 2)}}


def _poste(cote, libelle, montant, ref=None, pid="p"):
    return {"id": str(uuid.uuid4()), "cote": cote, "libelle": libelle,
            "montant": montant, "rubrique_ref": ref}


# ─── Convention de signe : le point à ne pas rater ───────────────────────────

def test_montant_audite_par_cote():
    """La feuille maîtresse raisonne en solde net débiteur ; le client publie
    des montants positifs des deux côtés du bilan."""
    clients = next(r for r in RUBRIQUES if r["ref"] == "AC-CLIENTS")
    frs = next(r for r in RUBRIQUES if r["ref"] == "PA-FOURNISSEURS")
    assert montant_audite_pour({**clients, "montant_ajuste": 5_000_000}, COTE_ACTIF) == 5_000_000
    # Un fournisseur est créditeur : solde net débiteur négatif, présenté positif.
    assert montant_audite_pour({**frs, "montant_ajuste": -3_000_000}, COTE_PASSIF) == 3_000_000


def test_rubrique_a_double_sens_selon_le_cote_declare():
    """Un compte de tiers créditeur se présente au passif : c'est le côté déclaré
    par l'état publié qui commande, pas le type de la rubrique."""
    mixte = next(r for r in RUBRIQUES if r["type"] == "bilan_mixte")
    r = {**mixte, "montant_ajuste": -800_000}
    assert montant_audite_pour(r, COTE_PASSIF) == 800_000
    assert montant_audite_pour(r, COTE_ACTIF) == -800_000


# ─── Rapprochement ───────────────────────────────────────────────────────────

def test_etats_qui_cadrent_parfaitement():
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "PA-FOURNISSEURS": -5_000_000})
    postes = [_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS"),
              _poste(COTE_PASSIF, "Fournisseurs", 5_000_000, "PA-FOURNISSEURS")]
    rap = rapprocher(postes, m, seuil=100_000)
    assert all(l["statut"] == STATUT_CONCORDANT for l in rap["lignes"])
    assert rap["equilibre_bilan"]["equilibre"] is True
    assert rap["synthese"]["cadre"] is True


def test_ecart_significatif_au_dela_du_seuil():
    m = _matrice(**{"AC-CLIENTS": 5_000_000})
    postes = [_poste(COTE_ACTIF, "Clients", 5_400_000, "AC-CLIENTS")]
    rap = rapprocher(postes, m, seuil=100_000)
    ligne = rap["lignes"][0]
    assert ligne["statut"] == STATUT_ECART_SIGNIFICATIF
    assert ligne["ecart"] == 400_000
    assert ligne["ecart_pct"] == 8.0
    assert rap["synthese"]["nb_ecarts_significatifs"] == 1
    assert rap["synthese"]["cadre"] is False


def test_ecart_sous_le_seuil_signale_sans_etre_significatif():
    m = _matrice(**{"AC-CLIENTS": 5_000_000})
    rap = rapprocher([_poste(COTE_ACTIF, "Clients", 5_050_000, "AC-CLIENTS")], m, seuil=100_000)
    assert rap["lignes"][0]["statut"] == STATUT_ECART
    assert rap["synthese"]["nb_ecarts_significatifs"] == 0


def test_arrondi_de_presentation_nest_pas_un_ecart():
    """Les états sont souvent publiés au millier près : un franc d'écart n'est
    pas une anomalie d'audit."""
    m = _matrice(**{"AC-CLIENTS": 5_000_000})
    rap = rapprocher([_poste(COTE_ACTIF, "Clients", 5_000_000 + TOLERANCE_ARRONDI,
                             "AC-CLIENTS")], m, seuil=100_000)
    assert rap["lignes"][0]["statut"] == STATUT_CONCORDANT


def test_plusieurs_postes_presentes_sur_une_meme_rubrique_sont_agreges():
    """Le client peut éclater une rubrique en plusieurs lignes de présentation :
    on compare des sommes, jamais des lignes isolées."""
    m = _matrice(**{"AC-CLIENTS": 5_000_000})
    postes = [_poste(COTE_ACTIF, "Clients France", 3_000_000, "AC-CLIENTS"),
              _poste(COTE_ACTIF, "Clients export", 2_000_000, "AC-CLIENTS")]
    rap = rapprocher(postes, m, seuil=100_000)
    assert len(rap["lignes"]) == 1
    assert rap["lignes"][0]["montant_presente"] == 5_000_000
    assert rap["lignes"][0]["statut"] == STATUT_CONCORDANT
    assert len(rap["lignes"][0]["postes"]) == 2


def test_poste_non_rattache_est_isole_pas_ignore():
    m = _matrice(**{"AC-CLIENTS": 5_000_000})
    postes = [_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS"),
              _poste(COTE_ACTIF, "Poste exotique", 900_000, None)]
    rap = rapprocher(postes, m, seuil=100_000)
    assert len(rap["non_rattaches"]) == 1
    assert rap["non_rattaches"][0]["statut"] == STATUT_NON_RATTACHE
    assert rap["synthese"]["cadre"] is False, "un poste non rattaché empêche de conclure"


def test_rubrique_auditee_absente_des_etats_presentes():
    """Un poste significatif de la balance qui n'apparaît nulle part dans les
    états publiés est une anomalie d'exhaustivité."""
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "AC-STOCKS": 3_000_000})
    rap = rapprocher([_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS")], m, seuil=100_000)
    assert [a["rubrique_ref"] for a in rap["rubriques_absentes"]] == ["AC-STOCKS"]
    assert rap["rubriques_absentes"][0]["montant_audite"] == 3_000_000


def test_rubrique_non_significative_absente_nest_pas_signalee():
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "AC-STOCKS": 500})
    rap = rapprocher([_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS")], m, seuil=100_000)
    assert rap["rubriques_absentes"] == []


def test_bilan_presente_desequilibre():
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "PA-FOURNISSEURS": -4_000_000})
    postes = [_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS"),
              _poste(COTE_PASSIF, "Fournisseurs", 4_000_000, "PA-FOURNISSEURS")]
    eq = rapprocher(postes, m, seuil=100_000)["equilibre_bilan"]
    assert eq["equilibre"] is False and eq["ecart"] == 1_000_000


def test_desequilibre_egal_au_resultat_est_diagnostique():
    """Cause la plus fréquente d'un bilan déséquilibré : le résultat n'a pas été
    porté aux capitaux propres. Le dire évite de chercher une anomalie ailleurs.
    Constaté sur le dossier ARULOS, dont la balance n'a pas encore viré le résultat."""
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "PA-CAPITAL": -4_000_000,
                    "RE-ACHATS": 2_000_000, "RE-VENTES": -3_000_000})
    assert m["totaux"]["resultat"] == 1_000_000
    postes = [_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS"),
              _poste(COTE_PASSIF, "Capital", 4_000_000, "PA-CAPITAL"),
              _poste(COTE_CHARGES, "Achats", 2_000_000, "RE-ACHATS"),
              _poste(COTE_PRODUITS, "Ventes", 3_000_000, "RE-VENTES")]
    eq = rapprocher(postes, m, seuil=100_000)["equilibre_bilan"]
    assert eq["equilibre"] is False and eq["ecart"] == 1_000_000
    assert eq["explique_par_resultat"] is True


def test_desequilibre_sans_rapport_avec_le_resultat_nest_pas_explique():
    m = _matrice(**{"AC-CLIENTS": 5_000_000, "PA-CAPITAL": -4_000_000})
    postes = [_poste(COTE_ACTIF, "Clients", 5_000_000, "AC-CLIENTS"),
              _poste(COTE_PASSIF, "Capital", 3_000_000, "PA-CAPITAL")]
    eq = rapprocher(postes, m, seuil=100_000)["equilibre_bilan"]
    assert eq["equilibre"] is False and eq["explique_par_resultat"] is False


def test_resultat_presente_vs_resultat_audite():
    m = _matrice(**{"RE-ACHATS": 2_000_000, "RE-VENTES": -3_000_000})
    assert m["totaux"]["resultat"] == 1_000_000
    postes = [_poste(COTE_CHARGES, "Achats", 2_000_000, "RE-ACHATS"),
              _poste(COTE_PRODUITS, "Ventes", 2_600_000, "RE-VENTES")]
    rap = rapprocher(postes, m, seuil=100_000)
    assert rap["totaux"]["resultat_presente"] == 600_000
    assert rap["coherence_resultat"]["coherent"] is False
    assert rap["coherence_resultat"]["ecart"] == -400_000


def test_controles_densemble_non_applicables_sans_donnees():
    """Sans bilan présenté, l'équilibre ne se teste pas : ne pas conclure à un
    déséquilibre de zéro contre zéro."""
    m = _matrice(**{"RE-ACHATS": 2_000_000})
    rap = rapprocher([_poste(COTE_CHARGES, "Achats", 2_000_000, "RE-ACHATS")], m, seuil=100_000)
    assert rap["equilibre_bilan"]["applicable"] is False
    assert rap["coherence_resultat"]["applicable"] is True


# ─── Rattachement automatique par libellé ────────────────────────────────────

def test_suggestion_libelle_exact_et_approchant():
    assert suggerer_rubrique("Clients et comptes rattachés", RUBRIQUES, COTE_ACTIF) == "AC-CLIENTS"
    assert suggerer_rubrique("CLIENTS", RUBRIQUES, COTE_ACTIF) == "AC-CLIENTS"


def test_suggestion_respecte_le_cote():
    """« Fournisseurs » au passif ne doit pas viser une rubrique d'actif."""
    ref = suggerer_rubrique("Fournisseurs", RUBRIQUES, COTE_PASSIF)
    rub = next(r for r in RUBRIQUES if r["ref"] == ref)
    assert rub["type"] in ("bilan_passif", "bilan_mixte")


def test_suggestion_refuse_de_deviner():
    """Mieux vaut pas de rattachement qu'un mauvais : un rattachement erroné
    fabriquerait un écart imaginaire."""
    assert suggerer_rubrique("Poste maison sans équivalent", RUBRIQUES, COTE_ACTIF) is None
    assert suggerer_rubrique("", RUBRIQUES, COTE_ACTIF) is None


def test_valider_poste():
    with pytest.raises(ValueError, match="Côté inconnu"):
        valider_poste({"cote": "haut", "libelle": "x", "montant": 1})
    with pytest.raises(ValueError, match="libellé"):
        valider_poste({"cote": COTE_ACTIF, "libelle": " ", "montant": 1})
    valider_poste({"cote": COTE_ACTIF, "libelle": "Clients", "montant": 1})


# ─── Persistance ─────────────────────────────────────────────────────────────

def test_cadrage_bout_en_bout_produit_des_exceptions(tmp_path, monkeypatch):
    """De la balance ingérée à l'exception : le cadrage doit lever une exception
    standard pour l'écart, une pour le déséquilibre, une pour l'exhaustivité."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    monkeypatch.setenv("PROBARE_DATA_DIR", str(tmp_path / "projets"))
    import importlib
    from probare_engine.api import routes as routes_mod
    importlib.reload(routes_mod)
    # L'interprétation IA de chaque exception est hors sujet ici (et coûteuse).
    monkeypatch.setattr(routes_mod, "_auto_interpreter", lambda *a, **k: None)
    app = FastAPI(); app.include_router(routes_mod.router)
    client = TestClient(app)

    r = client.post("/projets", json={"nom": "EF", "client": "EF SARL",
                                      "exercice": "2024", "nif": "1"})
    pid = r.json()["id"]
    db = routes_mod._get_db(pid)
    db.update_projet(pid, {"seuil_signification": 100_000,
                           "etat_courant": "travaux_substantifs"})

    fid = str(uuid.uuid4())
    db.save_fichier_source({"id": fid, "projet_id": pid, "nom": "balance.csv",
                            "type": "balance", "type_document": "balance"})
    lignes = [("411000", 5_000_000.0), ("311000", 3_000_000.0),
              ("401000", -8_000_000.0)]
    donnees = []
    for i, (compte, solde) in enumerate(lignes, start=2):
        donnees += [
            {"id": str(uuid.uuid4()), "projet_id": pid, "fichier_source_id": fid,
             "valeur": compte, "type": "compte", "localisation": f"balance:{i}:Compte"},
            {"id": str(uuid.uuid4()), "projet_id": pid, "fichier_source_id": fid,
             "valeur": solde, "type": "montant", "localisation": f"balance:{i}:Solde"},
        ]
    db.save_donnees_sourcees(donnees)

    # Sans états présentés, le cadrage ne peut pas s'exécuter.
    r = client.post(f"/projets/{pid}/controles/cadrage-etats-financiers")
    assert r.status_code == 400 and "état financier présenté" in r.json()["detail"]

    # États publiés : clients surévalué de 400 k, stocks omis, bilan déséquilibré.
    r = client.put(f"/projets/{pid}/etats-financiers-presentes", json={"postes": [
        {"cote": "actif", "libelle": "Clients et comptes rattachés", "montant": 5_400_000},
        {"cote": "passif", "libelle": "Fournisseurs", "montant": 8_000_000},
    ]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nb_rattaches_auto"] == 2, "les deux libellés doivent se rattacher seuls"
    rap = d["rapprochement"]
    assert rap["synthese"]["nb_ecarts_significatifs"] == 1
    assert [a["rubrique_ref"] for a in rap["rubriques_absentes"]] == ["AC-STOCKS"]
    assert rap["equilibre_bilan"]["equilibre"] is False

    r = client.post(f"/projets/{pid}/controles/cadrage-etats-financiers")
    assert r.status_code == 200, r.text
    refs = [e["controle_ref"] for e in r.json()["exceptions"]]
    assert "EF-CADRAGE-ECART" in refs
    assert "EF-CADRAGE-EQUILIBRE" in refs
    assert "EF-CADRAGE-EXHAUSTIVITE" in refs

    ecart = next(e for e in r.json()["exceptions"] if e["controle_ref"] == "EF-CADRAGE-ECART")
    assert ecart["montant_estime"] == 400_000, "l'incidence chiffrée vient du Python"
    assert "Clients" in ecart["description"]

    # L'auditeur corrige le rattachement d'un poste : le rapprochement suit.
    poste = next(p for p in db.list_postes_ef(pid) if p["libelle"].startswith("Clients"))
    r = client.put(f"/projets/{pid}/etats-financiers-presentes/{poste['id']}/rubrique",
                   json={"rubrique_ref": None})
    assert r.status_code == 200
    assert r.json()["rapprochement"]["synthese"]["nb_non_rattaches"] == 1

    # Une ré-exécution ne doit pas empiler les exceptions.
    avant = len(client.post(f"/projets/{pid}/controles/cadrage-etats-financiers").json()["exceptions"])
    apres = len(client.post(f"/projets/{pid}/controles/cadrage-etats-financiers").json()["exceptions"])
    assert avant == apres


def test_remplacement_global_des_postes(db):
    pid = str(uuid.uuid4())
    db.create_projet({"id": pid, "nom": "X", "client": "X", "exercice": "2024"})
    db.remplacer_postes_ef(pid, [
        {"cote": COTE_ACTIF, "libelle": "Clients", "montant": 100, "rubrique_ref": "AC-CLIENTS"},
        {"cote": COTE_ACTIF, "libelle": "Stocks", "montant": 50},
    ])
    assert len(db.list_postes_ef(pid)) == 2

    # Un second import ne doit pas laisser d'orphelins du premier.
    db.remplacer_postes_ef(pid, [{"cote": COTE_ACTIF, "libelle": "Clients", "montant": 120}])
    postes = db.list_postes_ef(pid)
    assert len(postes) == 1 and postes[0]["montant"] == 120

    maj = db.maj_rubrique_poste_ef(pid, postes[0]["id"], "AC-CLIENTS")
    assert maj["rubrique_ref"] == "AC-CLIENTS"
