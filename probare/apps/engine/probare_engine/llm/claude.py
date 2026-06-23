"""Implémentation Claude de LLMClient — SDK anthropic."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Any
import anthropic
from .client import LLMClient


MODEL_DEFAULT = "claude-sonnet-4-6"
MODEL_ESCALADE = "claude-opus-4-8"
MODEL_SIMPLE = "claude-haiku-4-5-20251001"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaudeClient(LLMClient):
    """Implémentation Claude. Clé via ANTHROPIC_API_KEY."""

    def __init__(self, audit_logger=None):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY non définie dans l'environnement.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._audit_logger = audit_logger

    def _log(self, model: str, usage_type: str, tokens_in: int, tokens_out: int) -> None:
        if self._audit_logger:
            self._audit_logger("appel_llm", {
                "modele": model,
                "usage": usage_type,
                "tokens_entree": tokens_in,
                "tokens_sortie": tokens_out,
                "horodatage": _now(),
            })

    def mapper_colonnes(
        self,
        colonnes: list[str],
        exemples: dict[str, list[str]],
    ) -> dict:
        """Utilise Haiku pour classifier les colonnes d'un export comptable."""
        prompt = f"""Tu es un expert en comptabilité. Voici les colonnes d'un fichier comptable :
{json.dumps(colonnes, ensure_ascii=False)}

Exemples de valeurs par colonne :
{json.dumps(exemples, ensure_ascii=False, indent=2)}

Propose un mapping entre chaque nom de colonne et l'un des champs suivants :
compte, libelle, debit, credit, date, numero_piece, solde, exercice, autre

Règles :
- Chaque champ audit ne peut être assigné qu'une seule fois (sauf "autre").
- Si une colonne ne correspond à aucun champ, utilise "autre".
- Ne produis aucun calcul, aucun montant.

Réponds UNIQUEMENT avec un JSON valide de la forme :
{{"mapping": {{"NomColonne1": "champ1", "NomColonne2": "champ2", ...}}, "confiance": 0.0-1.0, "notes": "..."}}"""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "mapper_colonnes",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "mapping" in result:
            return result
        return {"mapping": {}, "confiance": 0.0, "notes": "Réponse non parseable."}

    # ─── Ingestion intelligente ────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Any:
        """Parse JSON depuis une réponse LLM en tolérant du texte avant/après."""
        import re as _re
        text = _re.sub(r"```(?:json)?\s*", "", text.strip()).strip()
        start = text.find("{")
        start_arr = text.find("[")
        # Prendre le premier délimiteur
        if start_arr >= 0 and (start < 0 or start_arr < start):
            end = text.rfind("]") + 1
            if end > start_arr:
                try:
                    return json.loads(text[start_arr:end])
                except Exception:
                    pass
        if start >= 0:
            end = text.rfind("}") + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except Exception:
                    pass
        return None

    def analyser_document_ingestion(
        self,
        nom_fichier: str,
        contenu_texte: str,
        documents_attendus: list[dict],
    ) -> dict:
        """Haiku identifie la nature d'un document déposé pour l'audit."""
        types_attendus = ", ".join(
            f"{d['type']} ({d.get('label', d['type'])})" for d in documents_attendus
        )
        prompt = f"""Tu es expert-comptable chargé d'identifier la nature d'un document d'audit.

Nom du fichier : {nom_fichier}

Contenu extrait (premiers caractères) :
{contenu_texte[:4000]}

Documents attendus dans cette mission : {types_attendus or "aucun spécifié"}

Identifie la nature de ce document. Types comptables reconnus :
- grand_livre : journal détaillé des écritures (date, compte, libellé, débit, crédit, pièce)
- balance : résumé par compte (soldes, totaux débits/crédits)
- releve_bancaire : extrait de compte bancaire
- bulletin_paie : fiche de paie employé
- facture : facture fournisseur ou client
- declaration_fiscale : TVA, impôts, déclarations
- contrat : accord, bail, convention
- rapport : rapport de gestion, rapport CA
- autre : tout autre document

Réponds UNIQUEMENT avec ce JSON valide (sans commentaire) :
{{
  "nature": "grand_livre|balance|releve_bancaire|bulletin_paie|facture|declaration_fiscale|contrat|rapport|autre",
  "type_comptable": "grand_livre|balance|releve_bancaire|null",
  "description": "Description en 1-2 phrases de ce que contient ce document",
  "objectif": "Utilité de ce document dans un contexte d'audit en 1 phrase",
  "correspond_a": "grand_livre|balance|releve_bancaire|null",
  "confiance": 0.0
}}"""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "analyser_document_ingestion",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if not isinstance(result, dict):
            return {"nature": "autre", "type_comptable": None, "correspond_a": None,
                    "description": nom_fichier, "objectif": "", "confiance": 0.0}
        # Normaliser correspond_a : null/None/string "null" → None
        if result.get("correspond_a") in (None, "null", ""):
            result["correspond_a"] = None
        if result.get("type_comptable") in (None, "null", ""):
            result["type_comptable"] = None
        return result

    def analyser_onglets_excel(
        self,
        nom_fichier: str,
        onglets: list[dict],
        documents_attendus: list[dict],
    ) -> list[dict]:
        """Haiku analyse chaque onglet d'un Excel et identifie sa nature."""
        types_attendus = ", ".join(
            f"{d['type']} ({d.get('label', d['type'])})" for d in documents_attendus
        )
        onglets_desc = ""
        for o in onglets:
            onglets_desc += f"\n--- Onglet : {o['nom']} ---\n"
            onglets_desc += f"Colonnes : {', '.join(o.get('colonnes', [])[:20])}\n"
            onglets_desc += f"Aperçu :\n{o.get('apercu', '')[:800]}\n"

        prompt = f"""Tu es expert-comptable. Analyse les onglets du fichier Excel "{nom_fichier}".

Documents attendus dans la mission : {types_attendus or "aucun spécifié"}

{onglets_desc}

Pour chaque onglet, identifie sa nature et si elle correspond à un document attendu.

Réponds UNIQUEMENT avec un tableau JSON (un objet par onglet, même ordre) :
[
  {{
    "nom_onglet": "nom exact de l'onglet",
    "nature": "grand_livre|balance|releve_bancaire|bulletin_paie|facture|autre",
    "type_comptable": "grand_livre|balance|releve_bancaire|null",
    "description": "ce que contient cet onglet en 1 phrase",
    "correspond_a": "grand_livre|balance|releve_bancaire|null",
    "confiance": 0.0,
    "recommande_import": true
  }}
]"""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "analyser_onglets_excel",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if not isinstance(result, list):
            return []
        for item in result:
            if item.get("correspond_a") in (None, "null", ""):
                item["correspond_a"] = None
            if item.get("type_comptable") in (None, "null", ""):
                item["type_comptable"] = None
        return result

    def decouper_liasse_document(
        self,
        nom_fichier: str,
        contenu_texte: str,
    ) -> dict:
        """Haiku identifie les frontières de documents dans une liasse PDF/Word."""
        prompt = f"""Tu es expert-comptable. Le fichier "{nom_fichier}" semble être une liasse regroupant plusieurs documents.

Contenu extrait :
{contenu_texte[:7000]}

Identifie s'il s'agit bien d'une liasse de documents distincts, et si oui, liste chaque document.

Réponds UNIQUEMENT avec ce JSON valide :
{{
  "est_liasse": true,
  "nb_documents": 1,
  "description_globale": "Description synthétique du contenu de la liasse",
  "documents": [
    {{
      "titre": "Titre ou type du document",
      "type": "facture|releve_bancaire|bulletin_paie|contrat|declaration_fiscale|rapport|autre",
      "reference": "numéro/référence si détecté ou null",
      "description": "Ce que contient ce document en 1 phrase",
      "debut_approximatif": "début du document (ex: 'Début du fichier' ou 'Après la facture X')",
      "fin_approximatif": "fin approximative"
    }}
  ]
}}

Si ce n'est pas une liasse (document unique), réponds avec est_liasse: false et nb_documents: 1."""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "decouper_liasse_document",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if not isinstance(result, dict):
            return {"est_liasse": False, "nb_documents": 1, "documents": [], "description_globale": ""}
        return result

    # ─── Évaluation Contrôle Interne ──────────────────────────────────────────

    def evaluer_controle_interne(
        self,
        cycle: str,
        reponses: list[dict],  # [{question_id, question, reponse, commentaire, risque_si_non}]
        contexte_projet: dict,
    ) -> dict:
        """Haiku synthétise l'évaluation du CI pour un cycle à partir des réponses QCI."""
        nb_oui = sum(1 for r in reponses if r.get("reponse") == "oui")
        nb_non = sum(1 for r in reponses if r.get("reponse") == "non")
        nb_na  = sum(1 for r in reponses if r.get("reponse") == "na")
        total  = nb_oui + nb_non
        score  = round(nb_oui / total, 2) if total > 0 else 0.0

        niveau = "élevé"
        if score >= 0.70:
            niveau = "faible"
        elif score >= 0.40:
            niveau = "moyen"

        reponses_txt = ""
        for r in reponses:
            reponses_txt += f"\n- [{r.get('reponse', '?').upper()}] {r.get('question', r.get('question_id', ''))}"
            if r.get("reponse") == "non" and r.get("risque_si_non"):
                reponses_txt += f"\n  → Risque : {r['risque_si_non']}"
            if r.get("commentaire"):
                reponses_txt += f"\n  → Commentaire auditeur : {r['commentaire']}"

        prompt = f"""Tu es auditeur senior. Tu évalues le contrôle interne du cycle {cycle.upper()} d'une entité dans le cadre d'un audit contractuel (Djibouti, référentiel NEP 315).

Entité : {contexte_projet.get('client', 'N/A')} — Exercice {contexte_projet.get('exercice', 'N/A')}

Score QCI : {nb_oui}/{total} (score = {score:.0%}) → Risque CI : {niveau.upper()}

Réponses au questionnaire :{reponses_txt}

Rédige une évaluation professionnelle du contrôle interne. Identifie les forces, les faiblesses significatives et leur implication sur les travaux d'audit.

Réponds UNIQUEMENT avec ce JSON valide :
{{
  "synthese": "Paragraphe de synthèse en 3-4 phrases — niveau de risque, raison principale, implication sur les travaux",
  "forces": ["Force 1", "Force 2"],
  "faiblesses": [
    "Faiblesse significative 1 (mention du risque associé)",
    "Faiblesse significative 2"
  ],
  "recommandations": [
    "Recommandation pour l'auditeur : ajuster les tests sur X en raison de Y",
    "Recommandation 2"
  ],
  "niveau_risque": "{niveau}",
  "score": {score}
}}"""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "evaluer_controle_interne",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if not isinstance(result, dict):
            return {
                "synthese": f"Évaluation automatique : score {score:.0%}, risque {niveau}.",
                "forces": [], "faiblesses": [], "recommandations": [],
                "niveau_risque": niveau, "score": score,
            }
        result.setdefault("niveau_risque", niveau)
        result.setdefault("score", score)
        return result

    def interpreter_exception(
        self,
        exception: dict,
        donnees_sources: list[dict],
        contexte_projet: dict,
    ) -> dict:
        """Interprète une exception et propose une décision de tranchement. Ne recalcule rien."""
        prompt = f"""Tu es auditeur senior certifié. Le moteur de contrôle déterministe a levé l'exception suivante.
Ton rôle : l'analyser, l'expliquer, et proposer une décision de tranchement documentée.

Contrôle : {exception.get('controle_ref')} ({exception.get('nep_ref')})
Sévérité : {exception.get('severite')}
Description technique du moteur : {exception.get('description')}

Contexte de la mission :
{json.dumps(contexte_projet, ensure_ascii=False)}

Ta tâche (sans jamais produire de calculs ni de montants non reçus ci-dessus) :
1. Expliquer l'exception en langage clair pour l'auditeur responsable.
2. Lister 2-3 hypothèses de cause les plus probables dans ce contexte.
3. Proposer les diligences à effectuer (pièces à demander, vérifications à mener).
4. Rédiger une décision de tranchement documentée, professionnelle et argumentée, prête à être validée ou modifiée par l'auditeur. Cette décision doit être rédigée à la première personne de l'auditeur.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "explication": "explication claire en 2-3 phrases",
  "hypotheses": ["hypothèse 1", "hypothèse 2", "hypothèse 3"],
  "diligences": ["diligence 1", "diligence 2"],
  "decision_proposee": "Texte complet de la décision rédigée, prêt à signer. Ex: J'ai examiné cette exception... L'écart s'explique par... Après vérification... Je tranche en faveur de...",
  "urgence": "faible|moyenne|elevee"
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "interpreter_exception",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "explication" in result:
            return result
        return {
            "explication": resp.content[0].text[:500],
            "hypotheses": [],
            "diligences": [],
            "decision_proposee": "",
            "urgence": "moyenne",
        }

    def analyser_document_annexe(
        self,
        nom: str,
        description: str,
        texte_brut: str,
    ) -> dict:
        """
        Analyse textuelle d'un document annexe. Ne calcule rien.
        Retourne un résumé, des points clés et des alertes potentielles.
        """
        prompt = f"""Tu es auditeur senior. L'auditeur t'a fourni un document annexe à analyser.

