"""SQLite storage — un fichier par projet."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectDB:
    """Thin wrapper autour d'un fichier SQLite de projet."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("DB not connected. Call connect() first.")
        return self._conn

    def _create_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS projet (
            id TEXT PRIMARY KEY,
            nom TEXT NOT NULL,
            client TEXT,
            nif TEXT,
            exercice TEXT,
            seuil_signification REAL,
            seuil_planification REAL,
            consentement_client INTEGER DEFAULT 0,
            consentement_horodatage TEXT,
            etat_courant TEXT DEFAULT 'cadrage',
            cycles_couverts TEXT,
            nature_mission TEXT DEFAULT 'contractuelle',
            referentiel_comptable TEXT DEFAULT 'pcgd',
            client_id TEXT,
            archive INTEGER DEFAULT 0,
            cree_le TEXT,
            modifie_le TEXT
        );

        CREATE TABLE IF NOT EXISTS fichier_source (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            nom TEXT NOT NULL,
            chemin_relatif TEXT,
            type TEXT,
            type_document TEXT,
            hash TEXT,
            importe_le TEXT
        );

        CREATE TABLE IF NOT EXISTS document_annexe (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            nom TEXT NOT NULL,
            chemin_relatif TEXT,
            description TEXT,
            resume_ia TEXT,
            points_cles TEXT,
            alertes TEXT,
            ia_analysee INTEGER DEFAULT 0,
            ajoute_le TEXT
        );

        CREATE TABLE IF NOT EXISTS donnee_sourcee (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            fichier_source_id TEXT REFERENCES fichier_source(id),
            valeur TEXT,
            type TEXT,
            localisation TEXT,
            confiance_extraction REAL DEFAULT 1.0,
            extrait_par TEXT DEFAULT 'ingestion-directe',
            horodatage TEXT
        );

        CREATE TABLE IF NOT EXISTS resultat_calcul (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            controle_ref TEXT NOT NULL,
            valeur REAL,
            statut TEXT CHECK(statut IN ('ok', 'exception')),
            details TEXT,
            sources TEXT,
            calcule_le TEXT
        );

        CREATE TABLE IF NOT EXISTS exception (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            controle_ref TEXT,
            nep_ref TEXT,
            severite TEXT CHECK(severite IN ('mineure', 'significative', 'critique')),
            description TEXT,
            statut TEXT CHECK(statut IN ('ouverte', 'tranchee')) DEFAULT 'ouverte',
            decision_humaine TEXT,
            decideur TEXT,
            interpretation_llm TEXT,
            hypotheses TEXT,
            diligences TEXT,
            decision_proposee TEXT,
            urgence TEXT,
            ia_analysee INTEGER DEFAULT 0,
            horodatage TEXT
        );

        CREATE TABLE IF NOT EXISTS feuille_travail (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            cycle TEXT,
            contenu_redige TEXT,
            sources TEXT,
            nep_ref TEXT,
            genere_le TEXT
        );

        CREATE TABLE IF NOT EXISTS document_brut (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL,
            nom TEXT NOT NULL,
            chemin_relatif TEXT,
            taille_octets INTEGER,
            type_mime TEXT,
            type_detecte TEXT,
            description_ia TEXT,
            statut TEXT DEFAULT 'uploade',
            catalogue_json TEXT,
            extraction_json TEXT,
            erreur TEXT,
            ajoute_le TEXT
        );

        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projet_id TEXT REFERENCES projet(id),
            type TEXT NOT NULL,
            payload TEXT,
            horodatage TEXT
        );

        CREATE TABLE IF NOT EXISTS planification (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL UNIQUE REFERENCES projet(id),
            forme_juridique TEXT,
            date_creation_entreprise TEXT,
            activites_principales TEXT,
            marches_principaux TEXT,
            dirigeants TEXT,
            systeme_information TEXT,
            effectif INTEGER,
            observations TEXT,
            facteurs_risque_inherent TEXT,
            balance_n1_fichier_id TEXT REFERENCES fichier_source(id),
            variations_json TEXT,
            interpretation_variations TEXT,
            variations_ia_horodatage TEXT,
            agregat_type TEXT DEFAULT 'total_bilan',
            agregat_valeur REAL,
            taux_signification REAL DEFAULT 0.01,
            taux_planification REAL DEFAULT 0.75,
            seuil_calcule REAL,
            seuil_planification_calcule REAL,
            agregats_json TEXT,
            statut TEXT DEFAULT 'en_cours',
            cree_le TEXT,
            modifie_le TEXT
        );

        CREATE TABLE IF NOT EXISTS risque (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            libelle TEXT NOT NULL,
            description TEXT,
            cycle TEXT,
            niveau TEXT DEFAULT 'moyen',
            assertions TEXT,
            source TEXT DEFAULT 'manuel',
            issu_ia INTEGER DEFAULT 0,
            valide_auditeur INTEGER DEFAULT 1,
            commentaire TEXT,
            cree_le TEXT
        );

        CREATE TABLE IF NOT EXISTS programme_travail_item (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            cycle TEXT,
            controle_ref TEXT,
            libelle TEXT NOT NULL,
            risque_id TEXT REFERENCES risque(id),
            priorite TEXT DEFAULT 'normale',
            statut TEXT DEFAULT 'inclus',
            notes TEXT,
            issu_ia INTEGER DEFAULT 0,
            cree_le TEXT
        );

        CREATE TABLE IF NOT EXISTS qci_reponse (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            cycle TEXT NOT NULL,
            question_id TEXT NOT NULL,
            reponse TEXT CHECK(reponse IN ('oui', 'non', 'na')),
            commentaire TEXT,
            repondu_le TEXT,
            UNIQUE(projet_id, cycle, question_id)
        );

        CREATE TABLE IF NOT EXISTS qci_evaluation (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL,
            cycle TEXT NOT NULL,
            score REAL,
            niveau_risque TEXT,
            synthese_ia TEXT,
            forces TEXT,
            faiblesses TEXT,
            recommandations TEXT,
            evalue_le TEXT,
            UNIQUE(projet_id, cycle)
        );

        CREATE TABLE IF NOT EXISTS qci_synthese_globale (
            projet_id TEXT PRIMARY KEY REFERENCES projet(id),
            niveau_global TEXT,
            score_global REAL,
            contenu_json TEXT,
            genere_le TEXT
        );

        CREATE TABLE IF NOT EXISTS circularisation (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            cycle TEXT NOT NULL,
            compte TEXT NOT NULL,
            libelle TEXT,
            solde_comptable REAL,
            sources TEXT,
            statut TEXT CHECK(statut IN ('propose','envoye','reponse_recue','sans_reponse','clos')) DEFAULT 'propose',
            lettre_ia TEXT,
            solde_confirme REAL,
            ecart REAL,
            ecart_pct REAL,
            est_significatif INTEGER DEFAULT 0,
            reponse_brute TEXT,
            analyse_ia TEXT,
            date_envoi TEXT,
            date_relance TEXT,
            date_reponse TEXT,
            cree_le TEXT,
            modifie_le TEXT
        );

        CREATE TABLE IF NOT EXISTS sondage (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            cycle TEXT NOT NULL,
            libelle TEXT,
            prefixes TEXT,
            population INTEGER,
            taille_echantillon INTEGER,
            taux_erreur_tolere REAL DEFAULT 0.05,
            niveau_confiance INTEGER DEFAULT 95,
            montant_population REAL,
            seed INTEGER,
            nb_anomalies INTEGER DEFAULT 0,
            montant_anomalies REAL DEFAULT 0.0,
            taux_anomalie REAL,
            montant_projete REAL,
            conclusion_ia TEXT,
            statut TEXT CHECK(statut IN ('en_cours','conclu')) DEFAULT 'en_cours',
            cree_le TEXT,
            modifie_le TEXT
        );

        CREATE TABLE IF NOT EXISTS sondage_element (
            id TEXT PRIMARY KEY,
            sondage_id TEXT NOT NULL REFERENCES sondage(id),
            projet_id TEXT NOT NULL,
            index_original INTEGER,
            compte TEXT,
            libelle TEXT,
            montant REAL,
            numero_piece TEXT,
            date_piece TEXT,
            sources TEXT,
            est_anomalie INTEGER DEFAULT 0,
            montant_anomalie REAL DEFAULT 0.0,
            commentaire TEXT
        );

        CREATE TABLE IF NOT EXISTS controle_ignore (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL,
            cycle TEXT NOT NULL,
            controle_ref TEXT NOT NULL,
            raison TEXT,
            horodatage TEXT,
            UNIQUE(projet_id, controle_ref)
        );

        CREATE TABLE IF NOT EXISTS peripherie_reponse (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL REFERENCES projet(id),
            diligence TEXT NOT NULL,
            question_id TEXT NOT NULL,
            reponse TEXT CHECK(reponse IN ('oui', 'non', 'na')),
            commentaire TEXT,
            repondu_le TEXT,
            UNIQUE(projet_id, diligence, question_id)
        );

        CREATE TABLE IF NOT EXISTS peripherie_evaluation (
            id TEXT PRIMARY KEY,
            projet_id TEXT NOT NULL,
            diligence TEXT NOT NULL,
            score REAL,
            niveau TEXT,
            synthese_ia TEXT,
            points_attention TEXT,
            diligences_complementaires TEXT,
            indicateurs_json TEXT,
            conclusion TEXT,
            conclu_par TEXT,
            conclu_le TEXT,
            lettre_ia TEXT,
            lettre_generee_le TEXT,
            evalue_le TEXT,
            UNIQUE(projet_id, diligence)
        );

        CREATE TABLE IF NOT EXISTS opinion (
            projet_id TEXT PRIMARY KEY REFERENCES projet(id),
            rigueur TEXT,
            type_opinion TEXT,
            titre TEXT,
            texte_opinion TEXT,
            fondement TEXT,
            observations TEXT,
            justification TEXT,
            proposee_par_ia INTEGER DEFAULT 0,
            modele_ia TEXT,
            validee INTEGER DEFAULT 0,
            validee_par TEXT,
            genere_le TEXT,
            modifie_le TEXT
        );
        """)
        self.conn.commit()

        # Migrations d'état pipeline
        try:
            self.conn.execute(
                "UPDATE projet SET etat_courant='travaux_substantifs' WHERE etat_courant='controles'"
            )
            # "extraction" bloqué → retour à ingestion pour que l'auditeur repasse l'étape
            self.conn.execute(
                "UPDATE projet SET etat_courant='ingestion' WHERE etat_courant='extraction'"
            )
            self.conn.commit()
        except Exception:
            pass

        # Migrations idempotentes : colonnes ajoutées après la v1 initiale
        migrations = [
            ("exception", "hypotheses", "TEXT"),
            ("exception", "diligences", "TEXT"),
            ("exception", "decision_proposee", "TEXT"),
            ("exception", "urgence", "TEXT"),
            ("exception", "ia_analysee", "INTEGER DEFAULT 0"),
            ("projet", "cycles_couverts", "TEXT"),
            ("fichier_source", "type_document", "TEXT"),
            ("projet", "nature_mission", "TEXT DEFAULT 'contractuelle'"),
            ("projet", "referentiel_comptable", "TEXT DEFAULT 'pcgd'"),
            ("projet", "client_id", "TEXT"),
            ("projet", "archive", "INTEGER DEFAULT 0"),
            ("planification", "note_synthese", "TEXT"),
            ("fichier_source", "description_ia", "TEXT"),
            ("fichier_source", "nature_ia", "TEXT"),
            ("fichier_source", "correspond_a", "TEXT"),
            ("fichier_source", "statut_checklist", "TEXT"),
            ("fichier_source", "onglet", "TEXT"),
            ("exception", "fichiers_sources", "TEXT"),
            ("circularisation", "date_relance", "TEXT"),
            ("sondage", "seed", "INTEGER"),
            # NEP 450 : typologie de résolution et incidence chiffrée
            ("exception", "type_resolution", "TEXT"),
            ("exception", "montant_incidence", "REAL"),
            # Montant estimé par le contrôle déterministe (pré-remplissage de l'incidence)
            ("exception", "montant_estime", "REAL"),
            # NEP 505 : procédures alternatives en cas de non-réponse
            ("circularisation", "procedures_alternatives", "TEXT"),
            # M2 — Seuils complémentaires (NEP 320/450)
            ("projet", "seuil_insignifiance", "REAL"),
            ("planification", "taux_insignifiance", "REAL"),
            ("planification", "seuil_insignifiance_calcule", "REAL"),
            # M2 — Seuils spécifiques par cycle : {cycle: {seuil, justification}}
            ("planification", "seuils_specifiques_json", "TEXT"),
        ]
        for table, col, typedef in migrations:
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
                self.conn.commit()
            except Exception:
                pass  # colonne déjà présente

    def _deserialize_exception(self, d: dict) -> dict:
        for field in ("hypotheses", "diligences", "fichiers_sources"):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = []
            elif not val:
                d[field] = []
        # Références de normes re-rendues dans le référentiel actif du cabinet
        # (les données peuvent avoir été écrites sous l'autre référentiel).
        from ..normes import reformater_refs
        if d.get("nep_ref"):
            d["nep_ref"] = reformater_refs(d["nep_ref"])
        return d

    # --- Projet ---

    def create_projet(self, data: dict) -> dict:
        now = _now()
        cycles = data.get("cycles_couverts") or ["tresorerie", "achats", "ventes"]
        self.conn.execute(
            """INSERT INTO projet (id,nom,client,nif,exercice,seuil_signification,
               seuil_planification,consentement_client,consentement_horodatage,
               etat_courant,cycles_couverts,nature_mission,referentiel_comptable,
               client_id,archive,cree_le,modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["nom"], data.get("client"), data.get("nif"),
             data.get("exercice"), data.get("seuil_signification"),
             data.get("seuil_planification"), int(data.get("consentement_client", False)),
             data.get("consentement_horodatage"), data.get("etat_courant", "cadrage"),
             json.dumps(cycles), data.get("nature_mission", "contractuelle"),
             data.get("referentiel_comptable", "pcgd"),
             data.get("client_id"), 0, now, now)
        )
        self.conn.commit()
        return self.get_projet(data["id"])

    def list_projets(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM projet ORDER BY cree_le DESC"
        ).fetchall()
        result = []
        for r in rows:
            # Réutiliser get_projet pour la désérialisation
            p = self.get_projet(dict(r)["id"])
            if p:
                result.append(p)
        return result

    def update_projet(self, projet_id: str, data: dict) -> dict | None:
        fields = {k: v for k, v in data.items()
                  if k in ("nom","client","nif","exercice","seuil_signification",
                           "seuil_planification","seuil_insignifiance","consentement_client",
                           "consentement_horodatage","etat_courant","cycles_couverts",
                           "nature_mission","referentiel_comptable","client_id","archive")}
        # Sérialiser cycles_couverts en JSON si c'est une liste
        if "cycles_couverts" in fields and isinstance(fields["cycles_couverts"], list):
            fields["cycles_couverts"] = json.dumps(fields["cycles_couverts"])
        fields["modifie_le"] = _now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [projet_id]
        self.conn.execute(f"UPDATE projet SET {set_clause} WHERE id=?", vals)
        self.conn.commit()
        return self.get_projet(projet_id)

    def get_projet(self, projet_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM projet WHERE id=?", (projet_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        # Désérialiser cycles_couverts — les anciens dossiers (colonne NULL)
        # couvrent les 3 cycles historiques par défaut.
        _CYCLES_DEFAUT = ["tresorerie", "achats", "ventes"]
        val = d.get("cycles_couverts")
        if val and isinstance(val, str):
            try:
                d["cycles_couverts"] = json.loads(val)
            except Exception:
                d["cycles_couverts"] = _CYCLES_DEFAUT
        elif not val:
            d["cycles_couverts"] = _CYCLES_DEFAUT
        return d

    # --- Fichier source ---

    def save_fichier_source(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO fichier_source
               (id,projet_id,nom,chemin_relatif,type,type_document,hash,importe_le,
                description_ia,nature_ia,correspond_a,statut_checklist,onglet)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data["nom"],
             data.get("chemin_relatif"), data.get("type"),
             data.get("type_document"), data.get("hash"),
             data.get("importe_le", _now()),
             data.get("description_ia"), data.get("nature_ia"),
             data.get("correspond_a"), data.get("statut_checklist"),
             data.get("onglet"))
        )
        self.conn.commit()
        return data

    def update_fichier_ia(self, fichier_id: str, data: dict) -> None:
        allowed = {"description_ia", "nature_ia", "correspond_a", "statut_checklist", "type_document"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE fichier_source SET {set_clause} WHERE id=?",
            list(fields.values()) + [fichier_id],
        )
        self.conn.commit()

    def delete_fichier_source(self, fichier_id: str) -> None:
        self.conn.execute("DELETE FROM donnee_sourcee WHERE fichier_source_id=?", (fichier_id,))
        self.conn.execute("DELETE FROM fichier_source WHERE id=?", (fichier_id,))
        self.conn.commit()

    def find_fichier_by_hash(self, projet_id: str, file_hash: str) -> dict | None:
        """Retourne un fichier source déjà importé avec le même hash (anti-doublon)."""
        if not file_hash:
            return None
        row = self.conn.execute(
            "SELECT * FROM fichier_source WHERE projet_id=? AND hash=? LIMIT 1",
            (projet_id, file_hash),
        ).fetchone()
        return dict(row) if row else None

    def list_fichiers_source(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM fichier_source WHERE projet_id=? ORDER BY importe_le",
            (projet_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Documents annexes ---

    def save_annexe(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO document_annexe
               (id,projet_id,nom,chemin_relatif,description,
                resume_ia,points_cles,alertes,ia_analysee,ajoute_le)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data["nom"],
             data.get("chemin_relatif"), data.get("description"),
             data.get("resume_ia"), data.get("points_cles"),
             data.get("alertes"), int(data.get("ia_analysee", 0)),
             data.get("ajoute_le", _now()))
        )
        self.conn.commit()
        return self.get_annexe(data["id"])

    def get_annexe(self, annexe_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM document_annexe WHERE id=?", (annexe_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for f in ("points_cles", "alertes"):
            val = d.get(f)
            if val and isinstance(val, str):
                try:
                    d[f] = json.loads(val)
                except Exception:
                    d[f] = []
        return d

    # --- Documents bruts ---

    def save_document_brut(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO document_brut
               (id,projet_id,nom,chemin_relatif,taille_octets,type_mime,
                type_detecte,description_ia,statut,catalogue_json,
                extraction_json,erreur,ajoute_le)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data["nom"],
             data.get("chemin_relatif"), data.get("taille_octets"),
             data.get("type_mime"), data.get("type_detecte"),
             data.get("description_ia"), data.get("statut", "uploade"),
             data.get("catalogue_json"), data.get("extraction_json"),
             data.get("erreur"), data.get("ajoute_le", _now()))
        )
        self.conn.commit()
        return self.get_document_brut(data["id"])

    def get_document_brut(self, doc_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM document_brut WHERE id=?", (doc_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for f in ("catalogue_json", "extraction_json"):
            val = d.get(f)
            if val and isinstance(val, str):
                try:
                    d[f] = json.loads(val)
                except Exception:
                    d[f] = None
        return d

    def list_documents_bruts(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM document_brut WHERE projet_id=? ORDER BY ajoute_le DESC",
            (projet_id,)
        ).fetchall()
        return [self.get_document_brut(dict(r)["id"]) for r in rows]

    def update_document_brut(self, doc_id: str, **fields) -> dict | None:
        for f in ("catalogue_json", "extraction_json"):
            if f in fields and isinstance(fields[f], dict):
                fields[f] = json.dumps(fields[f])
        set_clause = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [doc_id]
        self.conn.execute(f"UPDATE document_brut SET {set_clause} WHERE id=?", vals)
        self.conn.commit()
        return self.get_document_brut(doc_id)

    def delete_document_brut(self, doc_id: str) -> bool:
        self.conn.execute("DELETE FROM document_brut WHERE id=?", (doc_id,))
        self.conn.commit()
        return True

    def list_annexes(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM document_annexe WHERE projet_id=? ORDER BY ajoute_le DESC",
            (projet_id,)
        ).fetchall()
        return [self.get_annexe(dict(r)["id"]) for r in rows]

    def update_annexe_ia(self, annexe_id: str, resume: str,
                         points_cles: list, alertes: list) -> dict | None:
        self.conn.execute(
            """UPDATE document_annexe SET
               resume_ia=?, points_cles=?, alertes=?, ia_analysee=1
               WHERE id=?""",
            (resume, json.dumps(points_cles), json.dumps(alertes), annexe_id)
        )
        self.conn.commit()
        return self.get_annexe(annexe_id)

    def list_fichiers(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM fichier_source WHERE projet_id=?", (projet_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- QCI ---

    def save_qci_reponse(self, projet_id: str, cycle: str, question_id: str, reponse: str, commentaire: str = "") -> dict:
        rid = str(__import__("uuid").uuid4())
        now = _now()
        self.conn.execute(
            """INSERT INTO qci_reponse (id, projet_id, cycle, question_id, reponse, commentaire, repondu_le)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(projet_id, cycle, question_id) DO UPDATE SET
                 reponse=excluded.reponse,
                 commentaire=excluded.commentaire,
                 repondu_le=excluded.repondu_le""",
            (rid, projet_id, cycle, question_id, reponse, commentaire, now)
        )
        self.conn.commit()
        return {"projet_id": projet_id, "cycle": cycle, "question_id": question_id,
                "reponse": reponse, "commentaire": commentaire}

    def list_qci_reponses(self, projet_id: str, cycle: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM qci_reponse WHERE projet_id=? AND cycle=?",
            (projet_id, cycle)
        ).fetchall()
        return [dict(r) for r in rows]

    def save_qci_evaluation(self, projet_id: str, cycle: str, data: dict) -> dict:
        eid = str(__import__("uuid").uuid4())
        now = _now()
        self.conn.execute(
            """INSERT INTO qci_evaluation
               (id, projet_id, cycle, score, niveau_risque, synthese_ia, forces, faiblesses, recommandations, evalue_le)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(projet_id, cycle) DO UPDATE SET
                 score=excluded.score, niveau_risque=excluded.niveau_risque,
                 synthese_ia=excluded.synthese_ia, forces=excluded.forces,
                 faiblesses=excluded.faiblesses, recommandations=excluded.recommandations,
                 evalue_le=excluded.evalue_le""",
            (eid, projet_id, cycle,
             data.get("score"), data.get("niveau_risque"),
             data.get("synthese_ia") or data.get("synthese"),
             json.dumps(data.get("forces", []), ensure_ascii=False),
             json.dumps(data.get("faiblesses", []), ensure_ascii=False),
             json.dumps(data.get("recommandations", []), ensure_ascii=False),
             now)
        )
        self.conn.commit()
        return {**data, "projet_id": projet_id, "cycle": cycle}

    def get_qci_evaluations(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM qci_evaluation WHERE projet_id=?", (projet_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for field in ("forces", "faiblesses", "recommandations"):
                val = d.get(field)
                if val and isinstance(val, str):
                    try:
                        d[field] = json.loads(val)
                    except Exception:
                        d[field] = []
            # L'UI lit `synthese` ; la colonne stockée est `synthese_ia`
            d["synthese"] = d.get("synthese_ia")
            result.append(d)
        return result

    def save_qci_synthese_globale(self, projet_id: str, data: dict) -> dict:
        self.conn.execute(
            """INSERT INTO qci_synthese_globale
               (projet_id, niveau_global, score_global, contenu_json, genere_le)
               VALUES (?,?,?,?,?)
               ON CONFLICT(projet_id) DO UPDATE SET
                 niveau_global=excluded.niveau_global, score_global=excluded.score_global,
                 contenu_json=excluded.contenu_json, genere_le=excluded.genere_le""",
            (projet_id, data.get("niveau_global"), data.get("score_global"),
             json.dumps(data, ensure_ascii=False), _now())
        )
        self.conn.commit()
        return data

    def get_qci_synthese_globale(self, projet_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM qci_synthese_globale WHERE projet_id=?", (projet_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        contenu = d.get("contenu_json")
        if contenu:
            try:
                data = json.loads(contenu)
                data["genere_le"] = d.get("genere_le")
                return data
            except Exception:
                pass
        return None

    # --- Diligences ISA de périphérie (M3 : 210/220, 240, 550, 560, 570, 580, 260/265) ---

    def save_peripherie_reponse(self, projet_id: str, diligence: str,
                                question_id: str, reponse: str, commentaire: str = "") -> dict:
        rid = str(__import__("uuid").uuid4())
        now = _now()
        self.conn.execute(
            """INSERT INTO peripherie_reponse
               (id, projet_id, diligence, question_id, reponse, commentaire, repondu_le)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(projet_id, diligence, question_id) DO UPDATE SET
                 reponse=excluded.reponse,
                 commentaire=excluded.commentaire,
                 repondu_le=excluded.repondu_le""",
            (rid, projet_id, diligence, question_id, reponse, commentaire, now)
        )
        self.conn.commit()
        return {"projet_id": projet_id, "diligence": diligence,
                "question_id": question_id, "reponse": reponse, "commentaire": commentaire}

    def list_peripherie_reponses(self, projet_id: str, diligence: str | None = None) -> list[dict]:
        if diligence:
            rows = self.conn.execute(
                "SELECT * FROM peripherie_reponse WHERE projet_id=? AND diligence=?",
                (projet_id, diligence)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM peripherie_reponse WHERE projet_id=?", (projet_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def _deserialize_peripherie_evaluation(self, d: dict) -> dict:
        for field in ("points_attention", "diligences_complementaires"):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = []
            elif not val:
                d[field] = []
        val = d.get("indicateurs_json")
        if val and isinstance(val, str):
            try:
                d["indicateurs_json"] = json.loads(val)
            except Exception:
                d["indicateurs_json"] = None
        return d

    def save_peripherie_evaluation(self, projet_id: str, diligence: str, data: dict) -> dict:
        """Upsert de l'évaluation d'une diligence — préserve conclusion et lettre existantes."""
        eid = str(__import__("uuid").uuid4())
        now = _now()
        indicateurs = data.get("indicateurs_json")
        self.conn.execute(
            """INSERT INTO peripherie_evaluation
               (id, projet_id, diligence, score, niveau, synthese_ia,
                points_attention, diligences_complementaires, indicateurs_json, evalue_le)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(projet_id, diligence) DO UPDATE SET
                 score=excluded.score, niveau=excluded.niveau,
                 synthese_ia=excluded.synthese_ia,
                 points_attention=excluded.points_attention,
                 diligences_complementaires=excluded.diligences_complementaires,
                 indicateurs_json=excluded.indicateurs_json,
                 evalue_le=excluded.evalue_le""",
            (eid, projet_id, diligence,
             data.get("score"), data.get("niveau"),
             data.get("synthese_ia") or data.get("synthese"),
             json.dumps(data.get("points_attention", []), ensure_ascii=False),
             json.dumps(data.get("diligences_complementaires", []), ensure_ascii=False),
             json.dumps(indicateurs, ensure_ascii=False) if indicateurs is not None else None,
             now)
        )
        self.conn.commit()
        return self.get_peripherie_evaluation(projet_id, diligence)

    def get_peripherie_evaluation(self, projet_id: str, diligence: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM peripherie_evaluation WHERE projet_id=? AND diligence=?",
            (projet_id, diligence)
        ).fetchone()
        return self._deserialize_peripherie_evaluation(dict(row)) if row else None

    def list_peripherie_evaluations(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM peripherie_evaluation WHERE projet_id=?", (projet_id,)
        ).fetchall()
        return [self._deserialize_peripherie_evaluation(dict(r)) for r in rows]

    def conclure_peripherie(self, projet_id: str, diligence: str,
                            conclusion: str, conclu_par: str) -> dict | None:
        self.conn.execute(
            """UPDATE peripherie_evaluation SET conclusion=?, conclu_par=?, conclu_le=?
               WHERE projet_id=? AND diligence=?""",
            (conclusion, conclu_par, _now(), projet_id, diligence)
        )
        self.conn.commit()
        return self.get_peripherie_evaluation(projet_id, diligence)

    def save_peripherie_lettre(self, projet_id: str, diligence: str, lettre: str) -> dict | None:
        self.conn.execute(
            """UPDATE peripherie_evaluation SET lettre_ia=?, lettre_generee_le=?
               WHERE projet_id=? AND diligence=?""",
            (lettre, _now(), projet_id, diligence)
        )
        self.conn.commit()
        return self.get_peripherie_evaluation(projet_id, diligence)

    # --- Données sourcées ---

    def save_donnees_sourcees(self, donnees: list[dict]) -> int:
        self.conn.executemany(
            """INSERT OR IGNORE INTO donnee_sourcee
               (id,projet_id,fichier_source_id,valeur,type,localisation,
                confiance_extraction,extrait_par,horodatage)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [(d["id"], d["projet_id"], d["fichier_source_id"],
              str(d["valeur"]) if d["valeur"] is not None else None,
              d["type"], d["localisation"], d.get("confiance_extraction", 1.0),
              d.get("extrait_par", "ingestion-directe"),
              d.get("horodatage", _now()))
             for d in donnees]
        )
        self.conn.commit()
        return len(donnees)

    def get_donnees_by_fichier(self, fichier_source_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM donnee_sourcee WHERE fichier_source_id=?",
            (fichier_source_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_donnees_by_projet(self, projet_id: str, type_: str | None = None) -> list[dict]:
        if type_:
            rows = self.conn.execute(
                "SELECT * FROM donnee_sourcee WHERE projet_id=? AND type=?",
                (projet_id, type_)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM donnee_sourcee WHERE projet_id=?", (projet_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Résultats calculs ---

    def save_resultat(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO resultat_calcul
               (id,projet_id,controle_ref,valeur,statut,details,sources,calcule_le)
               VALUES (?,?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data["controle_ref"],
             data.get("valeur"), data["statut"],
             data.get("details"), json.dumps(data.get("sources", [])),
             data.get("calcule_le", _now()))
        )
        self.conn.commit()
        return data

    def list_resultats(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM resultat_calcul WHERE projet_id=? ORDER BY calcule_le",
            (projet_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"]) if d["sources"] else []
            result.append(d)
        return result

    def delete_resultats_by_refs(self, projet_id: str, refs: list[str]) -> int:
        """Supprime les résultats de contrôle pour les références données (ré-exécution idempotente)."""
        if not refs:
            return 0
        ph = ",".join("?" for _ in refs)
        cur = self.conn.execute(
            f"DELETE FROM resultat_calcul WHERE projet_id=? AND controle_ref IN ({ph})",
            (projet_id, *refs),
        )
        self.conn.commit()
        return cur.rowcount

    # --- Exceptions ---

    def save_exception(self, data: dict) -> dict:
        hyp = data.get("hypotheses")
        dil = data.get("diligences")
        fich = data.get("fichiers_sources")
        self.conn.execute(
            """INSERT OR REPLACE INTO exception
               (id,projet_id,controle_ref,nep_ref,severite,description,
                statut,decision_humaine,decideur,interpretation_llm,
                hypotheses,diligences,decision_proposee,urgence,ia_analysee,
                fichiers_sources,montant_estime,horodatage)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data.get("controle_ref"),
             data.get("nep_ref"), data.get("severite"),
             data.get("description"), data.get("statut", "ouverte"),
             data.get("decision_humaine"), data.get("decideur"),
             data.get("interpretation_llm"),
             json.dumps(hyp) if isinstance(hyp, list) else hyp,
             json.dumps(dil) if isinstance(dil, list) else dil,
             data.get("decision_proposee"),
             data.get("urgence"),
             int(data.get("ia_analysee", 0)),
             json.dumps(fich) if isinstance(fich, list) else fich,
             data.get("montant_estime"),
             data.get("horodatage", _now()))
        )
        self.conn.commit()
        return data

    def delete_open_exceptions_by_refs(self, projet_id: str, refs: list[str]) -> int:
        """Supprime les exceptions NON tranchées des contrôles donnés (préserve les décisions humaines)."""
        if not refs:
            return 0
        ph = ",".join("?" for _ in refs)
        cur = self.conn.execute(
            f"DELETE FROM exception WHERE projet_id=? AND statut='ouverte' AND controle_ref IN ({ph})",
            (projet_id, *refs),
        )
        self.conn.commit()
        return cur.rowcount

    def tranchees_signatures(self, projet_id: str, refs: list[str]) -> set:
        """Retourne {(controle_ref, description)} des exceptions déjà tranchées, pour éviter de les recréer."""
        if not refs:
            return set()
        ph = ",".join("?" for _ in refs)
        rows = self.conn.execute(
            f"SELECT controle_ref, description FROM exception "
            f"WHERE projet_id=? AND statut='tranchee' AND controle_ref IN ({ph})",
            (projet_id, *refs),
        ).fetchall()
        return {(r["controle_ref"], r["description"]) for r in rows}

    def update_exception_ia(self, exception_id: str, ia_result: dict) -> dict | None:
        self.conn.execute(
            """UPDATE exception SET
               interpretation_llm=?, hypotheses=?, diligences=?,
               decision_proposee=?, urgence=?, ia_analysee=1
               WHERE id=?""",
            (ia_result.get("explication", ""),
             json.dumps(ia_result.get("hypotheses", [])),
             json.dumps(ia_result.get("diligences", [])),
             ia_result.get("decision_proposee", ""),
             ia_result.get("urgence", "moyenne"),
             exception_id)
        )
        self.conn.commit()
        return self.get_exception(exception_id)

    def list_exceptions(self, projet_id: str, statut: str | None = None) -> list[dict]:
        # Tri (#2) : d'abord les exceptions OUVERTES (à traiter en priorité), puis les
        # TRANCHÉES ; au sein de chaque groupe, par matérialité décroissante (montant
        # d'anomalie : incidence résiduelle sinon montant estimé), puis chronologique.
        # Les normes n'imposent aucun ordre — la matérialité est le critère utile.
        ordre = (
            "ORDER BY CASE statut WHEN 'ouverte' THEN 0 ELSE 1 END, "
            "COALESCE(ABS(montant_incidence), ABS(montant_estime), 0) DESC, horodatage"
        )
        if statut:
            rows = self.conn.execute(
                f"SELECT * FROM exception WHERE projet_id=? AND statut=? {ordre}",
                (projet_id, statut)
            ).fetchall()
        else:
            rows = self.conn.execute(
                f"SELECT * FROM exception WHERE projet_id=? {ordre}",
                (projet_id,)
            ).fetchall()
        return [self._deserialize_exception(dict(r)) for r in rows]

    def get_exception(self, exception_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM exception WHERE id=?", (exception_id,)
        ).fetchone()
        return self._deserialize_exception(dict(row)) if row else None

    def trancher_exception(
        self,
        exception_id: str,
        decision: str,
        decideur: str,
        type_resolution: str | None = None,
        montant_incidence: float | None = None,
    ) -> dict | None:
        """
        Tranche une exception avec typologie NEP 450 :
        - 'corrigee'      : anomalie corrigée par le client — aucune incidence résiduelle.
        - 'sans_incidence': explication obtenue, aucune anomalie avérée.
        - 'non_corrigee'  : anomalie non corrigée — montant_incidence entre dans le
                            cumul comparé au seuil de signification.
        - 'insignifiante' : anomalie manifestement insignifiante — montant_incidence
                            inférieur au seuil d'insignifiance ; écartée du cumul mais
                            journalisée et listée au dossier.
        type_resolution None = tranchement rétrocompatible non typé.
        """
        self.conn.execute(
            """UPDATE exception SET statut='tranchee', decision_humaine=?,
               decideur=?, type_resolution=?, montant_incidence=?, horodatage=?
               WHERE id=?""",
            (decision, decideur, type_resolution, montant_incidence, _now(), exception_id)
        )
        self.conn.commit()
        return self.get_exception(exception_id)

    def has_open_exceptions(self, projet_id: str) -> bool:
        count = self.conn.execute(
            "SELECT COUNT(*) FROM exception WHERE projet_id=? AND statut='ouverte'",
            (projet_id,)
        ).fetchone()[0]
        return count > 0

    def synthese_anomalies(self, projet_id: str, seuil_signification: float | None,
                           seuil_planification: float | None) -> dict:
        """
        Synthèse NEP 450 : cumule les anomalies non corrigées et les compare aux seuils.
        Arithmétique 100 % Python — aucune valeur ne vient du LLM.
        """
        rows = self.conn.execute(
            "SELECT * FROM exception WHERE projet_id=? AND statut='tranchee'",
            (projet_id,)
        ).fetchall()
        tranchees = [dict(r) for r in rows]

        non_corrigees = [e for e in tranchees if e.get("type_resolution") == "non_corrigee"]
        corrigees = [e for e in tranchees if e.get("type_resolution") == "corrigee"]
        sans_incidence = [e for e in tranchees if e.get("type_resolution") == "sans_incidence"]
        # M2 (ISA 450) : anomalies manifestement insignifiantes — écartées du cumul
        # mais comptées et listées au dossier (jamais silencieuses).
        insignifiantes = [e for e in tranchees if e.get("type_resolution") == "insignifiante"]
        non_typees = [e for e in tranchees if not e.get("type_resolution")]

        cumul = sum(abs(float(e.get("montant_incidence") or 0.0)) for e in non_corrigees)
        total_insignifiantes = sum(
            abs(float(e.get("montant_incidence") or 0.0)) for e in insignifiantes)
        seuil_sig = float(seuil_signification or 0.0)
        seuil_plan = float(seuil_planification or 0.0)

        return {
            "cumul_non_corrigees": round(cumul, 2),
            "total_insignifiantes": round(total_insignifiantes, 2),
            "seuil_signification": seuil_sig or None,
            "seuil_planification": seuil_plan or None,
            "depasse_seuil_signification": bool(seuil_sig and cumul > seuil_sig),
            "depasse_seuil_planification": bool(seuil_plan and cumul > seuil_plan),
            "nb_ouvertes": self.conn.execute(
                "SELECT COUNT(*) FROM exception WHERE projet_id=? AND statut='ouverte'",
                (projet_id,)).fetchone()[0],
            "nb_corrigees": len(corrigees),
            "nb_non_corrigees": len(non_corrigees),
            "nb_sans_incidence": len(sans_incidence),
            "nb_insignifiantes": len(insignifiantes),
            "nb_non_typees": len(non_typees),
            "exceptions_non_corrigees": [
                {"id": e["id"], "controle_ref": e.get("controle_ref"),
                 "description": e.get("description"),
                 "montant_incidence": e.get("montant_incidence")}
                for e in non_corrigees
            ],
            "exceptions_insignifiantes": [
                {"id": e["id"], "controle_ref": e.get("controle_ref"),
                 "description": e.get("description"),
                 "montant_incidence": e.get("montant_incidence")}
                for e in insignifiantes
            ],
        }

    # --- Opinion d'audit (phase finale — ISA/NEP 700) ---

    def get_opinion(self, projet_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM opinion WHERE projet_id=?", (projet_id,)
        ).fetchone()
        return dict(row) if row else None

    def save_opinion(self, projet_id: str, data: dict) -> dict:
        """Upsert de l'opinion. Préserve genere_le à la première écriture."""
        now = _now()
        existing = self.get_opinion(projet_id)
        genere_le = (existing or {}).get("genere_le") or now
        merged = {**(existing or {}), **data}
        self.conn.execute(
            """INSERT INTO opinion
               (projet_id, rigueur, type_opinion, titre, texte_opinion, fondement,
                observations, justification, proposee_par_ia, modele_ia,
                validee, validee_par, genere_le, modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(projet_id) DO UPDATE SET
                 rigueur=excluded.rigueur, type_opinion=excluded.type_opinion,
                 titre=excluded.titre, texte_opinion=excluded.texte_opinion,
                 fondement=excluded.fondement, observations=excluded.observations,
                 justification=excluded.justification,
                 proposee_par_ia=excluded.proposee_par_ia, modele_ia=excluded.modele_ia,
                 validee=excluded.validee, validee_par=excluded.validee_par,
                 modifie_le=excluded.modifie_le""",
            (projet_id, merged.get("rigueur"), merged.get("type_opinion"),
             merged.get("titre"), merged.get("texte_opinion"), merged.get("fondement"),
             merged.get("observations"), merged.get("justification"),
             int(merged.get("proposee_par_ia", 0)), merged.get("modele_ia"),
             int(merged.get("validee", 0)), merged.get("validee_par"),
             genere_le, now)
        )
        self.conn.commit()
        return self.get_opinion(projet_id)

    # --- Contrôles ignorés (NEP 230 : documenter les procédures non réalisées) ---

    def save_controles_ignores(self, projet_id: str, cycle: str, ignores: list[dict]) -> None:
        """Remplace les motifs d'omission des contrôles du cycle par ceux de la dernière exécution."""
        self.conn.execute(
            "DELETE FROM controle_ignore WHERE projet_id=? AND cycle=?",
            (projet_id, cycle)
        )
        now = _now()
        self.conn.executemany(
            """INSERT OR REPLACE INTO controle_ignore
               (id, projet_id, cycle, controle_ref, raison, horodatage)
               VALUES (?,?,?,?,?,?)""",
            [(str(__import__("uuid").uuid4()), projet_id, cycle,
              i.get("controle_ref", ""), i.get("raison", ""), now)
             for i in ignores]
        )
        self.conn.commit()

    def list_controles_ignores(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM controle_ignore WHERE projet_id=? ORDER BY cycle, controle_ref",
            (projet_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Feuilles de travail ---

    def save_feuille_travail(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO feuille_travail
               (id,projet_id,cycle,contenu_redige,sources,nep_ref,genere_le)
               VALUES (?,?,?,?,?,?,?)""",
            (data["id"], data["projet_id"], data.get("cycle"),
             data.get("contenu_redige"), json.dumps(data.get("sources", [])),
             data.get("nep_ref"), data.get("genere_le", _now()))
        )
        self.conn.commit()
        return data

    def list_feuilles(self, projet_id: str) -> list[dict]:
        from ..normes import reformater_refs
        rows = self.conn.execute(
            "SELECT * FROM feuille_travail WHERE projet_id=? ORDER BY genere_le",
            (projet_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d["sources"]) if d["sources"] else []
            if d.get("nep_ref"):
                d["nep_ref"] = reformater_refs(d["nep_ref"])
            result.append(d)
        return result

    def delete_feuilles_par_cycle(self, projet_id: str, cycle: str) -> int:
        """Supprime les feuilles de travail existantes d'un cycle avant régénération
        (une régénération remplace la précédente, elle ne s'y ajoute pas)."""
        cur = self.conn.execute(
            "DELETE FROM feuille_travail WHERE projet_id=? AND cycle=?",
            (projet_id, cycle)
        )
        self.conn.commit()
        return cur.rowcount

    # --- Planification ---

    def _deserialize_planification(self, d: dict) -> dict:
        for field in ("dirigeants", "facteurs_risque_inherent", "variations_json", "agregats_json",
                      "seuils_specifiques_json"):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = [] if field in ("dirigeants", "facteurs_risque_inherent", "variations_json") else {}
            elif not val:
                d[field] = [] if field in ("dirigeants", "facteurs_risque_inherent", "variations_json") else {}
        return d

    def get_or_create_planification(self, projet_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM planification WHERE projet_id=?", (projet_id,)
        ).fetchone()
        if row:
            return self._deserialize_planification(dict(row))
        now = _now()
        pid = str(__import__("uuid").uuid4())
        self.conn.execute(
            """INSERT INTO planification (id, projet_id, cree_le, modifie_le)
               VALUES (?, ?, ?, ?)""",
            (pid, projet_id, now, now)
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM planification WHERE projet_id=?", (projet_id,)).fetchone()
        return self._deserialize_planification(dict(row))

    def update_planification(self, projet_id: str, data: dict) -> dict:
        # Garantit l'existence de la ligne : un UPDATE sur une planification
        # jamais initialisée serait un no-op silencieux (perte de la fiche entité).
        self.get_or_create_planification(projet_id)
        allowed = {
            "forme_juridique", "date_creation_entreprise", "activites_principales",
            "marches_principaux", "dirigeants", "systeme_information", "effectif",
            "observations", "facteurs_risque_inherent", "balance_n1_fichier_id",
            "variations_json", "interpretation_variations", "variations_ia_horodatage",
            "agregat_type", "agregat_valeur", "taux_signification", "taux_planification",
            "taux_insignifiance", "seuil_insignifiance_calcule", "seuils_specifiques_json",
            "seuil_calcule", "seuil_planification_calcule", "agregats_json", "statut",
            "note_synthese",
        }
        fields = {}
        for k, v in data.items():
            if k not in allowed:
                continue
            if k in ("dirigeants", "facteurs_risque_inherent", "variations_json", "agregats_json",
                     "seuils_specifiques_json") and isinstance(v, (list, dict)):
                fields[k] = json.dumps(v)
            else:
                fields[k] = v
        fields["modifie_le"] = _now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [projet_id]
        self.conn.execute(f"UPDATE planification SET {set_clause} WHERE projet_id=?", vals)
        self.conn.commit()
        return self.get_or_create_planification(projet_id)

    # --- Risques ---

    def save_risque(self, data: dict) -> dict:
        assertions = data.get("assertions")
        self.conn.execute(
            """INSERT OR REPLACE INTO risque
               (id, projet_id, libelle, description, cycle, niveau, assertions,
                source, issu_ia, valide_auditeur, commentaire, cree_le)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["id"], data["projet_id"], data["libelle"],
             data.get("description"), data.get("cycle"), data.get("niveau", "moyen"),
             json.dumps(assertions) if isinstance(assertions, list) else assertions,
             data.get("source", "manuel"), int(data.get("issu_ia", 0)),
             int(data.get("valide_auditeur", 1)), data.get("commentaire"),
             data.get("cree_le", _now()))
        )
        self.conn.commit()
        return self.get_risque(data["id"])

    def get_risque(self, risque_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM risque WHERE id=?", (risque_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        val = d.get("assertions")
        d["assertions"] = json.loads(val) if val and isinstance(val, str) else []
        return d

    def list_risques(self, projet_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM risque WHERE projet_id=? ORDER BY cree_le",
            (projet_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            val = d.get("assertions")
            d["assertions"] = json.loads(val) if val and isinstance(val, str) else []
            result.append(d)
        return result

    def update_risque(self, risque_id: str, data: dict) -> dict | None:
        allowed = {"libelle", "description", "cycle", "niveau", "assertions",
                   "source", "valide_auditeur", "commentaire"}
        fields = {}
        for k, v in data.items():
            if k not in allowed:
                continue
            if k == "assertions" and isinstance(v, list):
                fields[k] = json.dumps(v)
            else:
                fields[k] = v
        if not fields:
            return self.get_risque(risque_id)
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE risque SET {set_clause} WHERE id=?",
                          list(fields.values()) + [risque_id])
        self.conn.commit()
        return self.get_risque(risque_id)

    def delete_risque(self, risque_id: str) -> None:
        self.conn.execute("DELETE FROM risque WHERE id=?", (risque_id,))
        self.conn.commit()

    # --- Programme de travail ---

    def save_programme_item(self, data: dict) -> dict:
        self.conn.execute(
            """INSERT OR REPLACE INTO programme_travail_item
               (id, projet_id, cycle, controle_ref, libelle, risque_id,
                priorite, statut, notes, issu_ia, cree_le)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["id"], data["projet_id"], data.get("cycle"),
             data.get("controle_ref"), data["libelle"], data.get("risque_id"),
             data.get("priorite", "normale"), data.get("statut", "inclus"),
             data.get("notes"), int(data.get("issu_ia", 0)),
             data.get("cree_le", _now()))
        )
        self.conn.commit()
        return self.get_programme_item(data["id"])

    def get_programme_item(self, item_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM programme_travail_item WHERE id=?", (item_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_programme_items(self, projet_id: str, cycle: str | None = None) -> list[dict]:
        if cycle:
            rows = self.conn.execute(
                "SELECT * FROM programme_travail_item WHERE projet_id=? AND cycle=? ORDER BY cycle, priorite, cree_le",
                (projet_id, cycle)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM programme_travail_item WHERE projet_id=? ORDER BY cycle, priorite, cree_le",
                (projet_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def update_programme_item(self, item_id: str, data: dict) -> dict | None:
        allowed = {"libelle", "cycle", "controle_ref", "risque_id", "priorite", "statut", "notes"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return self.get_programme_item(item_id)
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE programme_travail_item SET {set_clause} WHERE id=?",
                          list(fields.values()) + [item_id])
        self.conn.commit()
        return self.get_programme_item(item_id)

    def delete_programme_items(self, projet_id: str) -> None:
        self.conn.execute("DELETE FROM programme_travail_item WHERE projet_id=?", (projet_id,))
        self.conn.commit()

    def delete_programme_item(self, item_id: str) -> None:
        self.conn.execute("DELETE FROM programme_travail_item WHERE id=?", (item_id,))
        self.conn.commit()

    # --- Circularisation ---

    def _deserialize_circularisation(self, d: dict) -> dict:
        for field in ("sources",):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = []
            elif not val:
                d[field] = []
        return d

    def save_circularisation(self, data: dict) -> dict:
        now = _now()
        data.setdefault("id", str(__import__("uuid").uuid4()))
        data.setdefault("cree_le", now)
        data["modifie_le"] = now
        sources = data.get("sources", [])
        if isinstance(sources, list):
            data["sources"] = json.dumps(sources)
        self.conn.execute(
            """INSERT OR REPLACE INTO circularisation
            (id, projet_id, cycle, compte, libelle, solde_comptable, sources, statut,
             lettre_ia, solde_confirme, ecart, ecart_pct, est_significatif, reponse_brute,
             analyse_ia, date_envoi, date_relance, date_reponse, cree_le, modifie_le)
            VALUES (:id,:projet_id,:cycle,:compte,:libelle,:solde_comptable,:sources,:statut,
             :lettre_ia,:solde_confirme,:ecart,:ecart_pct,:est_significatif,:reponse_brute,
             :analyse_ia,:date_envoi,:date_relance,:date_reponse,:cree_le,:modifie_le)""",
            {k: data.get(k) for k in (
                "id","projet_id","cycle","compte","libelle","solde_comptable","sources","statut",
                "lettre_ia","solde_confirme","ecart","ecart_pct","est_significatif","reponse_brute",
                "analyse_ia","date_envoi","date_relance","date_reponse","cree_le","modifie_le"
            )}
        )
        self.conn.commit()
        return self.get_circularisation(data["id"])

    def get_circularisation(self, circ_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM circularisation WHERE id=?", (circ_id,)
        ).fetchone()
        if not row:
            return None
        return self._deserialize_circularisation(dict(row))

    def list_circularisations(self, projet_id: str, cycle: str | None = None) -> list[dict]:
        if cycle:
            rows = self.conn.execute(
                "SELECT * FROM circularisation WHERE projet_id=? AND cycle=? ORDER BY cree_le",
                (projet_id, cycle)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM circularisation WHERE projet_id=? ORDER BY cycle, cree_le",
                (projet_id,)
            ).fetchall()
        return [self._deserialize_circularisation(dict(r)) for r in rows]

    def update_circularisation(self, circ_id: str, data: dict) -> dict | None:
        allowed = {
            "statut","lettre_ia","solde_confirme","ecart","ecart_pct","est_significatif",
            "reponse_brute","analyse_ia","date_envoi","date_relance","date_reponse","libelle",
            "procedures_alternatives"
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        fields["modifie_le"] = _now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE circularisation SET {set_clause} WHERE id=?",
            list(fields.values()) + [circ_id]
        )
        self.conn.commit()
        return self.get_circularisation(circ_id)

    def delete_circularisation(self, circ_id: str) -> None:
        self.conn.execute("DELETE FROM circularisation WHERE id=?", (circ_id,))
        self.conn.commit()

    # --- Sondages ---

    def _deserialize_sondage(self, d: dict) -> dict:
        for field in ("prefixes",):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = []
            elif not val:
                d[field] = []
        return d

    def _deserialize_sondage_element(self, d: dict) -> dict:
        for field in ("sources",):
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except Exception:
                    d[field] = []
            elif not val:
                d[field] = []
        return d

    def save_sondage(self, data: dict) -> dict:
        now = _now()
        data.setdefault("id", str(__import__("uuid").uuid4()))
        data.setdefault("cree_le", now)
        data["modifie_le"] = now
        prefixes = data.get("prefixes", [])
        if isinstance(prefixes, list):
            data["prefixes"] = json.dumps(prefixes)
        self.conn.execute(
            """INSERT OR REPLACE INTO sondage
            (id, projet_id, cycle, libelle, prefixes, population, taille_echantillon,
             taux_erreur_tolere, niveau_confiance, montant_population, seed,
             nb_anomalies, montant_anomalies, taux_anomalie, montant_projete,
             conclusion_ia, statut, cree_le, modifie_le)
            VALUES (:id,:projet_id,:cycle,:libelle,:prefixes,:population,:taille_echantillon,
             :taux_erreur_tolere,:niveau_confiance,:montant_population,:seed,
             :nb_anomalies,:montant_anomalies,:taux_anomalie,:montant_projete,
             :conclusion_ia,:statut,:cree_le,:modifie_le)""",
            {k: data.get(k) for k in (
                "id","projet_id","cycle","libelle","prefixes","population","taille_echantillon",
                "taux_erreur_tolere","niveau_confiance","montant_population","seed",
                "nb_anomalies","montant_anomalies","taux_anomalie","montant_projete",
                "conclusion_ia","statut","cree_le","modifie_le"
            )}
        )
        self.conn.commit()
        return self.get_sondage(data["id"])

    def get_sondage(self, sondage_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM sondage WHERE id=?", (sondage_id,)
        ).fetchone()
        if not row:
            return None
        return self._deserialize_sondage(dict(row))

    def list_sondages(self, projet_id: str, cycle: str | None = None) -> list[dict]:
        if cycle:
            rows = self.conn.execute(
                "SELECT * FROM sondage WHERE projet_id=? AND cycle=? ORDER BY cree_le",
                (projet_id, cycle)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM sondage WHERE projet_id=? ORDER BY cycle, cree_le",
                (projet_id,)
            ).fetchall()
        return [self._deserialize_sondage(dict(r)) for r in rows]

    def update_sondage(self, sondage_id: str, data: dict) -> dict | None:
        allowed = {
            "nb_anomalies","montant_anomalies","taux_anomalie","montant_projete",
            "conclusion_ia","statut","libelle","taille_echantillon","population","montant_population"
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        fields["modifie_le"] = _now()
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE sondage SET {set_clause} WHERE id=?",
            list(fields.values()) + [sondage_id]
        )
        self.conn.commit()
        return self.get_sondage(sondage_id)

    def delete_sondage(self, sondage_id: str) -> None:
        self.conn.execute("DELETE FROM sondage_element WHERE sondage_id=?", (sondage_id,))
        self.conn.execute("DELETE FROM sondage WHERE id=?", (sondage_id,))
        self.conn.commit()

    def save_sondage_element(self, data: dict) -> dict:
        data.setdefault("id", str(__import__("uuid").uuid4()))
        sources = data.get("sources", [])
        if isinstance(sources, list):
            data["sources"] = json.dumps(sources)
        self.conn.execute(
            """INSERT OR REPLACE INTO sondage_element
            (id, sondage_id, projet_id, index_original, compte, libelle, montant,
             numero_piece, date_piece, sources, est_anomalie, montant_anomalie, commentaire)
            VALUES (:id,:sondage_id,:projet_id,:index_original,:compte,:libelle,:montant,
             :numero_piece,:date_piece,:sources,:est_anomalie,:montant_anomalie,:commentaire)""",
            {k: data.get(k) for k in (
                "id","sondage_id","projet_id","index_original","compte","libelle","montant",
                "numero_piece","date_piece","sources","est_anomalie","montant_anomalie","commentaire"
            )}
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM sondage_element WHERE id=?", (data["id"],)
        ).fetchone()
        return self._deserialize_sondage_element(dict(row)) if row else {}

    def list_sondage_elements(self, sondage_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM sondage_element WHERE sondage_id=? ORDER BY index_original",
            (sondage_id,)
        ).fetchall()
        return [self._deserialize_sondage_element(dict(r)) for r in rows]

    def update_sondage_element(self, element_id: str, data: dict) -> dict | None:
        allowed = {"est_anomalie", "montant_anomalie", "commentaire"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            row = self.conn.execute(
                "SELECT * FROM sondage_element WHERE id=?", (element_id,)
            ).fetchone()
            return self._deserialize_sondage_element(dict(row)) if row else None
        set_clause = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE sondage_element SET {set_clause} WHERE id=?",
            list(fields.values()) + [element_id]
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM sondage_element WHERE id=?", (element_id,)
        ).fetchone()
        return self._deserialize_sondage_element(dict(row)) if row else None

    def delete_sondage_elements(self, sondage_id: str) -> None:
        self.conn.execute("DELETE FROM sondage_element WHERE sondage_id=?", (sondage_id,))
        self.conn.commit()

    def recalculer_sondage_stats(self, sondage_id: str) -> dict | None:
        """Recalcule nb_anomalies et montant_anomalies depuis les éléments marqués."""
        elements = self.list_sondage_elements(sondage_id)
        nb = sum(1 for e in elements if e.get("est_anomalie"))
        montant = sum(e.get("montant_anomalie") or 0.0 for e in elements if e.get("est_anomalie"))
        return self.update_sondage(sondage_id, {"nb_anomalies": nb, "montant_anomalies": montant})

    # --- Journal ---

    def log(self, projet_id: str | None, type_: str, payload: Any) -> None:
        self.conn.execute(
            "INSERT INTO journal (projet_id,type,payload,horodatage) VALUES (?,?,?,?)",
            (projet_id, type_, json.dumps(payload, default=str), _now())
        )
        self.conn.commit()

    def get_journal(self, projet_id: str, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM journal WHERE projet_id=? ORDER BY horodatage DESC LIMIT ?",
            (projet_id, limit)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d["payload"]) if d["payload"] else {}
            except Exception:
                pass
            result.append(d)
        return result
