<!-- safe-modify -- historique
Version actuelle : v2
v2 -- 2026-11-21 -- téléchargement automatique vérifié de la dernière version EML.
v1 -- version de base sauvegardée.
-->
# enshrouded-vf-installer

**FR** — Code source de l'installateur du mod **ShroudInFrench**, des voix françaises pour *Enshrouded* (525 pages de journal, 1 170 répliques de personnages en option, et narration d'introduction en option).
**EN** — Source code of the installer for **ShroudInFrench**, a French voice-over mod for *Enshrouded* (525 journal pages, 1,170 optional NPC lines, and an optional French intro narration).

Ce dépôt **ne contient ni les fichiers audio du mod, ni `emm.exe`** : l'installateur utilise les archives téléchargées sur Nexus Mods et l'outil `emm.exe` d'EML. Il sert à vérifier ce que fait l'installateur et à le recompiler. / This repository contains **neither the mod's audio files nor `emm.exe`**; the installer uses the archives downloaded from Nexus Mods and EML's `emm.exe`.

## Ce que fait l'installateur / What it does

Fenêtre Tk (Python, interface en français). Tout est dans [`installer/shroud_installer.py`](installer/shroud_installer.py) :

1. **Détecte le jeu** : registre Steam + `libraryfolders.vdf` + `appmanifest_1203620.acf` (build Steam affiché). Choix manuel possible.
2. **Récupère EML automatiquement** : consulte la dernière release officielle et télécharge `emm.exe` dans le profil utilisateur avec contrôle SHA-256. Si GitHub est inaccessible, un `emm.exe` local peut être sélectionné. Les archives Nexus sont détectées dans Téléchargements, Bureau, le dossier de l'installateur et celui du jeu, par leur contenu : principale (`mods/ShroudInFrench/mod.json`), PNJ (`n*.fqoa`) et Intro VF (`mods/ShroudInFrenchIntro/mod.json`).
3. **Installer / mettre à jour** : n'extrait que les fichiers présents dans les dossiers ShroudInFrench gérés par le mod (sans `..` ni chemin absolu), puis lance **`emm.exe run -p -f -g <jeu>`** ([EML](https://github.com/Brabb3l/kfc-parser), GPL-3.0) pour reconstruire le patch avec tous les mods EML présents (jeu fermé). Les cases PNJ et Intro VF activent ou retirent ces compléments indépendamment.
4. **Désinstaller** : retire `mods\\ShroudInFrench` et `mods\\ShroudInFrenchIntro`. S’il reste d’autres mods EML, force leur réapplication avec `emm.exe run -p -f -g <jeu>` et conserve leurs fichiers de données ainsi que le cache. Sans autre mod EML, restaure l’original avec `emm.exe restore -g <jeu>` et nettoie les fichiers appartenant à une installation récente et identifiée. Refuse toute opération si la sauvegarde d’origine est absente ou périmée.

**Ce qu'il ne fait pas** : aucune télémétrie, aucun droit administrateur, aucune modification des réglages Windows ni des sauvegardes de parties. Au démarrage, il consulte la dernière release officielle d'EML sur GitHub et télécharge `emm.exe` si nécessaire, dans le profil utilisateur avec vérification SHA-256 ; en cas d'absence de réseau, un `emm.exe` local reste utilisable. Il ne copie aucun fichier EML dans le dossier du jeu. Il lance `tasklist` et `emm.exe`.

## Installation sans l'installateur / Without the installer

Fermez le jeu, décompressez les archives téléchargées dans le dossier du jeu (principal et PNJ : `mods\ShroudInFrench\`; intro : `mods\ShroudInFrenchIntro\`), puis `emm.exe run -p -f -g "<dossier du jeu>"` (ou copiez `dbghelp.dll` d'EML à côté de `enshrouded.exe` et lancez le jeu). Pour retirer seulement un complément, supprimez son dossier et relancez cette commande. Pour tout désinstaller, supprimez les deux dossiers du mod ; s'il reste d'autres mods EML, reconstruisez le patch avec la commande `run`, sinon `emm.exe restore -g "<dossier du jeu>"`. Détail : [`docs/LISEZMOI_principal.txt`](docs/LISEZMOI_principal.txt). La notice du complément Intro est dans [`docs/LISEZMOI_intro.txt`](docs/LISEZMOI_intro.txt).

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
- [`docs/LISEZMOI_intro.txt`](docs/LISEZMOI_intro.txt) — notice d’installation/désinstallation du complément optionnel « Intro VF », indépendant du journal et des PNJ.
- [`docs/shroudinfrench_presentation.mp4`](docs/shroudinfrench_presentation.mp4) — vidéo de présentation (1 min 33) : Forgeron, Barbier et Alden en VF puis en VO.
- [`docs/banniere_shroudinfrench_1300x372.png`](docs/banniere_shroudinfrench_1300x372.png) — bannière du mod.

## Licences

- Code de ce dépôt : **MIT** ([LICENSE](LICENSE)).
- Les voix du mod (non incluses ici) sont générées avec XTTS-v2 (Coqui, licence **CPML** : usage non commercial). Projet de fan, non affilié à Keen Games ; il faut posséder le jeu.
- EML / `emm.exe` : Brabb3l, **GPL-3.0** — non inclus ici.




