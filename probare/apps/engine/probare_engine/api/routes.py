"""Routes FastAPI — toutes les routes de l'application."""
from __future__ import annotations
import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..storage.db import ProjectDB
from ..statemachine.pipeline import transition, peut_transitionner, PipelineError
from ..ingestion.excel_csv import lire_fichier, hash_file
from ..controls.engine import (
    # Trésorerie (existants)
    controle_equilibre_balance,
    controle_coherence_gl_balance,
    controle_sequence_pieces,
    controle_variations,
    controle_rapprochement_bancaire,
    controle_soldes_anormaux_tresorerie,
    # Partagés (nouveaux)
    controle_coherence_cycle,
    controle_soldes_anormaux,
    controle_montants_ronds,
    controle_cut_off,
    controle_doublons_factures,
    controle_concentration_compte,
    controle_ratio_avoirs,
    controle_creances_echues,
    # Utilitaires
    _group_rows,
    _filter_accounts,
    _get_amount,
)
from ..provenance.models import DonneeSourcee
from ..reporting.export import (
    generer_dossier_travail, generer_tableau_exceptions,
    generer_note_planification, ProvenanceError,
)
from ..anonymization.anonymizer import Anonymizer


router = APIRouter()
DATA_DIR = Path(os.environ.get("PROBARE_DATA_DIR", str(Path.home() / ".probare" / "projets")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_DIR = DATA_DIR.parent
CLIENTS_FILES_DIR = GLOBAL_DIR / "clients"
CLIENTS_FILES_DIR.mkdir(parents=True, exist_ok=True)
CLIENTS_DB_PATH = GLOBAL_DIR / "clients.db"

_db_cache: dict[str, ProjectDB] = {}
_clients_db_instance = None
_DB_CACHE_MAX = 20


def _get_clients_db():
    global _clients_db_instance
    if _clients_db_instance is None:
        from ..storage.clients_db import ClientsDB
        _clients_db_instance = ClientsDB(CLIENTS_DB_PATH)
        _clients_db_instance.connect()
    return _clients_db_instance


def _get_db(projet_id: str) -> ProjectDB:
    if projet_id not in _db_cache:
        if len(_db_cache) >= _DB_CACHE_MAX:
            oldest_key = next(iter(_db_cache))
            try:
                _db_cache[oldest_key].close()
            except Exception:
                pass
            del _db_cache[oldest_key]
        db_path = DATA_DIR / projet_id / "audit.db"
        db = ProjectDB(db_path)
        db.connect()
        _db_cache[projet_id] = db
    return _db_cache[projet_id]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_documents_attendus(projet_id: str, db) -> list[dict]:
    """Retourne la liste dédupliquée des documents attendus selon les cycles du projet."""
    from ..controls.document_types import DOCUMENTS_PAR_CYCLE
    projet = db.get_projet(projet_id)
    cycles = projet.get("cycles_couverts") or []
    seen: dict[str, dict] = {}
    for cycle in cycles:
        for doc in DOCUMENTS_PAR_CYCLE.get(cycle, []):
            seen[doc["type"]] = doc
    return list(seen.values())


def _parse_valeur(val: str | None, type_: str) -> float | str | None:
    if val is None:
        return None
    if type_ == "montant":
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except ValueError:
            return None
    return val


def _to_donnee(d: dict) -> DonneeSourcee:
    return DonneeSourcee(**{**d, "valeur": _parse_valeur(d["valeur"], d["type"])})


def _llm_guard(db: ProjectDB, projet_id: str) -> tuple[dict, "Anonymizer"]:
    """
    Garde obligatoire avant tout appel LLM.
    Vérifie la clé API et le consentement client.
    Retourne (projet, anonymizer) ou lève HTTPException.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "Clé API Claude non configurée dans l'environnement.")
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if not projet.get("consentement_client"):
        raise HTTPException(
            403,
            "Consentement client requis avant tout traitement IA. "
            "Activez-le dans les paramètres du projet (étape Cadrage)."
        )
    return projet, Anonymizer()


def _auto_interpreter(db, projet_id: str, projet: dict, exceptions: list[dict]) -> None:
    """Lance l'interprétation IA automatique de toutes les exceptions."""
    if not exceptions or not os.environ.get("ANTHROPIC_API_KEY"):
        return
    if not projet.get("consentement_client"):
        db.log(projet_id, "avertissement_llm", {
            "action": "auto_interpretation",
            "raison": "consentement_client non accordé — interprétation IA ignorée",
        })
        return
    try:
        from ..llm.claude import ClaudeClient
        anon = Anonymizer()
        entites = [v for v in [projet.get("client"), projet.get("nif")] if v]
        ctx = {"exercice": projet.get("exercice"), "seuil": projet.get("seuil_signification")}

        def log_llm(t, p):
            db.log(projet_id, t, p)

        client = ClaudeClient(audit_logger=log_llm)
        for exc in exceptions:
            exc_anon = anon.pseudonymiser_dict(exc, ["description"], entites)
            ia_res = client.interpreter_exception(exc_anon, [], ctx)
            if "explication" in ia_res:
                ia_res["explication"] = anon.re_identifier(ia_res["explication"])
            db.update_exception_ia(exc["id"], ia_res)
        db.log(projet_id, "appel_llm", {"action": "auto_interpretation", "nb": len(exceptions)})
    except Exception as e:
        db.log(projet_id, "erreur_llm", {"action": "auto_interpretation", "erreur": str(e)})


def _get_type_fichier(f: dict) -> str:
    """Retourne le type document prioritaire (type_document > type, compatibilité rétroactive)."""
    return f.get("type_document") or f.get("type") or ""


def _get_donnees_segmentees(db, projet_id: str):
    """
    Retourne (donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve).
    Utilise type_document en priorité, avec fallback sur type (rétrocompatibilité).
    """
    fichiers = db.list_fichiers(projet_id)
    ids_balance = {f["id"] for f in fichiers if _get_type_fichier(f) == "balance"}
    ids_gl = {f["id"] for f in fichiers if _get_type_fichier(f) == "grand_livre"}
    ids_releve = {f["id"] for f in fichiers if _get_type_fichier(f) == "releve_bancaire"}

    donnees_raw = db.get_donnees_by_projet(projet_id)
    donnees_all = [_to_donnee(d) for d in donnees_raw]

    # Données par type (exclusivement, sans fallback inter-types)
    donnees_balance = [d for d in donnees_all if d.fichier_source_id in ids_balance]
    donnees_gl = [d for d in donnees_all if d.fichier_source_id in ids_gl]

    # Si un seul type de fichier, il peut servir les deux fonctions
    if not donnees_balance:
        donnees_balance = donnees_gl
    if not donnees_gl:
        donnees_gl = donnees_balance

    rows_balance = _group_rows(donnees_balance) if donnees_balance else []
    rows_gl = _group_rows(donnees_gl) if donnees_gl else []

    return donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve


def _resoudre_fichiers_sources(exceptions: list[dict], donnees_all: list) -> None:
    """Pour chaque exception, résout sources (DonneeSourcee.id) → fichiers_sources (fichier_source_id)."""
    lookup = {d.id: d.fichier_source_id for d in donnees_all}
    for exc in exceptions:
        src_ids = exc.pop("sources", [])
        fichier_ids = list(dict.fromkeys(
            lookup[sid] for sid in (src_ids or []) if sid in lookup
        ))
        exc["fichiers_sources"] = fichier_ids


def _preconditions_check(
    controle_ref: str,
    ids_gl: set,
    ids_balance: set,
    ids_releve: set,
) -> tuple[bool, str]:
    """Vérifie que les fichiers requis pour ce contrôle sont présents."""
    from ..controls.document_types import PRECONDITIONS_CONTROLES, TYPES_DOCUMENT
    requis = PRECONDITIONS_CONTROLES.get(controle_ref, [])
    ids_par_type = {
        "grand_livre": ids_gl,
        "balance": ids_balance,
        "releve_bancaire": ids_releve,
    }
    manquants = [r for r in requis if not ids_par_type.get(r)]
    if not manquants:
        return True, ""
    labels = [TYPES_DOCUMENT[m].label if m in TYPES_DOCUMENT else m for m in manquants]
    return False, f"Données manquantes : {', '.join(labels)}"


# ─── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok", "service": "probare-engine", "version": "0.2.0"}


# ─── Projets ──────────────────────────────────────────────────────────────────

class CreateProjetBody(BaseModel):
    nom: str
    client: str | None = None
    nif: str | None = None
    exercice: str | None = None
    seuil_signification: float | None = None
    seuil_planification: float | None = None
    consentement_client: bool = False
    cycles_couverts: list[str] = []
    nature_mission: str = "contractuelle"
    client_id: str | None = None


@router.get("/projets")
def list_projets():
    projets = []
    for p in DATA_DIR.iterdir():
        if p.is_dir():
            db_path = p / "audit.db"
            if db_path.exists():
                try:
                    db = _get_db(p.name)
                    projet = db.get_projet(p.name)
                    if projet:
                        projets.append(projet)
                except Exception:
                    pass
    return {"projets": sorted(projets, key=lambda x: x.get("cree_le", ""), reverse=True)}


@router.post("/projets")
def create_projet(body: CreateProjetBody):
    projet_id = str(uuid.uuid4())
    db = _get_db(projet_id)
    data = {
        "id": projet_id,
        **body.model_dump(),
        "consentement_horodatage": _now() if body.consentement_client else None,
        "etat_courant": "cadrage",
    }
    projet = db.create_projet(data)
    db.log(projet_id, "action_humaine", {"action": "creation_projet", "nom": body.nom})
    return projet


@router.get("/projets/{projet_id}")
def get_projet(projet_id: str):
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    return projet


class UpdateProjetBody(BaseModel):
    nom: str | None = None
    client: str | None = None
    nif: str | None = None
    exercice: str | None = None
    seuil_signification: float | None = None
    seuil_planification: float | None = None
    consentement_client: bool | None = None
    cycles_couverts: list[str] | None = None
    nature_mission: str | None = None
    client_id: str | None = None


@router.patch("/projets/{projet_id}")
def update_projet(projet_id: str, body: UpdateProjetBody):
    db = _get_db(projet_id)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "consentement_client" in data and data["consentement_client"]:
        data["consentement_horodatage"] = _now()
    projet = db.update_projet(projet_id, data)
    db.log(projet_id, "action_humaine", {"action": "mise_a_jour_projet", "champs": list(data.keys())})
    return projet


@router.delete("/projets/{projet_id}")
def delete_projet(projet_id: str):
    import shutil
    projet_dir = DATA_DIR / projet_id
    if not projet_dir.exists():
        raise HTTPException(404, "Projet introuvable.")
    if projet_id in _db_cache:
        try:
            _db_cache[projet_id].close()
        except Exception:
            pass
        del _db_cache[projet_id]
    try:
        shutil.rmtree(str(projet_dir))
    except Exception as exc:
        raise HTTPException(500, f"Impossible de supprimer le projet : {exc}")
    return {"deleted": True, "projet_id": projet_id}


@router.get("/projets/{projet_id}/etat")
def get_etat(projet_id: str):
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    return {"etat_courant": projet["etat_courant"]}


class TransitionBody(BaseModel):
    vers: str
    acteur: str = "utilisateur"


@router.post("/projets/{projet_id}/transition")
def post_transition(projet_id: str, body: TransitionBody):
    db = _get_db(projet_id)
    try:
        projet = transition(db, projet_id, body.vers, body.acteur)
    except PipelineError as e:
        raise HTTPException(400, str(e))
    return projet


@router.get("/projets/{projet_id}/journal")
def get_journal(projet_id: str, limit: int = 50):
    db = _get_db(projet_id)
    return {"journal": db.get_journal(projet_id, limit)}


# ─── Ingestion ────────────────────────────────────────────────────────────────

# Types valides pour les fichiers comptables (hors annexes)
_TYPES_COMPTABLES = {"grand_livre", "balance", "releve_bancaire"}


@router.post("/projets/{projet_id}/fichiers")
async def upload_fichier(
    projet_id: str,
    fichier: UploadFile = File(...),
    type_fichier: str = Form("grand_livre"),
    description: str = Form(""),
    sheet_name: str = Form("0"),
):
    """
    Importe un fichier comptable ou un document annexe.
    type_fichier : grand_livre | balance | releve_bancaire | annexe
    """
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    uploads_dir = DATA_DIR / projet_id / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / (fichier.filename or "upload")
    content = await fichier.read()
    file_path.write_bytes(content)

    file_hash = hash_file(file_path)
    fichier_id = str(uuid.uuid4())

    # ── Documents annexes : stockage séparé, pas d'extraction DonneeSourcee ──
    if type_fichier == "annexe":
        annexe = db.save_annexe({
            "id": fichier_id,
            "projet_id": projet_id,
            "nom": fichier.filename or "document",
            "chemin_relatif": str(file_path.relative_to(DATA_DIR)),
            "description": description or "",
            "ajoute_le": _now(),
        })
        db.log(projet_id, "action_humaine", {
            "action": "import_annexe",
            "fichier": fichier.filename,
        })
        return {"type": "annexe", "annexe": annexe}

    # ── Fichiers comptables : extraction DonneeSourcee ──
    if type_fichier not in _TYPES_COMPTABLES:
        type_fichier = "grand_livre"  # sécurité : jamais de type inconnu

    db.save_fichier_source({
        "id": fichier_id,
        "projet_id": projet_id,
        "nom": fichier.filename or "fichier",
        "chemin_relatif": str(file_path.relative_to(DATA_DIR)),
        "type": type_fichier,        # compatibilité rétroactive
        "type_document": type_fichier,
        "hash": file_hash,
        "importe_le": _now(),
    })

    try:
        sheet = int(sheet_name) if sheet_name.isdigit() else sheet_name
        donnees, metadata = lire_fichier(file_path, projet_id, fichier_id, sheet)
    except Exception as e:
        raise HTTPException(400, f"Erreur de lecture : {e}")

    db.save_donnees_sourcees([d.model_dump() for d in donnees])
    db.log(projet_id, "action_humaine", {
        "action": "import_fichier",
        "fichier": fichier.filename,
        "type": type_fichier,
        "nb_donnees": len(donnees),
    })

    # Détection des onglets pour les Excel (toujours, sans IA)
    onglets_disponibles: list[str] = []
    if file_path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        try:
            import pandas as pd
            ef = pd.ExcelFile(str(file_path))
            onglets_disponibles = ef.sheet_names
        except Exception:
            pass

    # Analyse IA du document (Haiku, synchrone)
    analyse_ia: dict | None = None
    db.update_fichier_ia(fichier_id, {"statut_checklist": "analyse_en_cours"})
    if os.environ.get("ANTHROPIC_API_KEY") and projet.get("consentement_client"):
        try:
            from ..ingestion.dossier_brut import lire_contenu_pour_llm
            from ..llm.claude import ClaudeClient
            texte, _, _ = lire_contenu_pour_llm(file_path)
            docs_attendus = _get_documents_attendus(projet_id, db)
            llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
            analyse_ia = llm.analyser_document_ingestion(
                fichier.filename or "", texte[:5000], docs_attendus
            )
            type_detecte = analyse_ia.get("type_comptable")
            correspond_a = analyse_ia.get("correspond_a")
            update: dict = {
                "description_ia": analyse_ia.get("description", ""),
                "nature_ia": analyse_ia.get("nature", ""),
                "correspond_a": correspond_a,
                "statut_checklist": "valide" if correspond_a else "non_attendu",
                # Toujours normaliser : type comptable détecté OU "annexe"
                "type_document": type_detecte if type_detecte in ("grand_livre", "balance", "releve_bancaire") else "annexe",
            }
            db.update_fichier_ia(fichier_id, update)
        except Exception:
            db.update_fichier_ia(fichier_id, {"statut_checklist": "non_attendu"})
    else:
        db.update_fichier_ia(fichier_id, {"statut_checklist": "non_attendu"})

    return {
        "type": "fichier",
        "fichier_source_id": fichier_id,
        "nb_donnees_extraites": len(donnees),
        "metadata": metadata,
        "analyse_ia": analyse_ia,
        "onglets_disponibles": onglets_disponibles,
    }


@router.get("/projets/{projet_id}/fichiers")
def list_fichiers(projet_id: str):
    db = _get_db(projet_id)
    return {"fichiers": db.list_fichiers(projet_id)}


@router.delete("/projets/{projet_id}/fichiers/{fichier_id}")
def delete_fichier(projet_id: str, fichier_id: str):
    db = _get_db(projet_id)
    db.delete_fichier_source(fichier_id)
    db.log(projet_id, "action_humaine", {"action": "delete_fichier", "fichier_id": fichier_id})
    return {"deleted": True, "fichier_id": fichier_id}


@router.get("/projets/{projet_id}/documents-requis")
def get_documents_requis(projet_id: str):
    """
    Retourne la checklist des documents attendus selon les cycles déclarés au cadrage,
    avec le statut d'import (importé / manquant) pour chaque type.
    """
    from ..controls.document_types import checklist_documents
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    cycles = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    fichiers = db.list_fichiers(projet_id)
    checklist = checklist_documents(cycles, fichiers)
    manquants_requis = [d["type"] for d in checklist if d["requis"] and not d["importe"]]

    return {
        "cycles": cycles,
        "checklist": checklist,
        "preconditions_ok": len(manquants_requis) == 0,
        "manquants": manquants_requis,
    }


# ─── Ingestion intelligente : onglets Excel ───────────────────────────────────

@router.get("/projets/{projet_id}/fichiers/{fichier_id}/onglets")
def get_onglets_excel(projet_id: str, fichier_id: str):
    """Analyse les onglets d'un fichier Excel avec Haiku."""
    import pandas as pd
    db = _get_db(projet_id)
    fichiers = db.list_fichiers(projet_id)
    fichier = next((f for f in fichiers if f["id"] == fichier_id), None)
    if not fichier:
        raise HTTPException(404, "Fichier introuvable.")

    chemin = DATA_DIR / fichier["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")
    if chemin.suffix.lower() not in (".xlsx", ".xls", ".xlsm"):
        raise HTTPException(400, "Ce fichier n'est pas un Excel.")

    from ..ingestion.excel_csv import _detect_header_row
    ef = pd.ExcelFile(str(chemin))
    onglets_info = []
    for sheet_name in ef.sheet_names:
        try:
            header_row = _detect_header_row(chemin, sheet_name)
            df = pd.read_excel(str(chemin), sheet_name=sheet_name, header=header_row, nrows=20, dtype=str)
            apercu = df.to_csv(index=False)[:2000]
            colonnes = [str(c) for c in df.columns]
        except Exception:
            apercu = ""
            colonnes = []
        onglets_info.append({"nom": sheet_name, "colonnes": colonnes, "apercu": apercu})

    analyse_onglets = []
    db_projet = db.get_projet(projet_id)
    if os.environ.get("ANTHROPIC_API_KEY") and db_projet and db_projet.get("consentement_client"):
        try:
            from ..llm.claude import ClaudeClient
            docs_attendus = _get_documents_attendus(projet_id, db)
            llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
            analyse_onglets = llm.analyser_onglets_excel(fichier["nom"], onglets_info, docs_attendus)
        except Exception:
            analyse_onglets = []

    return {
        "fichier_id": fichier_id,
        "nom": fichier["nom"],
        "onglets": onglets_info,
        "analyse_ia": analyse_onglets,
    }


class ImporterOngletBody(BaseModel):
    sheet_name: str
    type_force: str | None = None


@router.post("/projets/{projet_id}/fichiers/{fichier_id}/importer-onglet")
def importer_onglet(projet_id: str, fichier_id: str, body: ImporterOngletBody):
    """Importe un onglet Excel comme fichier source distinct avec analyse Haiku."""
    import pandas as pd
    db = _get_db(projet_id)
    fichiers = db.list_fichiers(projet_id)
    fichier_parent = next((f for f in fichiers if f["id"] == fichier_id), None)
    if not fichier_parent:
        raise HTTPException(404, "Fichier parent introuvable.")

    chemin = DATA_DIR / fichier_parent["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    onglet_id = str(uuid.uuid4())
    nom_onglet = f"{fichier_parent['nom']} — {body.sheet_name}"

    try:
        donnees, metadata = lire_fichier(chemin, projet_id, onglet_id, body.sheet_name)
    except Exception as e:
        raise HTTPException(400, f"Erreur de lecture de l'onglet : {e}")

    analyse: dict = {}
    _proj_onglet = db.get_projet(projet_id)
    if os.environ.get("ANTHROPIC_API_KEY") and _proj_onglet and _proj_onglet.get("consentement_client"):
        try:
            df = pd.read_excel(str(chemin), sheet_name=body.sheet_name, nrows=10, dtype=str)
            apercu = df.to_csv(index=False)[:3000]
            from ..llm.claude import ClaudeClient
            docs_attendus = _get_documents_attendus(projet_id, db)
            llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
            analyses = llm.analyser_onglets_excel(
                fichier_parent["nom"],
                [{"nom": body.sheet_name, "colonnes": [str(c) for c in df.columns], "apercu": apercu}],
                docs_attendus,
            )
            if analyses:
                analyse = analyses[0]
        except Exception:
            pass

    type_detecte = body.type_force or analyse.get("type_comptable") or "annexe"
    correspond_a = analyse.get("correspond_a")

    db.save_fichier_source({
        "id": onglet_id,
        "projet_id": projet_id,
        "nom": nom_onglet,
        "chemin_relatif": fichier_parent.get("chemin_relatif", ""),
        "type": type_detecte,
        "type_document": type_detecte,
        "hash": fichier_parent.get("hash", ""),
        "importe_le": _now(),
        "description_ia": analyse.get("description", ""),
        "nature_ia": analyse.get("nature", ""),
        "correspond_a": correspond_a,
        "statut_checklist": "valide" if correspond_a else "non_attendu",
        "onglet": body.sheet_name,
    })
    db.save_donnees_sourcees([d.model_dump() for d in donnees])
    db.log(projet_id, "action_humaine", {
        "action": "import_onglet",
        "fichier": fichier_parent["nom"],
        "onglet": body.sheet_name,
        "nb_donnees": len(donnees),
    })

    return {
        "fichier_source_id": onglet_id,
        "nom": nom_onglet,
        "onglet": body.sheet_name,
        "type_document": type_detecte,
        "nb_donnees_extraites": len(donnees),
        "analyse_ia": analyse,
    }


@router.post("/projets/{projet_id}/fichiers/{fichier_id}/decouper-liasse")
def decouper_liasse(projet_id: str, fichier_id: str):
    """Haiku identifie les documents individuels dans une liasse PDF/Word."""
    db = _get_db(projet_id)
    fichiers = db.list_fichiers(projet_id)
    fichier = next((f for f in fichiers if f.get("id") == fichier_id), None)
    if not fichier:
        # Chercher aussi dans les annexes
        annexes = db.list_annexes(projet_id)
        fichier = next((a for a in annexes if a.get("id") == fichier_id), None)
    if not fichier:
        raise HTTPException(404, "Fichier introuvable.")

    chemin_rel = fichier.get("chemin_relatif")
    if not chemin_rel:
        raise HTTPException(400, "Chemin introuvable.")
    chemin = DATA_DIR / chemin_rel
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    texte, _, _ = lire_contenu_pour_llm(chemin)

    if not texte or len(texte) < 100:
        raise HTTPException(400, "Contenu insuffisant pour analyser la liasse.")
    _projet_liasse, _ = _llm_guard(db, projet_id)

    from ..llm.claude import ClaudeClient
    llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
    resultat = llm.decouper_liasse_document(fichier["nom"], texte[:8000])

    db.log(projet_id, "appel_ia", {
        "action": "decouper_liasse",
        "fichier_id": fichier_id,
        "nb_documents": resultat.get("nb_documents", 0),
    })

    return resultat


# ─── QCI — Évaluation du Contrôle Interne ────────────────────────────────────

@router.get("/projets/{projet_id}/qci")
def get_qci(projet_id: str):
    """Retourne les questions QCI et les réponses existantes pour tous les cycles du projet."""
    from ..controls.qci import QCI_PAR_CYCLE, calculer_niveau_risque
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    cycles = projet.get("cycles_couverts") or []
    evaluations = {e["cycle"]: e for e in db.get_qci_evaluations(projet_id)}

    result = {}
    for cycle in cycles:
        questions = QCI_PAR_CYCLE.get(cycle, [])
        reponses_db = db.list_qci_reponses(projet_id, cycle)
        reponses_map = {r["question_id"]: r for r in reponses_db}

        questions_avec_reponses = []
        for q in questions:
            rep = reponses_map.get(q["id"], {})
            questions_avec_reponses.append({
                **q,
                "reponse": rep.get("reponse"),
                "commentaire": rep.get("commentaire", ""),
                "repondu_le": rep.get("repondu_le"),
            })

        reponses_pour_score = [
            {"reponse": r.get("reponse")}
            for r in questions_avec_reponses if r.get("reponse")
        ]
        score_info = calculer_niveau_risque(reponses_pour_score) if reponses_pour_score else None

        result[cycle] = {
            "cycle": cycle,
            "questions": questions_avec_reponses,
            "nb_repondues": sum(1 for q in questions_avec_reponses if q.get("reponse")),
            "nb_total": len(questions),
            "score_info": score_info,
            "evaluation": evaluations.get(cycle),
        }

    return {"cycles": result, "projet_id": projet_id}


class QciReponseBody(BaseModel):
    reponses: list[dict]  # [{question_id, reponse, commentaire}]


@router.post("/projets/{projet_id}/qci/{cycle}/reponses")
def save_qci_reponses(projet_id: str, cycle: str, body: QciReponseBody):
    """Enregistre les réponses QCI pour un cycle."""
    from ..controls.qci import QCI_PAR_CYCLE
    db = _get_db(projet_id)
    if cycle not in QCI_PAR_CYCLE:
        raise HTTPException(400, f"Cycle inconnu : {cycle}")

    for rep in body.reponses:
        qid = rep.get("question_id")
        reponse = rep.get("reponse")
        commentaire = rep.get("commentaire", "")
        if not qid or reponse not in ("oui", "non", "na"):
            continue
        db.save_qci_reponse(projet_id, cycle, qid, reponse, commentaire)

    db.log(projet_id, "action_humaine", {
        "action": "qci_reponses",
        "cycle": cycle,
        "nb_reponses": len(body.reponses),
    })

    reponses = db.list_qci_reponses(projet_id, cycle)
    return {"cycle": cycle, "nb_enregistrees": len(reponses)}


@router.post("/projets/{projet_id}/qci/{cycle}/evaluer")
def evaluer_qci(projet_id: str, cycle: str):
    """Déclenche l'évaluation IA du contrôle interne pour un cycle."""
    from ..controls.qci import QCI_PAR_CYCLE, calculer_niveau_risque
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if cycle not in QCI_PAR_CYCLE:
        raise HTTPException(400, f"Cycle inconnu : {cycle}")

    questions = QCI_PAR_CYCLE[cycle]
    reponses_db = db.list_qci_reponses(projet_id, cycle)
    reponses_map = {r["question_id"]: r for r in reponses_db}

    reponses_enrichies = []
    for q in questions:
        rep = reponses_map.get(q["id"], {})
        reponses_enrichies.append({
            "question_id": q["id"],
            "question": q["question"],
            "reponse": rep.get("reponse"),
            "commentaire": rep.get("commentaire", ""),
            "risque_si_non": q.get("risque_si_non", ""),
        })

    reponses_avec_rep = [r for r in reponses_enrichies if r.get("reponse")]
    if len(reponses_avec_rep) < 3:
        raise HTTPException(400, "Répondez à au moins 3 questions avant de déclencher l'évaluation.")

    score_info = calculer_niveau_risque(reponses_avec_rep)

    if not os.environ.get("ANTHROPIC_API_KEY") or not projet.get("consentement_client"):
        evaluation = {
            "synthese": f"Score QCI : {score_info['score']:.0%} — Risque {score_info['niveau'].upper()}.",
            "forces": [], "faiblesses": [], "recommandations": [],
            "niveau_risque": score_info["niveau"],
            "score": score_info["score"],
        }
    else:
        from ..llm.claude import ClaudeClient
        anon_qci = Anonymizer()
        entites_qci = [v for v in [projet.get("client"), projet.get("nif")] if v]
        ctx_qci = {k: v for k, v in projet.items() if k not in ("client", "nif")}
        ctx_qci["client"] = anon_qci.pseudonymiser(projet.get("client") or "", entites_qci) if entites_qci else projet.get("client")
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        evaluation = llm.evaluer_controle_interne(cycle, reponses_enrichies, ctx_qci)

    evaluation["score"] = score_info["score"]
    evaluation["niveau_risque"] = score_info["niveau"]
    db.save_qci_evaluation(projet_id, cycle, evaluation)
    db.log(projet_id, "appel_ia", {
        "action": "evaluation_ci",
        "cycle": cycle,
        "niveau": score_info["niveau"],
        "score": score_info["score"],
    })

    return evaluation


# ─── Documents annexes ────────────────────────────────────────────────────────

@router.get("/projets/{projet_id}/annexes")
def list_annexes(projet_id: str):
    db = _get_db(projet_id)
    return {"annexes": db.list_annexes(projet_id)}


@router.post("/projets/{projet_id}/annexes/{annexe_id}/analyser")
async def analyser_annexe(projet_id: str, annexe_id: str):
    """
    Analyse IA d'un document annexe : résumé textuel, points clés, alertes.
    L'IA ne produit que du texte — aucun chiffre extrait ne rentre dans les calculs.
    """
    db = _get_db(projet_id)
    annexe = db.get_annexe(annexe_id)
    if not annexe or annexe["projet_id"] != projet_id:
        raise HTTPException(404, "Document annexe introuvable.")

    _llm_guard(db, projet_id)

    # Lire le contenu texte du fichier (Excel/CSV → texte brut)
    chemin = DATA_DIR / annexe["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    try:
        from ..ingestion.excel_csv import lire_fichier as lire
        donnees, metadata = lire(chemin, projet_id, annexe_id, 0)
        # Construire un résumé textuel de max 3 000 caractères
        lignes = []
        for d in donnees[:200]:
            if d.type == "texte" and d.valeur:
                lignes.append(str(d.valeur))
        texte_brut = "\n".join(lignes)[:3000]
    except Exception:
        texte_brut = f"[Nom du fichier : {annexe['nom']}]"

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        ia_result = client.analyser_document_annexe(
            nom=annexe["nom"],
            description=annexe.get("description", ""),
            texte_brut=texte_brut,
        )
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    updated = db.update_annexe_ia(
        annexe_id,
        ia_result.get("resume", ""),
        ia_result.get("points_cles", []),
        ia_result.get("alertes", []),
    )
    db.log(projet_id, "appel_llm", {"action": "analyse_annexe", "annexe_id": annexe_id})
    return updated


@router.post("/projets/{projet_id}/mapper-colonnes")
async def mapper_colonnes(projet_id: str, body: dict):
    db = _get_db(projet_id)
    _llm_guard(db, projet_id)
    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        result = client.mapper_colonnes(body.get("colonnes", []), body.get("exemples", {}))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return result


# ─── Contrôles ────────────────────────────────────────────────────────────────

@router.get("/projets/{projet_id}/controles")
def list_resultats(projet_id: str, cycle: str | None = None):
    db = _get_db(projet_id)
    resultats = db.list_resultats(projet_id)
    if cycle:
        from ..controls.registry import REGISTRE
        refs_cycle = {ref for ref, c in REGISTRE.items() if c.cycle == cycle}
        resultats = [r for r in resultats if r.get("controle_ref") in refs_cycle]
    return {"resultats": resultats}


@router.get("/projets/{projet_id}/controles/registre")
def get_registre(projet_id: str = None):
    from ..controls.registry import REGISTRE
    return {"controles": [
        {"ref": c.ref, "libelle": c.libelle, "nep_ref": c.nep_ref,
         "cycle": c.cycle, "description": c.description, "severite_defaut": c.severite_defaut}
        for c in REGISTRE.values()
    ]}


def _seuils_ci(db, projet_id: str, cycle: str) -> dict:
    """
    Retourne les multiplicateurs de sensibilité selon le niveau de risque CI du cycle.
    CI élevé → seuils plus bas → plus d'exceptions levées (approche substantive renforcée).
    CI faible → seuils plus hauts → on s'appuie sur le CI, moins d'exceptions.
    """
    evaluations = {e["cycle"]: e for e in db.get_qci_evaluations(projet_id)}
    eval_cycle = evaluations.get(cycle, {})
    niveau = (eval_cycle.get("niveau_risque") or "").lower()

    # Multiplicateur appliqué sur seuil_pct_min et seuil_abs_min
    # CI élevé : on divise les seuils par 2 (on devient plus sensible)
    # CI faible : on multiplie les seuils par 1.5 (on réduit les tests)
    if niveau == "eleve":
        return {"facteur": 0.5, "note_ci": "CI élevé — seuils de détection réduits (approche substantive renforcée)"}
    elif niveau == "faible":
        return {"facteur": 1.5, "note_ci": "CI faible — seuils de détection relevés (appui sur le contrôle interne)"}
    else:
        return {"facteur": 1.0, "note_ci": "CI moyen ou non évalué — seuils standards"}


# ─── Cycle Trésorerie ─────────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/tresorerie")
def run_controles_tresorerie(projet_id: str, body: dict = {}):
    """Lance les 8 contrôles déterministes du cycle trésorerie."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    cycles_couverts = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    if "tresorerie" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle trésorerie non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil = float(projet.get("seuil_signification") or 0)
    exercice = projet.get("exercice")
    ci = _seuils_ci(db, projet_id, "tresorerie")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. TRESOR-BAL-EQUIL : Σ débits = Σ crédits ──
    if _check("TRESOR-BAL-EQUIL"):
        donnees_balance_ds = [d for d in donnees_all if d.fichier_source_id in ids_balance] \
            if ids_balance else donnees_all
        debits = [d for d in donnees_balance_ds
                  if d.type == "montant" and "debit" in d.localisation.lower()]
        credits_ds = [d for d in donnees_balance_ds
                      if d.type == "montant" and "credit" in d.localisation.lower()]
        res, exc = controle_equilibre_balance(projet_id, debits, credits_ds)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 2. TRESOR-GL-COHER : cohérence GL/balance pour comptes 5xx ──
    if _check("TRESOR-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "TRESOR-GL-COHER", rows_gl, rows_balance, ("5",),
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 3. TRESOR-SEQ-PIECES : continuité des numéros de pièces ──
    if _check("TRESOR-SEQ-PIECES"):
        pieces = [d for d in donnees_all
                  if d.type == "numero_piece"
                  and (not ids_gl or d.fichier_source_id in ids_gl)]
        if pieces:
            res, exc = controle_sequence_pieces(projet_id, pieces, "TRESOR-SEQ-PIECES")
            resultats_total.append(res)
            if exc:
                exceptions_total.append(exc)

    # ── 4. TRESOR-SOLDE-ANORMAL : soldes créditeurs sur comptes 5xx ──
    if _check("TRESOR-SOLDE-ANORMAL"):
        rows_pour_solde = rows_balance if rows_balance else rows_gl
        ress, excs = controle_soldes_anormaux_tresorerie(projet_id, rows_pour_solde)
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 5. TRESOR-ROUND : montants ronds anormaux ──
    if _check("TRESOR-ROUND"):
        rows_pour_round = rows_gl if rows_gl else rows_balance
        res, exc = controle_montants_ronds(
            projet_id, "TRESOR-ROUND", rows_pour_round, ("5",)
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. TRESOR-CUT-OFF : concentration d'écritures en fin d'exercice ──
    if _check("TRESOR-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "TRESOR-CUT-OFF", rows_gl, ("5",), exercice
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. TRESOR-VARIATION : variations N/N-1 (si seuil défini et N-1 disponible) ──
    if seuil > 0 and _check("TRESOR-VARIATION"):
        rows_pour_solde = rows_balance if rows_balance else rows_gl
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, ("5",))
        if soldes_n:
            plan_var = db.get_or_create_planification(projet_id)
            n1_id = plan_var.get("balance_n1_fichier_id")
            if n1_id:
                donnees_n1_raw = db.get_donnees_by_fichier(n1_id)
                donnees_n1 = [_to_donnee(d) for d in donnees_n1_raw]
                rows_n1 = _group_rows(donnees_n1) if donnees_n1 else []
                soldes_n1 = _aggreger_soldes_nets(rows_n1, ("5",))
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1, seuil * ci_facteur, "TRESOR-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("TRESOR-VARIATION", "Balance N-1 non renseignée (configurez-la dans Planification → Variations).")

    # ── 8. TRESOR-RAPPROCH : rapprochement bancaire (si relevé importé) ──
    if _check("TRESOR-RAPPROCH"):
        # Extraire solde comptable (max solde 5xx en balance)
        rows_releve_ds = [d for d in donnees_all if d.fichier_source_id in ids_releve]
        rows_balance_5xx = _filter_accounts(rows_balance or rows_gl, ("5",))

        solde_compta_val = 0.0
        solde_compta_src = None
        for row in rows_balance_5xx:
            s = _get_amount(row, "solde")
            if s == 0:
                s = _get_amount(row, "debit") - _get_amount(row, "credit")
            if abs(s) > abs(solde_compta_val):
                solde_compta_val = s
                solde_compta_src = row.get("compte") or row.get("solde")

        # Extraire solde du relevé bancaire (dernier montant significatif)
        montants_releve = [d for d in rows_releve_ds if d.type == "montant"]
        solde_releve_val = 0.0
        solde_releve_src = None
        if montants_releve:
            # Prendre le montant dont la valeur absolue est la plus grande (solde final probable)
            montants_releve.sort(key=lambda d: abs(float(d.valeur or 0)), reverse=True)
            solde_releve_src = montants_releve[0]
            solde_releve_val = float(solde_releve_src.valeur or 0)

        if solde_compta_src and solde_releve_src:
            res, exc = controle_rapprochement_bancaire(
                projet_id, solde_compta_src, solde_releve_src
            )
            resultats_total.append(res)
            if exc:
                exceptions_total.append(exc)
        else:
            _skip("TRESOR-RAPPROCH",
                  "Impossible d'extraire les soldes du grand livre ou du relevé.")

    # Persistance
    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    for r in resultats_total:
        db.save_resultat(r)
    for e in exceptions_total:
        db.save_exception(e)

    db.log(projet_id, "transition_etat", {
        "action": "controles_tresorerie",
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    exceptions_enrichies = db.list_exceptions(projet_id)
    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": exceptions_enrichies,
        "controles_ignores": ignores,
    }


# ─── Cycle Achats-Fournisseurs ─────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/achats")
def run_controles_achats(projet_id: str, body: dict = {}):
    """Lance les 9 contrôles déterministes du cycle achats-fournisseurs."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    cycles_couverts = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    if "achats" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle achats-fournisseurs non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    exercice = projet.get("exercice")
    seuil = float(projet.get("seuil_signification") or 0)
    ci = _seuils_ci(db, projet_id, "achats")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_FOURN = ("40",)
    PREFIXES_ACHATS = ("60", "61", "62", "63")
    PREFIXES_CYCLE = PREFIXES_FOURN + PREFIXES_ACHATS

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. ACHAT-GL-COHER ──
    if _check("ACHAT-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "ACHAT-GL-COHER", rows_gl, rows_balance, PREFIXES_CYCLE,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. ACHAT-SEQ-FACTURES ──
    if _check("ACHAT-SEQ-FACTURES"):
        pieces_achats = [
            d for d in donnees_all
            if d.type == "numero_piece"
            and any(row.get("compte") and str(row["compte"].valeur or "").startswith(PREFIXES_CYCLE)
                    for row in rows_pour_mvt
                    if row.get("numero_piece") and row["numero_piece"].id == d.id)
        ]
        pieces = pieces_achats or [d for d in donnees_all if d.type == "numero_piece"]
        if pieces:
            res, exc = controle_sequence_pieces(projet_id, pieces, "ACHAT-SEQ-FACTURES")
            resultats_total.append(res)
            if exc:
                exceptions_total.append(exc)

    # ── 3. ACHAT-SOLDE-DEBITEUR ──
    if _check("ACHAT-SOLDE-DEBITEUR"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "ACHAT-SOLDE-DEBITEUR",
            rows_pour_solde, PREFIXES_FOURN, sens_normal="credit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 4. ACHAT-DOUBLON ──
    if _check("ACHAT-DOUBLON"):
        res, exc = controle_doublons_factures(
            projet_id, "ACHAT-DOUBLON", rows_pour_mvt, PREFIXES_FOURN,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. ACHAT-CONCENTRATION ──
    if _check("ACHAT-CONCENTRATION"):
        res, exc = controle_concentration_compte(
            projet_id, "ACHAT-CONCENTRATION", rows_pour_mvt, PREFIXES_FOURN, sens="credit",
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. ACHAT-AVOIR ──
    if _check("ACHAT-AVOIR"):
        res, exc = controle_ratio_avoirs(
            projet_id, "ACHAT-AVOIR", rows_pour_mvt, PREFIXES_FOURN, sens_avoir="debit",
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. ACHAT-ROUND ──
    if _check("ACHAT-ROUND"):
        res, exc = controle_montants_ronds(
            projet_id, "ACHAT-ROUND", rows_pour_mvt, PREFIXES_ACHATS,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 8. ACHAT-CUT-OFF ──
    if _check("ACHAT-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "ACHAT-CUT-OFF", rows_pour_mvt, PREFIXES_ACHATS, exercice,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 9. ACHAT-VARIATION ──
    if seuil > 0 and _check("ACHAT-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_ACHATS)
        if soldes_n:
            plan_var_a = db.get_or_create_planification(projet_id)
            n1_id_a = plan_var_a.get("balance_n1_fichier_id")
            if n1_id_a:
                donnees_n1_a = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_a)]
                rows_n1_a = _group_rows(donnees_n1_a) if donnees_n1_a else []
                soldes_n1_a = _aggreger_soldes_nets(rows_n1_a, PREFIXES_ACHATS)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_a, seuil * ci_facteur, "ACHAT-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("ACHAT-VARIATION", "Balance N-1 non renseignée (configurez-la dans Planification → Variations).")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    for r in resultats_total:
        db.save_resultat(r)
    for e in exceptions_total:
        db.save_exception(e)

    db.log(projet_id, "transition_etat", {
        "action": "controles_achats",
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    exceptions_enrichies = db.list_exceptions(projet_id)
    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": exceptions_enrichies,
        "controles_ignores": ignores,
    }


# ─── Cycle Ventes-Clients ─────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/ventes")
def run_controles_ventes(projet_id: str, body: dict = {}):
    """Lance les 10 contrôles déterministes du cycle ventes-clients."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    cycles_couverts = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    if "ventes" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle ventes-clients non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    exercice = projet.get("exercice")
    seuil = float(projet.get("seuil_signification") or 0)
    ci = _seuils_ci(db, projet_id, "ventes")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_CLIENTS = ("41",)
    PREFIXES_VENTES = ("70", "71", "72", "73")
    PREFIXES_CYCLE = PREFIXES_CLIENTS + PREFIXES_VENTES

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. VENTE-GL-COHER ──
    if _check("VENTE-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "VENTE-GL-COHER", rows_gl, rows_balance, PREFIXES_CYCLE,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. VENTE-SEQ-FACTURES ──
    if _check("VENTE-SEQ-FACTURES"):
        pieces = [d for d in donnees_all if d.type == "numero_piece"]
        if pieces:
            res, exc = controle_sequence_pieces(projet_id, pieces, "VENTE-SEQ-FACTURES")
            resultats_total.append(res)
            if exc:
                exceptions_total.append(exc)

    # ── 3. VENTE-SOLDE-CREDITEUR ──
    if _check("VENTE-SOLDE-CREDITEUR"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "VENTE-SOLDE-CREDITEUR",
            rows_pour_solde, PREFIXES_CLIENTS, sens_normal="debit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 4. VENTE-DOUBLON ──
    if _check("VENTE-DOUBLON"):
        res, exc = controle_doublons_factures(
            projet_id, "VENTE-DOUBLON", rows_pour_mvt, PREFIXES_CLIENTS,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. VENTE-CONCENTRATION ──
    if _check("VENTE-CONCENTRATION"):
        res, exc = controle_concentration_compte(
            projet_id, "VENTE-CONCENTRATION", rows_pour_mvt, PREFIXES_CLIENTS, sens="debit",
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. VENTE-AVOIR ──
    if _check("VENTE-AVOIR"):
        res, exc = controle_ratio_avoirs(
            projet_id, "VENTE-AVOIR", rows_pour_mvt, PREFIXES_CLIENTS, sens_avoir="credit",
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. VENTE-ROUND ──
    if _check("VENTE-ROUND"):
        res, exc = controle_montants_ronds(
            projet_id, "VENTE-ROUND", rows_pour_mvt, PREFIXES_VENTES,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 8. VENTE-CUT-OFF ──
    if _check("VENTE-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "VENTE-CUT-OFF", rows_pour_mvt, PREFIXES_VENTES, exercice,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 9. VENTE-CREANCES-ECHUES ──
    if _check("VENTE-CREANCES-ECHUES"):
        res, exc = controle_creances_echues(
            projet_id, rows_pour_mvt, exercice,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 10. VENTE-VARIATION ──
    if seuil > 0 and _check("VENTE-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_VENTES)
        if soldes_n:
            plan_var_v = db.get_or_create_planification(projet_id)
            n1_id_v = plan_var_v.get("balance_n1_fichier_id")
            if n1_id_v:
                donnees_n1_v = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_v)]
                rows_n1_v = _group_rows(donnees_n1_v) if donnees_n1_v else []
                soldes_n1_v = _aggreger_soldes_nets(rows_n1_v, PREFIXES_VENTES)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_v, seuil * ci_facteur, "VENTE-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("VENTE-VARIATION", "Balance N-1 non renseignée (configurez-la dans Planification → Variations).")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    for r in resultats_total:
        db.save_resultat(r)
    for e in exceptions_total:
        db.save_exception(e)

    db.log(projet_id, "transition_etat", {
        "action": "controles_ventes",
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    exceptions_enrichies = db.list_exceptions(projet_id)
    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": exceptions_enrichies,
        "controles_ignores": ignores,
    }


# ─── Utilitaires routes ───────────────────────────────────────────────────────

def _aggreger_soldes_nets(
    rows: list,
    prefixes: tuple[str, ...],
) -> dict[str, tuple[float, list[str]]]:
    """Agrège les soldes nets par compte pour les préfixes donnés."""
    rows_f = _filter_accounts(rows, prefixes)
    result: dict[str, tuple[float, list[str]]] = {}
    for row in rows_f:
        c = row.get("compte")
        if not c:
            continue
        num = str(c.valeur or "")
        s = _get_amount(row, "solde")
        if s == 0:
            s = _get_amount(row, "debit") - _get_amount(row, "credit")
        prev, srcs = result.get(num, (0.0, []))
        result[num] = (prev + s, srcs + [c.id])
    return result


# ─── Exceptions ───────────────────────────────────────────────────────────────

@router.get("/projets/{projet_id}/exceptions")
def list_exceptions(projet_id: str, statut: str | None = None, cycle: str | None = None):
    db = _get_db(projet_id)
    exceptions = db.list_exceptions(projet_id, statut)
    if cycle:
        from ..controls.registry import REGISTRE
        refs_cycle = {ref for ref, c in REGISTRE.items() if c.cycle == cycle}
        exceptions = [e for e in exceptions if e.get("controle_ref") in refs_cycle]
    return {"exceptions": exceptions}


class TrancheeBody(BaseModel):
    decision_humaine: str
    decideur: str


@router.post("/projets/{projet_id}/exceptions/{exception_id}/trancher")
def trancher_exception(projet_id: str, exception_id: str, body: TrancheeBody):
    db = _get_db(projet_id)
    exc = db.trancher_exception(exception_id, body.decision_humaine, body.decideur)
    if not exc:
        raise HTTPException(404, "Exception introuvable.")
    db.log(projet_id, "action_humaine", {
        "action": "trancher_exception",
        "exception_id": exception_id,
        "decideur": body.decideur,
        "decision": body.decision_humaine[:100],
    })
    return exc


@router.post("/projets/{projet_id}/exceptions/{exception_id}/interpreter")
def interpreter_exception(projet_id: str, exception_id: str):
    """(Re)lance l'interprétation IA d'une exception."""
    db = _get_db(projet_id)
    projet, anon = _llm_guard(db, projet_id)

    exc = db.get_exception(exception_id)
    if not exc:
        raise HTTPException(404, "Exception introuvable.")

    entites_sensibles = [v for v in [projet.get("client"), projet.get("nif")] if v]
    exc_anon = anon.pseudonymiser_dict(exc, ["description"], entites_sensibles)
    ctx = {"exercice": projet.get("exercice"), "seuil": projet.get("seuil_signification")}

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        result = client.interpreter_exception(exc_anon, [], ctx)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    if "explication" in result:
        result["explication"] = anon.re_identifier(result["explication"])

    updated = db.update_exception_ia(exception_id, result)
    return {**result, "exception": updated}


# ─── Génération ───────────────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/generer-feuille")
def generer_feuille(projet_id: str, body: dict = {}):
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)
    if db.has_open_exceptions(projet_id):
        raise HTTPException(400, "Exceptions ouvertes non tranchées.")

    cycle = body.get("cycle", "tresorerie")
    resultats = db.list_resultats(projet_id)
    exceptions = db.list_exceptions(projet_id)

    # Filtrer par cycle si spécifié
    from ..controls.registry import REGISTRE
    refs_cycle = {ref for ref, c in REGISTRE.items() if c.cycle == cycle}
    resultats_cycle = [r for r in resultats if r.get("controle_ref") in refs_cycle]
    exceptions_cycle = [e for e in exceptions if e.get("controle_ref") in refs_cycle]

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        result = client.rediger_feuille_travail(
            cycle,
            resultats_cycle or resultats,
            exceptions_cycle or exceptions,
            {"exercice": projet.get("exercice"), "seuil": projet.get("seuil_signification")},
        )
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    feuille = {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        "cycle": cycle,
        "contenu_redige": result.get("contenu", ""),
        "sources": [r["id"] for r in (resultats_cycle or resultats)[:20]],
        "nep_ref": "NEP 230",
        "genere_le": _now(),
    }
    db.save_feuille_travail(feuille)
    return {**feuille, "llm_result": result}


@router.get("/projets/{projet_id}/feuilles")
def list_feuilles(projet_id: str):
    db = _get_db(projet_id)
    return {"feuilles": db.list_feuilles(projet_id)}


@router.post("/projets/{projet_id}/exporter-dossier")
def exporter_dossier(projet_id: str):
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if db.has_open_exceptions(projet_id):
        raise HTTPException(400, "Exceptions ouvertes non tranchées.")

    resultats = db.list_resultats(projet_id)
    exceptions = db.list_exceptions(projet_id)
    feuilles = db.list_feuilles(projet_id)

    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"dossier_travail_{projet_id[:8]}.docx"

    try:
        generer_dossier_travail(projet, resultats, exceptions, feuilles, output_path)
    except ProvenanceError as e:
        raise HTTPException(422, str(e))

    db.log(projet_id, "action_humaine", {"action": "export_dossier", "fichier": str(output_path)})
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"dossier_travail_{projet_id[:8]}.docx",
    )


@router.post("/projets/{projet_id}/exporter-exceptions")
def exporter_exceptions(projet_id: str):
    db = _get_db(projet_id)
    exceptions = db.list_exceptions(projet_id)
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"exceptions_{projet_id[:8]}.xlsx"
    generer_tableau_exceptions(exceptions, output_path)
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"exceptions_{projet_id[:8]}.xlsx",
    )


# ─── Dossier Brut ─────────────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/dossier/fichiers")
async def upload_fichier_brut(
    projet_id: str,
    fichier: UploadFile = File(...),
):
    """Upload d'un document brut (PDF, image, Excel, CSV, Word...)."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")

    dossier_dir = DATA_DIR / projet_id / "dossier_brut"
    dossier_dir.mkdir(parents=True, exist_ok=True)

    nom_fichier = fichier.filename or f"document_{uuid.uuid4().hex[:8]}"
    file_path = dossier_dir / nom_fichier
    # Éviter les collisions de noms
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        file_path = dossier_dir / f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"

    content = await fichier.read()
    file_path.write_bytes(content)

    doc_id = str(uuid.uuid4())
    doc = db.save_document_brut({
        "id": doc_id,
        "projet_id": projet_id,
        "nom": nom_fichier,
        "chemin_relatif": str(file_path.relative_to(DATA_DIR)),
        "taille_octets": len(content),
        "type_mime": fichier.content_type or "",
        "statut": "uploade",
    })
    db.log(projet_id, "action_humaine", {
        "action": "upload_document_brut",
        "fichier": nom_fichier,
        "taille": len(content),
    })
    return doc


@router.get("/projets/{projet_id}/dossier")
def list_documents_bruts(projet_id: str):
    db = _get_db(projet_id)
    return {"documents": db.list_documents_bruts(projet_id)}


@router.delete("/projets/{projet_id}/dossier/{doc_id}")
def delete_document_brut(projet_id: str, doc_id: str):
    import shutil
    db = _get_db(projet_id)
    doc = db.get_document_brut(doc_id)
    if not doc or doc["projet_id"] != projet_id:
        raise HTTPException(404, "Document introuvable.")
    # Supprimer le fichier physique
    if doc.get("chemin_relatif"):
        try:
            (DATA_DIR / doc["chemin_relatif"]).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete_document_brut(doc_id)
    return {"deleted": True, "doc_id": doc_id}


@router.post("/projets/{projet_id}/dossier/{doc_id}/cataloguer")
async def cataloguer_document_brut(projet_id: str, doc_id: str):
    """Haiku — catalogue un document brut : identifie son type et le décrit."""
    db = _get_db(projet_id)
    doc = db.get_document_brut(doc_id)
    if not doc or doc["projet_id"] != projet_id:
        raise HTTPException(404, "Document introuvable.")
    _llm_guard(db, projet_id)

    chemin = DATA_DIR / doc["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    texte, b64, mime = lire_contenu_pour_llm(chemin)

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        catalogue = client.cataloguer_document(doc["nom"], texte, b64, mime)
    except RuntimeError as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(503, str(e))
    except Exception as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(500, f"Erreur de catalogage : {e}")

    updated = db.update_document_brut(
        doc_id,
        statut="catalogue",
        type_detecte=catalogue.get("type_detecte", "autre"),
        description_ia=catalogue.get("description", ""),
        catalogue_json=catalogue,
        erreur=None,
    )
    return updated


@router.post("/projets/{projet_id}/dossier/cataloguer-tous")
async def cataloguer_tous_documents_bruts(projet_id: str):
    """Haiku — catalogue tous les documents en statut 'uploade'."""
    db = _get_db(projet_id)
    _llm_guard(db, projet_id)

    docs = [d for d in db.list_documents_bruts(projet_id) if d["statut"] == "uploade"]
    if not docs:
        return {"nb_traites": 0, "message": "Aucun document en attente de catalogage."}

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    from ..llm.claude import ClaudeClient
    def log_llm(t, p): db.log(projet_id, t, p)
    client = ClaudeClient(audit_logger=log_llm)

    nb_ok, nb_erreur = 0, 0
    for doc in docs:
        try:
            chemin = DATA_DIR / doc["chemin_relatif"]
            if not chemin.exists():
                db.update_document_brut(doc["id"], statut="erreur",
                                        erreur="Fichier physique introuvable.")
                nb_erreur += 1
                continue
            texte, b64, mime = lire_contenu_pour_llm(chemin)
            catalogue = client.cataloguer_document(doc["nom"], texte, b64, mime)
            db.update_document_brut(
                doc["id"],
                statut="catalogue",
                type_detecte=catalogue.get("type_detecte", "autre"),
                description_ia=catalogue.get("description", ""),
                catalogue_json=catalogue,
                erreur=None,
            )
            nb_ok += 1
        except Exception as e:
            db.update_document_brut(doc["id"], statut="erreur", erreur=str(e))
            nb_erreur += 1

    return {
        "nb_traites": nb_ok + nb_erreur,
        "nb_ok": nb_ok,
        "nb_erreur": nb_erreur,
        "documents": db.list_documents_bruts(projet_id),
    }


@router.post("/projets/{projet_id}/dossier/{doc_id}/extraire")
async def extraire_document_brut(projet_id: str, doc_id: str):
    """Sonnet — extrait les données comptables structurées d'un document catalogué."""
    db = _get_db(projet_id)
    doc = db.get_document_brut(doc_id)
    if not doc or doc["projet_id"] != projet_id:
        raise HTTPException(404, "Document introuvable.")
    if doc["statut"] not in ("catalogue", "extrait"):
        raise HTTPException(400, "Cataloguez ce document avant d'extraire.")
    _llm_guard(db, projet_id)

    chemin = DATA_DIR / doc["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    texte, b64, mime = lire_contenu_pour_llm(chemin)
    catalogue = doc.get("catalogue_json") or {}

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        extraction = client.extraire_donnees_comptables(
            nom=doc["nom"],
            type_detecte=doc.get("type_detecte") or catalogue.get("type_detecte", "autre"),
            description=doc.get("description_ia") or catalogue.get("description", ""),
            contenu_texte=texte,
            contenu_b64=b64,
            media_type=mime,
        )
    except RuntimeError as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(503, str(e))
    except Exception as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(500, f"Erreur d'extraction : {e}")

    updated = db.update_document_brut(
        doc_id,
        statut="extrait",
        extraction_json=extraction,
        erreur=None,
    )
    return updated


@router.post("/projets/{projet_id}/dossier/extraire-tous")
async def extraire_tous_documents_bruts(projet_id: str):
    """Sonnet — extrait tous les documents en statut 'catalogue'."""
    db = _get_db(projet_id)
    _llm_guard(db, projet_id)

    docs = [d for d in db.list_documents_bruts(projet_id)
            if d["statut"] in ("catalogue",)]
    if not docs:
        return {"nb_traites": 0, "message": "Aucun document catalogué en attente d'extraction."}

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    from ..llm.claude import ClaudeClient
    def log_llm(t, p): db.log(projet_id, t, p)
    client = ClaudeClient(audit_logger=log_llm)

    nb_ok, nb_erreur = 0, 0
    for doc in docs:
        try:
            chemin = DATA_DIR / doc["chemin_relatif"]
            if not chemin.exists():
                db.update_document_brut(doc["id"], statut="erreur",
                                        erreur="Fichier physique introuvable.")
                nb_erreur += 1
                continue
            texte, b64, mime = lire_contenu_pour_llm(chemin)
            catalogue = doc.get("catalogue_json") or {}
            extraction = client.extraire_donnees_comptables(
                nom=doc["nom"],
                type_detecte=doc.get("type_detecte") or catalogue.get("type_detecte", "autre"),
                description=doc.get("description_ia") or catalogue.get("description", ""),
                contenu_texte=texte,
                contenu_b64=b64,
                media_type=mime,
            )
            db.update_document_brut(doc["id"], statut="extrait",
                                    extraction_json=extraction, erreur=None)
            nb_ok += 1
        except Exception as e:
            db.update_document_brut(doc["id"], statut="erreur", erreur=str(e))
            nb_erreur += 1

    return {
        "nb_traites": nb_ok + nb_erreur,
        "nb_ok": nb_ok,
        "nb_erreur": nb_erreur,
        "documents": db.list_documents_bruts(projet_id),
    }


@router.post("/projets/{projet_id}/dossier/{doc_id}/verifier")
async def verifier_document_brut(projet_id: str, doc_id: str):
    """Sonnet — vérifie ligne par ligne l'extraction d'Opus contre le document source."""
    db = _get_db(projet_id)
    doc = db.get_document_brut(doc_id)
    if not doc or doc["projet_id"] != projet_id:
        raise HTTPException(404, "Document introuvable.")
    if doc["statut"] not in ("extrait", "verifie"):
        raise HTTPException(400, "Extrayez d'abord ce document avant de le vérifier.")
    _llm_guard(db, projet_id)

    extraction = doc.get("extraction_json")
    if not extraction or not extraction.get("lignes"):
        raise HTTPException(400, "Aucune donnée extraite à vérifier.")

    chemin = DATA_DIR / doc["chemin_relatif"]
    if not chemin.exists():
        raise HTTPException(404, "Fichier physique introuvable.")

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    texte, b64, mime = lire_contenu_pour_llm(chemin)

    try:
        from ..llm.claude import ClaudeClient
        def log_llm(t, p): db.log(projet_id, t, p)
        client = ClaudeClient(audit_logger=log_llm)
        verification = client.verifier_extraction_donnees(
            nom=doc["nom"],
            type_detecte=doc.get("type_detecte", "autre"),
            lignes=extraction.get("lignes", []),
            contenu_texte=texte,
            contenu_b64=b64,
            media_type=mime,
        )
    except RuntimeError as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(503, str(e))
    except Exception as e:
        db.update_document_brut(doc_id, statut="erreur", erreur=str(e))
        raise HTTPException(500, f"Erreur de vérification : {e}")

    # Enrichir l'extraction_json avec les résultats de vérification
    import json as _json
    extraction_enrichie = {**extraction, "verification": verification}
    updated = db.update_document_brut(
        doc_id,
        statut="verifie",
        extraction_json=extraction_enrichie,
        verification_json=verification,
        erreur=None,
    )
    return updated


@router.post("/projets/{projet_id}/dossier/verifier-tous")
async def verifier_tous_documents_bruts(projet_id: str):
    """Sonnet — vérifie tous les documents en statut 'extrait'."""
    db = _get_db(projet_id)
    _llm_guard(db, projet_id)

    docs = [d for d in db.list_documents_bruts(projet_id) if d["statut"] == "extrait"]
    if not docs:
        return {"nb_traites": 0, "message": "Aucun document extrait en attente de vérification."}

    from ..ingestion.dossier_brut import lire_contenu_pour_llm
    from ..llm.claude import ClaudeClient
    def log_llm(t, p): db.log(projet_id, t, p)
    client = ClaudeClient(audit_logger=log_llm)

    nb_ok, nb_erreur = 0, 0
    for doc in docs:
        try:
            extraction = doc.get("extraction_json")
            if not extraction or not extraction.get("lignes"):
                db.update_document_brut(doc["id"], statut="erreur",
                                        erreur="Aucune donnée extraite à vérifier.")
                nb_erreur += 1
                continue
            chemin = DATA_DIR / doc["chemin_relatif"]
            if not chemin.exists():
                db.update_document_brut(doc["id"], statut="erreur",
                                        erreur="Fichier physique introuvable.")
                nb_erreur += 1
                continue
            texte, b64, mime = lire_contenu_pour_llm(chemin)
            verification = client.verifier_extraction_donnees(
                nom=doc["nom"],
                type_detecte=doc.get("type_detecte", "autre"),
                lignes=extraction.get("lignes", []),
                contenu_texte=texte,
                contenu_b64=b64,
                media_type=mime,
            )
            extraction_enrichie = {**extraction, "verification": verification}
            db.update_document_brut(doc["id"], statut="verifie",
                                    extraction_json=extraction_enrichie,
                                    verification_json=verification, erreur=None)
            nb_ok += 1
        except Exception as e:
            db.update_document_brut(doc["id"], statut="erreur", erreur=str(e))
            nb_erreur += 1

    return {
        "nb_traites": nb_ok + nb_erreur,
        "nb_ok": nb_ok,
        "nb_erreur": nb_erreur,
        "documents": db.list_documents_bruts(projet_id),
    }


@router.post("/projets/{projet_id}/dossier/{doc_id}/importer")
async def importer_document_brut(projet_id: str, doc_id: str):
    """Convertit l'extraction d'un document brut en DonneeSourcee importables."""
    db = _get_db(projet_id)
    doc = db.get_document_brut(doc_id)
    if not doc or doc["projet_id"] != projet_id:
        raise HTTPException(404, "Document introuvable.")
    if doc["statut"] not in ("extrait", "verifie"):
        raise HTTPException(400, "Extrayez (et idéalement vérifiez) ce document avant d'importer.")

    extraction = doc.get("extraction_json")
    if not extraction or not extraction.get("lignes"):
        raise HTTPException(400, "Aucune donnée extraite à importer.")

    from ..ingestion.dossier_brut import lignes_vers_csv
    from ..ingestion.excel_csv import lire_fichier, hash_file

    # Construire le CSV depuis les lignes extraites
    csv_content = lignes_vers_csv(extraction["lignes"])

    # Sauvegarder le CSV dans les uploads du projet
    uploads_dir = DATA_DIR / projet_id / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    type_sortie = extraction.get("type_sortie", "grand_livre")
    csv_nom = f"extrait_{doc['nom'][:40].replace(' ', '_')}_{doc_id[:6]}.csv"
    csv_path = uploads_dir / csv_nom
    csv_path.write_text(csv_content, encoding="utf-8")

    # Enregistrer comme fichier_source
    fichier_id = str(uuid.uuid4())
    file_hash = hash_file(csv_path)
    db.save_fichier_source({
        "id": fichier_id,
        "projet_id": projet_id,
        "nom": csv_nom,
        "chemin_relatif": str(csv_path.relative_to(DATA_DIR)),
        "type": type_sortie,
        "type_document": type_sortie,
        "hash": file_hash,
        "importe_le": _now(),
    })

    # Extraire les DonneeSourcee
    try:
        donnees, metadata = lire_fichier(csv_path, projet_id, fichier_id, 0)
    except Exception as e:
        raise HTTPException(400, f"Erreur d'ingestion du CSV extrait : {e}")

    db.save_donnees_sourcees([d.model_dump() for d in donnees])
    db.update_document_brut(doc_id, statut="importe")
    db.log(projet_id, "action_humaine", {
        "action": "import_dossier_brut",
        "doc_nom": doc["nom"],
        "type_sortie": type_sortie,
        "nb_lignes": len(donnees),
        "fichier_source_id": fichier_id,
    })

    return {
        "fichier_source_id": fichier_id,
        "type_document": type_sortie,
        "nb_donnees_extraites": len(donnees),
        "csv_nom": csv_nom,
        "document_brut": db.get_document_brut(doc_id),
    }


# ─── Clients & Dossiers permanents ───────────────────────────────────────────

from ..storage.clients_db import CATEGORIES_PERMANENTS


class CreateClientBody(BaseModel):
    nom: str
    nif: str
    secteur: str | None = None
    adresse: str | None = None
    dirigeants: str | None = None
    systemes_info: str | None = None
    notes: str | None = None


class UpdateClientBody(BaseModel):
    nom: str | None = None
    nif: str | None = None
    secteur: str | None = None
    adresse: str | None = None
    dirigeants: str | None = None
    systemes_info: str | None = None
    notes: str | None = None


@router.get("/clients")
def list_clients(q: str | None = None):
    cdb = _get_clients_db()
    if q and len(q) >= 2:
        clients = cdb.search_clients(q)
    else:
        clients = cdb.list_clients()
    for c in clients:
        c["nb_fichiers_permanents"] = cdb.count_fichiers_permanents(c["id"])
    return {"clients": clients}


@router.post("/clients")
def create_client(body: CreateClientBody):
    cdb = _get_clients_db()
    existing = cdb.get_client_by_nif(body.nif)
    if existing:
        raise HTTPException(409, f"Un client avec le NIF « {body.nif} » existe déjà.")
    client_id = str(uuid.uuid4())
    client = cdb.create_client({"id": client_id, **body.model_dump()})
    CLIENTS_FILES_DIR.joinpath(client_id).mkdir(parents=True, exist_ok=True)
    return client


@router.get("/clients/{client_id}")
def get_client(client_id: str):
    cdb = _get_clients_db()
    client = cdb.get_client(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable.")
    client["nb_fichiers_permanents"] = cdb.count_fichiers_permanents(client_id)
    client["fichiers_permanents"] = cdb.list_fichiers_permanents(client_id)
    client["categories"] = CATEGORIES_PERMANENTS
    return client


@router.patch("/clients/{client_id}")
def update_client(client_id: str, body: UpdateClientBody):
    cdb = _get_clients_db()
    if not cdb.get_client(client_id):
        raise HTTPException(404, "Client introuvable.")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "nif" in data:
        existing = cdb.get_client_by_nif(data["nif"])
        if existing and existing["id"] != client_id:
            raise HTTPException(409, f"Le NIF « {data['nif']} » est déjà utilisé.")
    return cdb.update_client(client_id, data)


@router.delete("/clients/{client_id}")
def delete_client(client_id: str):
    import shutil
    cdb = _get_clients_db()
    if not cdb.get_client(client_id):
        raise HTTPException(404, "Client introuvable.")
    cdb.delete_client(client_id)
    client_dir = CLIENTS_FILES_DIR / client_id
    if client_dir.exists():
        shutil.rmtree(str(client_dir), ignore_errors=True)
    return {"deleted": True, "client_id": client_id}


@router.get("/clients/{client_id}/permanent")
def list_permanent(client_id: str):
    cdb = _get_clients_db()
    if not cdb.get_client(client_id):
        raise HTTPException(404, "Client introuvable.")
    fichiers = cdb.list_fichiers_permanents(client_id)
    return {"fichiers": fichiers, "categories": CATEGORIES_PERMANENTS}


@router.post("/clients/{client_id}/permanent/fichiers")
async def upload_fichier_permanent(
    client_id: str,
    fichier: UploadFile = File(...),
    categorie: str = Form("autres"),
    description: str = Form(""),
):
    cdb = _get_clients_db()
    if not cdb.get_client(client_id):
        raise HTTPException(404, "Client introuvable.")

    if categorie not in CATEGORIES_PERMANENTS:
        categorie = "autres"

    client_dir = CLIENTS_FILES_DIR / client_id
    client_dir.mkdir(parents=True, exist_ok=True)

    nom_fichier = fichier.filename or f"document_{uuid.uuid4().hex[:8]}"
    file_path = client_dir / nom_fichier
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        file_path = client_dir / f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"

    content = await fichier.read()
    file_path.write_bytes(content)

    fid = str(uuid.uuid4())
    fichier_data = cdb.save_fichier_permanent({
        "id": fid,
        "client_id": client_id,
        "nom": nom_fichier,
        "chemin_relatif": str(file_path.relative_to(GLOBAL_DIR)),
        "categorie": categorie,
        "description": description,
        "taille_octets": len(content),
    })
    return fichier_data


@router.patch("/clients/{client_id}/permanent/{fichier_id}")
def update_fichier_permanent(client_id: str, fichier_id: str, body: dict):
    cdb = _get_clients_db()
    f = cdb.get_fichier_permanent(fichier_id)
    if not f or f["client_id"] != client_id:
        raise HTTPException(404, "Fichier introuvable.")
    return cdb.update_fichier_permanent(fichier_id, body)


@router.delete("/clients/{client_id}/permanent/{fichier_id}")
def delete_fichier_permanent(client_id: str, fichier_id: str):
    cdb = _get_clients_db()
    f = cdb.get_fichier_permanent(fichier_id)
    if not f or f["client_id"] != client_id:
        raise HTTPException(404, "Fichier introuvable.")
    chemin = GLOBAL_DIR / f["chemin_relatif"]
    try:
        chemin.unlink(missing_ok=True)
    except Exception:
        pass
    cdb.delete_fichier_permanent(fichier_id)
    return {"deleted": True, "fichier_id": fichier_id}


# ─── Sauvegarde / restauration (GEN-10 + EXP-04) ────────────────────────────

@router.get("/projets/{projet_id}/sauvegarder")
def sauvegarder_projet(projet_id: str):
    """Exporte le dossier complet en ZIP (SQLite + fichiers). Archive téléchargeable."""
    import shutil
    import zipfile
    import tempfile

    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    projet_dir = DATA_DIR / projet_id
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    nom_safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in projet.get("nom", projet_id)[:30])
    zip_name = f"probare_{nom_safe}_{now_str}.zip"

    tmp_zip = Path(tempfile.mktemp(suffix=".zip"))

    manifest = {
        "version": "1.0",
        "probare_export": True,
        "projet_id": projet_id,
        "nom": projet.get("nom"),
        "client": projet.get("client"),
        "exercice": projet.get("exercice"),
        "nature_mission": projet.get("nature_mission", "contractuelle"),
        "exported_at": _now(),
    }

    with zipfile.ZipFile(str(tmp_zip), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        db_path = projet_dir / "audit.db"
        if db_path.exists():
            zf.write(str(db_path), "audit.db")

        uploads_dir = projet_dir / "uploads"
        if uploads_dir.exists():
            for f in uploads_dir.rglob("*"):
                if f.is_file():
                    zf.write(str(f), f"uploads/{f.relative_to(uploads_dir)}")

        dossier_dir = projet_dir / "dossier_brut"
        if dossier_dir.exists():
            for f in dossier_dir.rglob("*"):
                if f.is_file():
                    zf.write(str(f), f"dossier_brut/{f.relative_to(dossier_dir)}")

    db.log(projet_id, "action_humaine", {"action": "sauvegarde_zip", "fichier": zip_name})

    return FileResponse(
        str(tmp_zip),
        media_type="application/zip",
        filename=zip_name,
        background=None,
    )


@router.post("/projets/restaurer")
async def restaurer_projet(
    archive: UploadFile = File(...),
):
    """Restaure un dossier depuis un ZIP exporté. Refuse si le projet existe déjà."""
    import zipfile
    import tempfile
    import shutil

    content = await archive.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(content)

        try:
            with zipfile.ZipFile(str(zip_path), "r") as zf:
                if "manifest.json" not in zf.namelist():
                    raise HTTPException(400, "Archive invalide : manifest.json absent.")
                manifest = json.loads(zf.read("manifest.json"))
                if not manifest.get("probare_export"):
                    raise HTTPException(400, "Archive invalide : ce n'est pas un export Probare.")
                zf.extractall(str(tmp_path))
        except zipfile.BadZipFile:
            raise HTTPException(400, "Fichier ZIP corrompu ou invalide.")

        projet_id = manifest.get("projet_id")
        if not projet_id:
            raise HTTPException(400, "manifest.json ne contient pas de projet_id.")

        dest_dir = DATA_DIR / projet_id
        if dest_dir.exists():
            raise HTTPException(
                409,
                f"Le dossier « {manifest.get('nom', projet_id)} » existe déjà. "
                "Supprimez-le d'abord pour le remplacer."
            )

        dest_dir.mkdir(parents=True, exist_ok=True)

        db_src = tmp_path / "audit.db"
        if not db_src.exists():
            shutil.rmtree(str(dest_dir), ignore_errors=True)
            raise HTTPException(400, "Archive invalide : audit.db absent.")
        shutil.copy2(str(db_src), str(dest_dir / "audit.db"))

        uploads_src = tmp_path / "uploads"
        if uploads_src.exists():
            shutil.copytree(str(uploads_src), str(dest_dir / "uploads"), dirs_exist_ok=True)

        dossier_src = tmp_path / "dossier_brut"
        if dossier_src.exists():
            shutil.copytree(str(dossier_src), str(dest_dir / "dossier_brut"), dirs_exist_ok=True)

    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(500, "Restauration échouée : impossible de lire le dossier restauré.")

    db.log(projet_id, "action_humaine", {
        "action": "restauration_zip",
        "source": archive.filename,
    })

    return {
        "restaure": True,
        "projet_id": projet_id,
        "projet": projet,
        "message": f"Dossier « {projet.get('nom')} » restauré avec succès.",
    }


@router.post("/projets/{projet_id}/archiver")
def archiver_projet(projet_id: str):
    """Archive un dossier clôturé — lecture seule, non modifiable."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if projet.get("archive"):
        return {"archive": True, "projet": projet, "message": "Dossier déjà archivé."}
    updated = db.update_projet(projet_id, {"archive": 1})
    db.log(projet_id, "action_humaine", {"action": "archivage_projet"})
    return {"archive": True, "projet": updated}


@router.post("/projets/{projet_id}/desarchiver")
def desarchiver_projet(projet_id: str):
    """Réouvre un dossier archivé pour modification."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    updated = db.update_projet(projet_id, {"archive": 0})
    db.log(projet_id, "action_humaine", {"action": "desarchivage_projet"})
    return {"archive": False, "projet": updated}


# ═══════════════════════════════════════════════════════════════════════════════
# PLANIFICATION (PLA-01 à PLA-08)
# ═══════════════════════════════════════════════════════════════════════════════

class FicheEntiteBody(BaseModel):
    forme_juridique: str | None = None
    date_creation_entreprise: str | None = None
    activites_principales: str | None = None
    marches_principaux: str | None = None
    dirigeants: list[dict] | None = None
    systeme_information: str | None = None
    effectif: int | None = None
    observations: str | None = None
    facteurs_risque_inherent: list[str] | None = None


class CalculVariationsBody(BaseModel):
    fichier_n_id: str
    fichier_n1_id: str | None = None


class CalculSeuilsBody(BaseModel):
    agregat_type: str = "total_bilan"
    taux_signification: float = 0.01
    taux_planification: float = 0.75


class RisqueBody(BaseModel):
    libelle: str
    description: str | None = None
    cycle: str | None = None
    niveau: str = "moyen"
    assertions: list[str] | None = None
    source: str = "manuel"
    commentaire: str | None = None


class UpdateRisqueBody(BaseModel):
    libelle: str | None = None
    description: str | None = None
    cycle: str | None = None
    niveau: str | None = None
    assertions: list[str] | None = None
    source: str | None = None
    valide_auditeur: bool | None = None
    commentaire: str | None = None


class UpdateProgrammeItemBody(BaseModel):
    libelle: str | None = None
    cycle: str | None = None
    controle_ref: str | None = None
    risque_id: str | None = None
    priorite: str | None = None
    statut: str | None = None
    notes: str | None = None


@router.get("/projets/{projet_id}/planification")
def get_planification(projet_id: str):
    """Retourne toutes les données de planification (fiche entité, variations, seuils, risques, programme)."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    plan = db.get_or_create_planification(projet_id)
    risques = db.list_risques(projet_id)
    programme = db.list_programme_items(projet_id)
    fichiers = db.list_fichiers_source(projet_id) if hasattr(db, "list_fichiers_source") else []
    # Tous les fichiers comptables sont proposés (balance, grand livre, etc.)
    # L'auditeur choisit lequel est N et lequel est N-1
    fichiers_comptables = [f for f in fichiers if f.get("type") not in ("annexe",)]
    return {
        "planification": plan,
        "risques": risques,
        "programme": programme,
        "balances_disponibles": fichiers_comptables,
    }


@router.patch("/projets/{projet_id}/planification/fiche-entite")
def update_fiche_entite(projet_id: str, body: FicheEntiteBody):
    """Met à jour la fiche de prise de connaissance de l'entité (PLA-01)."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    plan = db.update_planification(projet_id, data)
    db.log(projet_id, "action_humaine", {"action": "update_fiche_entite"})
    return {"planification": plan}


@router.post("/projets/{projet_id}/planification/calculer-variations")
def calculer_variations(projet_id: str, body: CalculVariationsBody):
    """Calcule les variations N/N-1 depuis les DonneeSourcee (PLA-02). Purement déterministe."""
    from ..planning.analytical import calculer_variations as calc_var, calculer_agregats
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    # Sauvegarder le choix du fichier N-1
    if body.fichier_n1_id:
        db.update_planification(projet_id, {"balance_n1_fichier_id": body.fichier_n1_id})

    seuil = projet.get("seuil_signification")
    variations = calc_var(
        db.conn, projet_id,
        fichier_n_id=body.fichier_n_id,
        fichier_n1_id=body.fichier_n1_id,
        seuil_signification=seuil,
    )
    agregats = calculer_agregats(db.conn, projet_id, body.fichier_n_id)

    plan = db.update_planification(projet_id, {
        "variations_json": variations,
        "agregats_json": agregats,
        "balance_n1_fichier_id": body.fichier_n1_id,
    })
    db.log(projet_id, "calcul_variations", {
        "nb_variations": len(variations),
        "nb_significatives": sum(1 for v in variations if v.get("significative")),
    })
    return {
        "variations": variations,
        "agregats": agregats,
        "planification": plan,
    }


@router.post("/projets/{projet_id}/planification/interpreter-variations")
def interpreter_variations(projet_id: str):
    """Sonnet interprète les variations analytiques significatives (PLA-03)."""
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    projet, anon_var = _llm_guard(db, projet_id)
    plan = db.get_or_create_planification(projet_id)
    variations = plan.get("variations_json") or []
    if not variations:
        raise HTTPException(400, "Aucune variation calculée. Lancez d'abord le calcul des variations.")

    significatives = [v for v in variations if v.get("significative")][:30]
    fiche = {k: plan.get(k) for k in (
        "forme_juridique", "activites_principales", "marches_principaux", "systeme_information"
    )}
    entites_var = [v for v in [projet.get("client"), projet.get("nif")] if v]
    contexte = {
        "exercice": projet.get("exercice"),
        "client": anon_var.pseudonymiser(projet.get("client") or "", entites_var) if entites_var else projet.get("client"),
        "seuil_signification": projet.get("seuil_signification"),
    }

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        result = llm.interpreter_variations_analytiques(
            significatives, fiche, projet.get("seuil_signification"), contexte
        )
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")

    now = datetime.now(timezone.utc).isoformat()
    plan = db.update_planification(projet_id, {
        "interpretation_variations": json.dumps(result),
        "variations_ia_horodatage": now,
    })
    return {"interpretation": result, "planification": plan}


@router.post("/projets/{projet_id}/planification/calculer-seuils")
def calculer_seuils(projet_id: str, body: CalculSeuilsBody):
    """Calcule les seuils depuis un agrégat et les applique au projet (PLA-04 + PLA-05)."""
    from ..planning.thresholds import calculer_seuils as calc_seuils
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")

    plan = db.get_or_create_planification(projet_id)
    agregats = plan.get("agregats_json") or {}
    agregat_valeur = agregats.get(body.agregat_type, 0.0)
    if not agregat_valeur:
        raise HTTPException(400, f"Agrégat '{body.agregat_type}' non disponible. Calculez d'abord les variations.")

    result = calc_seuils(
        body.agregat_type, agregat_valeur,
        body.taux_signification, body.taux_planification,
    )

    # Mettre à jour la planification et le projet
    db.update_planification(projet_id, {
        "agregat_type": body.agregat_type,
        "agregat_valeur": agregat_valeur,
        "taux_signification": body.taux_signification,
        "taux_planification": body.taux_planification,
        "seuil_calcule": result["seuil_signification"],
        "seuil_planification_calcule": result["seuil_planification"],
    })
    db.update_projet(projet_id, {
        "seuil_signification": result["seuil_signification"],
        "seuil_planification": result["seuil_planification"],
    })
    db.log(projet_id, "calcul_seuils", result)
    return {
        "seuils": result,
        "planification": db.get_or_create_planification(projet_id),
        "projet": db.get_projet(projet_id),
    }


# --- Risques ---

@router.get("/projets/{projet_id}/planification/risques")
def list_risques(projet_id: str):
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    return {"risques": db.list_risques(projet_id)}


@router.post("/projets/{projet_id}/planification/risques")
def create_risque(projet_id: str, body: RisqueBody):
    """Ajoute un risque manuellement."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    data = {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        **body.model_dump(),
        "issu_ia": 0,
        "valide_auditeur": 1,
    }
    risque = db.save_risque(data)
    db.log(projet_id, "action_humaine", {"action": "ajout_risque_manuel", "libelle": body.libelle})
    return {"risque": risque}


@router.post("/projets/{projet_id}/planification/proposer-risques")
def proposer_risques(projet_id: str):
    """Sonnet propose une cartographie de risques depuis la fiche entité + variations (PLA-06 + PLA-07)."""
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)
    plan = db.get_or_create_planification(projet_id)
    fiche = {k: plan.get(k) for k in (
        "forme_juridique", "date_creation_entreprise", "activites_principales",
        "marches_principaux", "dirigeants", "systeme_information", "effectif",
        "observations", "facteurs_risque_inherent"
    )}
    interp_raw = plan.get("interpretation_variations")
    zones_risque = []
    if interp_raw:
        try:
            interp = json.loads(interp_raw) if isinstance(interp_raw, str) else interp_raw
            zones_risque = interp.get("zones_risque", [])
        except Exception:
            pass

    existants = db.list_risques(projet_id)
    cycles = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        risques_proposes = llm.proposer_risques(fiche, zones_risque, cycles, existants)
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")

    # Insérer en base (non validés, source=ia)
    created = []
    for r in risques_proposes:
        data = {
            "id": str(uuid.uuid4()),
            "projet_id": projet_id,
            "libelle": r.get("libelle", "Risque IA"),
            "description": r.get("description"),
            "cycle": r.get("cycle"),
            "niveau": r.get("niveau", "moyen"),
            "assertions": r.get("assertions", []),
            "source": r.get("source", "ia"),
            "issu_ia": 1,
            "valide_auditeur": 0,
        }
        saved = db.save_risque(data)
        created.append(saved)

    db.log(projet_id, "appel_ia", {"action": "proposer_risques", "nb": len(created)})
    return {"risques_proposes": created, "total": len(created)}


@router.patch("/projets/{projet_id}/planification/risques/{risque_id}")
def update_risque(projet_id: str, risque_id: str, body: UpdateRisqueBody):
    db = _get_db(projet_id)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "valide_auditeur" in data:
        data["valide_auditeur"] = int(data["valide_auditeur"])
    risque = db.update_risque(risque_id, data)
    if not risque:
        raise HTTPException(404, "Risque introuvable.")
    return {"risque": risque}


@router.delete("/projets/{projet_id}/planification/risques/{risque_id}")
def delete_risque(projet_id: str, risque_id: str):
    db = _get_db(projet_id)
    db.delete_risque(risque_id)
    return {"deleted": True}


@router.post("/projets/{projet_id}/planification/risques/{risque_id}/reformuler")
def reformuler_risque(projet_id: str, risque_id: str):
    """Haiku reformule un risque manuel pour l'homogénéiser avec les risques IA."""
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    _llm_guard(db, projet_id)
    risque = db.get_risque(risque_id)
    if not risque:
        raise HTTPException(404, "Risque introuvable.")
    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        reformule = llm.reformuler_risque(risque)
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")

    if not reformule:
        return {"risque": risque}

    updates = {}
    if reformule.get("libelle"):
        updates["libelle"] = reformule["libelle"]
    if reformule.get("description"):
        updates["description"] = reformule["description"]
    if reformule.get("assertions"):
        updates["assertions"] = reformule["assertions"]

    updated = db.update_risque(risque_id, updates)
    db.log(projet_id, "appel_ia", {"action": "reformuler_risque", "risque_id": risque_id})
    return {"risque": updated}


# --- Programme de travail ---

@router.get("/projets/{projet_id}/planification/programme")
def get_programme(projet_id: str):
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    items = db.list_programme_items(projet_id)
    return {"programme": items, "total": len(items)}


@router.post("/projets/{projet_id}/planification/generer-programme")
def generer_programme(projet_id: str):
    """Sonnet génère le programme de travail depuis les risques validés (PLA-08)."""
    from ..llm.claude import ClaudeClient
    from ..controls.registry import REGISTRE
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)

    risques_valides = [r for r in db.list_risques(projet_id) if r.get("valide_auditeur")]
    if not risques_valides:
        raise HTTPException(400, "Aucun risque validé. Validez au moins un risque avant de générer le programme.")

    cycles = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    registry = [
        {"ref": c.ref, "libelle": c.libelle, "cycle": c.cycle, "nep_ref": c.nep_ref}
        for c in REGISTRE.values()
        if c.cycle in cycles
    ]

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        items_ia = llm.generer_programme_travail(risques_valides, cycles, registry)
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")

    # Remplacer le programme existant
    db.delete_programme_items(projet_id)

    risques_by_libelle = {r["libelle"]: r["id"] for r in risques_valides}
    created = []
    for item in items_ia:
        risque_libelle = item.get("risque_libelle")
        risque_id = risques_by_libelle.get(risque_libelle) if risque_libelle else None
        data = {
            "id": str(uuid.uuid4()),
            "projet_id": projet_id,
            "cycle": item.get("cycle"),
            "controle_ref": item.get("controle_ref"),
            "libelle": item.get("libelle", item.get("controle_ref", "Contrôle")),
            "risque_id": risque_id,
            "priorite": item.get("priorite", "normale"),
            "statut": item.get("statut", "inclus"),
            "notes": item.get("notes"),
            "issu_ia": 1,
        }
        saved = db.save_programme_item(data)
        created.append(saved)

    db.log(projet_id, "appel_ia", {"action": "generer_programme", "nb": len(created)})
    return {"programme": created, "total": len(created)}


@router.patch("/projets/{projet_id}/planification/programme/{item_id}")
def update_programme_item(projet_id: str, item_id: str, body: UpdateProgrammeItemBody):
    db = _get_db(projet_id)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    item = db.update_programme_item(item_id, data)
    if not item:
        raise HTTPException(404, "Élément introuvable.")
    return {"item": item}


@router.delete("/projets/{projet_id}/planification/programme/{item_id}")
def delete_programme_item(projet_id: str, item_id: str):
    db = _get_db(projet_id)
    db.delete_programme_item(item_id)
    return {"deleted": True}


@router.post("/projets/{projet_id}/planification/generer-synthese")
def generer_synthese(projet_id: str):
    """Sonnet génère la note de synthèse de planification qui justifie le programme de travail."""
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)

    plan = db.get_or_create_planification(projet_id)
    risques_valides = [r for r in db.list_risques(projet_id) if r.get("valide_auditeur")]
    programme_inclus = [p for p in db.list_programme_items(projet_id) if p.get("statut") == "inclus"]

    if not risques_valides:
        raise HTTPException(400, "Aucun risque validé — impossible de générer la synthèse.")

    interpretation = None
    raw = plan.get("interpretation_variations")
    if raw:
        if isinstance(raw, str):
            try:
                interpretation = json.loads(raw)
            except Exception:
                pass
        else:
            interpretation = raw

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        note = llm.generer_note_synthese(projet, plan, interpretation, risques_valides, programme_inclus)
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")

    note_str = json.dumps(note, ensure_ascii=False)
    db.update_planification(projet_id, {"note_synthese": note_str})
    db.log(projet_id, "appel_ia", {"action": "generer_note_synthese"})

    # Génération du .docx de planification
    try:
        all_risques  = db.list_risques(projet_id)
        all_programme = db.list_programme_items(projet_id)
        output_dir = DATA_DIR / projet_id / "exports"
        output_path = output_dir / f"note_planification_{projet_id[:8]}.docx"
        generer_note_planification(projet, plan, all_risques, all_programme, note, output_path)
        db.log(projet_id, "action_ia", {"action": "generer_note_planification_docx",
                                         "fichier": str(output_path)})
        docx_pret = True
    except Exception as e:
        db.log(projet_id, "erreur", {"action": "generer_note_planification_docx", "detail": str(e)})
        docx_pret = False

    return {"note_synthese": note, "docx_pret": docx_pret}


@router.get("/projets/{projet_id}/planification/telecharger-note")
def telecharger_note_planification(projet_id: str):
    """Retourne la Note de Planification .docx générée."""
    output_path = DATA_DIR / projet_id / "exports" / f"note_planification_{projet_id[:8]}.docx"
    if not output_path.exists():
        raise HTTPException(404, "Note de planification non encore générée. "
                                 "Lancez d'abord la génération du programme de travail.")
    db = _get_db(projet_id)
    db.log(projet_id, "action_humaine", {"action": "telecharger_note_planification"})
    projet = db.get_projet(projet_id)
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    exercice = (projet.get("exercice") or "N").replace("/", "-")
    filename = f"Note_Planification_{client_slug}_{exercice}.docx"
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )
