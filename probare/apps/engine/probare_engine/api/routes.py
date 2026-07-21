"""Routes FastAPI — toutes les routes de l'application."""
from __future__ import annotations
import os
import re
import uuid
import json
import threading
from collections import OrderedDict
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
    # Partagés
    controle_coherence_cycle,
    controle_soldes_anormaux,
    controle_montants_ronds,
    controle_cut_off,
    controle_doublons_factures,
    controle_concentration_compte,
    controle_ratio_avoirs,
    controle_creances_echues,
    # Nouveaux cycles
    controle_amortissement_manquant,
    controle_amort_excedent,
    controle_ratio_charges_sociales,
    controle_mensualite_paie,
    controle_tva_coherence,
    controle_mouvement_provisions,
    controle_coherence_resultat,
    # Utilitaires
    _group_rows,
    _filter_accounts,
    _get_amount,
    _get_str,
)
from ..provenance.models import DonneeSourcee
from ..reporting.export import (
    generer_dossier_travail, generer_tableau_exceptions,
    generer_note_planification, generer_rapport_audit,
    generer_memorandum_controle_comptes, ProvenanceError,
)
from ..anonymization.anonymizer import Anonymizer
from ..normes import norme, reformater_refs, lire_config, ecrire_config, \
    REFERENTIEL_ACTIF, REFERENTIELS, LIBELLES_REFERENTIEL, \
    REFERENTIELS_COMPTABLES, libelle_referentiel_comptable


