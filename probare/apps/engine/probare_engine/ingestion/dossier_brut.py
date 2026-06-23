"""Lecture de documents bruts (PDF, images, Excel, CSV...) pour l'analyse IA."""
from __future__ import annotations
import base64
import io
import csv
from pathlib import Path


IMAGE_MIMES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def lire_contenu_pour_llm(path: Path) -> tuple[str, str, str]:
    """
    Lit un fichier et retourne (text_content, base64_content, media_type).

    - text_content  : contenu texte lisible (limité à 10 000 caractères)
    - base64_content: données encodées en base64 pour les images
    - media_type    : type MIME si base64 fourni (ex: "image/jpeg")

    Pour les Excel : conversion CSV → texte.
    Pour les images: base64 + media_type, text_content vide.
    Pour les PDF   : extraction texte si possible, sinon message d'erreur.
    """
    suffix = path.suffix.lower()

    # Excel → CSV texte
    if suffix in (".xlsx", ".xls", ".xlsm"):
        try:
            import pandas as pd
            df = pd.read_excel(str(path), nrows=400, dtype=str)
            text = df.to_csv(index=False)
            return text[:10_000], "", ""
        except Exception as e:
            return f"[Fichier Excel : {path.name} — erreur : {e}]", "", ""

    # CSV / TXT / TSV
    if suffix in (".csv", ".txt", ".tsv"):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            return text[:10_000], "", ""
        except Exception:
            return f"[Fichier texte non lisible : {path.name}]", "", ""

    # Images → base64 pour Claude Vision
    if suffix in IMAGE_MIMES:
        try:
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            return "", b64, IMAGE_MIMES[suffix]
        except Exception as e:
            return f"[Image non lisible : {path.name} — {e}]", "", ""

    # PDF → extraction texte en priorité
    if suffix == ".pdf":
        # Tentative 1 : pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages: list[str] = []
            for page in reader.pages[:20]:
                t = page.extract_text()
                if t:
                    pages.append(t)
            text = "\n".join(pages).strip()
            if text:
                return text[:10_000], "", ""
        except Exception:
            pass
        # Tentative 2 : pdfminer
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(str(path)).strip()
            if text:
                return text[:10_000], "", ""
        except Exception:
            pass
        return (
            f"[PDF : {path.name} — extraction texte impossible "
            f"(document scanné ou protégé). Décris ce que tu sais du nom de fichier.]",
            "", "",
        )

    # Word .docx
    if suffix == ".docx":
        try:
            import docx as _docx
            doc = _docx.Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text[:10_000], "", ""
        except Exception:
            pass
        return f"[Fichier Word : {path.name} — extraction impossible]", "", ""

    # Fallback : essayer UTF-8
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:10_000], "", ""
    except Exception:
        return f"[Fichier non lisible : {path.name}]", "", ""


def lignes_vers_csv(lignes: list[dict]) -> str:
    """Convertit la liste de lignes extraites par le LLM en CSV importable."""
    colonnes = ["date", "compte", "libelle", "debit", "credit", "piece", "tiers"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=colonnes, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    for ligne in lignes:
        row = {
            "date": ligne.get("date") or "",
            "compte": ligne.get("compte") or "",
            "libelle": ligne.get("libelle") or "",
            "debit": ligne.get("debit") or 0,
            "credit": ligne.get("credit") or 0,
            "piece": ligne.get("reference") or "",
            "tiers": ligne.get("tiers") or "",
        }
        writer.writerow(row)
    return buf.getvalue()
