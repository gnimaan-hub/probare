"""Point d'entrée du binaire gelé (PyInstaller).

Un script hors du paquet, plutôt que `probare_engine/__main__.py` directement :
PyInstaller exécute son script d'entrée sous le nom `__main__` et sans contexte
de paquet. Pris comme entrée, `__main__.py` ne peut donc pas s'appuyer sur son
appartenance à `probare_engine`, et le graphe de dépendances du paquet n'est
collecté que par raccroc. Passer par un module extérieur qui importe le paquet
en absolu rend les deux explicites.

En développement, l'application lance uvicorn directement — ce fichier ne sert
qu'à la construction.
"""
from probare_engine.__main__ import main

if __name__ == "__main__":
    main()
