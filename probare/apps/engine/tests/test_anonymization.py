"""Tests de la couche d'anonymisation."""
from probare_engine.anonymization.anonymizer import Anonymizer


def test_pseudonymisation_basique():
    anon = Anonymizer()
    result = anon.pseudonymiser("Client : Entreprise ABC, NIF : DJI123456", ["Entreprise ABC", "DJI123456"])
    assert "Entreprise ABC" not in result
    assert "DJI123456" not in result
    assert "[ENTITE_" in result


def test_re_identification():
    anon = Anonymizer()
    pseudonymise = anon.pseudonymiser("Client ABC doit 5000", ["Client ABC"])
    re_identifie = anon.re_identifier(pseudonymise)
    assert "Client ABC" in re_identifie


def test_montants_non_modifies():
    anon = Anonymizer()
    texte = "Le montant de 50000 XDJ est dû par Client X"
    result = anon.pseudonymiser(texte, ["Client X"])
    assert "50000" in result
    assert "XDJ" in result


def test_aucun_token_envoye():
    """La table de correspondance reste locale — jamais sérialisée."""
    anon = Anonymizer()
    anon.pseudonymiser("Fournisseur Y", ["Fournisseur Y"])
    # La table interne ne doit jamais figurer dans le texte pseudonymisé
    assert anon.nb_entites == 1
    # Vérifier qu'on peut retrouver la valeur réelle localement
    token = anon._real_to_token["Fournisseur Y"]
    assert anon._token_to_real[token] == "Fournisseur Y"


def test_pseudonymisation_dict():
    anon = Anonymizer()
    data = {"description": "Facture de Dupont SA", "montant": "1000"}
    result = anon.pseudonymiser_dict(data, ["description"], ["Dupont SA"])
    assert "Dupont SA" not in result["description"]
    assert result["montant"] == "1000"
