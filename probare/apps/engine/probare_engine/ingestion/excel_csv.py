"""Ingestion Excel/CSV → DonneeSourcee avec provenance complète."""
from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from ..provenance.models import DonneeSourcee


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _detect_column_mapping(df: pd.DataFrame) -> dict[str, str | None]:
    """Heuristique simple pour mapper les colonnes connues."""
    cols = {c.lower().strip(): c for c in df.columns}
    mapping: dict[str, str | None] = {
        "compte": None, "libelle": None, "debit": None,
        "credit": None, "date": None, "numero_piece": None,
        "solde": None, "exercice": None,
    }
    synonymes = {
        "compte": ["compte", "account", "n_compte", "num_compte", "code_compte"],
        "libelle": ["libelle", "libellé", "label", "designation", "désignation", "intitulé", "intitule"],
        "debit": ["debit", "débit", "db", "montant_debit", "montant_débit"],
        "credit": ["credit", "crédit", "cr", "montant_credit", "montant_crédit"],
        "date": ["date", "date_ecriture", "date_piece", "date_op"],
        "numero_piece": ["piece", "pièce", "numero_piece", "num_piece", "ref_piece", "facture", "n_facture"],
        "solde": ["solde", "balance", "sold"],
        "exercice": ["exercice", "annee", "année", "year"],
    }
    for field, syns in synonymes.items():
        for syn in syns:
            if syn in cols:
                mapping[field] = cols[syn]
                break
    return mapping


def lire_fichier(
    path: Path,
    projet_id: str,
    fichier_source_id: str,
    sheet_name: str | int = 0,
    column_mapping: dict[str, str] | None = None,
) -> tuple[list[DonneeSourcee], dict]:
    """
    Lit un fichier Excel ou CSV et retourne une liste de DonneeSourcee
    et les métadonnées (mapping colonnes, nb lignes, etc.).
    """
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, header=0)
        source_prefix = f"{Path(path).stem}!{_sheet_name(df, sheet_name)}"
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
        source_prefix = Path(path).stem
    else:
        raise ValueError(f"Format non supporté : {suffix}")

    df = df.dropna(how="all").reset_index(drop=True)

    mapping = column_mapping or _detect_column_mapping(df)
    metadata = {
        "nb_lignes": len(df),
        "colonnes": list(df.columns),
        "mapping_detecte": mapping,
        "feuille": sheet_name if isinstance(sheet_name, str) else f"feuille_{sheet_name}",
    }

    donnees: list[DonneeSourcee] = []

    for row_idx, row in df.iterrows():
        row_num = int(row_idx) + 2  # +2 car ligne 1 = en-tête

        for field_name, col_name in mapping.items():
            if col_name is None or col_name not in df.columns:
                continue
            raw_val = row.get(col_name)
            if pd.isna(raw_val) or raw_val is None or str(raw_val).strip() == "":
                continue

            type_donnee = _type_for_field(field_name)
            val = _coerce_value(raw_val, type_donnee)
            localisation = f"{source_prefix}:{row_num}:{col_name}"

            donnees.append(DonneeSourcee(
                id=str(uuid.uuid4()),
                projet_id=projet_id,
                fichier_source_id=fichier_source_id,
                valeur=val,
                type=type_donnee,
                localisation=localisation,
                confiance_extraction=1.0,
                extrait_par="ingestion-directe",
                horodatage=_now(),
            ))

    return donnees, metadata


def _sheet_name(df: pd.DataFrame, sheet_name: str | int) -> str:
    if isinstance(sheet_name, str):
        return sheet_name
    return str(sheet_name)


def _type_for_field(field_name: str) -> str:
    type_map = {
        "compte": "compte",
        "libelle": "texte",
        "debit": "montant",
        "credit": "montant",
        "date": "date",
        "numero_piece": "numero_piece",
        "solde": "montant",
        "exercice": "texte",
    }
    return type_map.get(field_name, "texte")


def _coerce_value(raw: Any, type_: str) -> float | str | None:
    if type_ == "montant":
        try:
            cleaned = str(raw).replace(" ", "").replace(",", ".").replace("\xa0", "")
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    return str(raw).strip() if raw is not None else None
