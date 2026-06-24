"""Export PDF du dossier de travail — NEP 230.

Utilise fpdf2 (pure Python, aucune dépendance système).
Reproduit la structure du dossier .docx : entête, contrôles, exceptions, feuilles.
Chaque chiffre est tracé jusqu'à sa source (même contrainte que export.py).
FPDF est importé en mode lazy pour éviter les conflits d'environnement.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def generer_dossier_travail_pdf(
    projet: dict,
    resultats: list[dict],
    exceptions: list[dict],
    feuilles: list[dict],
    output_path: str | Path,
) -> Path:
    """Génère le dossier de travail en PDF.

    Paramètres identiques à generer_dossier_travail() dans export.py.
    """
    try:
        from fpdf import FPDF
    except ImportError as e:
        raise ImportError(
            "fpdf2 est requis pour l'export PDF. "
            "Installez-le : pip install fpdf2>=2.7.0"
        ) from e

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Définit la classe ici pour capturer FPDF depuis le scope local
    class AuditPDF(FPDF):
        def __init__(self, p: dict):
            super().__init__()
            self._projet = p
            self.set_auto_page_break(auto=True, margin=20)
            self.add_page()

        def header(self):
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(100, 100, 100)
            titre = (
                f"Probare — Dossier de travail — "
                f"{self._projet.get('client', '')} — {self._projet.get('exercice', '')}"
            )
            self.cell(0, 6, titre, align="L")
            self.ln(3)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()} — Généré le {_now_str()} — NEP 230", align="C")

        def section_title(self, text: str):
            self.set_font("Helvetica", "B", 12)
            self.set_fill_color(240, 245, 255)
            self.set_text_color(30, 60, 130)
            self.cell(0, 8, text, fill=True, ln=True)
            self.set_text_color(0, 0, 0)
            self.ln(2)

        def sub_title(self, text: str):
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(50, 50, 50)
            self.cell(0, 7, text, ln=True)
            self.set_text_color(0, 0, 0)

        def kv_row(self, key: str, value: str):
            self.set_font("Helvetica", "B", 9)
            self.cell(55, 6, key + " :", ln=False)
            self.set_font("Helvetica", "", 9)
            self.multi_cell(0, 6, str(value or "—"))

    pdf = AuditPDF(projet)

    # ── Page de garde ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 60, 130)
    pdf.ln(10)
    pdf.cell(0, 12, "Dossier de travail d'audit", align="C", ln=True)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"Client : {projet.get('client', 'N/A')}", align="C", ln=True)
    pdf.cell(0, 8, f"Exercice : {projet.get('exercice', 'N/A')}", align="C", ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, f"Généré le {_now_str()}", align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(200, 210, 230)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 6,
        "Conformément à la NEP 230 (Documentation des travaux d'audit), ce dossier "
        "retrace les diligences effectuées, les résultats des contrôles déterministes "
        "et les exceptions relevées et tranchées. Chaque chiffre est tracé jusqu'à sa source.",
        fill=True, border=1)
    pdf.ln(4)
    pdf.kv_row("Nature de la mission", projet.get("nature_mission", "contractuelle").capitalize())
    seuil = projet.get("seuil_signification")
    pdf.kv_row("Seuil de signification", f"{seuil:,.0f} FDJ" if seuil else "Non défini")
    nif = projet.get("nif")
    if nif:
        pdf.kv_row("NIF", nif)
    pdf.ln(4)

    # ── Récapitulatif des contrôles ────────────────────────────────────────────
    if resultats:
        pdf.add_page()
        pdf.section_title("Résultats des contrôles déterministes")
        nb_ok = sum(1 for r in resultats if r.get("statut") == "ok")
        nb_ko = len(resultats) - nb_ok
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6,
            f"Contrôles effectués : {len(resultats)}   |   Sans anomalie : {nb_ok}   |   Exceptions levées : {nb_ko}",
            ln=True)
        pdf.ln(3)

        cycles: dict[str, list] = {}
        for r in resultats:
            cycle = (r.get("controle_ref") or "").split("-")[0].lower() or "autre"
            cycles.setdefault(cycle, []).append(r)

        SEV_OK = (16, 185, 129)
        SEV_KO = (239, 68, 68)

        for cycle, items in cycles.items():
            pdf.sub_title(f"Cycle : {cycle.upper()}")
            for r in items:
                ok = r.get("statut") == "ok"
                color = SEV_OK if ok else SEV_KO
                pdf.set_x(14)
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(*color)
                pdf.cell(18, 5, "[OK]" if ok else "[EXC]", ln=False)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(0, 5, r.get("controle_ref", ""), ln=True)
                details_raw = r.get("details")
                if details_raw:
                    import json
                    try:
                        details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
                        msg = details.get("message") or details.get("description") or str(details)[:120]
                    except Exception:
                        msg = str(details_raw)[:120]
                    pdf.set_x(18)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 5, msg[:200])
                    pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

    # ── Exceptions ────────────────────────────────────────────────────────────
    if exceptions:
        pdf.add_page()
        pdf.section_title("Exceptions relevées et tranchées")
        pdf.set_font("Helvetica", "", 9)
        nb_tranchees = sum(1 for e in exceptions if e.get("statut") == "tranchee")
        pdf.cell(0, 6, f"Total : {len(exceptions)}   |   Tranchées : {nb_tranchees}", ln=True)
        pdf.ln(3)

        SEV_COLORS = {
            "critique": (239, 68, 68),
            "significative": (245, 158, 11),
            "mineure": (107, 114, 128),
        }

        for exc in exceptions:
            sev = exc.get("severite", "mineure")
            color = SEV_COLORS.get(sev, (107, 114, 128))
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*color)
            pdf.cell(0, 6,
                f"[{sev.upper()}] {exc.get('controle_ref', '')} — {exc.get('nep_ref', '')}",
                ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)
            desc = exc.get("description") or ""
            pdf.set_x(14)
            pdf.multi_cell(0, 5, desc[:300])
            decision = exc.get("decision_humaine") or exc.get("decision_proposee") or ""
            if decision:
                pdf.set_x(14)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(60, 120, 60)
                pdf.multi_cell(0, 5, f"Decision : {decision[:300]}")
                pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

    # ── Feuilles de travail ────────────────────────────────────────────────────
    for ft in feuilles:
        pdf.add_page()
        pdf.section_title(f"Feuille de travail — Cycle {ft.get('cycle', '').upper()}")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5,
            f"Référence NEP : {ft.get('nep_ref', '')}   |   Généré le : {ft.get('genere_le', '')[:10]}",
            ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        contenu = ft.get("contenu_redige") or ""
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, contenu[:3000])
        if ft.get("sources"):
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(120, 120, 120)
            nb_src = len(ft["sources"]) if isinstance(ft["sources"], list) else 0
            pdf.cell(0, 5,
                f"Sources : {nb_src} résultat(s) de contrôle(s) — tracabilité NEP 230",
                ln=True)
            pdf.set_text_color(0, 0, 0)

    pdf.output(str(output_path))
    return output_path
