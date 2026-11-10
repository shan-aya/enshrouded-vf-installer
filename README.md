# enshrouded-vf-installer

**FR** — Code source de l'installateur du mod **ShroudInFrench**, des voix françaises pour *Enshrouded* (525 pages de journal en fichier principal, 1 170 répliques de personnages en fichier optionnel).
**EN** — Source code of the installer for **ShroudInFrench**, a French voice-over mod for *Enshrouded* (525 journal pages as the main file, 1,170 NPC lines as an optional file).

Ce dépôt **ne contient ni les fichiers audio du mod, ni `emm.exe`** : l'installateur utilise les archives téléchargées sur Nexus Mods et l'outil `emm.exe` d'EML. Il sert à vérifier ce que fait l'installateur et à le recompiler. / This repository contains **neither the mod's audio files nor `emm.exe`**; the installer uses the archives downloaded from Nexus Mods and EML's `emm.exe`.

## Ce que fait l'installateur / What it does

Fenêtre Tk (Python, interface en français). Tout est dans [`installer/shroud_installer.py`](installer/shroud_installer.py) (~330 lignes) :

1. **Détecte le jeu** : registre Steam + `libraryfolders.vdf` + `appmanifest_1203620.acf` (build Steam affiché). Choix manuel possible.
2. **Trouve les archives et `emm.exe`** dans Téléchargements, Bureau, le dossier de l'installateur et celui du jeu ; les archives sont reconnues **par leur contenu** (pas par leur nom) : « principale » = contient `mods/ShroudInFrench/mod.json`, « PNJ » = fichiers `n*.fqoa` seuls.
3. **Installer** : décompresse **uniquement** les entrées sous `mods/ShroudInFrench/` (sans `..` ni chemin absolu) dans le dossier du jeu, puis lance **`emm.exe run -p -g <jeu>`** ([EML](https://github.com/Brabb3l/kfc-parser), GPL-3.0) qui applique le patch (jeu fermé). Écrit `<jeu>\vf_install.json`. Une case permet d'inclure ou non les répliques de personnages.
4. **Désinstaller** : `emm.exe restore -g <jeu>` (restaure `enshrouded.kfc` depuis `enshrouded.kfc.bak`), supprime `mods\ShroudInFrench` et les fichiers `enshrouded_055.dat`+ ajoutés par le patch. Refuse de restaurer si le jeu a été mis à jour depuis (sauvegarde périmée) et renvoie vers « Vérifier l'intégrité des fichiers du jeu » dans Steam.

**Ce qu'il ne fait pas** : aucun accès réseau, aucune télémétrie, aucun droit administrateur, aucune modification hors du dossier du jeu (ni registre, ni réglages Windows, ni sauvegardes de parties). Le seul lien externe : les boutons « Où le télécharger ? » et « Payez-moi un café » ouvrent une page dans le navigateur, sur clic. Il lance deux programmes : `tasklist` (pour vérifier que le jeu est fermé) et `emm.exe`.

## Installation sans l'installateur / Without the installer

Fermez le jeu, décompressez les archives du mod dans le dossier du jeu (elles créent `mods\ShroudInFrench\`), puis `emm.exe run -p -g "<dossier du jeu>"` (ou copiez `dbghelp.dll` d'EML à côté de `enshrouded.exe` et lancez le jeu). Désinstallation : `emm.exe restore -g "<dossier du jeu>"` et suppression de `mods\ShroudInFrench`. Détail : [`docs/LISEZMOI_principal.txt`](docs/LISEZMOI_principal.txt).

## Compiler / Build

Prérequis : Windows x64, **Python 3.14** (avec tkinter), `pip install pyinstaller==6.20.0`.

```powershell
.\build_installer.ps1 -Python "C:\Program Files\Python314\python.exe"
# -> dist\ShroudInFrench_Installateur\ShroudInFrench_Installateur.exe  (mode onedir)
```

Le script fait deux choses :
1. `build\extract_tcl_tk.py` extrait les bibliothèques **Tcl/Tk 9** (embarquées en `zipfs` dans la DLL de Python 3.14) vers `build\tclx\` — le crochet de PyInstaller 6.20 ne les trouve pas seul avec Tcl/Tk 9 ;
2. PyInstaller compile avec [`build\ShroudInFrench_Installateur.spec`](build/ShroudInFrench_Installateur.spec), qui embarque ces bibliothèques (`_tcl_data`, `_tk_data`) et l'image d'en-tête (`installer/assets/entete.png`).

> Les exécutables PyInstaller sont parfois signalés à tort par des antivirus (faux positifs) ; le dossier `_internal` contient notamment `base_library.zip` (bibliothèque standard Python). Si besoin, installez sans l'installateur (voir ci-dessus).

## Documentation

- [`docs/LISEZMOI_principal.txt`](docs/LISEZMOI_principal.txt) — notice du fichier principal (installation avec EML, désinstallation, limites).
- [`docs/LISEZMOI_PNJ.txt`](docs/LISEZMOI_PNJ.txt) — notice du fichier optionnel « répliques des personnages ».
- [`docs/shroudinfrench_presentation.mp4`](docs/shroudinfrench_presentation.mp4) — vidéo de présentation (33 s) : Forgeron, Barbier et Alden en VF puis en VO.
- [`docs/banniere_shroudinfrench_1300x372.png`](docs/banniere_shroudinfrench_1300x372.png) — bannière du mod.

## Licences

- Code de ce dépôt : **MIT** ([LICENSE](LICENSE)).
- Les voix du mod (non incluses ici) sont générées avec XTTS-v2 (Coqui, licence **CPML** : usage non commercial). Projet de fan, non affilié à Keen Games ; il faut posséder le jeu.
- EML / `emm.exe` : Brabb3l, **GPL-3.0** — non inclus ici.



