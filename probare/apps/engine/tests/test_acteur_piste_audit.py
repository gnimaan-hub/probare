"""Piste d'audit — identification de l'auteur des actions (ISA 230).

Une documentation d'audit qui n'identifie pas la personne ayant exécuté le
travail ne satisfait pas ISA 230. Ces tests figent le fait que le nom saisi
dans la fiche Cabinet, transmis par l'en-tête « X-Probare-Acteur », atterrit
bien dans la colonne `journal.acteur`.

Le point réellement fragile est la PROPAGATION : le nom voyage par
`ContextVar`, posé dans un middleware asynchrone, et doit rester visible dans
les routes synchrones, que Starlette exécute dans un thread de travail. Si
cette propagation cassait — mise à jour de Starlette ou d'anyio —, la piste
d'audit redeviendrait anonyme en silence. C'est ce que vérifie
`test_acteur_traverse_middleware_et_route_synchrone`.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("PROBARE_DATA_DIR", "/tmp/probare_test_acteur/projets")

from probare_engine.acteur import acteur_courant, definir_acteur, normaliser


# ─── Normalisation du nom ────────────────────────────────────────────────────

class TestNormalisation:
    def test_nom_simple_conserve(self):
        assert normaliser("Awale Hassan") == "Awale Hassan"

    def test_espaces_superflus_retires(self):
        assert normaliser("  Awale Hassan  ") == "Awale Hassan"

    @pytest.mark.parametrize("vide", [None, "", "   "])
    def test_vide_donne_none(self, vide):
        assert normaliser(vide) is None

    def test_caracteres_de_controle_retires(self):
        """Un retour chariot dans le nom permettrait de maquiller une ligne de
        journal en en fabriquant une seconde à la lecture."""
        assert normaliser("Awale\nAdministrateur") == "AwaleAdministrateur"
        assert normaliser("Awale\x00\tHassan") == "AwaleHassan"

    def test_nom_tronque_a_la_longueur_max(self):
        assert len(normaliser("A" * 500)) == 120

    def test_nom_uniquement_caracteres_de_controle_donne_none(self):
        assert normaliser("\n\t\x00") is None


# ─── Écriture en base ────────────────────────────────────────────────────────

class TestColonneJournal:
    @pytest.fixture
    def db(self, tmp_path):
        from probare_engine.storage.db import ProjectDB
        d = ProjectDB(tmp_path / "audit.db")
        d.connect()
        # `journal.projet_id` référence `projet(id)` et les clés étrangères sont
        # actives : le projet doit exister avant qu'on puisse le journaliser.
        d.create_projet({"id": "p1", "nom": "Projet de test"})
        yield d
        d.close()

    def test_log_enregistre_l_acteur_du_contexte(self, db):
        token = definir_acteur("Awale Hassan (Commissaire aux comptes)")
        try:
            db.log("p1", "action_humaine", {"quoi": "validation"})
        finally:
            from probare_engine.acteur import reinitialiser_acteur
            reinitialiser_acteur(token)
        ligne = db.get_journal("p1")[0]
        assert ligne["acteur"] == "Awale Hassan (Commissaire aux comptes)"

    def test_log_sans_contexte_laisse_acteur_null(self, db):
        """Hors requête HTTP (tâche de fond, script) il n'y a pas d'auteur
        humain : mieux vaut NULL qu'un nom par défaut trompeur."""
        assert acteur_courant() is None
        db.log("p1", "transition_etat", {"vers": "revue"})
        assert db.get_journal("p1")[0]["acteur"] is None

    def test_acteur_explicite_prime_sur_le_contexte(self, db):
        token = definir_acteur("Contexte")
        try:
            db.log("p1", "action_humaine", {}, acteur="Explicite")
        finally:
            from probare_engine.acteur import reinitialiser_acteur
            reinitialiser_acteur(token)
        assert db.get_journal("p1")[0]["acteur"] == "Explicite"

    def test_migration_ajoute_la_colonne_a_une_base_existante(self, tmp_path):
        """Une base créée avant cette version doit se voir ajouter la colonne
        sans perdre ses lignes — et sans qu'on invente un auteur pour elles."""
        import sqlite3
        from probare_engine.storage.db import ProjectDB

        chemin = tmp_path / "ancienne.db"
        ancienne = sqlite3.connect(str(chemin))
        ancienne.executescript("""
            CREATE TABLE journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projet_id TEXT, type TEXT NOT NULL, payload TEXT, horodatage TEXT
            );
            INSERT INTO journal (projet_id, type, payload, horodatage)
            VALUES ('p1', 'transition_etat', '{}', '2025-01-01T00:00:00+00:00');
        """)
        ancienne.commit()
        ancienne.close()

        db = ProjectDB(chemin)
        db.connect()
        try:
            lignes = db.get_journal("p1")
            assert len(lignes) == 1
            assert lignes[0]["acteur"] is None
            token = definir_acteur("Awale Hassan")
            try:
                db.log("p1", "action_humaine", {})
            finally:
                from probare_engine.acteur import reinitialiser_acteur
                reinitialiser_acteur(token)
            assert db.get_journal("p1")[0]["acteur"] == "Awale Hassan"
        finally:
            db.close()


# ─── Propagation de bout en bout ─────────────────────────────────────────────

class TestPropagationHTTP:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.delenv("PROBARE_API_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from fastapi.testclient import TestClient
        from probare_engine.main import app
        return TestClient(app)

    @staticmethod
    def _journal(pid: str) -> list[dict]:
        from probare_engine.api.routes import _get_db
        return _get_db(pid).get_journal(pid)

    def test_acteur_traverse_middleware_et_route_synchrone(self, client):
        """Le cœur du dispositif : l'en-tête posé sur la requête doit ressortir
        dans le journal écrit par une route synchrone, donc avoir traversé le
        middleware asynchrone PUIS le passage au thread de travail."""
        pid = client.post(
            "/api/projets",
            json={"nom": "T-acteur"},
            headers={"X-Probare-Acteur": "Awale Hassan (Commissaire aux comptes)"},
        ).json()["id"]

        lignes = self._journal(pid)
        assert lignes, "la création de projet doit être journalisée"
        assert all(l["acteur"] == "Awale Hassan (Commissaire aux comptes)" for l in lignes)

    def test_sans_entete_le_journal_reste_sans_auteur(self, client):
        pid = client.post("/api/projets", json={"nom": "T-acteur-anon"}).json()["id"]
        assert all(l["acteur"] is None for l in self._journal(pid))

    def test_acteur_non_reporte_d_une_requete_sur_la_suivante(self, client):
        """Le ContextVar est global au processus : s'il n'était pas réinitialisé
        en fin de requête, une action anonyme hériterait de l'auteur précédent."""
        pid = client.post(
            "/api/projets",
            json={"nom": "T-acteur-fuite"},
            headers={"X-Probare-Acteur": "Premier Auteur"},
        ).json()["id"]

        client.patch(f"/api/projets/{pid}", json={"nom": "T-acteur-fuite-2"})

        acteurs = [l["acteur"] for l in self._journal(pid)]
        assert "Premier Auteur" in acteurs
        assert None in acteurs, f"l'auteur a fuité d'une requête à l'autre : {acteurs}"

    def test_acteur_expose_par_la_route_journal(self, client):
        pid = client.post(
            "/api/projets",
            json={"nom": "T-acteur-api"},
            headers={"X-Probare-Acteur": "Awale Hassan"},
        ).json()["id"]

        journal = client.get(f"/api/projets/{pid}/journal").json()["journal"]
        assert journal
        assert journal[0]["acteur"] == "Awale Hassan"
