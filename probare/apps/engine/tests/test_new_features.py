"""Tests des nouvelles fonctionnalités : document_types, préconditions, DB migrations."""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, "D:\\pip\\packages")


# ─── document_types ──────────────────────────────────────────────────────────

def test_types_document_complets():
    from probare_engine.controls.document_types import TYPES_DOCUMENT
    assert "grand_livre" in TYPES_DOCUMENT
    assert "balance" in TYPES_DOCUMENT
    assert "releve_bancaire" in TYPES_DOCUMENT
    assert "annexe" in TYPES_DOCUMENT


def test_preconditions_tous_controles_declares():
    from probare_engine.controls.document_types import PRECONDITIONS_CONTROLES
    from probare_engine.controls.registry import REGISTRE
    # Chaque contrôle du registre doit avoir une précondition
    refs_registre = set(REGISTRE.keys())
    refs_precond = set(PRECONDITIONS_CONTROLES.keys())
    manquants = refs_registre - refs_precond
    assert not manquants, f"Contrôles sans préconditions : {manquants}"


def test_preconditions_check_ok():
    from probare_engine.api.routes import _preconditions_check
    ok, msg = _preconditions_check(
        "TRESOR-BAL-EQUIL", ids_gl=set(), ids_balance={"abc"}, ids_releve=set()
    )
    assert ok
    assert msg == ""


def test_preconditions_check_manquant():
    from probare_engine.api.routes import _preconditions_check
    ok, msg = _preconditions_check(
        "TRESOR-BAL-EQUIL", ids_gl=set(), ids_balance=set(), ids_releve=set()
    )
    assert not ok
    assert "Balance" in msg


def test_preconditions_rapproch_sans_releve():
    from probare_engine.api.routes import _preconditions_check
    ok, msg = _preconditions_check(
        "TRESOR-RAPPROCH", ids_gl={"gl"}, ids_balance={"bal"}, ids_releve=set()
    )
    assert not ok
    assert "bancaire" in msg.lower() or "releve" in msg.lower()


def test_preconditions_rapproch_avec_releve():
    from probare_engine.api.routes import _preconditions_check
    ok, _ = _preconditions_check(
        "TRESOR-RAPPROCH", ids_gl={"gl"}, ids_balance={"bal"}, ids_releve={"rel"}
    )
    assert ok


def test_preconditions_gl_coher_besoin_deux():
    from probare_engine.api.routes import _preconditions_check
    # GL sans balance → KO
    ok, _ = _preconditions_check("TRESOR-GL-COHER", {"gl"}, set(), set())
    assert not ok
    # Balance sans GL → KO
    ok, _ = _preconditions_check("TRESOR-GL-COHER", set(), {"bal"}, set())
    assert not ok
    # Les deux → OK
    ok, _ = _preconditions_check("TRESOR-GL-COHER", {"gl"}, {"bal"}, set())
    assert ok


# ─── checklist_documents ─────────────────────────────────────────────────────

def test_checklist_tresorerie_seul():
    from probare_engine.controls.document_types import checklist_documents
    fichiers = [
        {"type_document": "grand_livre", "id": "1", "nom": "gl.xlsx", "importe_le": "2024-01-01"}
    ]
    checklist = checklist_documents(["tresorerie"], fichiers)
    types = {d["type"] for d in checklist}
    assert "grand_livre" in types
    assert "balance" in types
    assert "releve_bancaire" in types  # optionnel mais présent pour trésorerie
    # GL importé
    gl = next(d for d in checklist if d["type"] == "grand_livre")
    assert gl["importe"] is True
    assert gl["nb_fichiers"] == 1
    # Balance non importée
    bal = next(d for d in checklist if d["type"] == "balance")
    assert bal["importe"] is False


def test_checklist_multi_cycle_deduplication():
    from probare_engine.controls.document_types import checklist_documents
    fichiers = []
    # Achats + ventes : grand_livre et balance ne doivent apparaître qu'une fois
    checklist = checklist_documents(["achats", "ventes"], fichiers)
    types = [d["type"] for d in checklist]
    assert types.count("grand_livre") == 1
    assert types.count("balance") == 1
    # Pas de relevé bancaire (pas trésorerie)
    assert "releve_bancaire" not in types


def test_checklist_cycles_dans_entry():
    from probare_engine.controls.document_types import checklist_documents
    fichiers = []
    checklist = checklist_documents(["tresorerie", "achats"], fichiers)
    gl = next(d for d in checklist if d["type"] == "grand_livre")
    assert "tresorerie" in gl["cycles"]
    assert "achats" in gl["cycles"]


def test_checklist_compat_type_ancien():
    """Rétrocompatibilité : type_document absent → fallback sur type."""
    from probare_engine.controls.document_types import checklist_documents
    fichiers = [
        {"type": "balance", "id": "1", "nom": "bal.csv", "importe_le": "2024-01-01"}
    ]
    checklist = checklist_documents(["tresorerie"], fichiers)
    bal = next(d for d in checklist if d["type"] == "balance")
    assert bal["importe"] is True


