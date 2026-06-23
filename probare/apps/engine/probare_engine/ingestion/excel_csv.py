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
    """
    Mappe les colonnes connues avec correspondance exacte puis par sous-chaîne.
    Gère les balances (Solde Débiteur / Solde Créditeur) et les grands livres.
    """
    col_keys = {c.lower().strip(): c for c in df.columns}
    mapping: dict[str, str | None] = {
        "compte": None, "libelle": None, "debit": None,
        "credit": None, "date": None, "numero_piece": None,
        "solde": None, "exercice": None,
    }

    # Synonymes exacts (sous-chaîne dans le nom de colonne en minuscules)
    # Ordre : du plus précis au plus générique pour éviter les collisions
    synonymes: dict[str, list[str]] = {
        "compte":       ["n° compte", "n°compte", "num_compte", "n_compte", "code_compte",
                         "numéro de compte", "numero de compte", "num. compte",
                         "compte", "account", "code"],
        "libelle":      ["intitulé du compte", "intitule du compte", "libellé du compte",
                         "libellé", "libelle", "intitulé", "intitule",
                         "designation", "désignation", "label"],
        # Débit total / mouvements : priorité sur "solde débiteur"
        "debit":        ["mouvement débit", "mouvement debit", "total débit", "total debit",
                         "montant débit", "montant debit", "montant_débit", "montant_debit",
                         "débit", "debit", " db"],
        # Crédit total / mouvements
        "credit":       ["mouvement crédit", "mouvement credit", "total crédit", "total credit",
                         "montant crédit", "montant credit", "montant_crédit", "montant_credit",
                         "crédit", "credit", " cr"],
        # Solde débiteur et créditeur — traités séparément ci-dessous
        "solde":        ["solde net", "solde final", "solde", "balance", "sold"],
        "date":         ["date opération", "date operation", "date écriture", "date ecriture",
                         "date_ecriture", "date_piece", "date_op", "date"],
        "numero_piece": ["n° pièce", "n°pièce", "ref piece", "ref_piece", "num_piece",
                         "numéro pièce", "n° facture", "n°facture", "facture", "pièce", "piece"],
        "exercice":     ["exercice", "annee", "année", "year"],
    }

    def _find(syns: list[str]) -> str | None:
        """Cherche d'abord une correspondance exacte puis par sous-chaîne."""
        for syn in syns:
            if syn in col_keys:
                return col_keys[syn]
        # Sous-chaîne (permet "Solde Débiteur" → debit)
        for syn in syns:
            for key, orig in col_keys.items():
                if syn in key:
                    return orig
        return None

    for field, syns in synonymes.items():
        mapping[field] = _find(syns)

    # Cas spécial balance : "Solde Débiteur" → debit, "Solde Créditeur" → credit
    if mapping["debit"] is None:
        for key, orig in col_keys.items():
            if "solde" in key and ("débit" in key or "debit" in key):
                mapping["debit"] = orig
                break
    if mapping["credit"] is None:
        for key, orig in col_keys.items():
            if "solde" in key and ("crédit" in key or "credit" in key):
                mapping["credit"] = orig
                break

    # Éviter que "solde" soit mappé sur une colonne déjà prise par debit/credit
    if mapping["solde"] and mapping["solde"] in (mapping["debit"], mapping["credit"]):
        mapping["solde"] = None

    return mapping


_HEADER_KEYWORDS = {
    "compte", "account", "code",
    "libelle", "libellé", "intitulé", "intitule", "designation", "désignation",
    "debit", "débit", "credit", "crédit",
    "solde", "balance",
    "date", "piece", "pièce", "ref",
    "montant", "amount",
}


def _detect_header_row(path: Path, sheet_name: str | int, max_scan: int = 15) -> int:
    """
    Scanne les premières lignes pour trouver la ligne d'en-tête réelle.
    Retourne l'index 0-based de la ligne à passer à pd.read_excel(header=N).

    Stratégie : la ligne d'en-tête est celle qui contient ≥ 2 mots-clés
    comptables parmi ses cellules non-vides. On prend la première telle ligne.
    """
    try:
        raw = pd.read_excel(
            path, sheet_name=sheet_name, dtype=str, header=None, nrows=max_scan
        )
    except Exception:
        return 0

    for idx, row in raw.iterrows():
        cells = [str(v).lower().strip() for v in row if pd.notna(v) and str(v).strip()]
        if len(cells) < 2:
            continue
        hits = sum(
            1 for c in cells
            if any(kw in c for kw in _HEADER_KEYWORDS)
        )
        if hits >= 2:
            return int(idx)

    return 0


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
        header_row = _detect_header_row(path, sheet_name)
        df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, header=header_row)
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
