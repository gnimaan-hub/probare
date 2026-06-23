"""DonneeSourcee — seule porte d'entrée des nombres dans le moteur."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
import uuid


class DonneeSourcee(BaseModel):
    """Toute valeur numérique ou texte provenant d'une source externe.
    Aucun calcul ne s'effectue sur des valeurs non sourcées.
    """
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    projet_id: str
    fichier_source_id: str
    valeur: float | str | None
    type: Literal["montant", "texte", "date", "compte", "numero_piece"]
    localisation: str  # ex: "Balance!B5" ou "grand_livre.csv:ligne:42:col:Debit"
    confiance_extraction: float = Field(ge=0.0, le=1.0, default=1.0)
    extrait_par: str = "ingestion-directe"
    horodatage: str = ""
