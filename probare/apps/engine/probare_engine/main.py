"""Point d'entrée FastAPI — sidecar Probare."""
import os
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Publier la clé API Claude dans l'environnement du processus. La déduction du
# chemin de `.env` depuis `__file__` ne tient pas une fois l'application gelée
# par PyInstaller (les sources sont dépliées dans un répertoire temporaire) :
# la résolution est déportée dans cle_api, qui couvre les deux modes.
from .cle_api import installer_cle_api

installer_cle_api()

from .acteur import ENTETE_ACTEUR, definir_acteur, reinitialiser_acteur
from .api.routes import router

app = FastAPI(
    title="Probare Engine",
    version="0.1.0",
    description="Moteur d'audit comptable — FastAPI sidecar",
)

# Le sidecar n'écoute que sur 127.0.0.1 et n'utilise aucun cookie : on n'active
# donc pas allow_credentials (la combinaison "*" + credentials est de toute façon
# refusée par les navigateurs). La protection réelle contre un site tiers qui
# tenterait d'appeler l'API locale est le jeton partagé ci-dessous.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["content-disposition"],
)


# ─── Authentification par jeton partagé ──────────────────────────────────────
# Electron génère un jeton au démarrage, l'injecte dans l'environnement du
# sidecar (PROBARE_API_TOKEN) et le transmet au renderer via IPC. Toute requête
# doit alors présenter l'en-tête « X-Probare-Token ». Si aucun jeton n'est
# configuré (ex. tests, exécution standalone), la garde est désactivée.
_API_TOKEN = os.environ.get("PROBARE_API_TOKEN")
_EXEMPT_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def verifier_jeton(request: Request, call_next):
    if _API_TOKEN and request.method != "OPTIONS" and request.url.path not in _EXEMPT_PATHS:
        if request.headers.get("x-probare-token") != _API_TOKEN:
            return JSONResponse({"detail": "Jeton d'API manquant ou invalide."}, status_code=401)
    return await call_next(request)


# ─── Identité de l'auteur des actions (ISA 230) ──────────────────────────────
# Le renderer transmet le « Responsable signataire » de la fiche Cabinet sur
# chaque requête ; toute écriture au journal l'enregistre. Voir acteur.py pour
# pourquoi ce n'est pas — et n'a pas à être — une authentification.


@app.middleware("http")
async def rattacher_acteur(request: Request, call_next):
    token = definir_acteur(request.headers.get(ENTETE_ACTEUR))
    try:
        return await call_next(request)
    finally:
        reinitialiser_acteur(token)


# ─── Verrou lecture seule des dossiers archivés ──────────────────────────────
# Un dossier archivé est scellé : toute mutation (POST/PATCH/PUT/DELETE) est
# refusée, à l'exception du désarchivage explicite qui, lui, est journalisé.
_PROJET_PATH_RE = re.compile(r"^/api/projets/([0-9a-fA-F-]{8,64})(/.*)?$")


@app.middleware("http")
async def verrou_archive(request: Request, call_next):
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        m = _PROJET_PATH_RE.match(request.url.path)
        if m and (m.group(2) or "") != "/desarchiver":
            projet_id = m.group(1)
            try:
                from .api.routes import DATA_DIR, _get_db
                # Ne pas ouvrir la base d'un projet qui n'existe pas : `_get_db`
                # la CRÉE, et une requête portant un identifiant bien formé mais
                # inconnu sèmerait un dossier de mission vide dans les données de
                # l'utilisateur. Sans base, il n'y a rien à archiver.
                if not (DATA_DIR / projet_id / "audit.db").exists():
                    return await call_next(request)
                projet = _get_db(projet_id).get_projet(projet_id)
                if projet and projet.get("archive"):
                    return JSONResponse(
                        {"detail": "Dossier archivé — lecture seule. "
                                   "Désarchivez-le pour le modifier."},
                        status_code=403,
                    )
            except Exception:
                # Id invalide ou projet inexistant : la route donnera la vraie erreur.
                pass
    return await call_next(request)


app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    pass
