# enshrouded-vf-installer

**FR** — Code source de l'installateur (et des scripts d'installation manuelle) du mod **VF Enshrouded**, des voix françaises pour *Enshrouded* (pages de journal, et répliques des personnages en fichier optionnel).
**EN** — Source code of the installer (and manual install scripts) for **VF Enshrouded**, a French voice-over mod for *Enshrouded*.

Ce dépôt **ne contient ni les fichiers audio du mod, ni `emm.exe`**. Il sert à vérifier ce que fait l'installateur et à le recompiler. / This repository contains **neither the mod's audio files nor `emm.exe`**; it lets anyone review and rebuild the installer.

## Ce que fait l'installateur / What it does

Fenêtre Tk (Python, interface en français). Tout est dans [`installer/vf_installer.py`](installer/vf_installer.py) (~250 lignes) :

1. **Détecte le jeu** : registre Steam + `libraryfolders.vdf` + `appmanifest_1203620.acf` (build Steam affiché). Choix manuel possible.
2. **Installer** : copie `mod\vf-enshrouded\` (script Lua + fichiers audio `*.fqoa`) dans `<jeu>\mods\vf-enshrouded\`, puis lance **`emm.exe run -p -g <jeu>`** ([EML](https://github.com/Brabb3l/kfc-parser), GPL-3.0) qui applique le patch (jeu fermé). Écrit `<jeu>\vf_install.json`.
3. **Désinstaller** : `emm.exe restore -g <jeu>` (restaure `enshrouded.kfc` depuis `enshrouded.kfc.bak`), supprime `mods\vf-enshrouded` et les fichiers `enshrouded_055.dat`+ ajoutés par le patch. Refuse de restaurer si le jeu a été mis à jour depuis (sauvegarde périmée).
4. **Option PNJ** : si les fichiers `n*.fqoa` (fichier optionnel) sont présents, une case permet de les inclure ou non.

**Ce qu'il ne fait pas** : aucun accès réseau, aucune télémétrie, aucun droit administrateur, aucune modification hors du dossier du jeu (ni registre, ni réglages Windows, ni sauvegardes de parties). Le seul lien externe : le bouton « Payez-moi un café » ouvre `https://buymeacoffee.com/shan_aya` dans le navigateur, sur clic. Il lance deux programmes : `tasklist` (pour vérifier que le jeu est fermé) et `emm.exe`.

## Compiler / Build

Prérequis : Windows x64, **Python 3.14** (avec tkinter), `pip install pyinstaller==6.20.0`.

```powershell
.\build_installer.ps1 -Python "C:\Program Files\Python314\python.exe"
# -> dist\VF_Enshrouded_Installateur\VF_Enshrouded_Installateur.exe  (mode onedir)
```

Le script fait deux choses :
1. `build\extract_tcl_tk.py` extrait les bibliothèques **Tcl/Tk 9** (embarquées en `zipfs` dans la DLL de Python 3.14) vers `build\tclx\` — le crochet de PyInstaller 6.20 ne les trouve pas seul avec Tcl/Tk 9 ;
2. PyInstaller compile avec [`build\VF_Enshrouded_Installateur.spec`](build/VF_Enshrouded_Installateur.spec), qui embarque ces bibliothèques (`_tcl_data`, `_tk_data`) et l'image d'en-tête (`installer/assets/entete.png`).

> Les exécutables PyInstaller sont parfois signalés à tort par des antivirus (faux positifs) ; le dossier `_internal` contient notamment `base_library.zip` (bibliothèque standard Python). Si besoin, utilisez les scripts manuels ci-dessous, qui font la même chose sans exécutable.

## Disposition attendue à côté de l'exécutable / Package layout

```
VF_Enshrouded\
  installateur\VF_Enshrouded_Installateur.exe   (+ _internal\)
  emm\emm.exe                                   <- https://github.com/Brabb3l/kfc-parser/releases  (v0.2.0 : SHA-256 b1133f6b8ea7000596cc7710901bd8307b48165b0e650c0487a611d90ea49305)
  mod\vf-enshrouded\{mod.json, src\mod.lua, j*.fqoa [, n*.fqoa]}
  LISEZMOI.txt
```

## Scripts manuels / Manual scripts

[`scripts/installation_manuelle.bat`](scripts/installation_manuelle.bat) et [`scripts/desinstallation_manuelle.bat`](scripts/desinstallation_manuelle.bat) : mêmes opérations que l'installateur, en invite de commandes (copie robocopy + `emm.exe run -p` / `emm.exe restore`), sans exécutable compilé.

## Documentation

- [`docs/LISEZMOI_principal.txt`](docs/LISEZMOI_principal.txt) — notice du fichier principal (installation avec EML, désinstallation, limites).
- [`docs/LISEZMOI_PNJ.txt`](docs/LISEZMOI_PNJ.txt) — notice du fichier optionnel « répliques des personnages ».
- [`docs/LISEZMOI_installateur.txt`](docs/LISEZMOI_installateur.txt) — notice de la version avec installateur.

## Licences

- Code de ce dépôt : **MIT** ([LICENSE](LICENSE)).
- Les voix du mod (non incluses ici) sont générées avec XTTS-v2 (Coqui, licence **CPML** : usage non commercial). Projet de fan, non affilié à Keen Games ; il faut posséder le jeu.
- EML / `emm.exe` : Brabb3l, **GPL-3.0** — non inclus ici.
