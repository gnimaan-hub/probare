"""Base SQLite globale — clients et dossiers permanents partagés entre missions."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


CATEGORIES_PERMANENTS: dict[str, str] = {
    "statuts": "Statuts et actes constitutifs",
    "pv_ag": "Procès-verbaux d'assemblée générale",
    "contrats": "Contrats significatifs",
    "organigramme": "Organigramme et dirigeants",
    "politique_comptable": "Politique comptable",
    "rapports_anterieurs": "Rapports d'audit antérieurs",
    "correspondances": "Correspondances importantes",
    "autres": "Autres documents",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClientsDB:
    """Base globale partagée entre tous les projets : clients + dossiers permanents."""

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
            raise RuntimeError("ClientsDB non connectée. Appeler connect() d'abord.")
        return self._conn

    def _create_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS client (
            id          TEXT PRIMARY KEY,
            nom         TEXT NOT NULL,
            nif         TEXT NOT NULL UNIQUE,
            secteur     TEXT,
            adresse     TEXT,
            dirigeants  TEXT,
            systemes_info TEXT,
            notes       TEXT,
            cree_le     TEXT,
            modifie_le  TEXT
        );

        CREATE TABLE IF NOT EXISTS fichier_permanent (
            id              TEXT PRIMARY KEY,
            client_id       TEXT NOT NULL REFERENCES client(id) ON DELETE CASCADE,
            nom             TEXT NOT NULL,
            chemin_relatif  TEXT NOT NULL,
            categorie       TEXT DEFAULT 'autres',
            description     TEXT,
            taille_octets   INTEGER,
            ajoute_le       TEXT,
            modifie_le      TEXT
        );
        """)
        self.conn.commit()

    # ── Clients ────────────────────────────────────────────────────────────────

    def create_client(self, data: dict) -> dict:
        now = _now()
        self.conn.execute(
            """INSERT INTO client
               (id,nom,nif,secteur,adresse,dirigeants,systemes_info,notes,cree_le,modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["nom"], data["nif"],
             data.get("secteur"), data.get("adresse"),
             data.get("dirigeants"), data.get("systemes_info"),
             data.get("notes"), now, now),
        )
        self.conn.commit()
        return self.get_client(data["id"])

    def get_client(self, client_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM client WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None

    def get_client_by_nif(self, nif: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM client WHERE nif=?", (nif,)).fetchone()
        return dict(row) if row else None

    def list_clients(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM client ORDER BY nom").fetchall()
        return [dict(r) for r in rows]

    def search_clients(self, q: str) -> list[dict]:
        like = f"%{q}%"
        rows = self.conn.execute(
            "SELECT * FROM client WHERE nom LIKE ? OR nif LIKE ? ORDER BY nom",
            (like, like),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_client(self, client_id: str, data: dict) -> dict | None:
        allowed = ("nom", "nif", "secteur", "adresse", "dirigeants", "systemes_info", "notes")
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return self.get_client(client_id)
        fields["modifie_le"] = _now()
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE client SET {sets} WHERE id=?", (*fields.values(), client_id))
        self.conn.commit()
        return self.get_client(client_id)

    def delete_client(self, client_id: str) -> bool:
        self.conn.execute("DELETE FROM client WHERE id=?", (client_id,))
        self.conn.commit()
        return True

    def count_missions(self, client_id: str, projets_db_dir: Path) -> int:
        """Compte les missions liées à ce client en scannant les projets existants."""
        count = 0
        try:
            for p in projets_db_dir.iterdir():
                if not p.is_dir():
                    continue
                db_path = p / "audit.db"
                if not db_path.exists():
                    continue
                try:
                    conn = sqlite3.connect(str(db_path))
                    row = conn.execute(
                        "SELECT COUNT(*) FROM projet WHERE client_id=?", (client_id,)
                    ).fetchone()
                    count += row[0] if row else 0
                    conn.close()
                except Exception:
                    pass
        except Exception:
            pass
        return count

    # ── Fichiers permanents ────────────────────────────────────────────────────

    def save_fichier_permanent(self, data: dict) -> dict:
        now = _now()
        self.conn.execute(
            """INSERT INTO fichier_permanent
               (id,client_id,nom,chemin_relatif,categorie,description,taille_octets,ajoute_le,modifie_le)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["client_id"], data["nom"], data["chemin_relatif"],
             data.get("categorie", "autres"), data.get("description", ""),
             data.get("taille_octets"), now, now),
        )
        self.conn.commit()
        return self.get_fichier_permanent(data["id"])

    def get_fichier_permanent(self, fid: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM fichier_permanent WHERE id=?", (fid,)
        ).fetchone()
        return dict(row) if row else None

    def list_fichiers_permanents(self, client_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM fichier_permanent WHERE client_id=? ORDER BY categorie, nom",
            (client_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_fichier_permanent(self, fid: str, data: dict) -> dict | None:
        allowed = ("categorie", "description", "nom")
        fields = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not fields:
            return self.get_fichier_permanent(fid)
        fields["modifie_le"] = _now()
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE fichier_permanent SET {sets} WHERE id=?", (*fields.values(), fid)
        )
        self.conn.commit()
        return self.get_fichier_permanent(fid)

    def delete_fichier_permanent(self, fid: str) -> bool:
        self.conn.execute("DELETE FROM fichier_permanent WHERE id=?", (fid,))
        self.conn.commit()
        return True

    def count_fichiers_permanents(self, client_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM fichier_permanent WHERE client_id=?", (client_id,)
        ).fetchone()
        return row[0] if row else 0
