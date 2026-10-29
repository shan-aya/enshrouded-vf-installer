# Compile l'installateur (PyInstaller, mode "onedir"). Prerequis : Python 3.14 (x64) avec tkinter, et `pip install pyinstaller==6.20.0`.
# usage : .\build_installer.ps1 [-Python "C:\Program Files\Python314\python.exe"]    -> dist\VF_Enshrouded_Installateur\
param([string]$Python = "python")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
& $Python "$root\build\extract_tcl_tk.py" "$root\build\tclx"                       # bibliotheques Tcl/Tk 9 a embarquer
& $Python -m PyInstaller --noconfirm --distpath "$root\dist" --workpath "$root\build\work" "$root\build\VF_Enshrouded_Installateur.spec"
Write-Host "Termine : $root\dist\VF_Enshrouded_Installateur\VF_Enshrouded_Installateur.exe"