router = APIRouter()
DATA_DIR = Path(os.environ.get("PROBARE_DATA_DIR", str(Path.home() / ".probare" / "projets")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_DIR = DATA_DIR.parent
CLIENTS_FILES_DIR = GLOBAL_DIR / "clients"
CLIENTS_FILES_DIR.mkdir(parents=True, exist_ok=True)
CLIENTS_DB_PATH = GLOBAL_DIR / "clients.db"

_db_cache: "OrderedDict[str, ProjectDB]" = OrderedDict()
_db_cache_lock = threading.Lock()
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
    _safe_id(projet_id, "Projet")
    with _db_cache_lock:
        db = _db_cache.get(projet_id)
        if db is not None:
            _db_cache.move_to_end(projet_id)  # LRU : marquer comme récemment utilisé
            return db
        # Éviction du moins récemment utilisé (jamais celui qu'on vient d'accéder)
        while len(_db_cache) >= _DB_CACHE_MAX:
            oldest_key, oldest_db = _db_cache.popitem(last=False)
            try:
                oldest_db.close()
            except Exception:
                pass
        db_path = DATA_DIR / projet_id / "audit.db"
        db = ProjectDB(db_path)
        db.connect()
        _db_cache[projet_id] = db
        return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Garde-fous chemins (anti path-traversal) ────────────────────────────────

_ID_RE = re.compile(r"\A[0-9a-fA-F-]{8,64}\Z")


def _safe_id(value: str, label: str = "identifiant") -> str:
    """
    Valide qu'un identifiant utilisé comme segment de chemin est bien un UUID/id
    inoffensif (hexadécimal + tirets). Bloque « .. », « / », chemins absolus, etc.
    """
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise HTTPException(400, f"{label} invalide.")
    return value


def _safe_filename(name: str | None, defaut: str = "upload") -> str:
    """
    Ne conserve que le nom de base d'un fichier fourni par le client (retire tout
    composant de chemin). Empêche l'écriture hors du répertoire cible via un nom
    du type « ../../evil ».
    """
    base = Path(name or "").name.strip()
    # Neutraliser les cas résiduels ("..", noms vides, séparateurs Windows)
    base = base.replace("\\", "").replace("/", "")
    if not base or base in (".", ".."):
        return f"{defaut}_{uuid.uuid4().hex[:8]}"
    return base


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
    # La balance N-1 (référencée en planification) sert aux procédures analytiques
    # uniquement : l'inclure ici fusionnerait N et N-1 dans les agrégats des
    # contrôles de l'exercice (faux écarts GL/Balance, soldes N doublés).
    n1_id = db.get_or_create_planification(projet_id).get("balance_n1_fichier_id")
    ids_balance = {f["id"] for f in fichiers
                   if _get_type_fichier(f) == "balance" and f["id"] != n1_id}
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


_ETATS_AVANT_CONTROLES = ("cadrage", "evaluation_ci", "ingestion")


def _exiger_etat_pour_controles(projet: dict) -> None:
    """Garde de pipeline : les contrôles supposent l'ingestion terminée et la
    planification posée (seuil, programme). Avant cela, leur exécution
    produirait des résultats incomplets versés au dossier (NEP 230)."""
    etat = projet.get("etat_courant") or ""
    if etat in _ETATS_AVANT_CONTROLES:
        raise HTTPException(
            400,
            f"Les contrôles ne peuvent pas être exécutés à l'étape « {etat} » : "
            "terminez l'ingestion et la planification (seuil de signification, "
            "programme de travail), puis passez aux travaux substantifs.",
        )


def _pieces_dedupliquees(rows: list, prefixes: tuple[str, ...] | None = None) -> list:
    """Une pièce par (numéro, date) pour l'analyse de séquence.

    Dans un grand livre en partie double, chaque pièce figure sur plusieurs
    lignes (débit/crédit) : ce ne sont pas des doublons. En revanche, le même
    numéro utilisé à DEUX dates différentes (double saisie) reste détecté.
    `prefixes` restreint aux écritures touchant les comptes du cycle.
    """
    vus: set[tuple[str, str]] = set()
    pieces = []
    for row in rows:
        p = row.get("numero_piece")
        if not p:
            continue
        if prefixes:
            c = row.get("compte")
            num = str(c.valeur or "") if c else ""
            if not num.startswith(prefixes):
                continue
        cle = (str(p.valeur or ""), _get_str(row, "date"))
        if cle in vus:
            continue
        vus.add(cle)
        pieces.append(p)
    return pieces


def _resoudre_fichiers_sources(exceptions: list[dict], donnees_all: list) -> None:
    """Pour chaque exception, résout sources (DonneeSourcee.id) → fichiers_sources (fichier_source_id)."""
    lookup = {d.id: d.fichier_source_id for d in donnees_all}
    for exc in exceptions:
        src_ids = exc.pop("sources", [])
        fichier_ids = list(dict.fromkeys(
            lookup[sid] for sid in (src_ids or []) if sid in lookup
        ))
        exc["fichiers_sources"] = fichier_ids


def _persister_controles(db, projet_id: str, resultats_total: list, exceptions_total: list,
                         cycle: str | None = None, ignores: list | None = None) -> list:
    """
    Persiste résultats et exceptions de façon idempotente.
    Persiste aussi les contrôles ignorés avec leur motif (NEP 230 : les procédures
    prévues non réalisées doivent être documentées dans le dossier).

    Une ré-exécution des contrôles d'un cycle ne doit plus accumuler de doublons :
    on purge d'abord les anciens résultats et les exceptions NON tranchées des
    contrôles qui viennent d'être relancés, puis on réécrit les nouveaux. Les
    exceptions déjà tranchées par l'auditeur sont préservées et ne sont pas recréées.

    Retourne la liste des exceptions effectivement enregistrées (les nouvelles),
    pour que l'interprétation IA ne porte que sur celles-ci.
    """
    refs = {r.get("controle_ref") for r in resultats_total if r.get("controle_ref")}
    refs |= {e.get("controle_ref") for e in exceptions_total if e.get("controle_ref")}
    refs = [r for r in refs if r]

    db.delete_resultats_by_refs(projet_id, refs)
    db.delete_open_exceptions_by_refs(projet_id, refs)
    deja_tranchees = db.tranchees_signatures(projet_id, refs)

    for r in resultats_total:
        db.save_resultat(r)

    enregistrees = []
    for e in exceptions_total:
        if (e.get("controle_ref"), e.get("description")) in deja_tranchees:
            continue  # déjà tranchée par l'auditeur — ne pas recréer un doublon
        db.save_exception(e)
        enregistrees.append(e)

    if cycle is not None:
        db.save_controles_ignores(projet_id, cycle, ignores or [])
    return enregistrees


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


# ─── Configuration cabinet (référentiel de normes) ───────────────────────────

class ConfigBody(BaseModel):
    referentiel_normes: str | None = None


@router.get("/config")
def get_config():
    """Configuration globale du cabinet.

    `referentiel_actif` est celui chargé au démarrage du moteur — c'est lui qui
    régit tous les affichages et livrables de la session en cours.
    `referentiel_normes` est celui écrit dans la configuration ; s'ils diffèrent,
    un redémarrage de l'application est nécessaire pour appliquer le changement.
    """
    config = lire_config()
    configure = str(config.get("referentiel_normes", "isa")).lower()
    if configure not in REFERENTIELS:
        configure = "isa"
    return {
        "referentiel_normes": configure,
        "referentiel_actif": REFERENTIEL_ACTIF,
        "redemarrage_requis": configure != REFERENTIEL_ACTIF,
        "referentiels_disponibles": [
            {"id": k, "libelle": LIBELLES_REFERENTIEL[k]} for k in REFERENTIELS
        ],
    }


@router.patch("/config")
def update_config(body: ConfigBody):
    """Modifie la configuration cabinet. Le changement de référentiel ne prend
    effet qu'au prochain démarrage de l'application (cohérence des livrables
    générés pendant la session en cours)."""
    updates: dict = {}
    if body.referentiel_normes is not None:
        ref = body.referentiel_normes.lower()
        if ref not in REFERENTIELS:
            raise HTTPException(400, f"Référentiel inconnu : {body.referentiel_normes}. "
                                     f"Valeurs admises : {sorted(REFERENTIELS)}.")
        updates["referentiel_normes"] = ref
    if not updates:
        raise HTTPException(400, "Aucun paramètre à modifier.")
    config = ecrire_config(updates)
    configure = config.get("referentiel_normes", "isa")
    return {
        "referentiel_normes": configure,
        "referentiel_actif": REFERENTIEL_ACTIF,
        "redemarrage_requis": configure != REFERENTIEL_ACTIF,
        "message": ("Référentiel enregistré. Redémarrez l'application pour "
                    "l'appliquer à l'ensemble du logiciel."
                    if configure != REFERENTIEL_ACTIF
                    else "Référentiel enregistré (déjà actif)."),
    }


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
    _safe_id(projet_id, "Projet")
    projet_dir = DATA_DIR / projet_id
    if not projet_dir.exists():
        raise HTTPException(404, "Projet introuvable.")
    with _db_cache_lock:
        db_cached = _db_cache.pop(projet_id, None)
    if db_cached is not None:
        try:
            db_cached.close()
        except Exception:
            pass
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
    # NEP 450 : confirmation explicite requise si le cumul des anomalies non
    # corrigées dépasse le seuil de signification au passage en génération.
    confirmer_depassement_seuil: bool = False


@router.post("/projets/{projet_id}/transition")
def post_transition(projet_id: str, body: TransitionBody):
    db = _get_db(projet_id)
    try:
        projet = transition(db, projet_id, body.vers, body.acteur,
                            confirmer_depassement_seuil=body.confirmer_depassement_seuil)
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
    nom_fichier = _safe_filename(fichier.filename, "upload")
    file_path = uploads_dir / nom_fichier
    content = await fichier.read()
    file_path.write_bytes(content)

    file_hash = hash_file(file_path)
    fichier_id = str(uuid.uuid4())

    # Anti-doublon : un même fichier comptable déjà importé fausserait les contrôles
    # (accumulation de DonneeSourcee). On refuse le ré-import à l'identique.
    if type_fichier != "annexe":
        existant = db.find_fichier_by_hash(projet_id, file_hash)
        if existant:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(
                409,
                f"Ce fichier a déjà été importé (« {existant.get('nom')} »). "
                "Supprimez l'import existant avant de le réimporter.",
            )

    # ── Documents annexes : stockage séparé, pas d'extraction DonneeSourcee ──
    if type_fichier == "annexe":
        annexe = db.save_annexe({
            "id": fichier_id,
            "projet_id": projet_id,
            "nom": nom_fichier,
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
        "nom": nom_fichier,
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


def _niveau_global_ci(evaluations: list[dict]) -> tuple[str, float]:
    """Niveau global = le pire niveau parmi les cycles évalués ; score = moyenne."""
    niveaux = [e.get("niveau_risque") for e in evaluations if e.get("niveau_risque")]
    scores = [e.get("score") for e in evaluations if e.get("score") is not None]
    if "eleve" in niveaux:
        niveau = "eleve"
    elif "moyen" in niveaux:
        niveau = "moyen"
    elif niveaux:
        niveau = "faible"
    else:
        niveau = "eleve"
    score = round(sum(scores) / len(scores), 2) if scores else 0.0
    return niveau, score


@router.get("/projets/{projet_id}/qci/synthese-globale")
def get_synthese_globale_ci(projet_id: str):
    """Retourne la synthèse globale CI déjà générée (ou null)."""
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    return {"synthese": db.get_qci_synthese_globale(projet_id)}


@router.post("/projets/{projet_id}/qci/synthese-globale/export")
def exporter_synthese_globale_ci(projet_id: str):
    """Exporte la synthèse globale CI déjà générée en .docx mis en forme (#2)."""
    from ..reporting.export import generer_synthese_ci_docx
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    synthese = db.get_qci_synthese_globale(projet_id)
    if not synthese:
        raise HTTPException(400, "Générez d'abord la synthèse globale avant de l'exporter.")
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"synthese_ci_{projet_id[:8]}.docx"
    generer_synthese_ci_docx(projet, synthese, output_path)
    db.log(projet_id, "action_humaine", {"action": "exporter_synthese_ci"})
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Synthese_controle_interne_{client_slug}.docx",
    )


@router.post("/projets/{projet_id}/qci/synthese-globale")
def generer_synthese_globale_ci(projet_id: str):
    """Sonnet rédige la synthèse globale de l'évaluation du contrôle interne
    à partir des évaluations par cycle déjà réalisées (#1)."""
    from ..controls.qci import QCI_PAR_CYCLE
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)

    evaluations = db.get_qci_evaluations(projet_id)
    if len(evaluations) < 1:
        raise HTTPException(400, "Évaluez au moins un cycle avant de générer la synthèse globale.")

    niveau_global, score_global = _niveau_global_ci(evaluations)

    # Réponses déterminantes : les « non » (chaque non = une faiblesse) porteuses
    # de risque, tous cycles confondus.
    determinantes = []
    for e in evaluations:
        cycle = e.get("cycle")
        questions = {q["id"]: q for q in QCI_PAR_CYCLE.get(cycle, [])}
        for rep in db.list_qci_reponses(projet_id, cycle):
            if rep.get("reponse") == "non":
                q = questions.get(rep.get("question_id"), {})
                determinantes.append({
                    "cycle": cycle,
                    "question": q.get("question", rep.get("question_id")),
                    "reponse": "non",
                    "risque_si_non": q.get("risque_si_non", ""),
                    "commentaire": rep.get("commentaire", ""),
                })

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        anon = Anonymizer()
        entites = [v for v in [projet.get("client"), projet.get("nif")] if v]
        ctx = {k: v for k, v in projet.items() if k not in ("client", "nif")}
        ctx["client"] = anon.pseudonymiser(projet.get("client") or "", entites) if entites else projet.get("client")
        note = llm.synthetiser_controle_interne_global(
            evaluations, determinantes, ctx, niveau_global, score_global)
    except Exception as e:
        db.log(projet_id, "erreur", {"action": "synthese_globale_ci", "detail": str(e)})
        raise HTTPException(500, f"Erreur LLM : {e}")

    matrice = [{"cycle": e.get("cycle"), "niveau_risque": e.get("niveau_risque"),
                "score": e.get("score")} for e in evaluations]
    synthese = {
        **note,
        "niveau_global": niveau_global,
        "score_global": score_global,
        "matrice": matrice,
        "nb_cycles_evalues": len(evaluations),
    }
    db.save_qci_synthese_globale(projet_id, synthese)
    db.log(projet_id, "appel_ia", {"action": "synthese_globale_ci",
                                   "niveau": niveau_global, "score": score_global})
    return {"synthese": synthese}


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
def get_registre(projet_id: str | None = None):
    from ..controls.registry import REGISTRE
    return {"controles": [
        {"ref": c.ref, "libelle": c.libelle, "nep_ref": c.nep_ref,
         "cycle": c.cycle, "description": c.description, "severite_defaut": c.severite_defaut}
        for c in REGISTRE.values()
    ]}


def _seuil_cycle(db, projet: dict, cycle: str) -> tuple[float, str | None]:
    """M2 (ISA 320) : seuil applicable aux contrôles d'un cycle.

    Retourne (seuil, note). Un seuil spécifique défini en planification pour le
    cycle remplace le seuil de signification global (il est toujours inférieur,
    la route de saisie l'impose). La note documente la substitution (NEP 230)."""
    seuil_global = float(projet.get("seuil_signification") or 0)
    plan = db.get_or_create_planification(projet["id"])
    specifiques = plan.get("seuils_specifiques_json") or {}
    cfg = specifiques.get(cycle) if isinstance(specifiques, dict) else None
    if cfg and float(cfg.get("seuil") or 0) > 0:
        seuil = float(cfg["seuil"])
        return seuil, (f"Seuil spécifique du cycle appliqué ({seuil:,.0f} au lieu de "
                       f"{seuil_global:,.0f}) — {cfg.get('justification', '')}")
    return seuil_global, None


def _seuils_ci(db, projet_id: str, cycle: str) -> dict:
    """
    Retourne les multiplicateurs de sensibilité selon le niveau de risque CI du cycle.

    NEP 330 : on ne peut alléger les travaux substantifs en s'appuyant sur le
    contrôle interne qu'après avoir testé son efficacité. Le QCI étant purement
    déclaratif (aucun test de procédures n'est implémenté), le facteur est
    PLAFONNÉ à 1.0 : un CI jugé mauvais durcit les seuils (0.5), un CI jugé bon
    ne les relâche jamais.
    """
    evaluations = {e["cycle"]: e for e in db.get_qci_evaluations(projet_id)}
    eval_cycle = evaluations.get(cycle, {})
    niveau = (eval_cycle.get("niveau_risque") or "").lower()

    if niveau == "eleve":
        return {"facteur": 0.5, "note_ci": "CI élevé — seuils de détection réduits (approche substantive renforcée)"}
    elif niveau == "faible":
        return {"facteur": 1.0, "note_ci": "CI faible (déclaratif) — seuils standards maintenus : "
                                           f"aucun allègement sans test d'efficacité du CI ({norme(330)})"}
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
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    if "tresorerie" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle trésorerie non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "tresorerie")
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
        # Séquence globale du journal : une pièce par (numéro, date) — la
        # partie double répète chaque pièce sur ses lignes débit/crédit.
        pieces = _pieces_dedupliquees(rows_gl)
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
            projet_id, "TRESOR-ROUND", rows_pour_round, ("5",), sensibilite=ci_facteur
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. TRESOR-CUT-OFF : concentration d'écritures en fin d'exercice ──
    if _check("TRESOR-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "TRESOR-CUT-OFF", rows_gl, ("5",), exercice, sensibilite=ci_facteur
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. TRESOR-VARIATION : variations N/N-1 (si seuil défini et N-1 disponible) ──
    if seuil <= 0:
        _skip("TRESOR-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
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
                # Source = la donnée MONTANT (le numéro de compte n'est pas un solde)
                if row.get("solde"):
                    solde_compta_src = row["solde"]
                elif _get_amount(row, "debit") >= _get_amount(row, "credit"):
                    solde_compta_src = row.get("debit")
                else:
                    solde_compta_src = row.get("credit")

        # Extraire le solde du relevé : solde de la DERNIÈRE ligne datée
        # (le solde de clôture), et non « le plus grand montant du fichier ».
        solde_releve_val = 0.0
        solde_releve_src = None
        rows_releve = _group_rows(rows_releve_ds) if rows_releve_ds else []
        lignes_soldees = [(r, _get_str(r, "date")) for r in rows_releve if r.get("solde")]
        if lignes_soldees:
            lignes_soldees.sort(key=lambda x: x[1])  # dates ISO : tri lexical = tri chronologique
            derniere = lignes_soldees[-1][0]
            solde_releve_src = derniere["solde"]
            solde_releve_val = float(solde_releve_src.valeur or 0)
        else:
            # Repli : ancien comportement (relevé sans colonne solde)
            montants_releve = [d for d in rows_releve_ds if d.type == "montant"]
            if montants_releve:
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
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="tresorerie", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_tresorerie",
        "note_seuil": note_seuil,
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
    _exiger_etat_pour_controles(projet)

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
    seuil, note_seuil = _seuil_cycle(db, projet, "achats")
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
        # Pièces des écritures du cycle uniquement, dédupliquées (partie double).
        # Si la numérotation est partagée entre journaux, le contrôle neutralise
        # de lui-même l'analyse des trous (heuristique de couverture).
        pieces = _pieces_dedupliquees(rows_pour_mvt, PREFIXES_CYCLE)
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
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. ACHAT-AVOIR : crédits sur comptes de charges (60x…), hors 603x
    # (variations de stocks, créditrices par nature) ──
    if _check("ACHAT-AVOIR"):
        res, exc = controle_ratio_avoirs(
            projet_id, "ACHAT-AVOIR", rows_pour_mvt, PREFIXES_ACHATS, sens_avoir="credit",
            sensibilite=ci_facteur, exclure_prefixes=("603",),
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. ACHAT-ROUND ──
    if _check("ACHAT-ROUND"):
        res, exc = controle_montants_ronds(
            projet_id, "ACHAT-ROUND", rows_pour_mvt, PREFIXES_ACHATS,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 8. ACHAT-CUT-OFF ──
    if _check("ACHAT-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "ACHAT-CUT-OFF", rows_pour_mvt, PREFIXES_ACHATS, exercice,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 9. ACHAT-VARIATION ──
    if seuil <= 0:
        _skip("ACHAT-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
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
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="achats", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_achats",
        "note_seuil": note_seuil,
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
    _exiger_etat_pour_controles(projet)

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
    seuil, note_seuil = _seuil_cycle(db, projet, "ventes")
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
        # Pièces des écritures du cycle uniquement, dédupliquées (partie double).
        pieces = _pieces_dedupliquees(rows_pour_mvt, PREFIXES_CYCLE)
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
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 6. VENTE-AVOIR : débits sur comptes de produits (70x…) ──
    if _check("VENTE-AVOIR"):
        res, exc = controle_ratio_avoirs(
            projet_id, "VENTE-AVOIR", rows_pour_mvt, PREFIXES_VENTES, sens_avoir="debit",
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 7. VENTE-ROUND ──
    if _check("VENTE-ROUND"):
        res, exc = controle_montants_ronds(
            projet_id, "VENTE-ROUND", rows_pour_mvt, PREFIXES_VENTES,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 8. VENTE-CUT-OFF ──
    if _check("VENTE-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "VENTE-CUT-OFF", rows_pour_mvt, PREFIXES_VENTES, exercice,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 9. VENTE-CREANCES-ECHUES ──
    if _check("VENTE-CREANCES-ECHUES"):
        res, exc = controle_creances_echues(
            projet_id, rows_pour_mvt, exercice, sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 10. VENTE-VARIATION ──
    if seuil <= 0:
        _skip("VENTE-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
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
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="ventes", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_ventes",
        "note_seuil": note_seuil,
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


# ─── Cycle Immobilisations ────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/immobilisations")
def run_controles_immobilisations(projet_id: str, body: dict = {}):
    """Lance les 5 contrôles déterministes du cycle immobilisations."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or []
    if "immobilisations" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle immobilisations non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "immobilisations")
    exercice = projet.get("exercice")
    ci = _seuils_ci(db, projet_id, "immobilisations")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_IMO_BRUT = ("20", "21", "22", "23", "24", "25", "26", "27")
    PREFIXES_IMO_ALL = PREFIXES_IMO_BRUT + ("28",)

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. IMO-GL-COHER ──
    if _check("IMO-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "IMO-GL-COHER", rows_gl, rows_balance, PREFIXES_IMO_ALL,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. IMO-AMORTISSEMENT ──
    if _check("IMO-AMORTISSEMENT"):
        res, exc = controle_amortissement_manquant(projet_id, rows_pour_solde)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 3. IMO-AMORT-EXCEDENT ──
    if _check("IMO-AMORT-EXCEDENT"):
        res, exc = controle_amort_excedent(projet_id, rows_pour_solde)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 4. IMO-SOLDE-ANORMAL ──
    if _check("IMO-SOLDE-ANORMAL"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "IMO-SOLDE-ANORMAL",
            rows_pour_solde, PREFIXES_IMO_BRUT, sens_normal="debit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 5. IMO-VARIATION ──
    if seuil <= 0:
        _skip("IMO-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
    if seuil > 0 and _check("IMO-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_IMO_ALL)
        if soldes_n:
            plan_imo = db.get_or_create_planification(projet_id)
            n1_id_imo = plan_imo.get("balance_n1_fichier_id")
            if n1_id_imo:
                donnees_n1_imo = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_imo)]
                rows_n1_imo = _group_rows(donnees_n1_imo) if donnees_n1_imo else []
                soldes_n1_imo = _aggreger_soldes_nets(rows_n1_imo, PREFIXES_IMO_ALL)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_imo, seuil * ci_facteur, "IMO-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("IMO-VARIATION", "Balance N-1 non renseignée.")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="immobilisations", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_immobilisations",
        "note_seuil": note_seuil,
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": db.list_exceptions(projet_id),
        "controles_ignores": ignores,
    }


# ─── Cycle Stocks ─────────────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/stocks")
def run_controles_stocks(projet_id: str, body: dict = {}):
    """Lance les 5 contrôles déterministes du cycle stocks."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or []
    if "stocks" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle stocks non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "stocks")
    exercice = projet.get("exercice")
    ci = _seuils_ci(db, projet_id, "stocks")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_STOCK = ("3",)

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. STOCK-GL-COHER ──
    if _check("STOCK-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "STOCK-GL-COHER", rows_gl, rows_balance, PREFIXES_STOCK,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. STOCK-SOLDE-ANORMAL ──
    if _check("STOCK-SOLDE-ANORMAL"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "STOCK-SOLDE-ANORMAL",
            rows_pour_solde, PREFIXES_STOCK, sens_normal="debit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 3. STOCK-ROUND ──
    if _check("STOCK-ROUND"):
        res, exc = controle_montants_ronds(
            projet_id, "STOCK-ROUND", rows_pour_mvt, PREFIXES_STOCK,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 4. STOCK-CUT-OFF ──
    if _check("STOCK-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "STOCK-CUT-OFF", rows_pour_mvt, PREFIXES_STOCK, exercice,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. STOCK-VARIATION ──
    if seuil <= 0:
        _skip("STOCK-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
    if seuil > 0 and _check("STOCK-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_STOCK)
        if soldes_n:
            plan_stk = db.get_or_create_planification(projet_id)
            n1_id_stk = plan_stk.get("balance_n1_fichier_id")
            if n1_id_stk:
                donnees_n1_stk = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_stk)]
                rows_n1_stk = _group_rows(donnees_n1_stk) if donnees_n1_stk else []
                soldes_n1_stk = _aggreger_soldes_nets(rows_n1_stk, PREFIXES_STOCK)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_stk, seuil * ci_facteur, "STOCK-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("STOCK-VARIATION", "Balance N-1 non renseignée.")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="stocks", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_stocks",
        "note_seuil": note_seuil,
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": db.list_exceptions(projet_id),
        "controles_ignores": ignores,
    }


# ─── Cycle Paie / Personnel ───────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/paie")
def run_controles_paie(projet_id: str, body: dict = {}):
    """Lance les 5 contrôles déterministes du cycle paie/personnel."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or []
    if "paie" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle paie/personnel non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "paie")
    exercice = projet.get("exercice")
    ci = _seuils_ci(db, projet_id, "paie")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_CHARGES = ("64",)
    PREFIXES_DETTES = ("42",)
    PREFIXES_CYCLE = PREFIXES_CHARGES + PREFIXES_DETTES

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. PAIE-GL-COHER ──
    if _check("PAIE-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "PAIE-GL-COHER", rows_gl, rows_balance, PREFIXES_CYCLE,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. PAIE-SOLDE-ANORMAL ──
    if _check("PAIE-SOLDE-ANORMAL"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "PAIE-SOLDE-ANORMAL",
            rows_pour_solde, PREFIXES_DETTES, sens_normal="credit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 3. PAIE-RATIO-SOCIAL ──
    if _check("PAIE-RATIO-SOCIAL"):
        res, exc = controle_ratio_charges_sociales(projet_id, rows_pour_mvt)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 4. PAIE-MENSUALITE ──
    if _check("PAIE-MENSUALITE"):
        res, exc = controle_mensualite_paie(projet_id, rows_pour_mvt, exercice)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. PAIE-VARIATION ──
    if seuil <= 0:
        _skip("PAIE-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
    if seuil > 0 and _check("PAIE-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_CHARGES)
        if soldes_n:
            plan_paie = db.get_or_create_planification(projet_id)
            n1_id_paie = plan_paie.get("balance_n1_fichier_id")
            if n1_id_paie:
                donnees_n1_paie = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_paie)]
                rows_n1_paie = _group_rows(donnees_n1_paie) if donnees_n1_paie else []
                soldes_n1_paie = _aggreger_soldes_nets(rows_n1_paie, PREFIXES_CHARGES)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_paie, seuil * ci_facteur, "PAIE-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("PAIE-VARIATION", "Balance N-1 non renseignée.")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="paie", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_paie",
        "note_seuil": note_seuil,
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": db.list_exceptions(projet_id),
        "controles_ignores": ignores,
    }


# ─── Cycle Impôts / Taxes ─────────────────────────────────────────────────────

@router.post("/projets/{projet_id}/controles/impots")
def run_controles_impots(projet_id: str, body: dict = {}):
    """Lance les 5 contrôles déterministes du cycle impôts/taxes."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or []
    if "impots" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle impôts/taxes non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "impots")
    exercice = projet.get("exercice")
    ci = _seuils_ci(db, projet_id, "impots")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_TVA = ("44",)
    PREFIXES_CHARGES_FISC = ("63",)
    PREFIXES_CYCLE = PREFIXES_TVA + PREFIXES_CHARGES_FISC

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. TAXE-GL-COHER ──
    if _check("TAXE-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "TAXE-GL-COHER", rows_gl, rows_balance, PREFIXES_CYCLE,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. TAXE-TVA-COHERENCE ──
    if _check("TAXE-TVA-COHERENCE"):
        res, exc = controle_tva_coherence(projet_id, rows_pour_solde)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 3. TAXE-SOLDE-ANORMAL : TVA collectée (4457x) doit être créditrice ──
    if _check("TAXE-SOLDE-ANORMAL"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "TAXE-SOLDE-ANORMAL",
            rows_pour_solde, ("4457",), sens_normal="credit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 4. TAXE-CUT-OFF ──
    if _check("TAXE-CUT-OFF"):
        res, exc = controle_cut_off(
            projet_id, "TAXE-CUT-OFF", rows_pour_mvt, PREFIXES_CHARGES_FISC, exercice,
            sensibilite=ci_facteur,
        )
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. TAXE-VARIATION ──
    if seuil <= 0:
        _skip("TAXE-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
    if seuil > 0 and _check("TAXE-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_CHARGES_FISC)
        if soldes_n:
            plan_taxe = db.get_or_create_planification(projet_id)
            n1_id_taxe = plan_taxe.get("balance_n1_fichier_id")
            if n1_id_taxe:
                donnees_n1_taxe = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_taxe)]
                rows_n1_taxe = _group_rows(donnees_n1_taxe) if donnees_n1_taxe else []
                soldes_n1_taxe = _aggreger_soldes_nets(rows_n1_taxe, PREFIXES_CHARGES_FISC)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_taxe, seuil * ci_facteur, "TAXE-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("TAXE-VARIATION", "Balance N-1 non renseignée.")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="impots", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_impots",
        "note_seuil": note_seuil,
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": db.list_exceptions(projet_id),
        "controles_ignores": ignores,
    }


# ─── Cycle Capitaux propres et provisions ─────────────────────────────────────

@router.post("/projets/{projet_id}/controles/capitaux-propres")
def run_controles_capitaux_propres(projet_id: str, body: dict = {}):
    """Lance les 5 contrôles déterministes du cycle capitaux propres et provisions."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles_couverts = projet.get("cycles_couverts") or []
    if "capitaux_propres" not in cycles_couverts:
        return {"nb_controles": 0, "nb_exceptions": 0, "resultats": [],
                "exceptions": [], "cycle_ignore": True,
                "message": "Cycle capitaux propres non sélectionné au cadrage."}

    donnees_all, rows_gl, rows_balance, ids_gl, ids_balance, ids_releve = \
        _get_donnees_segmentees(db, projet_id)
    if not donnees_all:
        raise HTTPException(400, "Aucune donnée importée.")

    seuil, note_seuil = _seuil_cycle(db, projet, "capitaux_propres")
    ci = _seuils_ci(db, projet_id, "capitaux_propres")
    ci_facteur = ci["facteur"]
    resultats_total, exceptions_total, ignores = [], [], []

    PREFIXES_CP = ("10", "11", "12", "13")
    PREFIXES_PROV = ("15",)
    PREFIXES_ALL = PREFIXES_CP + PREFIXES_PROV

    rows_pour_solde = rows_balance if rows_balance else (rows_gl if rows_gl else [])
    rows_pour_mvt = rows_gl if rows_gl else (rows_balance if rows_balance else [])

    def _skip(ref: str, raison: str):
        ignores.append({"controle_ref": ref, "raison": raison})

    def _check(ref: str) -> bool:
        ok, msg = _preconditions_check(ref, ids_gl, ids_balance, ids_releve)
        if not ok:
            _skip(ref, msg)
        return ok

    # ── 1. CP-GL-COHER ──
    if _check("CP-GL-COHER"):
        ress, excs = controle_coherence_cycle(
            projet_id, "CP-GL-COHER", rows_gl, rows_balance, PREFIXES_ALL,
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 2. CP-RESULTAT-COHERENCE ──
    if _check("CP-RESULTAT-COHERENCE"):
        res, exc = controle_coherence_resultat(projet_id, rows_pour_solde)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 3. CP-SOLDE-ANORMAL : capitaux propres (10x-13x) doivent être créditeurs ──
    if _check("CP-SOLDE-ANORMAL"):
        ress, excs = controle_soldes_anormaux(
            projet_id, "CP-SOLDE-ANORMAL",
            rows_pour_solde, PREFIXES_CP, sens_normal="credit",
        )
        resultats_total.extend(ress)
        exceptions_total.extend(excs)

    # ── 4. CP-PROVISION-MOUVEMENT ──
    if _check("CP-PROVISION-MOUVEMENT"):
        res, exc = controle_mouvement_provisions(projet_id, rows_pour_mvt)
        resultats_total.append(res)
        if exc:
            exceptions_total.append(exc)

    # ── 5. CP-VARIATION ──
    if seuil <= 0:
        _skip("CP-VARIATION", f"Seuil de signification non défini — contrôle de variation non exécuté ({norme(320)}).")
    if seuil > 0 and _check("CP-VARIATION"):
        soldes_n = _aggreger_soldes_nets(rows_pour_solde, PREFIXES_CP)
        if soldes_n:
            plan_cp = db.get_or_create_planification(projet_id)
            n1_id_cp = plan_cp.get("balance_n1_fichier_id")
            if n1_id_cp:
                donnees_n1_cp = [_to_donnee(d) for d in db.get_donnees_by_fichier(n1_id_cp)]
                rows_n1_cp = _group_rows(donnees_n1_cp) if donnees_n1_cp else []
                soldes_n1_cp = _aggreger_soldes_nets(rows_n1_cp, PREFIXES_CP)
                ress, excs = controle_variations(
                    projet_id, soldes_n, soldes_n1_cp, seuil * ci_facteur, "CP-VARIATION",
                )
                resultats_total.extend(ress)
                exceptions_total.extend(excs)
            else:
                _skip("CP-VARIATION", "Balance N-1 non renseignée.")

    _resoudre_fichiers_sources(exceptions_total, donnees_all)
    exceptions_total = _persister_controles(db, projet_id, resultats_total, exceptions_total,
                                           cycle="capitaux_propres", ignores=ignores)

    db.log(projet_id, "transition_etat", {
        "action": "controles_capitaux_propres",
        "note_seuil": note_seuil,
        "nb_resultats": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "nb_ignores": len(ignores),
    })
    _auto_interpreter(db, projet_id, projet, exceptions_total)

    return {
        "nb_controles": len(resultats_total),
        "nb_exceptions": len(exceptions_total),
        "resultats": resultats_total,
        "exceptions": db.list_exceptions(projet_id),
        "controles_ignores": ignores,
    }


# Cycle (clé projet) → fonction de contrôle. La clé « capitaux_propres » du
# projet correspond à la route « capitaux-propres ».
_RUN_CONTROLES = {
    "tresorerie": lambda pid: run_controles_tresorerie(pid, {}),
    "achats": lambda pid: run_controles_achats(pid, {}),
    "ventes": lambda pid: run_controles_ventes(pid, {}),
    "immobilisations": lambda pid: run_controles_immobilisations(pid, {}),
    "stocks": lambda pid: run_controles_stocks(pid, {}),
    "paie": lambda pid: run_controles_paie(pid, {}),
    "impots": lambda pid: run_controles_impots(pid, {}),
    "capitaux_propres": lambda pid: run_controles_capitaux_propres(pid, {}),
}


@router.post("/projets/{projet_id}/controles/lancer-tout")
def run_tous_controles(projet_id: str, body: dict = {}):
    """Lance en une fois les contrôles de tous les cycles couverts par la mission (#7).

    Chaque cycle est exécuté via sa propre logique (idempotente) ; on renvoie un
    récapitulatif par cycle plus l'agrégat, et la liste consolidée des exceptions.
    """
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    _exiger_etat_pour_controles(projet)

    cycles = projet.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
    par_cycle = []
    total_res = total_exc = 0
    for cycle in cycles:
        runner = _RUN_CONTROLES.get(cycle)
        if not runner:
            continue
        try:
            res = runner(projet_id)
        except HTTPException as e:
            par_cycle.append({"cycle": cycle, "erreur": e.detail})
            continue
        if res.get("cycle_ignore"):
            par_cycle.append({"cycle": cycle, "cycle_ignore": True,
                              "message": res.get("message")})
            continue
        nb_res = res.get("nb_controles", 0)
        nb_exc = res.get("nb_exceptions", 0)
        total_res += nb_res
        total_exc += nb_exc
        par_cycle.append({"cycle": cycle, "nb_controles": nb_res,
                          "nb_exceptions": nb_exc,
                          "nb_ignores": len(res.get("controles_ignores", []))})

    db.log(projet_id, "action_humaine", {"action": "controles_lancer_tout",
                                         "cycles": cycles, "nb_exceptions_total": total_exc})
    return {
        "par_cycle": par_cycle,
        "nb_controles_total": total_res,
        "nb_exceptions_total": total_exc,
        "exceptions": db.list_exceptions(projet_id),
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
    # NEP 450 : typologie de la résolution
    # 'corrigee'       — anomalie corrigée par le client
    # 'sans_incidence' — explication obtenue, aucune anomalie avérée
    # 'non_corrigee'   — anomalie maintenue ; montant_incidence requis (> 0)
    # 'insignifiante'  — anomalie manifestement insignifiante (M2) ; montant requis,
    #                    inférieur au seuil d'insignifiance ; hors cumul mais au dossier
    type_resolution: str | None = None
    montant_incidence: float | None = None


_TYPES_RESOLUTION = {"corrigee", "sans_incidence", "non_corrigee", "insignifiante"}


@router.post("/projets/{projet_id}/exceptions/{exception_id}/trancher")
def trancher_exception(projet_id: str, exception_id: str, body: TrancheeBody):
    db = _get_db(projet_id)
    if body.type_resolution is not None and body.type_resolution not in _TYPES_RESOLUTION:
        raise HTTPException(400, f"type_resolution invalide : {body.type_resolution}. "
                                 f"Valeurs admises : {sorted(_TYPES_RESOLUTION)}.")
    if body.type_resolution == "non_corrigee" and not (body.montant_incidence and body.montant_incidence > 0):
        raise HTTPException(400, "Une anomalie non corrigée doit porter un montant d'incidence "
                                 f"positif ({norme(450)}) pour entrer dans le cumul comparé au seuil.")
    if body.type_resolution == "insignifiante":
        projet = db.get_projet(projet_id)
        seuil_insign = float((projet or {}).get("seuil_insignifiance") or 0)
        if seuil_insign <= 0:
            raise HTTPException(400, "Aucun seuil d'anomalies manifestement insignifiantes n'est "
                                     f"défini ({norme(450)}). Calculez les seuils en Planification "
                                     "avant d'utiliser cette résolution.")
        if not (body.montant_incidence and body.montant_incidence > 0):
            raise HTTPException(400, "Une anomalie insignifiante doit porter son montant "
                                     "(positif) pour être documentée au dossier.")
        if body.montant_incidence > seuil_insign:
            raise HTTPException(400, f"Le montant ({body.montant_incidence:,.0f}) dépasse le seuil "
                                     f"d'insignifiance ({seuil_insign:,.0f}) : cette anomalie ne peut "
                                     f"pas être écartée comme manifestement insignifiante ({norme(450)}). "
                                     "Tranchez-la comme corrigée, sans incidence ou non corrigée.")
        exc_courante = db.get_exception(exception_id)
        if exc_courante and exc_courante.get("severite") == "critique":
            raise HTTPException(400, "Une exception critique ne peut pas être écartée comme "
                                     "manifestement insignifiante : elle exige un tranchement motivé.")
    montant = (body.montant_incidence
               if body.type_resolution in ("non_corrigee", "insignifiante") else None)
    exc = db.trancher_exception(
        exception_id, body.decision_humaine, body.decideur,
        type_resolution=body.type_resolution, montant_incidence=montant,
    )
    if not exc:
        raise HTTPException(404, "Exception introuvable.")
    db.log(projet_id, "action_humaine", {
        "action": "trancher_exception",
        "exception_id": exception_id,
        "decideur": body.decideur,
        "type_resolution": body.type_resolution,
        "montant_incidence": montant,
        "decision": body.decision_humaine[:100],
    })
    return exc


@router.get("/projets/{projet_id}/exceptions/synthese")
def synthese_exceptions(projet_id: str):
    """Synthèse NEP 450 : cumul des anomalies non corrigées comparé aux seuils."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    synthese = db.synthese_anomalies(
        projet_id,
        projet.get("seuil_signification"),
        projet.get("seuil_planification"),
    )
    # M2 : le seuil d'insignifiance accompagne la synthèse (affichage UI, dossier)
    synthese["seuil_insignifiance"] = projet.get("seuil_insignifiance")
    return synthese


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

    # Une régénération remplace la feuille précédente du cycle, elle ne s'y
    # ajoute pas — sans quoi le dossier de travail et le mémorandum accumulent
    # des doublons (dont d'anciennes versions en échec de génération).
    db.delete_feuilles_par_cycle(projet_id, cycle)

    feuille = {
        "id": str(uuid.uuid4()),
        "projet_id": projet_id,
        "cycle": cycle,
        "contenu_redige": result.get("contenu", ""),
        "sources": [r["id"] for r in (resultats_cycle or resultats)[:20]],
        "nep_ref": norme(230),
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
    controles_ignores = db.list_controles_ignores(projet_id)
    synthese = db.synthese_anomalies(
        projet_id, projet.get("seuil_signification"), projet.get("seuil_planification"),
    )
    synthese["seuil_insignifiance"] = projet.get("seuil_insignifiance")

    # M3 : état des diligences ISA de périphérie versé au dossier (NEP 230)
    diligences_dossier = get_peripherie(projet_id).get("diligences", [])

    # M1 : état récapitulatif des ajustements + balance ajustée (ISA 450)
    from ..ajustements import synthese_ajustements
    ecritures_dossier = [_enrichir_ecriture(e) for e in db.list_ecritures_ajustement(projet_id)]
    ajustements_dossier = None
    if ecritures_dossier:
        ajustements_dossier = {
            "ecritures": ecritures_dossier,
            "synthese": synthese_ajustements(ecritures_dossier),
            "balance_ajustee": get_balance_ajustee(projet_id),
        }

    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"dossier_travail_{projet_id[:8]}.docx"

    try:
        generer_dossier_travail(projet, resultats, exceptions, feuilles, output_path,
                                controles_ignores=controles_ignores,
                                synthese_anomalies=synthese,
                                diligences_peripherie=diligences_dossier,
                                ajustements=ajustements_dossier)
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


@router.post("/projets/{projet_id}/qci/exporter-questionnaire")
def exporter_questionnaire_vierge(projet_id: str):
    """Génère le questionnaire de contrôle interne vierge .docx à imprimer (#2)."""
    from ..reporting.export import generer_questionnaire_vierge
    from ..controls.qci import QCI_PAR_CYCLE
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    cycles = projet.get("cycles_couverts") or list(QCI_PAR_CYCLE.keys())
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"questionnaire_ci_{projet_id[:8]}.docx"
    generer_questionnaire_vierge(projet, QCI_PAR_CYCLE, cycles, output_path)
    db.log(projet_id, "action_humaine", {"action": "exporter_questionnaire_ci"})
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Questionnaire_CI_{client_slug}.docx",
    )


@router.post("/projets/{projet_id}/exporter-diligences")
def exporter_diligences(projet_id: str, seulement_ouvertes: bool = True):
    """Génère la demande de diligences .docx à présenter au client (#9)."""
    from ..reporting.export import generer_demande_diligences
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    exceptions = db.list_exceptions(projet_id)
    # Carte des sources de détection (#3) : fichier_source_id → fichier_source
    fichiers_map = {f["id"]: f for f in db.list_fichiers_source(projet_id)}
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"diligences_{projet_id[:8]}.docx"
    generer_demande_diligences(projet, exceptions, output_path,
                               seulement_ouvertes=seulement_ouvertes,
                               fichiers_map=fichiers_map)
    db.log(projet_id, "action_humaine", {"action": "exporter_diligences"})
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Demande_diligences_{client_slug}.docx",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE RAPPORT D'AUDIT — synthèse de mission, opinion (Opus), livrables finaux
# ═══════════════════════════════════════════════════════════════════════════════

_LABELS_PHASES = {
    "cadrage": "Cadrage", "evaluation_ci": "Contrôle interne", "ingestion": "Ingestion",
    "planification": "Planification", "travaux_substantifs": "Travaux substantifs",
    "revue": "Revue des exceptions", "generation": "Dossier de travail",
    "opinion": "Rapport d'audit",
}

_MEDIA_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _synthese_mission(db: ProjectDB, projet_id: str, projet: dict) -> dict:
    """Récapitulatif déterministe de toutes les phases de la mission.

    100 % calculé par le code depuis la base (aucun chiffre LLM). Sert à la fois
    au tableau de bord de fin de mission et d'entrée à la proposition d'opinion.
    """
    plan = db.get_or_create_planification(projet_id)
    fichiers = db.list_fichiers_source(projet_id)
    docs_bruts = db.list_documents_bruts(projet_id)
    annexes = db.list_annexes(projet_id)
    qci_evals = db.get_qci_evaluations(projet_id)
    qci_glob = db.get_qci_synthese_globale(projet_id) or {}
    risques = db.list_risques(projet_id)
    programme = db.list_programme_items(projet_id)
    resultats = db.list_resultats(projet_id)
    exceptions = db.list_exceptions(projet_id)
    circ = db.list_circularisations(projet_id)
    sondages = db.list_sondages(projet_id)
    feuilles = db.list_feuilles(projet_id)
    ignores = db.list_controles_ignores(projet_id)
    anomalies = db.synthese_anomalies(
        projet_id, projet.get("seuil_signification"), projet.get("seuil_planification"))
    opinion = db.get_opinion(projet_id)

    def _cnt(items, pred):
        return sum(1 for x in items if pred(x))

    circ_par_statut: dict[str, int] = {}
    for c in circ:
        circ_par_statut[c.get("statut", "?")] = circ_par_statut.get(c.get("statut", "?"), 0) + 1

    phases = [
        {"id": "cadrage", "label": _LABELS_PHASES["cadrage"], "indicateurs": {
            "Nature de mission": projet.get("nature_mission") or "—",
            "Cycles couverts": len(projet.get("cycles_couverts") or []),
            "Consentement client": "Oui" if projet.get("consentement_client") else "Non",
        }},
        {"id": "evaluation_ci", "label": _LABELS_PHASES["evaluation_ci"], "indicateurs": {
            "Niveau CI global": qci_glob.get("niveau_global") or "—",
            "Cycles évalués": len(qci_evals),
        }},
        {"id": "ingestion", "label": _LABELS_PHASES["ingestion"], "indicateurs": {
            "Fichiers comptables": len(fichiers),
            "Documents bruts": len(docs_bruts),
            "Annexes": len(annexes),
        }},
        {"id": "planification", "label": _LABELS_PHASES["planification"], "indicateurs": {
            "Seuil de signification": projet.get("seuil_signification") or plan.get("seuil_calcule"),
            "Risques identifiés": len(risques),
            "dont élevés": _cnt(risques, lambda r: r.get("niveau") == "eleve"),
            "Contrôles programmés": _cnt(programme, lambda p: p.get("statut") == "inclus"),
            "Note de synthèse": "Oui" if plan.get("note_synthese") else "Non",
        }},
        {"id": "travaux_substantifs", "label": _LABELS_PHASES["travaux_substantifs"], "indicateurs": {
            "Contrôles exécutés": len(resultats),
            "Sans anomalie": _cnt(resultats, lambda r: r.get("statut") == "ok"),
            "Exceptions levées": _cnt(resultats, lambda r: r.get("statut") == "exception"),
            "Circularisations": len(circ),
            "Sondages": len(sondages),
        }},
        {"id": "revue", "label": _LABELS_PHASES["revue"], "indicateurs": {
            "Exceptions ouvertes": anomalies.get("nb_ouvertes", 0),
            "Corrigées": anomalies.get("nb_corrigees", 0),
            "Sans incidence": anomalies.get("nb_sans_incidence", 0),
            "Non corrigées": anomalies.get("nb_non_corrigees", 0),
            "Cumul non corrigé": anomalies.get("cumul_non_corrigees", 0),
            "Dépasse le seuil": "Oui" if anomalies.get("depasse_seuil_signification") else "Non",
        }},
        {"id": "generation", "label": _LABELS_PHASES["generation"], "indicateurs": {
            "Feuilles de travail": len(feuilles),
            "Contrôles non exécutés": len(ignores),
        }},
        {"id": "opinion", "label": _LABELS_PHASES["opinion"], "indicateurs": {
            "Rigueur retenue": (opinion or {}).get("rigueur") or "—",
            "Type d'opinion": (opinion or {}).get("type_opinion") or "—",
            "Opinion validée": "Oui" if (opinion or {}).get("validee") else "Non",
        }},
    ]

    # Fichiers : ingérés (sources) et produits (exports)
    def _f(nom, categorie, meta=""):
        return {"nom": nom, "categorie": categorie, "detail": meta}

    fichiers_ingeres = (
        [_f(f.get("nom"), "Fichier comptable", f.get("type_document") or f.get("type") or "")
         for f in fichiers]
        + [_f(d.get("nom"), "Document brut", d.get("type_detecte") or "") for d in docs_bruts]
        + [_f(a.get("nom"), "Annexe", "") for a in annexes]
    )
    exports_dir = DATA_DIR / projet_id / "exports"
    fichiers_produits = []
    if exports_dir.exists():
        for f in sorted(exports_dir.glob("*")):
            if f.is_file():
                fichiers_produits.append(
                    _f(f.name, "Livrable produit", f"{f.stat().st_size // 1024} Ko"))

    return {
        "projet": {
            "client": projet.get("client"),
            "exercice": projet.get("exercice"),
            "nature_mission": projet.get("nature_mission"),
            "etat_courant": projet.get("etat_courant"),
            "referentiel_audit": REFERENTIEL_ACTIF.upper(),
            "referentiel_comptable": projet.get("referentiel_comptable"),
            "referentiel_comptable_label": libelle_referentiel_comptable(
                projet.get("referentiel_comptable")),
            "cycles_couverts": projet.get("cycles_couverts"),
            "seuil_signification": projet.get("seuil_signification"),
            "seuil_planification": projet.get("seuil_planification"),
        },
        "phases": phases,
        "anomalies": anomalies,
        "controle_interne": {
            "niveau_global": qci_glob.get("niveau_global"),
            "score_global": qci_glob.get("score_global"),
            "par_cycle": [{"cycle": e.get("cycle"), "niveau": e.get("niveau_risque"),
                           "score": e.get("score")} for e in qci_evals],
        },
        "fichiers": {"ingérés": fichiers_ingeres, "produits": fichiers_produits},
        "opinion": opinion,
    }


@router.get("/projets/{projet_id}/synthese-mission")
def get_synthese_mission(projet_id: str):
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    return _synthese_mission(db, projet_id, projet)


@router.get("/referentiels-comptables")
def list_referentiels_comptables():
    """Liste des référentiels comptables applicables à l'entité auditée
    (à distinguer du référentiel d'audit ISA/NEP). Défaut : PCGD (Djibouti)."""
    return {"referentiels": [{"id": k, "libelle": v}
                             for k, v in REFERENTIELS_COMPTABLES.items()],
            "defaut": "pcgd"}


@router.get("/projets/{projet_id}/opinion")
def get_opinion(projet_id: str):
    db = _get_db(projet_id)
    return {"opinion": db.get_opinion(projet_id)}


class OpinionProposerBody(BaseModel):
    rigueur: str = "moderee"
    # Si renseigné, l'auditeur IMPOSE le type d'opinion et l'IA se contente de rédiger
    # le texte pour ce type (#3). Sinon l'IA détermine le type selon la rigueur.
    type_impose: str | None = None


class OpinionUpdateBody(BaseModel):
    type_opinion: str | None = None
    titre: str | None = None
    texte_opinion: str | None = None
    fondement: str | None = None
    observations: str | None = None
    justification: str | None = None
    rigueur: str | None = None
    validee: bool | None = None
    validee_par: str | None = None


class ExportSigneBody(BaseModel):
    cabinet: dict | None = None


_RIGUEURS_VALIDES = {"stricte", "moderee", "permissive"}
_TYPES_OPINION_VALIDES = {"sans_reserve", "avec_reserve", "defavorable", "impossibilite"}


@router.post("/projets/{projet_id}/opinion/proposer")
def proposer_opinion(projet_id: str, body: OpinionProposerBody):
    """Opus propose une opinion d'audit selon la rigueur choisie par l'auditeur."""
    from ..llm.claude import ClaudeClient
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)

    rigueur = (body.rigueur or "moderee").lower()
    if rigueur not in _RIGUEURS_VALIDES:
        raise HTTPException(400, f"Rigueur inconnue : {body.rigueur}. "
                                 f"Valeurs admises : {sorted(_RIGUEURS_VALIDES)}.")

    type_impose = (body.type_impose or "").strip().lower() or None
    if type_impose and type_impose not in _TYPES_OPINION_VALIDES:
        raise HTTPException(400, f"Type d'opinion inconnu : {body.type_impose}. "
                                 f"Valeurs admises : {sorted(_TYPES_OPINION_VALIDES)}.")

    recap = _synthese_mission(db, projet_id, projet)
    # Entrée LLM compacte et déterministe : phases + anomalies + contrôle interne.
    recap_llm = {
        "phases": recap["phases"],
        "anomalies": recap["anomalies"],
        "controle_interne": recap["controle_interne"],
    }
    ref_compta = libelle_referentiel_comptable(projet.get("referentiel_comptable"))

    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        proposee = llm.proposer_opinion(projet, recap_llm, rigueur, ref_compta,
                                        type_impose=type_impose)
    except Exception as e:
        db.log(projet_id, "erreur", {"action": "proposer_opinion", "detail": str(e)})
        raise HTTPException(500, f"Erreur LLM : {e}")

    opinion = db.save_opinion(projet_id, {
        "rigueur": rigueur,
        "type_opinion": proposee.get("type_opinion"),
        "titre": proposee.get("titre"),
        "texte_opinion": proposee.get("texte_opinion"),
        "fondement": proposee.get("fondement"),
        "observations": proposee.get("observations"),
        "justification": proposee.get("justification"),
        "proposee_par_ia": 1,
        "modele_ia": proposee.get("modele_ia"),
        "validee": 0,
        "validee_par": None,
    })
    db.log(projet_id, "appel_ia", {"action": "proposer_opinion", "rigueur": rigueur,
                                   "type_opinion": proposee.get("type_opinion"),
                                   "type_impose": type_impose})
    return {"opinion": opinion}


@router.put("/projets/{projet_id}/opinion")
def update_opinion(projet_id: str, body: OpinionUpdateBody):
    """Enregistre les corrections/validation de l'auditeur sur l'opinion proposée."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    existing = db.get_opinion(projet_id)
    if not existing:
        raise HTTPException(400, "Aucune opinion à mettre à jour — proposez d'abord une opinion.")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "validee" in updates:
        updates["validee"] = 1 if updates["validee"] else 0
    # Une correction manuelle d'un champ rédactionnel n'est plus « pure IA ».
    if any(k in updates for k in ("texte_opinion", "type_opinion", "fondement", "observations")):
        updates.setdefault("proposee_par_ia", 0)
    opinion = db.save_opinion(projet_id, updates)
    db.log(projet_id, "action_humaine", {"action": "maj_opinion",
                                         "validee": bool(opinion.get("validee"))})
    return {"opinion": opinion}


@router.post("/projets/{projet_id}/exporter-rapport-audit")
def exporter_rapport_audit(projet_id: str, body: ExportSigneBody | None = None):
    """Génère le RAPPORT D'AUDIT .docx à partir de l'opinion validée."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    opinion = db.get_opinion(projet_id)
    if not opinion or not opinion.get("texte_opinion"):
        raise HTTPException(400, "Aucune opinion disponible. Proposez puis validez l'opinion "
                                 "avant de générer le rapport d'audit.")
    if not opinion.get("validee"):
        raise HTTPException(400, "L'opinion n'est pas encore validée par l'auditeur. "
                                 "Validez l'opinion avant de générer le rapport d'audit.")
    plan = db.get_or_create_planification(projet_id)
    cabinet = (body.cabinet if body else None) or {}
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"rapport_audit_{projet_id[:8]}.docx"
    generer_rapport_audit(projet, opinion, output_path, cabinet=cabinet, plan=plan)
    db.log(projet_id, "action_humaine", {"action": "exporter_rapport_audit",
                                         "type_opinion": opinion.get("type_opinion")})
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    return FileResponse(str(output_path), media_type=_MEDIA_DOCX,
                        filename=f"Rapport_audit_{client_slug}.docx")


@router.post("/projets/{projet_id}/exporter-memorandum")
def exporter_memorandum(projet_id: str, body: ExportSigneBody | None = None):
    """Génère le MÉMORANDUM SUR LE CONTRÔLE DES COMPTES .docx."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    plan = db.get_or_create_planification(projet_id)
    cabinet = (body.cabinet if body else None) or {}
    # Agrégat déterministe complet (toutes phases, anomalies, CI, fichiers) pour un mémo exhaustif (#5).
    synthese = _synthese_mission(db, projet_id, projet)
    output_dir = DATA_DIR / projet_id / "exports"
    output_path = output_dir / f"memorandum_controle_comptes_{projet_id[:8]}.docx"
    generer_memorandum_controle_comptes(
        projet,
        db.list_resultats(projet_id),
        db.list_exceptions(projet_id),
        db.list_feuilles(projet_id),
        output_path,
        plan=plan,
        circularisations=db.list_circularisations(projet_id),
        sondages=db.list_sondages(projet_id),
        controles_ignores=db.list_controles_ignores(projet_id),
        cabinet=cabinet,
        synthese=synthese,
    )
    db.log(projet_id, "action_humaine", {"action": "exporter_memorandum"})
    client_slug = (projet.get("client") or "client").replace(" ", "_")[:20]
    return FileResponse(str(output_path), media_type=_MEDIA_DOCX,
                        filename=f"Memorandum_controle_comptes_{client_slug}.docx")


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

    nom_fichier = _safe_filename(fichier.filename, "document")
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
    _safe_id(client_id, "Client")
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
    _safe_id(client_id, "Client")
    cdb = _get_clients_db()
    if not cdb.get_client(client_id):
        raise HTTPException(404, "Client introuvable.")

    if categorie not in CATEGORIES_PERMANENTS:
        categorie = "autres"

    client_dir = CLIENTS_FILES_DIR / client_id
    client_dir.mkdir(parents=True, exist_ok=True)

    nom_fichier = _safe_filename(fichier.filename, "document")
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

    fd, tmp_zip_str = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    tmp_zip = Path(tmp_zip_str)

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

    from starlette.background import BackgroundTask

    def _cleanup(path: str):
        try:
            os.unlink(path)
        except OSError:
            pass

    return FileResponse(
        str(tmp_zip),
        media_type="application/zip",
        filename=zip_name,
        background=BackgroundTask(_cleanup, str(tmp_zip)),
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
                # Extraction sécurisée : refuser tout membre qui sortirait de tmp_path
                # (protection Zip Slip — chemins absolus ou « .. »).
                base_resolue = tmp_path.resolve()
                for membre in zf.namelist():
                    cible = (tmp_path / membre).resolve()
                    if cible != base_resolue and base_resolue not in cible.parents:
                        raise HTTPException(400, "Archive invalide : chemin de fichier non autorisé.")
                zf.extractall(str(tmp_path))
        except zipfile.BadZipFile:
            raise HTTPException(400, "Fichier ZIP corrompu ou invalide.")

        projet_id = manifest.get("projet_id")
        if not projet_id:
            raise HTTPException(400, "manifest.json ne contient pas de projet_id.")
        _safe_id(projet_id, "Projet")

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
    # M2 (ISA 450) : seuil des anomalies manifestement insignifiantes,
    # en fraction du seuil de signification (pratique usuelle : 1 à 5 %).
    taux_insignifiance: float = 0.03


class SeuilsSpecifiquesBody(BaseModel):
    # M2 (ISA 320) : seuils spécifiques par cycle — {cycle: {seuil, justification}}.
    # Un seuil spécifique remplace le seuil global pour les contrôles du cycle ;
    # il doit être INFÉRIEUR au seuil global (un seuil spécifique sert à durcir
    # la détection sur une zone sensible, jamais à l'assouplir).
    seuils: dict[str, dict]


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
        "cycles_couverts": projet.get("cycles_couverts") or [],
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

    from ..planning.thresholds import TAUX_INSIGNIFIANCE_MAX
    if not (0 < body.taux_insignifiance <= TAUX_INSIGNIFIANCE_MAX):
        raise HTTPException(400, f"Le taux d'insignifiance doit être compris entre 0 et "
                                 f"{TAUX_INSIGNIFIANCE_MAX:.0%} du seuil de signification ({norme(450)}).")

    result = calc_seuils(
        body.agregat_type, agregat_valeur,
        body.taux_signification, body.taux_planification,
        body.taux_insignifiance,
    )

    # Mettre à jour la planification et le projet
    db.update_planification(projet_id, {
        "agregat_type": body.agregat_type,
        "agregat_valeur": agregat_valeur,
        "taux_signification": body.taux_signification,
        "taux_planification": body.taux_planification,
        "taux_insignifiance": body.taux_insignifiance,
        "seuil_calcule": result["seuil_signification"],
        "seuil_planification_calcule": result["seuil_planification"],
        "seuil_insignifiance_calcule": result["seuil_insignifiance"],
    })
    db.update_projet(projet_id, {
        "seuil_signification": result["seuil_signification"],
        "seuil_planification": result["seuil_planification"],
        "seuil_insignifiance": result["seuil_insignifiance"],
    })
    db.log(projet_id, "calcul_seuils", result)
    return {
        "seuils": result,
        "planification": db.get_or_create_planification(projet_id),
        "projet": db.get_projet(projet_id),
    }


@router.put("/projets/{projet_id}/planification/seuils-specifiques")
def update_seuils_specifiques(projet_id: str, body: SeuilsSpecifiquesBody):
    """M2 (ISA 320) : seuils spécifiques par cycle, avec justification obligatoire.

    Un seuil spécifique remplace le seuil global pour les contrôles du cycle
    concerné. Il doit être positif et INFÉRIEUR au seuil de signification global
    (il sert à durcir la détection sur une zone sensible, jamais à l'assouplir)."""
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    seuil_global = float(projet.get("seuil_signification") or 0)
    if seuil_global <= 0:
        raise HTTPException(400, f"Définissez d'abord le seuil de signification global ({norme(320)}) "
                                 "avant de fixer des seuils spécifiques.")

    cycles_couverts = set(projet.get("cycles_couverts") or [])
    valides: dict[str, dict] = {}
    for cycle, cfg in (body.seuils or {}).items():
        if cycle not in cycles_couverts:
            raise HTTPException(400, f"Cycle « {cycle} » hors du périmètre de la mission.")
        try:
            seuil = float(cfg.get("seuil") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, f"Seuil spécifique invalide pour le cycle {cycle}.")
        justification = str(cfg.get("justification") or "").strip()
        if seuil <= 0:
            raise HTTPException(400, f"Le seuil spécifique du cycle {cycle} doit être positif.")
        if seuil >= seuil_global:
            raise HTTPException(400, f"Le seuil spécifique du cycle {cycle} doit être inférieur "
                                     f"au seuil global ({seuil_global:,.0f}) : un seuil spécifique "
                                     f"durcit la détection, il ne l'assouplit pas ({norme(320)}).")
        if len(justification) < 10:
            raise HTTPException(400, f"Justifiez le seuil spécifique du cycle {cycle} "
                                     "(10 caractères minimum) — la justification figure au dossier.")
        valides[cycle] = {"seuil": round(seuil, 2), "justification": justification}

    db.update_planification(projet_id, {"seuils_specifiques_json": valides})
    db.log(projet_id, "action_humaine", {
        "action": "seuils_specifiques",
        "cycles": {c: v["seuil"] for c, v in valides.items()},
    })
    return {"seuils_specifiques": valides,
            "planification": db.get_or_create_planification(projet_id)}


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
        db.log(projet_id, "erreur", {"action": "generer_programme", "detail": str(e)})
        raise HTTPException(500, f"Erreur LLM : {e}")

    if not items_ia:
        db.log(projet_id, "erreur", {"action": "generer_programme",
                                     "detail": "Aucun contrôle retourné par l'IA."})
        raise HTTPException(502, "L'IA n'a retourné aucun contrôle pour le programme de travail. "
                                 "Le programme existant est conservé — relancez la génération.")

    # Remplacer le programme existant (uniquement après validation de la réponse IA)
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
    if not programme_inclus:
        raise HTTPException(400, "Aucun contrôle inclus dans le programme de travail — générez "
                                 "d'abord le programme avant la note de synthèse.")

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
        db.log(projet_id, "erreur", {"action": "generer_note_synthese", "detail": str(e)})
        raise HTTPException(500, f"Erreur LLM : {e}")

    if not note.get("sections"):
        db.log(projet_id, "erreur", {"action": "generer_note_synthese",
                                     "detail": "Note de synthèse vide (aucune section)."})
        raise HTTPException(502, "La note de synthèse générée est vide — la note de planification "
                                 "n'a pas été produite. Relancez la génération.")

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


# ─── Circularisation (NEP 505) ────────────────────────────────────────────────

class CircularisationBody(BaseModel):
    cycle: str
    compte: str
    libelle: str | None = None
    solde_comptable: float | None = None
    sources: list[str] = []
    type_circularisation: str = "client"


@router.get("/projets/{projet_id}/circularisation")
def list_circularisations(projet_id: str, cycle: str | None = None):
    db = _get_db(projet_id)
    items = db.list_circularisations(projet_id, cycle)
    return {"circularisations": items}


# Seuls les comptes de TIERS se circularisent (ISA 505) : clients, fournisseurs,
# banques. Les comptes de flux (60x/70x…) ne sont pas des tiers à confirmer.
_PREFIXES_TIERS_CIRCU = {
    "ventes": ["41"],
    "achats": ["40"],
    "tresorerie": ["51", "52"],
}


@router.post("/projets/{projet_id}/circularisation/proposer")
def proposer_tiers_circularisation(projet_id: str, body: dict):
    """Propose les N tiers à circulariser pour un cycle donné."""
    from ..controls.circularisation import proposer_tiers
    cycle = body.get("cycle", "ventes")
    n = int(body.get("n", 10))
    prefixes = body.get("prefixes") or _PREFIXES_TIERS_CIRCU.get(cycle)
    if not prefixes:
        raise HTTPException(400, f"Cycle « {cycle} » sans comptes de tiers à circulariser "
                                 f"(cycles possibles : {', '.join(_PREFIXES_TIERS_CIRCU)}).")
    db = _get_db(projet_id)
    # Soldes de la balance N uniquement (la balance N-1 et le relevé
    # fausseraient les soldes proposés à la confirmation).
    _, rows_gl, rows_balance, *_ = _get_donnees_segmentees(db, projet_id)
    rows = rows_balance if rows_balance else rows_gl
    tiers = [t for t in proposer_tiers(rows, prefixes, n) if abs(t.get("solde") or 0) > 0.01]
    return {"tiers": tiers}


@router.post("/projets/{projet_id}/circularisation")
def create_circularisation(projet_id: str, body: CircularisationBody):
    db = _get_db(projet_id)
    data = body.model_dump()
    data["projet_id"] = projet_id
    data["statut"] = "propose"
    item = db.save_circularisation(data)
    db.log(projet_id, "action_humaine", {"action": "creer_circularisation", "id": item["id"]})
    return {"circularisation": item}


_STATUTS_CIRCU = ("propose", "envoye", "reponse_recue", "sans_reponse", "clos")


@router.patch("/projets/{projet_id}/circularisation/{circ_id}")
def update_circularisation(projet_id: str, circ_id: str, body: dict):
    db = _get_db(projet_id)
    existant = db.get_circularisation(circ_id)
    if not existant:
        raise HTTPException(404, "Circularisation introuvable.")
    if "statut" in body and body["statut"] not in _STATUTS_CIRCU:
        raise HTTPException(400, f"Statut « {body['statut']} » invalide. "
                                 f"Statuts possibles : {', '.join(_STATUTS_CIRCU)}.")
    # NEP 505 : une circularisation restée sans réponse ne peut être close
    # qu'après documentation des procédures alternatives mises en œuvre.
    if body.get("statut") == "clos" and existant.get("statut") == "sans_reponse":
        procedures = body.get("procedures_alternatives") or existant.get("procedures_alternatives")
        if not procedures or not str(procedures).strip():
            raise HTTPException(
                400,
                f"{norme(505)} : en l'absence de réponse du tiers, documentez les procédures "
                "alternatives mises en œuvre (champ procedures_alternatives) avant de clore."
            )
    item = db.update_circularisation(circ_id, body)
    db.log(projet_id, "action_humaine", {"action": "maj_circularisation", "id": circ_id,
                                          "statut": body.get("statut")})
    return {"circularisation": item}


@router.post("/projets/{projet_id}/circularisation/{circ_id}/relancer")
def relancer_circularisation(projet_id: str, circ_id: str, body: dict | None = None):
    """Trace une relance du tiers (NEP 505). Peut marquer le dossier 'sans_reponse'."""
    db = _get_db(projet_id)
    circ = db.get_circularisation(circ_id)
    if not circ:
        raise HTTPException(404, "Circularisation introuvable.")
    updates: dict = {"date_relance": (body or {}).get("date_relance") or _now()}
    if (body or {}).get("marquer_sans_reponse"):
        updates["statut"] = "sans_reponse"
    item = db.update_circularisation(circ_id, updates)
    db.log(projet_id, "action_humaine", {"action": "relance_circularisation", "id": circ_id})
    return {"circularisation": item}


@router.delete("/projets/{projet_id}/circularisation/{circ_id}")
def delete_circularisation(projet_id: str, circ_id: str):
    db = _get_db(projet_id)
    db.delete_circularisation(circ_id)
    db.log(projet_id, "action_humaine", {"action": "supprimer_circularisation", "id": circ_id})
    return {"deleted": True}


@router.post("/projets/{projet_id}/circularisation/{circ_id}/generer-lettre")
def generer_lettre_circularisation(projet_id: str, circ_id: str):
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)
    circ = db.get_circularisation(circ_id)
    if not circ:
        raise HTTPException(404, "Circularisation introuvable.")
    from ..llm.claude import ClaudeClient
    ctx = {"exercice": projet.get("exercice"), "seuil_signification": projet.get("seuil_signification")}
    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        lettre = llm.generer_lettre_circularisation(
            tiers={**circ, "solde_comptable": circ.get("solde_comptable")},
            contexte_projet=ctx,
            type_circularisation=circ.get("type_circularisation", "client"),
        )
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")
    # La génération de la lettre n'est PAS un envoi : le statut reste inchangé.
    # L'auditeur marque l'envoi réel via PATCH {statut: "envoye", date_envoi: ...}.
    item = db.update_circularisation(circ_id, {
        "lettre_ia": json.dumps(lettre, ensure_ascii=False),
    })
    db.log(projet_id, "appel_llm", {"action": "generer_lettre_circularisation", "id": circ_id})
    return {"circularisation": item, "lettre": lettre}


@router.post("/projets/{projet_id}/circularisation/{circ_id}/enregistrer-reponse")
def enregistrer_reponse_circularisation(projet_id: str, circ_id: str, body: dict):
    """Enregistre le solde confirmé par le tiers et calcule l'écart (Python)."""
    from ..controls.circularisation import calculer_ecart
    db = _get_db(projet_id)
    circ = db.get_circularisation(circ_id)
    if not circ:
        raise HTTPException(404, "Circularisation introuvable.")
    projet_circ = db.get_projet(projet_id) or {}
    seuil_ref = projet_circ.get("seuil_planification") or projet_circ.get("seuil_signification")
    solde_confirme = float(body.get("solde_confirme", 0.0))
    solde_comptable = float(circ.get("solde_comptable") or 0.0)
    ecart_data = calculer_ecart(solde_comptable, solde_confirme, seuil_reference=seuil_ref)
    ecart_data.pop("seuil_reference", None)  # non persistable (colonne absente)
    item = db.update_circularisation(circ_id, {
        "solde_confirme": solde_confirme,
        "reponse_brute": body.get("reponse_brute", ""),
        "date_reponse": body.get("date_reponse") or _now(),
        "statut": "reponse_recue",
        **ecart_data,
    })
    db.log(projet_id, "action_humaine", {"action": "enregistrer_reponse_circularisation",
                                          "id": circ_id, "ecart": ecart_data["ecart"]})
    return {"circularisation": item, "ecart": ecart_data}


@router.post("/projets/{projet_id}/circularisation/{circ_id}/analyser")
def analyser_reponse_circularisation(projet_id: str, circ_id: str):
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)
    circ = db.get_circularisation(circ_id)
    if not circ:
        raise HTTPException(404, "Circularisation introuvable.")
    if circ.get("statut") not in ("reponse_recue", "clos"):
        raise HTTPException(400, "Enregistrez d'abord la réponse du tiers.")
    from ..controls.circularisation import calculer_ecart
    from ..llm.claude import ClaudeClient
    ecart_data = calculer_ecart(
        float(circ.get("solde_comptable") or 0.0),
        float(circ.get("solde_confirme") or 0.0),
        seuil_reference=projet.get("seuil_planification") or projet.get("seuil_signification"),
    )
    ctx = {"exercice": projet.get("exercice"), "seuil_signification": projet.get("seuil_signification")}
    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        analyse = llm.analyser_reponse_circularisation(
            tiers=circ, ecart=ecart_data,
            reponse_brute=circ.get("reponse_brute") or "",
            contexte_projet=ctx,
        )
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")
    item = db.update_circularisation(circ_id, {
        "analyse_ia": json.dumps(analyse, ensure_ascii=False),
        "statut": "clos",
    })
    db.log(projet_id, "appel_llm", {"action": "analyser_reponse_circularisation", "id": circ_id})
    return {"circularisation": item, "analyse": analyse}


# ─── Sondages sur pièces (NEP 530) ───────────────────────────────────────────

def _cycle_prefixes(cycle: str) -> list[str]:
    """Retourne les préfixes de compte standard pour un cycle."""
    _MAP = {
        "tresorerie": ["51", "52", "53", "54", "58"],
        "achats": ["40", "60", "61", "62"],
        "ventes": ["41", "70", "71", "72"],
        "immobilisations": ["20", "21", "22", "23", "28"],
        "stocks": ["31", "32", "33", "34", "35", "37", "38"],
        "paie": ["42", "43", "64"],
        "impots": ["44", "63"],
        "capitaux_propres": ["10", "11", "12", "13", "14", "15", "16"],
    }
    return _MAP.get(cycle, [])


class SondageCreateBody(BaseModel):
    cycle: str
    libelle: str | None = None
    prefixes: list[str] = []
    # Unités tolérantes : taux accepté en fraction (0.05) ou en % (5) ;
    # niveau de confiance accepté en % (95) ou en fraction (0.95).
    taux_erreur_tolere: float = 0.05
    niveau_confiance: float = 95


@router.get("/projets/{projet_id}/sondages")
def list_sondages(projet_id: str, cycle: str | None = None):
    db = _get_db(projet_id)
    items = db.list_sondages(projet_id, cycle)
    for s in items:
        s["elements"] = db.list_sondage_elements(s["id"])
    return {"sondages": items}


@router.post("/projets/{projet_id}/sondages")
def create_sondage(projet_id: str, body: SondageCreateBody):
    """Crée un sondage et calcule la taille d'échantillon recommandée (Python)."""
    from ..controls.sondages import calculer_taille_echantillon
    db = _get_db(projet_id)
    prefixes = body.prefixes or _cycle_prefixes(body.cycle)

    # Normalisation des unités (voir SondageCreateBody)
    taux = body.taux_erreur_tolere / 100 if body.taux_erreur_tolere >= 1 else body.taux_erreur_tolere
    niveau = int(round(body.niveau_confiance * 100 if body.niveau_confiance <= 1 else body.niveau_confiance))
    libelle = body.libelle or f"Sondage — cycle {body.cycle}"

    # Population = écritures du grand livre du cycle (les balances N/N-1
    # ne sont pas des pièces à sonder).
    _, rows_gl, rows_balance, *_ = _get_donnees_segmentees(db, projet_id)
    rows = rows_gl if rows_gl else rows_balance
    population_rows = _filter_accounts(rows, tuple(prefixes)) if prefixes else rows
    population = len(population_rows)
    montant_population = sum(
        abs(_get_amount(r, "solde") or (_get_amount(r, "debit") - _get_amount(r, "credit")))
        for r in population_rows
    )
    calcul = calculer_taille_echantillon(population, taux, niveau)
    import time
    seed = int(time.time()) % 1000000
    data = {
        "projet_id": projet_id,
        "cycle": body.cycle,
        "libelle": libelle,
        "prefixes": prefixes,
        "population": population,
        "taille_echantillon": calcul["taille_recommandee"],
        "taux_erreur_tolere": taux,
        "niveau_confiance": niveau,
        "montant_population": round(montant_population, 2),
        "seed": seed,
        "statut": "en_cours",
    }
    sondage = db.save_sondage(data)
    db.log(projet_id, "action_humaine", {"action": "creer_sondage", "id": sondage["id"],
                                          "population": population, "taille": calcul["taille_recommandee"]})
    return {"sondage": sondage, "calcul": calcul}


@router.post("/projets/{projet_id}/sondages/{sondage_id}/selectionner")
def selectionner_echantillon(projet_id: str, sondage_id: str, body: dict | None = None):
    """Sélectionne l'échantillon (Python pur — déterministe par seed)."""
    from ..controls.sondages import selectionner_echantillon as _selectionner
    db = _get_db(projet_id)
    sondage = db.get_sondage(sondage_id)
    if not sondage:
        raise HTTPException(404, "Sondage introuvable.")
    prefixes = sondage.get("prefixes") or []
    n = int(sondage.get("taille_echantillon") or 10)
    seed = sondage.get("seed")
    if body and body.get("taille_echantillon"):
        n = int(body["taille_echantillon"])
        db.update_sondage(sondage_id, {"taille_echantillon": n})
    # Même population que le calcul de taille : écritures du grand livre
    # (les balances N/N-1 ne sont pas des pièces à sonder).
    _, rows_gl, rows_balance, *_ = _get_donnees_segmentees(db, projet_id)
    rows = rows_gl if rows_gl else rows_balance
    elements = _selectionner(rows, prefixes, n, seed)
    db.delete_sondage_elements(sondage_id)
    for elt in elements:
        db.save_sondage_element({**elt, "sondage_id": sondage_id, "projet_id": projet_id})
    saved = db.list_sondage_elements(sondage_id)
    db.log(projet_id, "action_humaine", {"action": "selectionner_echantillon",
                                          "sondage_id": sondage_id, "n": len(saved)})
    return {"elements": saved, "sondage": db.get_sondage(sondage_id)}


@router.patch("/projets/{projet_id}/sondages/{sondage_id}/elements/{element_id}")
def update_sondage_element(projet_id: str, sondage_id: str, element_id: str, body: dict):
    """Marque un élément comme anomalie ou non — les stats sont recalculées côté Python."""
    db = _get_db(projet_id)
    elt = db.update_sondage_element(element_id, body)
    if not elt:
        raise HTTPException(404, "Élément introuvable.")
    sondage = db.recalculer_sondage_stats(sondage_id)
    db.log(projet_id, "action_humaine", {"action": "maj_element_sondage", "element_id": element_id,
                                          "est_anomalie": body.get("est_anomalie")})
    return {"element": elt, "sondage": sondage}


@router.post("/projets/{projet_id}/sondages/{sondage_id}/conclure")
def conclure_sondage(projet_id: str, sondage_id: str):
    """Calcule la projection d'erreur (Python) et demande la conclusion à l'IA."""
    from ..controls.sondages import projeter_erreur
    db = _get_db(projet_id)
    projet, _ = _llm_guard(db, projet_id)
    sondage = db.get_sondage(sondage_id)
    if not sondage:
        raise HTTPException(404, "Sondage introuvable.")
    elements = db.list_sondage_elements(sondage_id)
    nb = int(sondage.get("nb_anomalies") or 0)
    montant_anomalies = float(sondage.get("montant_anomalies") or 0.0)
    taille = int(sondage.get("taille_echantillon") or len(elements))
    montant_pop = float(sondage.get("montant_population") or 0.0)
    # Montant réellement testé = somme des montants des éléments sélectionnés.
    montant_ech = sum(abs(float(e.get("montant") or 0.0)) for e in elements)
    projection = projeter_erreur(nb, montant_anomalies, montant_pop, taille, montant_ech)
    db.update_sondage(sondage_id, {
        "taux_anomalie": projection["taux_anomalie"],
        "montant_projete": projection["montant_projete_population"],
    })
    from ..llm.claude import ClaudeClient
    ctx = {"exercice": projet.get("exercice"), "seuil_signification": projet.get("seuil_signification")}
    anomalies = [e for e in elements if e.get("est_anomalie")]
    try:
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        conclusion = llm.conclure_sondage(sondage, projection, anomalies, ctx)
    except Exception as e:
        raise HTTPException(500, f"Erreur LLM : {e}")
    sondage = db.update_sondage(sondage_id, {
        "conclusion_ia": json.dumps(conclusion, ensure_ascii=False),
        "statut": "conclu",
    })
    db.log(projet_id, "appel_llm", {"action": "conclure_sondage", "id": sondage_id})
    return {"sondage": sondage, "projection": projection, "conclusion": conclusion}


@router.delete("/projets/{projet_id}/sondages/{sondage_id}")
def delete_sondage(projet_id: str, sondage_id: str):
    db = _get_db(projet_id)
    db.delete_sondage(sondage_id)
    db.log(projet_id, "action_humaine", {"action": "supprimer_sondage", "id": sondage_id})
    return {"deleted": True}


# ─── Diligences ISA de périphérie (M3 : 210/220, 240, 550, 560, 570, 580, 260/265) ───

class PeripherieReponseBody(BaseModel):
    reponses: list[dict]  # [{question_id, reponse, commentaire}]


class PeripherieConclusionBody(BaseModel):
    conclusion: str
    conclu_par: str


def _statut_diligence(defn: dict, reponses: list[dict], evaluation: dict | None) -> str:
    """Statut d'avancement d'une diligence pour l'UI : non_commencee →
    en_cours → evaluee → conclue."""
    if evaluation and evaluation.get("conclusion"):
        return "conclue"
    if evaluation and evaluation.get("evalue_le"):
        return "evaluee"
    if any(r.get("reponse") for r in reponses):
        return "en_cours"
    return "non_commencee"


@router.get("/projets/{projet_id}/peripherie")
def get_peripherie(projet_id: str):
    """Retourne les 7 diligences de périphérie : questions, réponses, score
    calculé, évaluation IA, conclusion et lettre éventuelles."""
    from ..controls.peripherie import liste_diligences, calculer_niveau_diligence
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")

    evaluations = {e["diligence"]: e for e in db.list_peripherie_evaluations(projet_id)}
    reponses_all = db.list_peripherie_reponses(projet_id)

    result = []
    for defn in liste_diligences():
        code = defn["code"]
        reponses_map = {r["question_id"]: r for r in reponses_all if r["diligence"] == code}
        questions = []
        for q in defn["questions"]:
            rep = reponses_map.get(q["id"], {})
            questions.append({**q, "reponse": rep.get("reponse"),
                              "commentaire": rep.get("commentaire", ""),
                              "repondu_le": rep.get("repondu_le")})
        avec_reponse = [q for q in questions if q.get("reponse")]
        score_info = calculer_niveau_diligence(avec_reponse) if avec_reponse else None
        evaluation = evaluations.get(code)
        result.append({
            **{k: v for k, v in defn.items() if k != "questions"},
            "questions": questions,
            "nb_repondues": len(avec_reponse),
            "nb_total": len(questions),
            "score_info": score_info,
            "evaluation": evaluation,
            "statut": _statut_diligence(defn, questions, evaluation),
        })
    return {"diligences": result, "projet_id": projet_id}


@router.post("/projets/{projet_id}/peripherie/{diligence}/reponses")
def save_peripherie_reponses(projet_id: str, diligence: str, body: PeripherieReponseBody):
    """Enregistre les réponses au questionnaire d'une diligence de périphérie."""
    from ..controls.peripherie import get_diligence
    db = _get_db(projet_id)
    if not get_diligence(diligence):
        raise HTTPException(400, f"Diligence inconnue : {diligence}")

    for rep in body.reponses:
        qid = rep.get("question_id")
        reponse = rep.get("reponse")
        if not qid or reponse not in ("oui", "non", "na"):
            continue
        db.save_peripherie_reponse(projet_id, diligence, qid, reponse, rep.get("commentaire", ""))

    db.log(projet_id, "action_humaine", {
        "action": "peripherie_reponses",
        "diligence": diligence,
        "nb_reponses": len(body.reponses),
    })
    return {"diligence": diligence,
            "nb_enregistrees": len(db.list_peripherie_reponses(projet_id, diligence))}


@router.post("/projets/{projet_id}/peripherie/{diligence}/evaluer")
def evaluer_peripherie(projet_id: str, diligence: str):
    """Évalue une diligence : score déterministe + synthèse IA. Pour la
    continuité (ISA 570), les indicateurs financiers sont calculés par le
    moteur depuis la balance. Pour la fraude (ISA 240), les risques proposés
    par l'IA alimentent la cartographie des risques (non validés)."""
    from ..controls.peripherie import get_diligence, calculer_niveau_diligence, indicateurs_continuite
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    defn = get_diligence(diligence)
    if not defn:
        raise HTTPException(400, f"Diligence inconnue : {diligence}")

    reponses_map = {r["question_id"]: r for r in db.list_peripherie_reponses(projet_id, diligence)}
    reponses_enrichies = []
    for q in defn["questions"]:
        rep = reponses_map.get(q["id"], {})
        reponses_enrichies.append({
            "question_id": q["id"], "question": q["question"],
            "reponse": rep.get("reponse"), "commentaire": rep.get("commentaire", ""),
            "risque_si_non": q.get("risque_si_non", ""),
        })
    avec_reponse = [r for r in reponses_enrichies if r.get("reponse")]
    if len(avec_reponse) < 3:
        raise HTTPException(400, "Répondez à au moins 3 questions avant de déclencher l'évaluation.")

    score_info = calculer_niveau_diligence(avec_reponse)

    # ISA 570 : indicateurs financiers déterministes depuis la balance importée.
    indicateurs = None
    if diligence == "continuite":
        try:
            _, _, rows_balance, *_ = _get_donnees_segmentees(db, projet_id)
        except Exception:
            rows_balance = []
        if rows_balance:
            indicateurs = indicateurs_continuite(
                rows_balance, float(projet.get("seuil_signification") or 0) or None)

    if not os.environ.get("ANTHROPIC_API_KEY") or not projet.get("consentement_client"):
        evaluation = {
            "synthese": f"Score : {score_info['score']:.0%} — Niveau {score_info['niveau'].upper()}. "
                        "(Mode dégradé : synthèse IA indisponible.)",
            "points_attention": [], "diligences_complementaires": [],
            "conclusion_proposee": "",
        }
    else:
        from ..llm.claude import ClaudeClient
        anon = Anonymizer()
        entites = [v for v in [projet.get("client"), projet.get("nif")] if v]
        ctx = {k: v for k, v in projet.items() if k not in ("client", "nif")}
        ctx["client"] = anon.pseudonymiser(projet.get("client") or "", entites) if entites else projet.get("client")
        try:
            llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
            evaluation = llm.evaluer_diligence_peripherie(
                defn, reponses_enrichies, score_info, ctx, indicateurs)
        except RuntimeError as e:
            raise HTTPException(503, str(e))

    # ISA 240 : injecter les risques de fraude proposés dans la cartographie
    # (issus de l'IA, NON validés — l'auditeur les valide en Planification).
    risques_crees = 0
    if diligence == "fraude":
        for r in (evaluation.pop("risques_fraude", None) or [])[:8]:
            if not isinstance(r, dict) or not r.get("libelle"):
                continue
            db.save_risque({
                "id": str(uuid.uuid4()), "projet_id": projet_id,
                "libelle": str(r.get("libelle"))[:200],
                "description": r.get("description"),
                "cycle": r.get("cycle"), "niveau": r.get("niveau", "moyen"),
                "source": "fraude_240", "issu_ia": 1, "valide_auditeur": 0,
            })
            risques_crees += 1

    data = {
        **evaluation,
        "score": score_info["score"],
        "niveau": score_info["niveau"],
        "indicateurs_json": indicateurs,
    }
    saved = db.save_peripherie_evaluation(projet_id, diligence, data)
    db.log(projet_id, "appel_ia", {
        "action": "evaluer_peripherie", "diligence": diligence,
        "niveau": score_info["niveau"], "score": score_info["score"],
        "risques_fraude_crees": risques_crees,
    })
    return {"evaluation": saved, "score_info": score_info,
            "indicateurs": indicateurs, "risques_fraude_crees": risques_crees}


@router.post("/projets/{projet_id}/peripherie/{diligence}/conclure")
def conclure_peripherie(projet_id: str, diligence: str, body: PeripherieConclusionBody):
    """L'auditeur signe la conclusion d'une diligence. Pour la continuité
    (ISA 570), cette conclusion est un prérequis du passage en génération."""
    from ..controls.peripherie import get_diligence
    db = _get_db(projet_id)
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if not get_diligence(diligence):
        raise HTTPException(400, f"Diligence inconnue : {diligence}")
    if len(body.conclusion.strip()) < 20:
        raise HTTPException(400, "La conclusion doit être argumentée (20 caractères minimum).")
    if len(body.conclu_par.strip()) < 2:
        raise HTTPException(400, "Le nom du signataire est requis.")
    if not db.get_peripherie_evaluation(projet_id, diligence):
        raise HTTPException(400, "Évaluez d'abord la diligence avant de signer sa conclusion.")

    saved = db.conclure_peripherie(projet_id, diligence,
                                   body.conclusion.strip(), body.conclu_par.strip())
    db.log(projet_id, "action_humaine", {
        "action": "conclure_peripherie", "diligence": diligence,
        "conclu_par": body.conclu_par.strip(),
        "conclusion": body.conclusion.strip()[:100],
    })
    return {"evaluation": saved}


@router.post("/projets/{projet_id}/peripherie/{diligence}/generer-lettre")
def generer_lettre_peripherie(projet_id: str, diligence: str):
    """Génère le projet de lettre lié à la diligence : lettre d'affirmation
    (ISA 580) ou communication à la gouvernance (ISA 260/265). Le contenu chiffré
    (anomalies, faiblesses CI, seuil) vient du code — l'IA rédige, ne calcule pas."""
    from ..controls.peripherie import get_diligence
    db = _get_db(projet_id)
    defn = get_diligence(diligence)
    if not defn:
        raise HTTPException(400, f"Diligence inconnue : {diligence}")
    if not defn.get("lettre"):
        raise HTTPException(400, f"La diligence « {defn['libelle']} » ne produit pas de lettre.")
    projet, anon = _llm_guard(db, projet_id)

    # Contenu réel du dossier, calculé par le code déterministe.
    synthese = db.synthese_anomalies(
        projet_id, projet.get("seuil_signification"), projet.get("seuil_planification"))
    faiblesses_ci = []
    for e in db.get_qci_evaluations(projet_id):
        for f in (e.get("faiblesses") or [])[:5]:
            faiblesses_ci.append({"cycle": e.get("cycle"), "faiblesse": f})
    elements = {
        "exercice": projet.get("exercice"),
        "seuil_signification": projet.get("seuil_signification"),
        "anomalies_non_corrigees": synthese.get("exceptions_non_corrigees", []),
        "cumul_anomalies_non_corrigees": synthese.get("cumul_non_corrigees"),
        "nb_anomalies_corrigees": synthese.get("nb_corrigees"),
        "nb_anomalies_insignifiantes": synthese.get("nb_insignifiantes"),
        "faiblesses_controle_interne": faiblesses_ci[:15],
    }

    try:
        from ..llm.claude import ClaudeClient
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        lettre = llm.generer_lettre_peripherie(defn["lettre"], projet, elements)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    # La lettre s'accroche à l'évaluation : créer la ligne si le questionnaire
    # n'a pas encore été évalué (la lettre peut précéder l'évaluation).
    if not db.get_peripherie_evaluation(projet_id, diligence):
        db.save_peripherie_evaluation(projet_id, diligence, {})
    saved = db.save_peripherie_lettre(
        projet_id, diligence, json.dumps(lettre, ensure_ascii=False))
    db.log(projet_id, "appel_ia", {"action": "generer_lettre_peripherie",
                                   "diligence": diligence, "type": defn["lettre"]})
    return {"lettre": lettre, "evaluation": saved}


# ─── Écritures d'ajustement (M1 — ISA 450) ───────────────────────────────────

class LigneAjustementBody(BaseModel):
    compte: str
    libelle: str | None = None
    debit: float = 0
    credit: float = 0


class EcritureAjustementBody(BaseModel):
    libelle: str
    lignes: list[LigneAjustementBody]
    type_anomalie: str = "factuelle"
    justification: str | None = None
    exception_id: str | None = None
    cree_par: str | None = None


class UpdateEcritureBody(BaseModel):
    libelle: str | None = None
    lignes: list[LigneAjustementBody] | None = None
    type_anomalie: str | None = None
    justification: str | None = None
    statut: str | None = None
    acteur: str | None = None


def _exiger_projet_actif(db, projet_id: str) -> dict:
    projet = db.get_projet(projet_id)
    if not projet:
        raise HTTPException(404, "Projet introuvable.")
    if projet.get("archive"):
        raise HTTPException(400, "Dossier archivé — lecture seule.")
    return projet


def _enrichir_ecriture(e: dict) -> dict:
    from ..ajustements import effets_ecriture, LIBELLES_STATUT, LIBELLES_TYPE
    e = dict(e)
    e.update(effets_ecriture(e.get("lignes") or []))
    e["statut_libelle"] = LIBELLES_STATUT.get(e.get("statut"), e.get("statut"))
    e["type_libelle"] = LIBELLES_TYPE.get(e.get("type_anomalie"), e.get("type_anomalie"))
    return e


@router.get("/projets/{projet_id}/ajustements")
def list_ajustements(projet_id: str):
    """Liste des écritures d'ajustement + état récapitulatif ISA 450 (le « SUM »)."""
    from ..ajustements import synthese_ajustements
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    ecritures = [_enrichir_ecriture(e) for e in db.list_ecritures_ajustement(projet_id)]
    return {"ecritures": ecritures, "synthese": synthese_ajustements(ecritures)}


@router.post("/projets/{projet_id}/ajustements")
def create_ajustement(projet_id: str, body: EcritureAjustementBody):
    """Crée une écriture d'ajustement (statut initial : proposée).

    L'équilibre débits = crédits est vérifié par le moteur — une écriture
    déséquilibrée est refusée (partie double, ISA 450)."""
    from ..ajustements import valider_lignes, AjustementError, TYPES_ANOMALIE
    db = _get_db(projet_id)
    _exiger_projet_actif(db, projet_id)

    if body.type_anomalie not in TYPES_ANOMALIE:
        raise HTTPException(400, f"Type d'anomalie invalide : {body.type_anomalie}.")
    if len(body.libelle.strip()) < 5:
        raise HTTPException(400, "Le libellé de l'écriture est requis (5 caractères minimum).")
    lignes = [l.model_dump() for l in body.lignes]
    try:
        total_d, total_c = valider_lignes(lignes)
    except AjustementError as e:
        raise HTTPException(400, str(e))
    if body.exception_id and not db.get_exception(body.exception_id):
        raise HTTPException(404, "Exception liée introuvable.")

    ecriture = db.save_ecriture_ajustement({
        "id": str(uuid.uuid4()), "projet_id": projet_id,
        "exception_id": body.exception_id, "libelle": body.libelle.strip(),
        "type_anomalie": body.type_anomalie, "justification": body.justification,
        "total_debits": total_d, "total_credits": total_c,
        "cree_par": body.cree_par,
    }, lignes)
    db.log(projet_id, "action_humaine", {
        "action": "creer_ecriture_ajustement", "id": ecriture["id"],
        "libelle": body.libelle.strip()[:80], "montant": total_d,
        "exception_id": body.exception_id,
    })
    return _enrichir_ecriture(ecriture)


@router.patch("/projets/{projet_id}/ajustements/{ecriture_id}")
def update_ajustement(projet_id: str, ecriture_id: str, body: UpdateEcritureBody):
    """Modifie une écriture (contenu et/ou statut).

    - Le contenu (lignes, libellé…) n'est modifiable que tant que l'écriture
      n'est pas passée.
    - Les transitions de statut suivent le cycle de vie :
      proposée → acceptée client → passée / refusée. « Passée » est terminal.
    """
    from ..ajustements import (valider_lignes, AjustementError, TYPES_ANOMALIE,
                               TRANSITIONS_STATUT, LIBELLES_STATUT)
    db = _get_db(projet_id)
    _exiger_projet_actif(db, projet_id)
    ecriture = db.get_ecriture_ajustement(ecriture_id)
    if not ecriture or ecriture.get("projet_id") != projet_id:
        raise HTTPException(404, "Écriture introuvable.")

    fields: dict = {}
    lignes = None

    # Modification de contenu — interdite une fois l'écriture passée
    contenu_modifie = any(v is not None for v in (body.libelle, body.lignes,
                                                  body.type_anomalie, body.justification))
    if contenu_modifie:
        if ecriture["statut"] == "passee":
            raise HTTPException(400, "Écriture passée (comptabilisée) : son contenu ne se "
                                     "modifie plus. Créez une écriture complémentaire si besoin.")
        if body.libelle is not None:
            if len(body.libelle.strip()) < 5:
                raise HTTPException(400, "Libellé trop court (5 caractères minimum).")
            fields["libelle"] = body.libelle.strip()
        if body.type_anomalie is not None:
            if body.type_anomalie not in TYPES_ANOMALIE:
                raise HTTPException(400, f"Type d'anomalie invalide : {body.type_anomalie}.")
            fields["type_anomalie"] = body.type_anomalie
        if body.justification is not None:
            fields["justification"] = body.justification
        if body.lignes is not None:
            lignes = [l.model_dump() for l in body.lignes]
            try:
                total_d, total_c = valider_lignes(lignes)
            except AjustementError as e:
                raise HTTPException(400, str(e))
            fields["total_debits"] = total_d
            fields["total_credits"] = total_c

    # Transition de statut
    if body.statut is not None and body.statut != ecriture["statut"]:
        autorisees = TRANSITIONS_STATUT.get(ecriture["statut"], [])
        if body.statut not in autorisees:
            raise HTTPException(400, f"Transition interdite : "
                                     f"{LIBELLES_STATUT.get(ecriture['statut'])} → "
                                     f"{LIBELLES_STATUT.get(body.statut, body.statut)}.")
        fields["statut"] = body.statut

    if not fields and lignes is None:
        return _enrichir_ecriture(ecriture)

    updated = db.update_ecriture_ajustement(ecriture_id, fields, lignes)
    db.log(projet_id, "action_humaine", {
        "action": "modifier_ecriture_ajustement", "id": ecriture_id,
        "statut": fields.get("statut"), "acteur": body.acteur,
        "contenu_modifie": contenu_modifie,
    })
    return _enrichir_ecriture(updated)


@router.delete("/projets/{projet_id}/ajustements/{ecriture_id}")
def delete_ajustement(projet_id: str, ecriture_id: str):
    """Supprime une écriture — seulement tant qu'elle est proposée ou refusée."""
    db = _get_db(projet_id)
    _exiger_projet_actif(db, projet_id)
    ecriture = db.get_ecriture_ajustement(ecriture_id)
    if not ecriture or ecriture.get("projet_id") != projet_id:
        raise HTTPException(404, "Écriture introuvable.")
    if ecriture["statut"] in ("acceptee_client", "passee"):
        raise HTTPException(400, "Cette écriture est acceptée ou passée : elle fait partie "
                                 "du dossier et ne se supprime plus.")
    db.delete_ecriture_ajustement(ecriture_id)
    db.log(projet_id, "action_humaine", {"action": "supprimer_ecriture_ajustement",
                                         "id": ecriture_id})
    return {"deleted": True}


@router.post("/projets/{projet_id}/ajustements/proposer/{exception_id}")
def proposer_ajustement_depuis_exception(projet_id: str, exception_id: str):
    """L'IA propose le schéma comptable de l'écriture corrigeant une exception.

    Le MONTANT vient du code (incidence saisie par l'auditeur, sinon montant
    estimé par le contrôle). L'IA choisit les comptes et le sens — le moteur
    vérifie ensuite l'équilibre et que chaque montant est bien celui imposé."""
    from ..ajustements import valider_lignes, AjustementError, TOLERANCE_EQUILIBRE
    from ..normes import libelle_referentiel_comptable
    db = _get_db(projet_id)
    projet, anon = _llm_guard(db, projet_id)
    exc = db.get_exception(exception_id)
    if not exc:
        raise HTTPException(404, "Exception introuvable.")

    montant = exc.get("montant_incidence") or exc.get("montant_estime")
    if not montant or float(montant) <= 0:
        raise HTTPException(400, "Cette exception ne porte aucun montant (incidence ou estimation) : "
                                 "l'écriture ne peut pas être proposée. Saisissez les lignes manuellement.")
    montant = round(float(montant), 2)

    entites = [v for v in [projet.get("client"), projet.get("nif")] if v]
    exc_anon = anon.pseudonymiser_dict(exc, ["description", "decision_humaine"], entites)

    try:
        from ..llm.claude import ClaudeClient
        llm = ClaudeClient(audit_logger=lambda t, p: db.log(projet_id, t, p))
        proposition = llm.proposer_ecriture_ajustement(
            exc_anon, montant, {"exercice": projet.get("exercice")},
            libelle_referentiel_comptable(projet.get("referentiel_comptable")))
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    # Garde-fou : le LLM ne calcule jamais — on vérifie que l'écriture est
    # équilibrée ET que son total est exactement le montant imposé par le code.
    lignes = proposition.get("lignes") or []
    try:
        total_d, _ = valider_lignes(lignes)
    except AjustementError as e:
        raise HTTPException(502, f"Proposition IA invalide ({e}). Relancez ou saisissez manuellement.")
    if abs(total_d - montant) > TOLERANCE_EQUILIBRE:
        raise HTTPException(502, f"Proposition IA rejetée : total {total_d:,.2f} ≠ montant "
                                 f"calculé {montant:,.2f}. Relancez ou saisissez manuellement.")

    db.log(projet_id, "appel_ia", {"action": "proposer_ecriture_ajustement",
                                   "exception_id": exception_id, "montant": montant})
    # Proposition NON enregistrée : l'auditeur la relit, l'ajuste et la crée lui-même.
    return {"proposition": {
        "libelle": proposition.get("libelle") or f"Correction — {exc.get('controle_ref')}",
        "type_anomalie": proposition.get("type_anomalie", "factuelle"),
        "justification": anon.re_identifier(proposition.get("justification") or ""),
        "exception_id": exception_id,
        "lignes": lignes,
        "montant": montant,
    }}


@router.get("/projets/{projet_id}/balance-ajustee")
def get_balance_ajustee(projet_id: str, seulement_ajustes: bool = False):
    """Balance ajustée = balance importée + écritures PASSÉES.

    Chaque ligne garde ses sources (provenance) : celles de la balance
    importée et celles des lignes d'écritures."""
    from ..ajustements import balance_ajustee
    db = _get_db(projet_id)
    if not db.get_projet(projet_id):
        raise HTTPException(404, "Projet introuvable.")
    _, _, rows_balance, *_ = _get_donnees_segmentees(db, projet_id)
    soldes_bruts = _aggreger_soldes_nets(rows_balance, tuple("123456789"))
    ecritures = db.list_ecritures_ajustement(projet_id)
    result = balance_ajustee(soldes_bruts, ecritures)
    if seulement_ajustes:
        result["lignes"] = [l for l in result["lignes"] if l["ajustement"] != 0]
    return result
