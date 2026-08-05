# Installer Probare sur le poste d'un cabinet

Le poste destinataire n'a besoin **ni de Python, ni de Node** : le moteur d'audit
est compilé en exécutable autonome et embarqué dans l'installeur.

---

## 1. Construire l'installeur (poste de développement)

### Prérequis

| Outil | Version | Vérifier |
|---|---|---|
| Python | 3.10+ | `python -V` |
| Node.js | 18+ | `node -v` |
| PyInstaller | 6+ | `pip install pyinstaller` |

Les dépendances du moteur doivent être importables : `fastapi`, `uvicorn`,
`anthropic`, `pandas`, `openpyxl`, `python-docx`. `build_engine.py` le vérifie
avant de lancer quoi que ce soit et s'arrête en nommant ce qui manque.

> Sur le poste de développement actuel, les paquets pip sont dans
> `D:\pip\packages`, hors du `sys.path` par défaut. Préfixer les commandes de
> `PYTHONPATH=D:\pip\packages`.

### Commande unique

Depuis `probare/apps/desktop` :

```bash
npm run installeur
```

Cet enchaînement fait trois choses :

1. `build:engine` — compile le moteur avec PyInstaller et le dépose dans
   `apps/desktop/resources/engine/`.
2. `build` — compile le processus principal Electron, le préchargement et
   l'interface dans `out/`.
3. `electron-builder` — produit l'installeur dans `apps/desktop/release/`.

Le résultat est `release/Probare Setup 0.1.0.exe`. Comptez une dizaine de
minutes au premier passage.

### Si electron-builder boucle sur « cannot move downloaded into final location »

electron-builder télécharge son outillage (`winCodeSign`, `nsis`) dans le
répertoire temporaire, puis le renomme dans son cache. Quand `TEMP` et le cache
sont sur **deux disques différents** — le cas sur le poste de développement
actuel, où `TEMP=D:\Temp` et le cache est sous `C:\Users\…\AppData\Local` —, le
renommage échoue avec « The system cannot move the file to a different disk
drive ». electron-builder retélécharge alors en boucle sans jamais aboutir.

Placer le cache sur le même disque que `TEMP` :

```bash
ELECTRON_BUILDER_CACHE=D:/Temp/electron-builder-cache npx electron-builder
```

### Cible ZIP portable

La configuration produit aussi une archive ZIP à côté de l'installeur. Elle se
décompresse et s'exécute sans installation — utile lorsque le poste du cabinet
restreint les installations, ou comme repli si l'outillage NSIS ne peut pas
être téléchargé.

### Étapes séparées

```bash
npm run build:engine
```

```bash
npm run build
```

```bash
npm run dist
```

---

## 2. La clé API Claude

Probare est IA-first : sans clé, les contrôles déterministes fonctionnent, mais
les exceptions ne sont pas interprétées et aucun projet de rédaction n'est
produit. L'interface affiche alors un bandeau orange le disant explicitement.

Le moteur cherche la clé dans cet ordre :

1. la variable d'environnement `ANTHROPIC_API_KEY` ;
2. un fichier `.env` placé à côté de l'exécutable du moteur ;
3. **une clé intégrée au binaire à la construction.**

La source 3 est celle utilisée pour la démonstration : `build_engine.py` lit la
clé dans `ANTHROPIC_API_KEY` ou dans `probare/.env`, la grave dans le binaire,
puis **supprime le fichier temporaire de l'arbre source**. Le cabinet n'a donc
rien à configurer.

> ### ⚠️ La clé intégrée n'est pas un secret
>
> Elle est extractible du binaire livré par quiconque en dispose. Ce mode
> convient à une version de démonstration remise à un cabinet identifié.
>
> - **Révoquez la clé à la fin du test**, sur console.anthropic.com.
> - Utilisez de préférence une clé dédiée, avec un plafond de dépense.
> - Pour une diffusion réelle, il faudra soit faire saisir sa clé au cabinet,
>   soit passer par un relais serveur qui ne la distribue jamais.

Pour produire un binaire sans clé intégrée :

```bash
python ../engine/build_engine.py --sans-cle
```

---

## 3. Installer sur le poste du cabinet

1. Copier `Probare Setup 0.1.0.exe` sur le poste.
2. L'exécuter. L'installeur permet de choisir le répertoire d'installation et
   ne requiert pas de droits administrateur (installation par utilisateur).
3. Lancer Probare depuis le raccourci du bureau.

