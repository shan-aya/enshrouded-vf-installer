"""Extrait la bibliotheque Tcl et Tk de Python 3.14 (Tcl/Tk 9 : elles sont embarquees dans la DLL, en zipfs) vers un dossier,
pour que PyInstaller les embarque dans l'exe (le crochet de PyInstaller 6.20 ne les trouve pas seul avec Tcl/Tk 9).
usage : python extract_tcl_tk.py <dossier_sortie>   -> <dossier_sortie>\tcl\tcl_library et <dossier_sortie>\tk\tk_library"""
import os, shutil, sys, tkinter
out = os.path.abspath(sys.argv[1]); os.makedirs(out, exist_ok=True)
root = tkinter.Tk(); root.withdraw(); tcl = root.tk
for name, lib in (("tcl", "tcl_library"), ("tk", "tk_library")):
    src = tcl.eval(f"set {lib}")                       # ex. //zipfs:/lib/tcl/tcl_library
    dst = os.path.join(out, name, lib)
    if os.path.isdir(dst): shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tcl.eval(f'file copy -force "{src}" "{dst.replace(os.sep, "/")}"')
    print(name, "->", dst, sum(len(f) for _, _, f in os.walk(dst)), "fichiers")
root.destroy()
