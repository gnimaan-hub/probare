"""Tests unitaires pour le module controls/opinion.py (NEP 450 + OPI)."""
import pytest
from probare_engine.controls.opinion import agreger_anomalies, determiner_type_opinion


def _exc(severite: str, statut: str = "tranchee", montant: float = 0.0) -> dict:
    return {
        "severite": severite,
        "statut": statut,
        "controle_ref": "TRESOR-TEST",
        "montant_anomalie": montant,
    }


# ─── agreger_anomalies ────────────────────────────────────────────────────────

def test_agregation_vide():
    result = agreger_anomalies([], seuil_signification=10000.0)
    assert result["nb_total"] == 0
    assert result["nb_critiques"] == 0
    assert result["cumul_montant"] == 0.0
    assert result["depasse_seuil"] is False


def test_agregation_comptage():
    exceptions = [
        _exc("critique"),
        _exc("significative"),
        _exc("significative"),
        _exc("mineure"),
        _exc("mineure"),
        _exc("mineure"),
    ]
    result = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert result["nb_critiques"] == 1
    assert result["nb_significatives"] == 2
    assert result["nb_mineures"] == 3
    assert result["nb_total"] == 6
    assert result["nb_tranchees"] == 6


def test_agregation_cumul_montant():
    exceptions = [
        _exc("significative", montant=3000.0),
        _exc("significative", montant=4000.0),
    ]
    result = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert result["cumul_montant"] == 7000.0
    assert result["depasse_seuil"] is True


def test_agregation_sous_seuil():
    exceptions = [_exc("mineure", montant=100.0)]
    result = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert result["depasse_seuil"] is False


def test_agregation_exceptions_ouvertes():
    exceptions = [
        _exc("critique", statut="ouverte"),
        _exc("mineure", statut="tranchee"),
    ]
    result = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert result["nb_ouvertes"] == 1
    assert result["nb_tranchees"] == 1
    # Les ouvertes ne sont pas comptées comme critiques/significatives (tranchees uniquement)
    assert result["nb_critiques"] == 0


# ─── determiner_type_opinion ──────────────────────────────────────────────────

def test_opinion_vide():
    agg = agreger_anomalies([], seuil_signification=10000.0)
    assert determiner_type_opinion(agg) == "propre"


def test_opinion_mineures_uniquement():
    exceptions = [_exc("mineure") for _ in range(5)]
    agg = agreger_anomalies(exceptions, seuil_signification=10000.0)
    assert determiner_type_opinion(agg) == "propre"


def test_opinion_critiques_refus():
    exceptions = [_exc("critique", montant=100.0)]
    agg = agreger_anomalies(exceptions, seuil_signification=10000.0)
    assert determiner_type_opinion(agg) == "refus"


def test_opinion_significatives_depasse_seuil():
    exceptions = [_exc("significative", montant=8000.0)]
    agg = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert agg["depasse_seuil"] is True
    assert determiner_type_opinion(agg) == "reserve"


def test_opinion_significatives_sous_seuil():
    exceptions = [_exc("significative", montant=500.0)]
    agg = agreger_anomalies(exceptions, seuil_signification=5000.0)
    assert agg["depasse_seuil"] is False
    assert determiner_type_opinion(agg) == "propre_avec_observation"


def test_opinion_incomplete_si_ouvertes():
    exceptions = [_exc("mineure", statut="ouverte")]
    agg = agreger_anomalies(exceptions, seuil_signification=10000.0)
    assert determiner_type_opinion(agg) == "incomplete"


def test_opinion_critiques_priorite_sur_significatives():
    exceptions = [
        _exc("critique", montant=100.0),
        _exc("significative", montant=100.0),
    ]
    agg = agreger_anomalies(exceptions, seuil_signification=10000.0)
    assert determiner_type_opinion(agg) == "refus"