### Windows bloque le lancement — deux mécanismes très différents

Probare n'est pas signé numériquement. Windows y réagit de deux façons, et la
distinction commande la conduite à tenir.

#### SmartScreen — un avertissement, contournable

Fenêtre bleue « Windows a protégé votre ordinateur ». Il existe un
contournement : **« Informations complémentaires » → « Exécuter quand même »**.
Gênant devant un client, mais sans blocage.

#### Contrôle intelligent des applications (Smart App Control) — un blocage sec

Fenêtre sombre « Le Contrôle intelligent des applications a bloqué une
application potentiellement dangereuse ». Elle ne propose que « OK » et
« Obtenir des applications du Store » : **aucun « Exécuter quand même »**. Ni
l'installeur ni le ZIP portable ne démarreront, et « Débloquer » dans les
propriétés du fichier n'y change rien.

Smart App Control n'existe que sous Windows 11, et seulement sur les postes
installés à neuf (un poste mis à niveau depuis Windows 10 l'a désactivé). Il
n'autorise que les applications signées jouissant d'une réputation établie.

Vérifier son état : **Sécurité Windows → Contrôle des applications et du
navigateur → Contrôle intelligent des applications**.

Trois issues, par ordre de préférence pour une démonstration :

1. **Présenter sur un poste où il est inactif.** Le plus rapide et sans effet de
   bord : la plupart des postes Windows 10, et tous les Windows 11 mis à niveau.
2. **Le désactiver sur le poste de démonstration.**
   > ⚠️ **Irréversible.** Microsoft ne permet pas de le réactiver : il faut
   > réinstaller Windows. Ne le faites pas sur le poste de travail du cabinet ;
   > c'est une décision qui appartient à son propriétaire, informé de cela.
3. **Signer l'application** — la seule vraie solution pour une diffusion.

#### Signer l'application

Un certificat de signature de code au nom du cabinet ou de l'éditeur :

| Type | Effet | Délai |
|---|---|---|
| **OV** (validation d'organisation) | Supprime SmartScreen après accumulation de réputation ; Smart App Control peut continuer à bloquer un moment | quelques jours de vérification d'identité |
| **EV** (validation étendue) | Réputation immédiate, accepté par Smart App Control | quelques jours, coût supérieur, clé sur jeton matériel |

Aucune modification du code n'est nécessaire : electron-builder signe
automatiquement si les variables d'environnement sont présentes.

```bash
CSC_LINK=/chemin/certificat.pfx CSC_KEY_PASSWORD=motdepasse npx electron-builder
```

### Où Probare écrit-il ?

| Chemin | Contenu |
|---|---|
| `%USERPROFILE%\.probare\projets\<id>\audit.db` | Un dossier d'audit par mission |
| `%USERPROFILE%\.probare\config.json` | Référentiel de normes (ISA/NEP) |
| Stockage local de l'application | Fiche identité du cabinet |

Rien n'est écrit ailleurs, et rien ne quitte le poste hors des appels à l'API
Claude — eux-mêmes conditionnés au consentement client activé au cadrage.

---

## 4. Premier démarrage

À l'ouverture, Probare affiche son écran de démarrage pendant que le moteur se
lance (quelques secondes ; davantage au tout premier lancement, l'antivirus
analysant un exécutable inconnu). L'application patiente jusqu'à 45 secondes.

En cas d'échec, l'écran « Moteur non disponible » affiche **la sortie d'erreur
réelle du moteur** — c'est le point de départ de tout diagnostic. Le bouton
« Réessayer » relance le sondage sans redémarrer l'application.

### Étape à ne pas sauter

Ouvrir **Configuration** et renseigner la fiche cabinet. Deux conséquences :

- Sans raison sociale, signataire, qualité et ville, le moteur **refuse de
  produire** le rapport d'audit et le mémorandum — un livrable engageant ne sort
  pas avec une identité incomplète.
- Le **responsable signataire** devient l'auteur inscrit dans la piste d'audit
  (ISA 230) : chaque action journalisée porte son nom. Tant que la fiche est
  vide, l'historique affiche « auteur non renseigné ».

---

## 5. Désinstaller

Panneau de configuration → Applications → Probare → Désinstaller.

Les dossiers d'audit dans `%USERPROFILE%\.probare\` ne sont **pas** supprimés :
ce sont des dossiers de travail d'audit, leur suppression doit rester une
décision explicite. Les retirer à la main si le test le justifie.
