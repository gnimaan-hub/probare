"""Export dossier de travail (docx) et tableaux (xlsx) avec contrôle de provenance."""
from __future__ import annotations
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..normes import norme, prefixe_actif


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


class ProvenanceError(Exception):
    """Levée si un chiffre sans source est détecté dans un livrable."""


def _verifier_sources(valeur: Any, sources: list[str], libelle: str) -> None:
    """Échoue si une valeur numérique n'a pas de source."""
    if isinstance(valeur, (int, float)) and valeur != 0 and not sources:
        raise ProvenanceError(
            f"Valeur '{libelle}' = {valeur} sans source. "
            f"La génération est bloquée (règle B.2)."
        )


_MONTANT_RE = re.compile(r'\b\d{1,3}(?:[,\s]\d{3})+(?:[.,]\d+)?\b|\b\d{5,}(?:[.,]\d+)?\b')


def _verifier_provenance_texte_llm(
    contenu: str,
    valeurs_python: set[float],
    contexte: str,
) -> list[str]:
    """
    Scanne contenu à la recherche de grands nombres (≥ 1 000) non calculés par Python.
    Retourne la liste des avertissements (n'interrompt pas la génération).
    """
    avertissements = []
    for m in _MONTANT_RE.finditer(contenu):
        raw = m.group().replace(',', '').replace(' ', '').replace('\xa0', '')
        try:
            val = float(raw)
        except ValueError:
            continue
        if val < 1000:
            continue
        # Tolérance ±0.5% ou 1 FDJ
        if not any(abs(val - v) <= max(0.005 * v, 1.0) for v in valeurs_python):
            avertissements.append(
                f"Nombre {val:,.0f} dans '{contexte}' non retrouvé dans les valeurs Python."
            )
    return avertissements


