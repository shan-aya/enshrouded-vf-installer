@echo off
chcp 65001 >nul
setlocal
rem Installation manuelle de la VF (sans l'installateur graphique) : utile si un antivirus bloque VF_Enshrouded_Installateur.exe.
rem Fermez COMPLETEMENT Enshrouded avant de lancer ce fichier. Il copie le mod dans le dossier du jeu puis applique le patch avec emm.exe.
echo.
echo  VF Enshrouded - installation manuelle
echo  =====================================
tasklist /FI "IMAGENAME eq enshrouded.exe" 2>nul | find /I "enshrouded.exe" >nul && (echo  Enshrouded est lance : fermez-le completement puis relancez ce fichier. & pause & exit /b 1)
set "JEU="
set /p JEU= Dossier du jeu (celui qui contient enshrouded.exe, ex. C:\Program Files (x86)\Steam\steamapps\common\Enshrouded) :
set "JEU=%JEU:"=%"
if not exist "%JEU%\enshrouded.exe" (echo  enshrouded.exe introuvable dans "%JEU%". & pause & exit /b 1)
if not exist "%~dp0mod\vf-enshrouded\mod.json" (echo  Le dossier "mod" doit rester a cote de ce fichier. & pause & exit /b 1)
rem Complement PNJ (fichier separe) : present si des fichiers n*.fqoa ont ete deposes dans mod\vf-enshrouded
set "HASPNJ=0"
dir /b "%~dp0mod\vf-enshrouded\n*.fqoa" >nul 2>&1 && set "HASPNJ=1"
set "PNJ=O"
if "%HASPNJ%"=="1" set /p PNJ= Inclure les repliques de personnages (PNJ) ? [O/n] :
if "%HASPNJ%"=="0" echo  Complement PNJ non present : pages de journal seules.
rem Reinstallation : si une installation precedente existe (et que le jeu n'a pas ete mis a jour depuis), on restaure d'abord les fichiers d'origine.
if exist "%JEU%\enshrouded.kfc.bak" (
  powershell -NoProfile -Command "if ((Get-Item '%JEU%\enshrouded.exe').LastWriteTime -gt (Get-Item '%JEU%\enshrouded.kfc.bak').LastWriteTime.AddSeconds(1)) { exit 2 } else { exit 0 }"
  if not errorlevel 2 (
    echo  Restauration des fichiers d'origine avant reinstallation...
    "%~dp0emm\emm.exe" restore -g "%JEU%" >nul
    for /l %%i in (55,1,99) do if exist "%JEU%\enshrouded_0%%i.dat" del /q "%JEU%\enshrouded_0%%i.dat"
  )
)
echo.
echo  Copie du mod (plusieurs centaines de Mo)...
if exist "%JEU%\mods\vf-enshrouded" rmdir /s /q "%JEU%\mods\vf-enshrouded"
robocopy "%~dp0mod\vf-enshrouded" "%JEU%\mods\vf-enshrouded" /E /NFL /NDL /NJH /NJS /NP >nul
rem Script du mod : avec complement -> mod_complet.lua ; PNJ refuses sur un paquet qui les contient -> mod_sans_pnj.lua
if "%HASPNJ%"=="1" if /I "%PNJ%"=="n" (
  del /q "%JEU%\mods\vf-enshrouded\n*.fqoa" >nul 2>&1
  if exist "%~dp0mod\variantes\mod_sans_pnj.lua" copy /y "%~dp0mod\variantes\mod_sans_pnj.lua" "%JEU%\mods\vf-enshrouded\src\mod.lua" >nul
  echo  Option : pages de journal seules.
)
if "%HASPNJ%"=="1" if /I not "%PNJ%"=="n" if exist "%~dp0mod\variantes\mod_complet.lua" copy /y "%~dp0mod\variantes\mod_complet.lua" "%JEU%\mods\vf-enshrouded\src\mod.lua" >nul
echo  Application du patch (une a deux minutes)...
"%~dp0emm\emm.exe" run -p -g "%JEU%"
if errorlevel 1 (echo. & echo  Le patch a echoue. Retrait du mod copie. & rmdir /s /q "%JEU%\mods\vf-enshrouded" & pause & exit /b 1)
echo.
echo  Termine. Dans le jeu : Options - JEU - Langue du doublage - "Francais (VF)".
pause
