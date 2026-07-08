"""Régression : note de planification « 0 contrôle prévu sur 0 » (23/06/2026).

Cause racine : depuis le passage de 3 à 8 cycles (registre ~52 contrôles), la
réponse JSON de `generer_programme_travail` pouvait dépasser `max_tokens` et
être tronquée ; le parsing échouait alors SILENCIEUSEMENT (`return []`), la
route effaçait le programme existant et sauvait 0 items, et la note .docx
sortait avec « 0 contrôle(s) inclus sur 0 planifiés ». Même schéma pour
`generer_note_synthese` (fallback silencieux -> section 7 vide, disparition
des paragraphes IA des sections 2/3/4/6).

Ces tests vérifient que les échecs sont désormais BRUYANTS (RuntimeError)
et que les réponses valides passent toujours.
"""
import json
import os
import types

import pytest


# ─── Fabrique d'un ClaudeClient sans clé API ni appel réseau ────────────────

def _fake_client(response_text: str, stop_reason: str = "end_turn"):
    """Construit un ClaudeClient dont l'appel messages.create est simulé."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")
    from probare_engine.llm.claude import ClaudeClient

    client = ClaudeClient()

    class _Usage:
        input_tokens = 100
        output_tokens = 200

    class _Block:
        text = response_text

    class _Resp:
        content = [_Block()]
        usage = _Usage()

    _Resp.stop_reason = stop_reason

    client._client = types.SimpleNamespace(
        messages=types.SimpleNamespace(create=lambda **kwargs: _Resp())
    )
    return client


RISQUES = [{"id": "r1", "libelle": "Risque de fraude sur la trésorerie",
            "cycle": "tresorerie", "niveau": "eleve", "valide_auditeur": 1}]
REGISTRY = [{"ref": "TRESOR-BAL-EQUIL", "libelle": "Équilibre balance",
             "cycle": "tresorerie", "nep_ref": "NEP 500"}]


# ─── generer_programme_travail ───────────────────────────────────────────────

def test_programme_reponse_valide():
    reponse = json.dumps({"items": [{
        "controle_ref": "TRESOR-BAL-EQUIL", "libelle": "Équilibre balance",
        "cycle": "tresorerie", "risque_libelle": "Risque de fraude sur la trésorerie",
        "priorite": "haute", "statut": "inclus", "notes": None,
    }]})
    client = _fake_client(reponse)
    items = client.generer_programme_travail(RISQUES, ["tresorerie"], REGISTRY)
    assert len(items) == 1
    assert items[0]["controle_ref"] == "TRESOR-BAL-EQUIL"


def test_programme_json_tronque_leve_erreur():
    # JSON coupé en plein milieu — c'est ce que produit une troncature max_tokens
    reponse = '{"items": [{"controle_ref": "TRESOR-BAL-EQUIL", "libelle": "Équi'
    client = _fake_client(reponse, stop_reason="max_tokens")
    with pytest.raises(RuntimeError, match="tronquée"):
        client.generer_programme_travail(RISQUES, ["tresorerie"], REGISTRY)


def test_programme_json_invalide_leve_erreur():
    client = _fake_client("Je ne peux pas produire de JSON aujourd'hui.")
    with pytest.raises(RuntimeError, match="illisible"):
        client.generer_programme_travail(RISQUES, ["tresorerie"], REGISTRY)


def test_programme_items_vides_retournes_tels_quels():
    # Une liste vide N'EST PAS un échec de parsing : la route décide (502, programme conservé).
    client = _fake_client('{"items": []}')
    assert client.generer_programme_travail(RISQUES, ["tresorerie"], REGISTRY) == []


# ─── generer_note_synthese ───────────────────────────────────────────────────

PROJET = {"client": "DEMO", "exercice": "2026", "cycles_couverts": ["tresorerie"]}
PLAN = {"seuil_calcule": 1000000}


def test_synthese_reponse_valide():
    reponse = json.dumps({
        "titre": "Note de synthèse de planification — DEMO — Exercice 2026",
        "sections": [{"titre": "1. Connaissance de l'entité", "contenu": "RAS."}],
        "conclusion": "Profil de risque maîtrisé.",
    })
    client = _fake_client(reponse)
    note = client.generer_note_synthese(PROJET, PLAN, None, RISQUES, [{"statut": "inclus"}])
    assert note["sections"], "les sections doivent être présentes"
    assert note["conclusion"]


def test_synthese_json_invalide_leve_erreur():
    # Avant le correctif : fallback silencieux {"titre": "Note de synthèse",
    # "sections": []} -> note .docx sans synthèse ni paragraphes IA.
    client = _fake_client("Voici la note : elle est trop longue pour du JSON.")
    with pytest.raises(RuntimeError, match="illisible"):
        client.generer_note_synthese(PROJET, PLAN, None, RISQUES, [{"statut": "inclus"}])


def test_synthese_tronquee_leve_erreur():
    reponse = '{"titre": "Note de synthèse de planification", "sections": [{"titre": "1.'
    client = _fake_client(reponse, stop_reason="max_tokens")
    with pytest.raises(RuntimeError, match="tronquée"):
        client.generer_note_synthese(PROJET, PLAN, None, RISQUES, [{"statut": "inclus"}])


def test_synthese_sections_vides_leve_erreur():
    reponse = json.dumps({"titre": "Note de synthèse", "sections": [], "conclusion": ""})
    client = _fake_client(reponse)
    with pytest.raises(RuntimeError, match="illisible|sections"):
        client.generer_note_synthese(PROJET, PLAN, None, RISQUES, [{"statut": "inclus"}])


# ─── update_planification sur ligne inexistante (trouvé au test E2E Harbi) ──

def test_update_planification_cree_la_ligne_si_absente(tmp_path):
    """Le premier PATCH de la fiche entité (avant tout GET /planification)
    doit persister — pas être un UPDATE no-op silencieux."""
    from probare_engine.storage.db import ProjectDB

    db = ProjectDB(tmp_path / "test.db")
    db.connect()
    db.create_projet({"id": "p1", "nom": "T", "etat_courant": "cadrage"})
    plan = db.update_planification("p1", {"forme_juridique": "SARL", "effectif": 14})
    assert plan["forme_juridique"] == "SARL"
    assert plan["effectif"] == 14