def generer_dossier_travail(
    projet: dict,
    resultats: list[dict],
    exceptions: list[dict],
    feuilles: list[dict],
    output_path: Path,
    controles_ignores: list[dict] | None = None,
    synthese_anomalies: dict | None = None,
) -> Path:
    """Génère le dossier de travail en .docx.
    Lève ProvenanceError si un chiffre non sourcé est détecté.
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx est requis pour la génération docx.")

    # Vérification provenance avant génération
    for res in resultats:
        _verifier_sources(res.get("valeur"), res.get("sources", []),
                          f"contrôle {res.get('controle_ref')}")

    # Valeurs calculées par Python (pour vérification des feuilles IA)
    valeurs_python: set[float] = {
        float(r["valeur"]) for r in resultats
        if r.get("valeur") is not None and isinstance(r.get("valeur"), (int, float))
    }
    avertissements_provenance: list[str] = []
    for ft in feuilles:
        contenu = ft.get("contenu_redige", "") or ""
        if contenu:
            warns = _verifier_provenance_texte_llm(contenu, valeurs_python, ft.get("cycle", "?"))
            avertissements_provenance.extend(warns)

    doc = Document()

    # Style du document
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # En-tête
    titre = doc.add_heading("DOSSIER DE TRAVAIL", 0)
    titre.alignment = WD_ALIGN_PARAGRAPH.CENTER

    info = doc.add_paragraph()
    info.add_run(f"Client : {projet.get('client', 'N/A')}\n").bold = True
    info.add_run(f"Exercice : {projet.get('exercice', 'N/A')}\n")
    _seuil = projet.get('seuil_signification')
    _seuil_txt = f"{_seuil:,.0f} FDJ" if isinstance(_seuil, (int, float)) else "Non défini"
    info.add_run(f"Seuil de signification : {_seuil_txt}\n")
    info.add_run(f"Généré le : {_now()}\n")
    info.add_run(f"Référence {norme(230)} : Dossier de travail\n")

    doc.add_paragraph("─" * 60)

    # Numérotation dynamique des sections (certaines sont conditionnelles)
    _num_section = 0

    def _titre_section(libelle: str) -> str:
        nonlocal _num_section
        _num_section += 1
        return f"{_num_section}. {libelle}"

    # Section résultats des contrôles
    doc.add_heading(_titre_section("Résultats des contrôles"), level=1)

    for res in resultats:
        sources_str = ", ".join(str(s)[:20] for s in (res.get("sources") or [])[:3])
        if len(res.get("sources") or []) > 3:
            sources_str += "..."

        p = doc.add_paragraph(style="List Bullet")
        label = f"[{res['controle_ref']}] {res.get('details', '')}"
        run = p.add_run(label)
        if res["statut"] == "exception":
            run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
        else:
            run.font.color.rgb = RGBColor(0x27, 0xAE, 0x60)

        if sources_str:
            p.add_run(f"\n   Sources : {sources_str}").font.size = Pt(9)

    # Section exceptions
    doc.add_heading(_titre_section("Exceptions et leur traitement"), level=1)

    open_exc = [e for e in exceptions if e.get("statut") == "ouverte"]
    closed_exc = [e for e in exceptions if e.get("statut") == "tranchee"]

    if open_exc:
        doc.add_paragraph(f"⚠ {len(open_exc)} exception(s) ouverte(s) non tranchée(s).")

    for exc in exceptions:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(f"[{exc.get('nep_ref')}] {exc.get('controle_ref')} — "
                        f"Sévérité : {exc.get('severite', 'N/A')}")
        if exc.get("statut") == "ouverte":
            run.font.color.rgb = RGBColor(0xE6, 0x7E, 0x22)
        else:
            run.font.color.rgb = RGBColor(0x27, 0xAE, 0x60)

        p.add_run(f"\n   {exc.get('description', '')}")
        if exc.get("decision_humaine"):
            p.add_run(f"\n   Décision : {exc['decision_humaine']} (par {exc.get('decideur', 'N/A')})")
        type_res = exc.get("type_resolution")
        if type_res:
            labels_res = {
                "corrigee": "Anomalie corrigée par le client",
                "sans_incidence": "Sans incidence — explication obtenue, aucune anomalie avérée",
                "non_corrigee": "Anomalie NON corrigée",
            }
            txt_res = labels_res.get(type_res, type_res)
            mi = exc.get("montant_incidence")
            if type_res == "non_corrigee" and isinstance(mi, (int, float)):
                txt_res += f" — incidence : {mi:,.2f}"
            p.add_run(f"\n   Résolution ({norme(450)}) : {txt_res}")
        if exc.get("interpretation_llm"):
            p.add_run(f"\n   Interprétation : {exc['interpretation_llm'][:200]}...")

    # Section synthèse NEP 450 — cumul des anomalies non corrigées vs seuil
    if synthese_anomalies:
        doc.add_heading(_titre_section(f"Synthèse des anomalies ({norme(450)})"), level=1)
        sa = synthese_anomalies
        p_syn = doc.add_paragraph()
        p_syn.add_run(
            f"Anomalies corrigées : {sa.get('nb_corrigees', 0)} — "
            f"Sans incidence : {sa.get('nb_sans_incidence', 0)} — "
            f"Non corrigées : {sa.get('nb_non_corrigees', 0)} — "
            f"Tranchées sans typologie : {sa.get('nb_non_typees', 0)}\n"
        )
        cumul = sa.get("cumul_non_corrigees", 0.0)
        seuil_sig = sa.get("seuil_signification")
        run_cumul = p_syn.add_run(
            f"Cumul des anomalies non corrigées : {cumul:,.2f}"
            + (f" / seuil de signification : {seuil_sig:,.2f}" if seuil_sig else " (seuil non défini)")
        )
        run_cumul.bold = True
        if sa.get("depasse_seuil_signification"):
            p_alerte = doc.add_paragraph()
            r = p_alerte.add_run(
                "⚠ Le cumul des anomalies non corrigées DÉPASSE le seuil de signification. "
                f"Conformément à la norme {norme(450)}, ce dépassement doit être pris en compte dans "
                "la formulation de l'opinion (réserve ou refus de certifier à envisager)."
            )
            r.bold = True
            r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
        elif seuil_sig:
            doc.add_paragraph(
                "Le cumul des anomalies non corrigées reste inférieur au seuil de "
                "signification. Prises isolément et en cumul, elles n'ont pas d'incidence "
                "significative sur les comptes pris dans leur ensemble."
            )
        for e_nc in sa.get("exceptions_non_corrigees", []):
            mi = e_nc.get("montant_incidence")
            doc.add_paragraph(
                f"[{e_nc.get('controle_ref')}] {(e_nc.get('description') or '')[:120]} — "
                f"incidence : {mi:,.2f}" if isinstance(mi, (int, float)) else
                f"[{e_nc.get('controle_ref')}] {(e_nc.get('description') or '')[:120]}",
                style="List Bullet",
            )

    # Section contrôles non exécutés (NEP 230)
    if controles_ignores:
        doc.add_heading(_titre_section(f"Contrôles prévus non exécutés ({norme(230)})"), level=1)
        doc.add_paragraph(
            "Les contrôles suivants n'ont pas pu être exécutés lors de la dernière "
            f"passe ; le motif est documenté conformément à la norme {norme(230)}."
        )
        for ci in controles_ignores:
            doc.add_paragraph(
                f"[{ci.get('controle_ref')}] ({ci.get('cycle', '?')}) — {ci.get('raison', '')}",
                style="List Bullet",
            )

    # Section feuilles de travail
    doc.add_heading(_titre_section("Feuilles de travail par cycle"), level=1)

    for ft in feuilles:
        doc.add_heading(f"Cycle : {ft.get('cycle', 'N/A')}", level=2)
        doc.add_paragraph(ft.get("contenu_redige", ""))
        sources_ft = ft.get("sources", [])
        if sources_ft:
            doc.add_paragraph(f"Sources : {', '.join(str(s) for s in sources_ft[:5])}")

    # Avertissements de provenance (si des nombres LLM ne sont pas tracés)
    if avertissements_provenance:
        doc.add_heading("⚠ Avertissements de traçabilité", level=1)
        p_warn = doc.add_paragraph()
        p_warn.add_run(
            "Les montants suivants ont été détectés dans les feuilles de travail rédigées par l'IA "
            "sans correspondance exacte dans les valeurs calculées par le moteur déterministe. "
            "L'auditeur doit les vérifier manuellement."
        ).italic = True
        for w in avertissements_provenance[:20]:
            doc.add_paragraph(w, style="List Bullet")

    # Pied de page
    doc.add_paragraph("─" * 60)
    footer = doc.add_paragraph()
    footer.add_run("Ce dossier est généré automatiquement par Probare. "
                   "L'opinion d'audit reste de la responsabilité exclusive "
                   "de l'auditeur habilité signataire.")
    footer.runs[0].italic = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def generer_note_planification(
    projet: dict,
    plan: dict,
    risques: list[dict],
    programme: list[dict],
    note_synthese: dict,
    output_path: Path,
) -> Path:
    """Génère la Note de Planification de l'Audit en .docx (NEP 300).

    Document complet structuré en 7 sections + page de garde,
    destiné au dossier de travail de la mission.
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx est requis.")

    VIOLET = RGBColor(0x4F, 0x46, 0xE5)
    ROUGE  = RGBColor(0xC0, 0x39, 0x2B)
    ORANGE = RGBColor(0xE6, 0x7E, 0x22)
    VERT   = RGBColor(0x27, 0xAE, 0x60)

    NIVEAU_LABELS = {
        "eleve":  "ÉLEVÉ",
        "moyen":  "MOYEN",
        "faible": "FAIBLE",
    }

    doc = Document()

    for section in doc.sections:
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    def h1(text: str):
        p = doc.add_heading(text, level=1)
        if p.runs:
            p.runs[0].font.color.rgb = VIOLET
        return p

    def h2(text: str):
        return doc.add_heading(text, level=2)

    def para(text: str, bold: bool = False, italic: bool = False, size: int = 11):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold   = bold
        run.italic = italic
        run.font.size = Pt(size)
        return p

    def sep():
        p = doc.add_paragraph("─" * 80)
        p.paragraph_format.space_after = Pt(0)
        if p.runs:
            p.runs[0].font.size = Pt(8)

    def fmt_montant(v: Any) -> str:
        try:
            return f"{float(v):,.0f} FDJ"
        except Exception:
            return str(v) if v is not None else "—"

    def label_val(p: Any, label: str, val: Any) -> None:
        r1 = p.add_run(f"{label} : ")
        r1.bold = True
        r1.font.size = Pt(11)
        p.add_run(str(val) if val is not None else "—").font.size = Pt(11)
        p.add_run("\n")

    # ── Index des sections IA ────────────────────────────────────────────────
    sections_ia: dict[str, str] = {}
    for s in (note_synthese.get("sections") or []):
        t = (s.get("titre") or "").strip()
        c = (s.get("contenu") or "").strip()
        if t:
            sections_ia[t] = c
    # Raccourcis tolérants
    def ia(key: str) -> str:
        for k, v in sections_ia.items():
            if key.lower() in k.lower():
                return v
        return ""

    client_nom = projet.get("client") or projet.get("nom") or "N/A"
    exercice   = projet.get("exercice") or "N/A"
    seuil_calc = plan.get("seuil_calcule")
    seuil_plan = plan.get("seuil_planification_calcule")
    agregat_type = plan.get("agregat_type") or "—"
    agregat_val  = plan.get("agregat_valeur")
    taux_sig     = plan.get("taux_signification")
    taux_plan    = plan.get("taux_planification")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PAGE DE GARDE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pg = doc.add_paragraph()
    pg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = pg.add_run("PROBARE")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = VIOLET

    pg2 = doc.add_paragraph()
    pg2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pg2.add_run("Logiciel d'audit IA-first — Djibouti").italic = True

    doc.add_paragraph()
    titre = doc.add_heading("NOTE DE PLANIFICATION DE L'AUDIT", level=0)
    titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    sep()
    doc.add_paragraph()

    garde = doc.add_paragraph()
    garde.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for lbl, val in [
        ("Entité auditée",    client_nom),
        ("Exercice",          exercice),
        ("Date d'émission",   _now()),
        ("Référentiel",       f"{norme(300)} — Planification"),
        ("Statut",            "Document de travail — CONFIDENTIEL"),
    ]:
        r2 = garde.add_run(f"{lbl} : {val}\n")
        r2.font.size = Pt(12)

    doc.add_paragraph()
    sep()
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SOMMAIRE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("Sommaire")
    for item in [
        "1. Cadre et objectifs de la mission",
        f"2. Connaissance de l'entité ({norme(315)})",
        f"3. Procédures analytiques préliminaires ({norme(520)})",
        f"4. Seuil de signification ({norme(320)})",
        f"5. Cartographie des risques ({norme(315)})",
        f"6. Programme de travail ({norme(300)} / {norme(330)})",
        "7. Synthèse et conclusion",
    ]:
        doc.add_paragraph(item, style="List Number")
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. CADRE ET OBJECTIFS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("1. Cadre et objectifs de la mission")
    para(
        f"La présente note de planification est établie conformément à la norme {norme(300)} "
        f"pour la mission d'audit des comptes de l'exercice {exercice} "
        f"de l'entité {client_nom}. Elle constitue un document de travail confidentiel "
        "intégré au dossier d'audit et doit être conservée pendant la durée légale (5 ans)."
    )
    h2("1.1 Objectifs de l'audit")
    para(
        "L'audit a pour objectif d'émettre une opinion sur la régularité, la sincérité "
        "et l'image fidèle des états financiers. Cet objectif est atteint par la mise en "
        "œuvre de diligences adaptées aux risques identifiés lors de la présente phase "
        "de planification."
    )
    h2("1.2 Référentiels applicables")
    for nep in [
        f"{norme(300)} — Planification de la mission",
        f"{norme(315)} — Connaissance de l'entité et identification des risques",
        f"{norme(320)} — Seuil de signification",
        f"{norme(330)} — Procédures d'audit mises en œuvre en réponse aux risques évalués",
        f"{norme(520)} — Procédures analytiques",
        f"{norme(230)} — Documentation des travaux",
    ]:
        doc.add_paragraph(nep, style="List Bullet")
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. CONNAISSANCE DE L'ENTITÉ
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(f"2. Connaissance de l'entité ({norme(315)})")

    contenu_entite = ia("connaissance")
    if contenu_entite:
        para(contenu_entite)
    doc.add_paragraph()

    h2("2.1 Identification et présentation générale")
    p_gen = doc.add_paragraph()
    label_val(p_gen, "Forme juridique",        plan.get("forme_juridique"))
    label_val(p_gen, "Date de création",       plan.get("date_creation_entreprise"))
    label_val(p_gen, "Effectif",               plan.get("effectif"))
    label_val(p_gen, "Système d'information",  plan.get("systeme_information"))

    if plan.get("activites_principales"):
        h2("2.2 Activités et marchés")
        para(plan["activites_principales"])
        if plan.get("marches_principaux"):
            para(f"Marchés principaux : {plan['marches_principaux']}")

    h2("2.3 Gouvernance — Dirigeants")
    dirigeants = plan.get("dirigeants") or []
    if dirigeants:
        t = doc.add_table(rows=1, cols=3)
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, col in enumerate(["Nom", "Fonction", "Email"]):
            hdr[i].text = col
            hdr[i].paragraphs[0].runs[0].bold = True
        for d in dirigeants:
            row = t.add_row().cells
            row[0].text = d.get("nom") or "—"
            row[1].text = d.get("fonction") or "—"
            row[2].text = d.get("email") or "—"
    else:
        para("Aucun dirigeant renseigné.", italic=True)

    h2("2.4 Facteurs de risque inhérent identifiés")
    facteurs = plan.get("facteurs_risque_inherent") or []
    if facteurs:
        for f in facteurs:
            doc.add_paragraph(str(f), style="List Bullet")
    else:
        para("Aucun facteur de risque inhérent spécifique identifié.", italic=True)

    if plan.get("observations"):
        h2("2.5 Observations complémentaires")
        para(plan["observations"])

    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. PROCÉDURES ANALYTIQUES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(f"3. Procédures analytiques préliminaires ({norme(520)})")

    contenu_analytique = ia("analytique") or ia("variations")
    if contenu_analytique:
        para(contenu_analytique)
    else:
        para(
            "Les procédures analytiques préliminaires consistent à comparer les données "
            "financières de l'exercice N aux données de l'exercice N-1 afin d'identifier "
            "les variations significatives susceptibles de révéler un risque d'anomalie."
        )

    h2("3.1 Variations significatives identifiées")
    variations: list[dict] = []
    vraw = plan.get("variations_json")
    if isinstance(vraw, str):
        try:
            variations = json.loads(vraw)
        except Exception:
            pass
    elif isinstance(vraw, list):
        variations = vraw

    sig = [v for v in variations if v.get("significative")]
    if sig:
        t = doc.add_table(rows=1, cols=5)
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, col in enumerate(["Compte", "Libellé", "Solde N", "Solde N-1", "Variation %"]):
            hdr[i].text = col
            hdr[i].paragraphs[0].runs[0].bold = True
        for v in sig[:30]:
            row = t.add_row().cells
            row[0].text = str(v.get("compte") or "")
            row[1].text = str(v.get("libelle") or "")
            row[2].text = fmt_montant(v.get("solde_n"))
            row[3].text = fmt_montant(v.get("solde_n1"))
            pct = v.get("delta_pct")
            row[4].text = f"{pct:+.1f} %" if pct is not None else "—"
        doc.add_paragraph()
    else:
        para("Aucune variation significative identifiée dans les données disponibles.", italic=True)

    h2("3.2 Interprétation")
    interp: dict | None = None
    iraw = plan.get("interpretation_variations")
    if isinstance(iraw, str):
        try:
            interp = json.loads(iraw)
        except Exception:
            pass
    elif isinstance(iraw, dict):
        interp = iraw

    if interp:
        if interp.get("synthese"):
            para(interp["synthese"])
        zones = interp.get("zones_risque") or []
        if zones:
            t2 = doc.add_table(rows=1, cols=3)
            t2.style = "Table Grid"
            hdr2 = t2.rows[0].cells
            for i, col in enumerate(["Cycle / Compte", "Niveau", "Explication"]):
                hdr2[i].text = col
                hdr2[i].paragraphs[0].runs[0].bold = True
            for z in zones:
                row = t2.add_row().cells
                row[0].text = z.get("libelle") or z.get("cycle") or "—"
                row[1].text = z.get("niveau") or "—"
                row[2].text = z.get("explication") or "—"
            doc.add_paragraph()
        if interp.get("facteurs_contextuels"):
            para(f"Facteurs contextuels : {interp['facteurs_contextuels']}")
        alertes = interp.get("alertes") or []
        if alertes:
            h2("Points d'attention")
            for a in alertes:
                doc.add_paragraph(str(a), style="List Bullet")
    else:
        para("Interprétation analytique non disponible.", italic=True)

    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. SEUIL DE SIGNIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(f"4. Seuil de signification ({norme(320)})")

    contenu_seuil = ia("seuil") or ia("risque")
    if contenu_seuil:
        para(contenu_seuil)

    h2("4.1 Base de calcul et paramètres retenus")
    p_seuil = doc.add_paragraph()
    label_val(p_seuil, "Agrégat retenu",          agregat_type)
    label_val(p_seuil, "Valeur de l'agrégat",     fmt_montant(agregat_val))
    label_val(p_seuil, "Taux de signification",   f"{taux_sig} %" if taux_sig else "—")
    label_val(p_seuil, "Taux de planification",   f"{taux_plan} %" if taux_plan else "—")
    label_val(p_seuil, "Seuil de signification",  fmt_montant(seuil_calc))
    label_val(p_seuil, "Seuil de planification",  fmt_montant(seuil_plan))

    h2("4.2 Justification du seuil retenu")
    para(
        f"Le seuil de signification de {fmt_montant(seuil_calc)} ({taux_sig or '—'} % "
        f"de {agregat_type}) est le montant au-delà duquel une anomalie, prise "
        f"isolément ou EN CUMUL avec les autres anomalies non corrigées ({norme(450)}), "
        "est susceptible d'influencer le jugement d'un utilisateur des comptes et "
        "d'affecter l'opinion d'audit. Une anomalie inférieure au seuil ne peut être "
        "considérée comme sans incidence qu'après agrégation avec l'ensemble des "
        "anomalies non corrigées relevées au cours de la mission. "
        "Le seuil de planification de "
        f"{fmt_montant(seuil_plan)} ({taux_plan or '—'} %) est appliqué pour les "
        "tests de détail afin de conserver une marge de sécurité permettant d'absorber "
        "les anomalies non détectées. Ces paramètres sont conformes aux pratiques "
        f"professionnelles et aux exigences de la norme {norme(320)}."
    )
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. CARTOGRAPHIE DES RISQUES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(f"5. Cartographie des risques ({norme(315)})")
    para(f"{len(risques)} risque(s) identifié(s) et validé(s) pour cette mission.")

    eleve  = [r for r in risques if r.get("niveau") == "eleve"]
    moyen  = [r for r in risques if r.get("niveau") == "moyen"]
    faible = [r for r in risques if r.get("niveau") == "faible"]
    para(f"Dont : {len(eleve)} élevé(s), {len(moyen)} moyen(s), {len(faible)} faible(s).")
    doc.add_paragraph()

    cycles_risques: dict[str, list[dict]] = {}
    for r in risques:
        c = r.get("cycle") or "transversal"
        cycles_risques.setdefault(c, []).append(r)

    for cycle_id, cycle_risques in sorted(cycles_risques.items()):
        h2(f"Cycle : {cycle_id.capitalize()}")
        t = doc.add_table(rows=1, cols=5)
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, col in enumerate(["Libellé du risque", "Niveau", "Source", "Assertions ISA", "Commentaire"]):
            hdr[i].text = col
            hdr[i].paragraphs[0].runs[0].bold = True
        for r in cycle_risques:
            row = t.add_row().cells
            row[0].text = r.get("libelle") or "—"
            row[1].text = NIVEAU_LABELS.get(r.get("niveau", ""), r.get("niveau", "—"))
            row[2].text = "IA" if r.get("issu_ia") else "Manuel"
            assertions = r.get("assertions") or []
            row[3].text = ", ".join(assertions) if assertions else "—"
            row[4].text = (r.get("commentaire") or "")[:100]
        doc.add_paragraph()

    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. PROGRAMME DE TRAVAIL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1(f"6. Programme de travail ({norme(300)} / {norme(330)})")

    contenu_programme = ia("programme") or ia("justification")
    if contenu_programme:
        para(contenu_programme)

    inclus = [p for p in programme if p.get("statut") == "inclus"]
    exclus = [p for p in programme if p.get("statut") != "inclus"]
    para(
        f"{len(inclus)} contrôle(s) inclus dans le programme sur {len(programme)} planifiés. "
        f"{len(exclus)} contrôle(s) exclu(s) sur la base du niveau de risque et du seuil de signification."
    )

    cycles_prog: dict[str, list[dict]] = {}
    for item in inclus:
        c = item.get("cycle") or "transversal"
        cycles_prog.setdefault(c, []).append(item)

    for cycle_id, items in sorted(cycles_prog.items()):
        h2(f"Cycle : {cycle_id.capitalize()}")
        t = doc.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        hdr = t.rows[0].cells
        for i, col in enumerate(["Réf. contrôle", "Libellé", "Priorité", "Notes"]):
            hdr[i].text = col
            hdr[i].paragraphs[0].runs[0].bold = True
        for item in items:
            row = t.add_row().cells
            row[0].text = item.get("controle_ref") or "—"
            row[1].text = (item.get("libelle") or "")[:120]
            row[2].text = item.get("priorite") or "—"
            row[3].text = (item.get("notes") or "")[:80]
        doc.add_paragraph()

    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. SYNTHÈSE ET CONCLUSION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("7. Synthèse et conclusion")

    if note_synthese.get("titre"):
        para(note_synthese["titre"], bold=True)
        doc.add_paragraph()

    for s in (note_synthese.get("sections") or []):
        h2(s.get("titre") or "")
        para(s.get("contenu") or "")

    if note_synthese.get("conclusion"):
        doc.add_paragraph()
        p_conc = doc.add_paragraph()
        r_conc = p_conc.add_run(note_synthese["conclusion"])
        r_conc.italic = True

    doc.add_paragraph()
    sep()

    # Zone de signature
    doc.add_paragraph()
    sig_p = doc.add_paragraph()
    sig_p.add_run("Validation par l'auditeur responsable de la mission\n\n").bold = True
    sig_p.add_run("Nom : ___________________________          ")
    sig_p.add_run("Date : ___________________________\n\n")
    sig_p.add_run("Signature : ___________________________")

    doc.add_paragraph()
    sep()

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_f = footer_p.add_run(
        f"Document généré par Probare le {_now()} · "
        f"Document confidentiel · Dossier de travail {norme(230)}"
    )
    r_f.font.size = Pt(9)
    r_f.italic = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def generer_tableau_exceptions(
    exceptions: list[dict],
    output_path: Path,
) -> Path:
    """Génère un tableau Excel des exceptions."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise ImportError("openpyxl est requis pour la génération xlsx.")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exceptions"

    headers = ["ID", "Contrôle", "NEP", "Sévérité", "Description",
               "Statut", "Décision", "Décideur", "Horodatage"]
    header_fill = PatternFill("solid", fgColor="4F46E5")
    header_font = Font(bold=True, color="FFFFFF")

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, exc in enumerate(exceptions, 2):
        ws.cell(row=row_idx, column=1, value=exc.get("id", "")[:8])
        ws.cell(row=row_idx, column=2, value=exc.get("controle_ref", ""))
        ws.cell(row=row_idx, column=3, value=exc.get("nep_ref", ""))
        ws.cell(row=row_idx, column=4, value=exc.get("severite", ""))
        ws.cell(row=row_idx, column=5, value=exc.get("description", "")[:200])
        ws.cell(row=row_idx, column=6, value=exc.get("statut", ""))
        ws.cell(row=row_idx, column=7, value=exc.get("decision_humaine", ""))
        ws.cell(row=row_idx, column=8, value=exc.get("decideur", ""))
        ws.cell(row=row_idx, column=9, value=exc.get("horodatage", ""))

        if exc.get("statut") == "ouverte":
            fill = PatternFill("solid", fgColor="FFF3CD")
        else:
            fill = PatternFill("solid", fgColor="D4EDDA")
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col).fill = fill

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].auto_size = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    return output_path


# ─── Demande de diligences au client (#9) ─────────────────────────────────────

# Cycle (préfixe de la référence de contrôle) → libellé lisible
_CYCLE_LABELS = {
    "TRESOR": "Trésorerie", "ACHAT": "Achats-Fournisseurs", "VENTE": "Ventes-Clients",
    "IMO": "Immobilisations", "STOCK": "Stocks", "PAIE": "Personnel-Paie",
    "TAXE": "Impôts et taxes", "CP": "Capitaux propres et provisions",
}


def _cycle_depuis_ref(ref: str) -> str:
    prefixe = (ref or "").split("-")[0]
    return _CYCLE_LABELS.get(prefixe, "Divers")


_SEVERITE_LABELS = {
    "critique": "Critique", "significative": "Significative", "mineure": "Mineure",
}


def generer_demande_diligences(
    projet: dict,
    exceptions: list[dict],
    output_path: Path,
    seulement_ouvertes: bool = True,
) -> Path:
    """Génère une demande de diligences .docx présentable au client (#9).

    Reprend chaque exception (anomalie relevée), regroupée par cycle, avec sa
    description, les hypothèses de cause et les diligences/pièces à fournir.
    Mise en page professionnelle, prête à imprimer/envoyer.
    """
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx est requis pour la génération docx.")

    VIOLET = RGBColor(0x4F, 0x46, 0xE5)
    exceptions = [e for e in exceptions
                  if not seulement_ouvertes or e.get("statut") == "ouverte"]

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    titre = doc.add_heading("DEMANDE DE DILIGENCES", 0)
    titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Points relevés lors de l'audit — pièces et explications attendues").italic = True

    info = doc.add_paragraph()
    info.add_run(f"Client : {projet.get('client', 'N/A')}\n").bold = True
    info.add_run(f"Exercice : {projet.get('exercice', 'N/A')}\n")
    info.add_run(f"Édité le : {_now()}\n")
    info.add_run(f"Nombre de points : {len(exceptions)}\n")

    doc.add_paragraph("─" * 60)

    intro = doc.add_paragraph()
    intro.add_run(
        "Dans le cadre de nos travaux d'audit, les points suivants nécessitent votre "
        "attention. Pour chacun, merci de nous communiquer les explications et les pièces "
        "justificatives correspondantes. Ces éléments nous permettront de conclure sur les "
        "zones concernées. Sauf mention contraire, tous les montants sont exprimés en FDJ."
    ).italic = True

    if not exceptions:
        doc.add_paragraph()
        p = doc.add_paragraph()
        p.add_run("Aucun point en attente à ce jour.").bold = True
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        return output_path

    # Regroupement par cycle
    par_cycle: dict[str, list[dict]] = {}
    for e in exceptions:
        par_cycle.setdefault(_cycle_depuis_ref(e.get("controle_ref", "")), []).append(e)

    compteur = 0
    for cycle in sorted(par_cycle):
        doc.add_heading(f"Cycle : {cycle}", level=1)
        for exc in par_cycle[cycle]:
            compteur += 1
            h = doc.add_heading(level=2)
            sev = _SEVERITE_LABELS.get(exc.get("severite", ""), exc.get("severite", ""))
            run = h.add_run(f"Point {compteur}"
                            + (f" — {sev}" if sev else ""))
            run.font.color.rgb = VIOLET

            p = doc.add_paragraph()
            p.add_run("Constat : ").bold = True
            p.add_run(exc.get("description", "") or "—")

            explication = exc.get("interpretation_llm") or exc.get("explication")
            if explication:
                p = doc.add_paragraph()
                p.add_run("Analyse préliminaire : ").bold = True
                p.add_run(str(explication))

            hypotheses = exc.get("hypotheses") or []
            if hypotheses:
                doc.add_paragraph("Causes possibles à confirmer :").runs[0].bold = True
                for hyp in hypotheses:
                    doc.add_paragraph(str(hyp), style="List Bullet")

            diligences = exc.get("diligences") or []
            if diligences:
                doc.add_paragraph("Éléments et pièces attendus de votre part :").runs[0].bold = True
                for dil in diligences:
                    doc.add_paragraph(str(dil), style="List Bullet")

            # Espace réponse client
            rep = doc.add_paragraph()
            rep.add_run("Réponse / pièces fournies : ").italic = True
            rep.add_run("_" * 55)
            doc.add_paragraph()

    doc.add_paragraph("─" * 60)
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = footer.add_run(f"Document généré par Probare le {_now()} · Confidentiel")
    r.font.size = Pt(9)
    r.italic = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
