"""Point d'entrée FastAPI — sidecar Probare."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Charger .env depuis la racine probare/ (4 niveaux au-dessus de ce fichier)
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).parent.parent.parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

from .api.routes import router

app = FastAPI(
    title="Probare Engine",
    version="0.1.0",
    description="Moteur d'audit comptable — FastAPI sidecar",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["content-disposition"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    pass
