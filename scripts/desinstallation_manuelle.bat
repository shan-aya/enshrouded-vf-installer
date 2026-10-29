@echo off
chcp 65001 >nul
setlocal
rem Desinstallation manuelle de la VF (restaure les fichiers d'origine du jeu avec emm.exe, puis retire le mod).
echo.
echo  VF Enshrouded - desinstallation manuelle
echo  ========================================
tasklist /FI "IMAGENAME eq enshrouded.exe" 2>nul | find /I "enshrouded.exe" >nul && (echo  Enshrouded est lance : fermez-le completement puis relancez ce fichier. & pause & exit /b 1)
set "JEU="
set /p JEU= Dossier du jeu (celui qui contient enshrouded.exe) :
set "JEU=%JEU:"=%"
if not exist "%JEU%\enshrouded.exe" (echo  enshrouded.exe introuvable dans "%JEU%". & pause & exit /b 1)
if not exist "%JEU%\enshrouded.kfc.bak" (echo  Pas de sauvegarde d'origine ^(enshrouded.kfc.bak^) : rien a restaurer. Utilisez Steam : Proprietes - Fichiers installes - Verifier l'integrite. & pause & exit /b 1)
rem Si le jeu a ete mis a jour depuis l'installation, la sauvegarde est perimee : ne PAS la restaurer.
powershell -NoProfile -Command "if ((Get-Item '%JEU%\enshrouded.exe').LastWriteTime -gt (Get-Item '%JEU%\enshrouded.kfc.bak').LastWriteTime.AddSeconds(1)) { exit 2 } else { exit 0 }"
if errorlevel 2 (echo  Le jeu a ete mis a jour depuis l'installation : la sauvegarde est perimee et ne doit PAS etre restauree. & echo  Utilisez Steam : clic droit sur Enshrouded - Proprietes - Fichiers installes - Verifier l'integrite des fichiers du jeu. & pause & exit /b 1)
echo  Restauration des fichiers d'origine...
"%~dp0emm\emm.exe" restore -g "%JEU%"
if errorlevel 1 (echo  La restauration a echoue. & pause & exit /b 1)
rmdir /s /q "%JEU%\mods\vf-enshrouded" >nul 2>&1
rem fichiers de donnees ajoutes par le patch (le jeu d'origine s'arrete a enshrouded_054.dat)
for /l %%i in (55,1,99) do if exist "%JEU%\enshrouded_0%%i.dat" del /q "%JEU%\enshrouded_0%%i.dat"
del /q "%JEU%\vf_install.json" >nul 2>&1
echo.
echo  Termine : le jeu est revenu a l'etat d'origine.
pause
