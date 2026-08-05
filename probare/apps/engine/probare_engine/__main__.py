"""Point d'entrée exécutable du moteur.

En développement, Electron lance `python -m uvicorn probare_engine.main:app`.
En production, il lance le binaire produit par PyInstaller, qui n'a pas de
ligne de commande uvicorn : ce module lui en tient lieu et accepte les mêmes
`--host` / `--port`, pour que les deux modes se pilotent identiquement.
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="probare_engine", description="Moteur d'audit Probare")
    # Le moteur n'est jamais exposé au réseau : il sert un client local unique
    # et son seul contrôle d'accès est un jeton partagé en mémoire.
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn

    # Import absolu : ce module sert aussi de point d'entrée au binaire gelé,
    # que PyInstaller exécute sans contexte de paquet — un import relatif y
    # échoue au démarrage.
    from probare_engine.main import app

    uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
