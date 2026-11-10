# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller (onedir) de l'installateur. Chemins relatifs au depot. Prerequis : build\tclx\ (voir build\extract_tcl_tk.py / build_installer.ps1).
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
a = Analysis(
    [os.path.join(ROOT, 'installer', 'shround_installer.py')],
    pathex=[],
    binaries=[],
    datas=[(os.path.join(ROOT, 'build', 'tclx', 'tcl', 'tcl_library'), '_tcl_data'),
           (os.path.join(ROOT, 'build', 'tclx', 'tk', 'tk_library'), '_tk_data'),
           (os.path.join(ROOT, 'installer', 'assets', 'entete.png'), 'assets')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ShroundInFrench_Installateur', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None,
          codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name='ShroundInFrench_Installateur')