Nom du document : {nom}
Description de l'auditeur : {description or "Non précisée"}

Contenu extrait (texte brut, peut être partiel) :
---
{texte_brut or "[Contenu non lisible]"}
---

Ta tâche :
1. Rédige un résumé concis du document (3-5 phrases maximum).
2. Identifie les points clés pertinents pour l'audit (clauses, engagements, montants cités, parties).
3. Signale les alertes potentielles (clauses inhabituelles, risques, incohérences apparentes).

Règles ABSOLUES :
- Tu ne produis pas de calculs. Si tu cites un montant, c'est uniquement parce qu'il est écrit dans le texte ci-dessus.
- Reste factuel. Ne présume pas de ce qui n'est pas dans le texte.
- Langue : français professionnel.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "resume": "Résumé du document en 3-5 phrases.",
  "points_cles": ["Point 1", "Point 2", "Point 3"],
  "alertes": ["Alerte 1 si applicable"]
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "analyser_document_annexe",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "resume" in result:
            return result
        return {
            "resume": resp.content[0].text[:500],
            "points_cles": [],
            "alertes": [],
        }

    def cataloguer_document(
        self,
        nom: str,
        contenu_texte: str,
        contenu_b64: str = "",
        media_type: str = "",
    ) -> dict:
        """Haiku — identifie le type et décrit un document brut pour l'audit."""
        _contenu_block = ("Contenu extrait :\n" + contenu_texte[:5000]) if contenu_texte \
            else "(Aucun contenu texte — base-toi sur le nom du fichier)"
        prompt = f"""Tu es un expert-comptable et auditeur. Analyse ce document et identifie-le.

Nom du fichier : {nom}

{_contenu_block}

Identifie le type parmi : facture_achat, facture_vente, releve_bancaire, grand_livre, balance, note_frais, contrat, attestation, rapport, ordre_virement, bordereau_remise, autre.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "type_detecte": "...",
  "description": "Description en 2-3 phrases pour l'auditeur.",
  "parties": ["Émetteur ou fournisseur...", "Destinataire ou client..."],
  "dates": ["YYYY-MM-DD ou description si flou"],
  "montants_cles": ["montant + devise si visibles"],
  "pertinence_audit": "elevee|moyenne|faible"
}}"""

        content: list = []
        if contenu_b64 and media_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64",
                 "media_type": media_type, "data": contenu_b64}},
                {"type": "text", "text": prompt},
            ]
        else:
            content = [{"type": "text", "text": prompt}]

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )
        self._log(MODEL_SIMPLE, "cataloguer_document",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "type_detecte" in result:
            return result
        return {
            "type_detecte": "autre",
            "description": resp.content[0].text[:300],
            "parties": [],
            "dates": [],
            "montants_cles": [],
            "pertinence_audit": "faible",
        }

    def extraire_donnees_comptables(
        self,
        nom: str,
        type_detecte: str,
        description: str,
        contenu_texte: str,
        contenu_b64: str = "",
        media_type: str = "",
    ) -> dict:
        """Sonnet — extrait les données comptables structurées d'un document brut.

        Règle fondamentale : le LLM recopie les chiffres du document, il ne calcule rien.
        """
        _contenu_block = ("Contenu :\n" + contenu_texte[:6000]) if contenu_texte else ""
        prompt = f"""Tu es un expert-comptable. Extrais TOUTES les données comptables de ce document.

Document : {nom}
Type détecté : {type_detecte}
Description : {description}

{_contenu_block}

Règles ABSOLUES :
1. Ne produis AUCUN calcul. Recopie exactement les chiffres visibles dans le document.
2. Chaque ligne = une écriture comptable ou une ligne de relevé bancaire.
3. Si un champ est absent, mets null ou 0.
4. Le champ "compte" doit contenir le numéro de compte (ex : 60100, 401000).
   Si le compte n'est pas visible, déduis-le du type :
   - facture_achat : compte 60x (charges) débit, 40x (fournisseurs) crédit
   - facture_vente : compte 41x (clients) débit, 70x (produits) crédit
5. type_sortie :
   - facture_achat / facture_vente → "grand_livre"
   - releve_bancaire → "releve_bancaire"
   - grand_livre → "grand_livre"
   - balance → "balance"
   - autre → "grand_livre"

Réponds UNIQUEMENT avec un JSON valide :
{{
  "type_sortie": "grand_livre|balance|releve_bancaire",
  "lignes": [
    {{
      "date": "YYYY-MM-DD ou vide",
      "compte": "numéro de compte ou vide",
      "libelle": "libellé de l'écriture",
      "debit": 0.0,
      "credit": 0.0,
      "reference": "numéro de pièce ou vide",
      "tiers": "nom du tiers ou vide"
    }}
  ]
}}"""

        content: list = []
        if contenu_b64 and media_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64",
                 "media_type": media_type, "data": contenu_b64}},
                {"type": "text", "text": prompt},
            ]
        else:
            content = [{"type": "text", "text": prompt}]

        resp = self._client.messages.create(
            model=MODEL_ESCALADE,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        self._log(MODEL_ESCALADE, "extraire_donnees_comptables",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "lignes" in result:
            result["nb_lignes"] = len(result.get("lignes", []))
            return result
        return {"type_sortie": "grand_livre", "lignes": [], "nb_lignes": 0}

    def verifier_extraction_donnees(
        self,
        nom: str,
        type_detecte: str,
        lignes: list[dict],
        contenu_texte: str,
        contenu_b64: str = "",
        media_type: str = "",
    ) -> dict:
        """Sonnet — vérifie ligne par ligne que l'extraction d'Opus correspond au document source.

        Ne recalcule rien. Compare uniquement les valeurs extraites avec le texte source.
        """
        import json as _json
        _contenu_block = ("Document source :\n" + contenu_texte[:5000]) if contenu_texte else ""
        _lignes_block = _json.dumps(lignes[:50], ensure_ascii=False, indent=2)
        prompt = f"""Tu es auditeur senior. Opus a extrait des données comptables d'un document.
Ton rôle : vérifier chaque ligne extraite contre le document source et signaler les anomalies.

Document : {nom}
Type : {type_detecte}

{_contenu_block}

Données extraites par Opus :
{_lignes_block}

Pour chaque ligne extraite, vérifie :
1. Le montant (débit ou crédit) est-il exactement celui visible dans le document ?
2. La date est-elle correcte ?
3. Le libellé est-il fidèle ?
4. Y a-t-il un compte comptable visible dans le source que Opus aurait manqué ?

Règles ABSOLUES :
- Tu ne produis aucun calcul, aucun montant inventé.
- Toute valeur que tu cites doit être présente dans le texte source ci-dessus.
- Si le texte source est absent ou illisible, indique confiance=0.5 pour toutes les lignes.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "score_global": 0.0,
  "lignes_verifiees": [
    {{
      "index": 0,
      "confiance": 1.0,
      "anomalie": false,
      "commentaire": "Montant et date confirmés dans le source."
    }}
  ],
  "resume_verification": "Synthèse globale en 1-2 phrases."
}}"""

        content: list = []
        if contenu_b64 and media_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64",
                 "media_type": media_type, "data": contenu_b64}},
                {"type": "text", "text": prompt},
            ]
        else:
            content = [{"type": "text", "text": prompt}]

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
        )
        self._log(MODEL_DEFAULT, "verifier_extraction_donnees",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "score_global" in result:
            return result
        return {
            "score_global": 0.5,
            "lignes_verifiees": [],
            "resume_verification": resp.content[0].text[:300],
        }

    def interpreter_variations_analytiques(
        self,
        variations_significatives: list[dict],
        fiche_entite: dict,
        seuil_signification: float | None,
        contexte_projet: dict,
    ) -> dict:
        """
        Sonnet interprète les variations analytiques significatives N/N-1.
        Ne calcule rien — les chiffres viennent tous de variations_significatives.
        """
        seuil_txt = f"{seuil_signification:,.0f} FDJ" if seuil_signification else "non défini"
        prompt = f"""Tu es auditeur senior certifié. Le moteur d'analyse déterministe a calculé
les variations N/N-1 significatives de la balance générale.

Seuil de signification de la mission : {seuil_txt}
Exercice audité : {contexte_projet.get('exercice', 'N/A')}
Secteur de l'entité : {fiche_entite.get('activites_principales', 'N/A')}
Forme juridique : {fiche_entite.get('forme_juridique', 'N/A')}

Variations significatives détectées (calculées par Python, ne les recalcule pas) :
{json.dumps(variations_significatives[:30], ensure_ascii=False, indent=2)}

Ta mission (sans produire aucun montant non reçu ci-dessus) :
1. Synthèse : les 3-5 variations les plus importantes et leur signification probable.
2. Zones à risque : quels cycles ou assertions méritent une attention renforcée ?
3. Facteurs contextuels : variations explicables par le secteur d'activité ? par une événement économique ?
4. Alerte : y a-t-il des incohérences flagrantes entre les comptes ?

Langue : français professionnel, style rapport d'audit.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "synthese": "Paragraphe de synthèse (5-8 phrases).",
  "zones_risque": [
    {{"cycle": "tresorerie|achats|ventes|transversal", "libelle": "...", "niveau": "eleve|moyen|faible", "explication": "..."}}
  ],
  "facteurs_contextuels": "Explication des variations par le contexte (2-3 phrases).",
  "alertes": ["Alerte 1 si applicable", "Alerte 2"]
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "interpreter_variations_analytiques",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "synthese" in result:
            return result
        return {
            "synthese": resp.content[0].text[:800],
            "zones_risque": [],
            "facteurs_contextuels": "",
            "alertes": [],
        }

    def proposer_risques(
        self,
        fiche_entite: dict,
        zones_risque: list[dict],
        cycles_couverts: list[str],
        risques_existants: list[dict],
    ) -> list[dict]:
        """
        Sonnet propose une cartographie de risques à partir de la fiche entité
        et des zones identifiées lors des procédures analytiques.
        Ne calcule rien. Propose uniquement — l'auditeur valide.
        """
        ASSERTIONS = ["existence", "exhaustivite", "evaluation", "cut_off", "droits", "presentation"]
        prompt = f"""Tu es auditeur senior. Tu dois proposer une cartographie des risques d'audit
pour cette entité, en te basant sur la fiche de connaissance et les variations analytiques.

Fiche entité :
{json.dumps(fiche_entite, ensure_ascii=False, indent=2)}

Zones à risque identifiées par les procédures analytiques :
{json.dumps(zones_risque, ensure_ascii=False, indent=2)}

Cycles couverts par la mission : {', '.join(cycles_couverts)}

Risques déjà renseignés (ne pas dupliquer) :
{json.dumps([r.get('libelle') for r in risques_existants], ensure_ascii=False)}

Assertions disponibles : {ASSERTIONS}
Cycles valides : tresorerie, achats, ventes, transversal
Niveaux : eleve, moyen, faible
Sources : analytique, entite, inherent, ia

Ta mission :
Propose entre 5 et 12 risques pertinents et distincts. Pour chaque risque :
- libelle court et précis (< 80 caractères)
- description explicative (1-2 phrases)
- cycle concerné
- niveau de risque justifié
- assertions impactées (sous-ensemble de : {ASSERTIONS})
- source du risque

Ne produis aucun montant non reçu. Reste factuel et professionnel.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "risques": [
    {{
      "libelle": "...",
      "description": "...",
      "cycle": "tresorerie|achats|ventes|transversal",
      "niveau": "eleve|moyen|faible",
      "assertions": ["existence", "exhaustivite"],
      "source": "analytique|entite|inherent|ia"
    }}
  ]
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "proposer_risques",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict):
            return result.get("risques", [])
        return []

    def reformuler_risque(self, risque: dict) -> dict:
        """
        Sonnet reformule un risque saisi manuellement pour l'homogénéiser
        avec les risques générés par l'IA (même format, même vocabulaire).
        Ne modifie pas le cycle ni le niveau — uniquement libellé, description, assertions.
        """
        ASSERTIONS = ["existence", "exhaustivite", "evaluation", "cut_off", "droits", "presentation"]
        prompt = f"""Tu es auditeur senior. Un auditeur vient de saisir manuellement un risque d'audit.
Reformule-le pour qu'il soit précis, professionnel et homogène avec une cartographie des risques d'audit.

Risque saisi :
- Libellé : {risque.get('libelle', '')}
- Description : {risque.get('description', '')}
- Cycle : {risque.get('cycle', '')}
- Niveau : {risque.get('niveau', '')}
- Assertions : {risque.get('assertions', [])}

Règles :
- Libellé : < 80 caractères, précis, en français professionnel (commence par un verbe ou un nom de risque)
- Description : 1-2 phrases expliquant le risque et son impact potentiel
- Assertions : sous-ensemble de {ASSERTIONS}, pertinentes pour ce risque
- Ne modifie pas le cycle ni le niveau
- Garde l'intention de l'auditeur, améliore uniquement la formulation

Réponds UNIQUEMENT avec un JSON valide :
{{
  "libelle": "...",
  "description": "...",
  "assertions": ["..."]
}}"""

        resp = self._client.messages.create(
            model=MODEL_SIMPLE,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_SIMPLE, "reformuler_risque",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        return result if isinstance(result, dict) else {}

    def generer_note_synthese(
        self,
        projet: dict,
        plan: dict,
        interpretation: dict | None,
        risques_valides: list[dict],
        programme_inclus: list[dict],
    ) -> dict:
        """
        Sonnet génère une note de synthèse de planification qui justifie le programme de travail.
        Répond à : Comment est né ce plan ? Pourquoi ces contrôles et pas d'autres ?
        """
        prompt = f"""Tu es auditeur senior. Tu dois rédiger la **note de synthèse de planification** de cette mission d'audit.
Ce document doit permettre à tout lecteur de comprendre pourquoi ce programme de travail a été retenu.

--- CONTEXTE MISSION ---
Client : {projet.get('client', 'N/A')}
Exercice audité : {projet.get('exercice', 'N/A')}
Nature de mission : {projet.get('nature_mission', 'contractuelle')}
Cycles couverts : {projet.get('cycles_couverts', [])}

--- FICHE ENTITÉ ---
Forme juridique : {plan.get('forme_juridique', 'N/A')}
Activités : {plan.get('activites_principales', 'N/A')}
Marchés : {plan.get('marches_principaux', 'N/A')}
Système d'information : {plan.get('systeme_information', 'N/A')}
Facteurs de risque inhérent : {plan.get('facteurs_risque_inherent', 'N/A')}

--- PROCÉDURES ANALYTIQUES ---
Seuil de signification retenu : {plan.get('seuil_calcule', 'N/A')} FDJ
{f"Synthèse des variations : {interpretation.get('synthese', '')}" if interpretation else "Pas de procédures analytiques N/N-1 effectuées."}
{f"Zones à risque identifiées : {json.dumps(interpretation.get('zones_risque', []), ensure_ascii=False)}" if interpretation else ""}

--- CARTOGRAPHIE DES RISQUES (validée par l'auditeur) ---
{json.dumps(risques_valides, ensure_ascii=False, indent=2)}

--- PROGRAMME DE TRAVAIL RETENU ---
{json.dumps(programme_inclus, ensure_ascii=False, indent=2)}

Ta mission :
Rédige une note de synthèse structurée en 4 parties :
1. **Connaissance de l'entité** — résumé du profil entité et des facteurs de risque inhérent
2. **Résultats des procédures analytiques** — ce que les chiffres révèlent, les zones d'attention
3. **Cartographie des risques et seuil** — risques retenus, leur niveau, les assertions visées, pourquoi
4. **Justification du programme de travail** — pourquoi ces contrôles, dans quel ordre, avec quelle intensité

Ton texte doit permettre de répondre à : "Pourquoi ce plan de travail et pas un autre ?"
Sois factuel, précis, professionnel. Utilise la première personne du pluriel ("nous avons").
Ne cite aucun montant qui ne serait pas dans les données fournies.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "titre": "Note de synthèse de planification — [Client] — Exercice [N]",
  "sections": [
    {{
      "titre": "1. Connaissance de l'entité",
      "contenu": "..."
    }},
    {{
      "titre": "2. Résultats des procédures analytiques",
      "contenu": "..."
    }},
    {{
      "titre": "3. Cartographie des risques et seuil de signification",
      "contenu": "..."
    }},
    {{
      "titre": "4. Justification du programme de travail",
      "contenu": "..."
    }}
  ],
  "conclusion": "..."
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "generer_note_synthese",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "sections" in result:
            return result
        return {"titre": "Note de synthèse", "sections": [], "conclusion": ""}

    def generer_programme_travail(
        self,
        risques_valides: list[dict],
        cycles_couverts: list[str],
        controles_registry: list[dict],
    ) -> list[dict]:
        """
        Sonnet génère un programme de travail adapté aux risques identifiés.
        Lie chaque contrôle du registre aux risques pertinents.
        Ne calcule rien.
        """
        prompt = f"""Tu es auditeur senior. Tu dois générer le programme de travail d'audit
en sélectionnant et priorisant les contrôles à mener selon les risques identifiés.

Risques validés par l'auditeur :
{json.dumps(risques_valides, ensure_ascii=False, indent=2)}

Cycles couverts : {', '.join(cycles_couverts)}

Registre des contrôles disponibles (réf → libellé → cycle → NEP) :
{json.dumps(controles_registry, ensure_ascii=False, indent=2)}

Pour chaque contrôle du registre que tu juges pertinent (en fonction des risques) :
1. Indique s'il doit être inclus ou exclu.
2. Associe-le au risque (libelle du risque) le plus pertinent parmi les risques fournis.
3. Attribue une priorité : haute (risque élevé lié), normale, faible (contrôle de routine).
4. Ajoute une note courte sur l'adaptation à ce contexte précis (1 phrase max).

Règle : si un risque élevé touche un cycle, tous les contrôles de ce cycle passent en priorité haute.

Réponds UNIQUEMENT avec un JSON valide :
{{
  "items": [
    {{
      "controle_ref": "TRESOR-BAL-EQUIL",
      "libelle": "Vérification de l'équilibre de la balance",
      "cycle": "tresorerie",
      "risque_libelle": "libellé du risque associé ou null",
      "priorite": "haute|normale|faible",
      "statut": "inclus|exclu",
      "notes": "Note contextuelle courte ou null"
    }}
  ]
}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "generer_programme_travail",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict):
            return result.get("items", [])
        return []

    def rediger_feuille_travail(
        self,
        cycle: str,
        resultats: list[dict],
        exceptions: list[dict],
        contexte_projet: dict,
    ) -> dict:
        """Rédige une feuille de travail à partir de résultats déjà calculés."""
        prompt = f"""Tu es auditeur senior. Rédige la feuille de travail pour le cycle {cycle}
en français, conformément aux NEP, à partir des résultats déterministes suivants.

Résultats des contrôles (calculés par le code, ne les modifie pas) :
{json.dumps(resultats[:20], ensure_ascii=False, indent=2)}

Exceptions levées et tranchées :
{json.dumps(exceptions[:10], ensure_ascii=False, indent=2)}

Contexte : {json.dumps(contexte_projet, ensure_ascii=False)}

Règles :
- Ne produis aucun montant que tu n'as pas reçu dans les données ci-dessus.
- Référence chaque chiffre à sa source (controle_ref).
- Structure : Objectif, Procédures effectuées, Résultats, Anomalies non corrigées, Conclusion.
- Langue : français professionnel.

Réponds UNIQUEMENT avec un JSON valide :
{{"titre": "...", "contenu": "...", "nep_refs": ["..."], "conclusion": "sans_reserve|reserve|refus"}}"""

        resp = self._client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        self._log(MODEL_DEFAULT, "rediger_feuille_travail",
                  resp.usage.input_tokens, resp.usage.output_tokens)

        result = self._parse_json(resp.content[0].text)
        if isinstance(result, dict) and "contenu" in result:
            return result
        return {
            "titre": f"Feuille de travail — {cycle}",
            "contenu": resp.content[0].text,
            "nep_refs": [],
            "conclusion": "sans_reserve",
        }