# ─── DB migrations ────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db():
    with tempfile.TemporaryDirectory() as tmp:
        from probare_engine.storage.db import ProjectDB
        db = ProjectDB(os.path.join(tmp, "test.db"))
        db.connect()
        yield db
        db._conn.close()


def test_db_create_projet_avec_cycles(tmp_db):
    p = tmp_db.create_projet({
        "id": "p1", "nom": "Test", "cycles_couverts": ["tresorerie"]
    })
    assert p["cycles_couverts"] == ["tresorerie"]


def test_db_cycles_default(tmp_db):
    """Un projet sans cycles_couverts retourne les 3 cycles par défaut."""
    tmp_db.create_projet({"id": "p2", "nom": "Test2"})
    tmp_db._conn.execute("UPDATE projet SET cycles_couverts=NULL WHERE id='p2'")
    tmp_db._conn.commit()
    p = tmp_db.get_projet("p2")
    assert set(p["cycles_couverts"]) == {"tresorerie", "achats", "ventes"}


def test_db_update_cycles(tmp_db):
    tmp_db.create_projet({"id": "p3", "nom": "Test3", "cycles_couverts": ["tresorerie"]})
    updated = tmp_db.update_projet("p3", {"cycles_couverts": ["achats", "ventes"]})
    assert set(updated["cycles_couverts"]) == {"achats", "ventes"}


def test_db_save_fichier_source_avec_type_document(tmp_db):
    tmp_db.create_projet({"id": "p4", "nom": "Test4"})
    tmp_db.save_fichier_source({
        "id": "f1", "projet_id": "p4", "nom": "gl.xlsx",
        "type": "grand_livre", "type_document": "grand_livre"
    })
    fichiers = tmp_db.list_fichiers("p4")
    assert len(fichiers) == 1
    assert fichiers[0]["type_document"] == "grand_livre"


def test_db_annexe_crud(tmp_db):
    tmp_db.create_projet({"id": "p5", "nom": "Test5"})
    anx = tmp_db.save_annexe({
        "id": "a1", "projet_id": "p5", "nom": "pv.docx",
        "description": "PV assemblée 2024"
    })
    assert anx["nom"] == "pv.docx"
    assert anx["ia_analysee"] == 0

    # Mise à jour IA
    updated = tmp_db.update_annexe_ia("a1", "Résumé du PV", ["Point 1", "Point 2"], ["Alerte"])
    assert updated["ia_analysee"] == 1
    assert updated["resume_ia"] == "Résumé du PV"
    assert updated["points_cles"] == ["Point 1", "Point 2"]
    assert updated["alertes"] == ["Alerte"]

    # Liste
    liste = tmp_db.list_annexes("p5")
    assert len(liste) == 1
    assert liste[0]["id"] == "a1"


def test_db_get_type_fichier_fallback():
    """_get_type_fichier retourne type_document en priorité, sinon type."""
    from probare_engine.api.routes import _get_type_fichier
    assert _get_type_fichier({"type_document": "balance", "type": "grand_livre"}) == "balance"
    assert _get_type_fichier({"type": "grand_livre"}) == "grand_livre"
    assert _get_type_fichier({}) == ""


# ─── Intégration segmentation ─────────────────────────────────────────────────

def test_get_donnees_segmentees_avec_releve(tmp_db):
    """ids_releve est correctement rempli quand un fichier releve_bancaire existe."""
    from probare_engine.api.routes import _get_donnees_segmentees
    tmp_db.create_projet({"id": "p6", "nom": "Test6"})
    tmp_db.save_fichier_source({
        "id": "f-gl", "projet_id": "p6", "nom": "gl.xlsx",
        "type": "grand_livre", "type_document": "grand_livre"
    })
    tmp_db.save_fichier_source({
        "id": "f-rel", "projet_id": "p6", "nom": "releve.xlsx",
        "type": "releve_bancaire", "type_document": "releve_bancaire"
    })
    _, _, _, ids_gl, ids_balance, ids_releve = _get_donnees_segmentees(tmp_db, "p6")
    assert "f-gl" in ids_gl
    assert "f-rel" in ids_releve
    assert len(ids_balance) == 0


def test_cycle_ignore_si_non_couvert(tmp_db):
    """Route controles/achats retourne cycle_ignore si achats pas dans cycles_couverts."""
    # On ne peut pas appeler la route FastAPI directement sans serveur,
    # mais on vérifie que la logique cycles_couverts fonctionne dans la DB.
    tmp_db.create_projet({
        "id": "p7", "nom": "Test7",
        "cycles_couverts": ["tresorerie"]  # achats non couvert
    })
    p = tmp_db.get_projet("p7")
    assert "achats" not in p["cycles_couverts"]
    assert "tresorerie" in p["cycles_couverts"]
