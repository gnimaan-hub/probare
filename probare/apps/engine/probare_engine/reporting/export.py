"""Export dossier de travail (docx) et tableaux (xlsx) avec contrôle de provenance."""
from __future__ import annotations
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def generer_dossier_travail(
    projet: dict,
    resultats: list[dict],
    exceptions: list[dict],
    feuilles: list[dict],
    output_path: Path,
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
    info.add_run(f"Seuil de signification : {projet.get('seuil_signification', 'N/A'):,.0f} FDJ\n")
    info.add_run(f"Généré le : {_now()}\n")
    info.add_run(f"Référence NEP 230 : Dossier de travail\n")

    doc.add_paragraph("─" * 60)

    # Section résultats des contrôles
    doc.add_heading("1. Résultats des contrôles", level=1)

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
    doc.add_heading("2. Exceptions et leur traitement", level=1)

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
        if exc.get("interpretation_llm"):
            p.add_run(f"\n   Interprétation : {exc['interpretation_llm'][:200]}...")

    # Section feuilles de travail
    doc.add_heading("3. Feuilles de travail par cycle", level=1)

    for ft in feuilles:
        doc.add_heading(f"Cycle : {ft.get('cycle', 'N/A')}", level=2)
        doc.add_paragraph(ft.get("contenu_redige", ""))
        sources_ft = ft.get("sources", [])
        if sources_ft:
            doc.add_paragraph(f"Sources : {', '.join(str(s) for s in sources_ft[:5])}")

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
        ("Référence NEP",     "300 — Planification"),
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
        "2. Connaissance de l'entité (NEP 315)",
        "3. Procédures analytiques préliminaires (NEP 520)",
        "4. Seuil de signification (NEP 320)",
        "5. Cartographie des risques (NEP 315)",
        "6. Programme de travail (NEP 300 / NEP 330)",
        "7. Synthèse et conclusion",
    ]:
        doc.add_paragraph(item, style="List Number")
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. CADRE ET OBJECTIFS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("1. Cadre et objectifs de la mission")
    para(
        f"La présente note de planification est établie conformément à la NEP 300 "
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
        "NEP 300 — Planification de la mission",
        "NEP 315 — Connaissance de l'entité et identification des risques",
        "NEP 320 — Seuil de signification",
        "NEP 330 — Procédures d'audit mises en œuvre en réponse aux risques évalués",
        "NEP 520 — Procédures analytiques",
        "NEP 230 — Documentation des travaux",
    ]:
        doc.add_paragraph(nep, style="List Bullet")
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. CONNAISSANCE DE L'ENTITÉ
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("2. Connaissance de l'entité (NEP 315)")

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
    h1("3. Procédures analytiques préliminaires (NEP 520)")

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
    h1("4. Seuil de signification (NEP 320)")

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
        f"de {agregat_type}) est celui en deçà duquel une anomalie est considérée "
        "comme non significative et n'affecte pas l'opinion d'audit. "
        "Le seuil de planification de "
        f"{fmt_montant(seuil_plan)} ({taux_plan or '—'} %) est appliqué pour les "
        "tests de détail afin de conserver une marge de sécurité permettant d'absorber "
        "les anomalies non détectées. Ces paramètres sont conformes aux pratiques "
        "professionnelles et aux exigences de la NEP 320."
    )
    doc.add_page_break()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. CARTOGRAPHIE DES RISQUES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    h1("5. Cartographie des risques (NEP 315)")
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
    h1("6. Programme de travail (NEP 300 / NEP 330)")

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
        "Document confidentiel · Dossier de travail NEP 230"
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
