"""Installateur de la VF d'Enshrouded (voix françaises clonées, emplacement « Français (VF) » du menu Langue du doublage).
Interface française uniquement. Détecte le dossier du jeu (Steam), copie le mod, applique le patch avec emm.exe, ou restaure l'original.
Dossier du paquet (à côté de l'exécutable) : emm\\emm.exe, mod\\vf-enshrouded\\ (mod.json, src\\mod.lua, *.fqoa), LISEZMOI.txt"""
import json, os, re, shutil, subprocess, sys, threading, time, webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

VERSION = "1.0"
APPID = "1203620"
MOD_NAME = "vf-enshrouded"
TESTED_BUILD = "26082781"   # build Steam (appmanifest) sur lequel la VF a été validée (version interne du jeu : 1273043)
BASE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
if os.path.basename(BASE).lower() == "installateur": BASE = os.path.dirname(BASE)   # exécutable dans un sous-dossier du paquet
EMM = os.path.join(BASE, "emm", "emm.exe")
MOD_SRC = os.path.join(BASE, "mod", MOD_NAME)
HELP_TXT = os.path.join(BASE, "LISEZMOI.txt")
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------- détection du jeu ----------
def steam_roots():
    roots = []
    try:
        import winreg
        for hive, key, name in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
            try:
                with winreg.OpenKey(hive, key) as k: roots.append(os.path.normpath(winreg.QueryValueEx(k, name)[0]))
            except OSError: pass
    except ImportError: pass
    for p in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"):
        if os.path.isdir(p): roots.append(p)
    return list(dict.fromkeys(roots))


def library_folders():
    libs = []
    for root in steam_roots():
        libs.append(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        try:
            txt = open(vdf, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', txt): libs.append(os.path.normpath(m.group(1).replace("\\\\", "\\")))
        except OSError: pass
    return list(dict.fromkeys(libs))


def find_game():
    """Retourne (dossier du jeu, build id) ou (None, None)."""
    for lib in library_folders():
        acf = os.path.join(lib, "steamapps", f"appmanifest_{APPID}.acf")
        if not os.path.isfile(acf): continue
        try: txt = open(acf, encoding="utf-8", errors="replace").read()
        except OSError: continue
        d = re.search(r'"installdir"\s+"([^"]+)"', txt); b = re.search(r'"buildid"\s+"(\d+)"', txt)
        game = os.path.join(lib, "steamapps", "common", d.group(1) if d else "Enshrouded")
        if is_game_dir(game): return game, (b.group(1) if b else "?")
    return None, None


def is_game_dir(p):
    return bool(p) and os.path.isfile(os.path.join(p, "enshrouded.exe")) and os.path.isfile(os.path.join(p, "enshrouded.kfc"))


def game_build(game):
    for lib in library_folders():
        acf = os.path.join(lib, "steamapps", f"appmanifest_{APPID}.acf")
        if os.path.isfile(acf) and os.path.normcase(os.path.join(lib, "steamapps", "common")) in os.path.normcase(game):
            m = re.search(r'"buildid"\s+"(\d+)"', open(acf, encoding="utf-8", errors="replace").read())
            if m: return m.group(1)
    return "?"


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq enshrouded.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, creationflags=NOWIN).stdout
        return "enshrouded.exe" in out.lower()
    except Exception: return False


def dat_files(game):
    return {f: (os.path.getsize(os.path.join(game, f)), int(os.path.getmtime(os.path.join(game, f)))) for f in os.listdir(game) if re.fullmatch(r"enshrouded_\d+\.dat", f)}


def dir_size(p):
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs)


def is_pnj_file(f): return f.startswith("n") and f.endswith(".fqoa")        # audio des PNJ (journal : j*.fqoa)
def pnj_available(): return any(is_pnj_file(f) for _, _, fs in os.walk(MOD_SRC) for f in fs)   # le complément PNJ (fichier séparé) a-t-il été déposé dans le paquet ?
def lua_variant(name): return os.path.join(os.path.dirname(MOD_SRC), "variantes", name)

# ---------- fenêtre ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"VF Enshrouded — installateur {VERSION}")
        self.geometry("760x780"); self.minsize(680, 640)
        self.game = None; self.busy = False
        try:   # bandeau (illustration + logo Shan_ayA) : embarque dans l'exe (assets\entete.png, 740 px de large)
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            self.img_header = tk.PhotoImage(file=os.path.join(base, "assets", "entete.png"))
            tk.Label(self, image=self.img_header, borderwidth=0).pack(pady=(10, 0))
        except Exception: pass                    # sans image, l'installateur fonctionne quand meme
        top = ttk.Frame(self, padding=10); top.pack(fill="x")
        ttk.Label(top, text="Dossier du jeu :").grid(row=0, column=0, sticky="w")
        self.var_game = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_game).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="Parcourir…", command=self.browse).grid(row=0, column=2)
        top.columnconfigure(1, weight=1)
        self.lbl_status = ttk.Label(self, text="", padding=(10, 0), wraplength=720, justify="left"); self.lbl_status.pack(fill="x")
        bt = ttk.Frame(self, padding=10); bt.pack(fill="x")
        self.btn_install = ttk.Button(bt, text="Installer la VF", command=lambda: self.run(self.do_install)); self.btn_install.pack(side="left")
        self.btn_uninstall = ttk.Button(bt, text="Désinstaller", command=lambda: self.run(self.do_uninstall)); self.btn_uninstall.pack(side="left", padx=8)
        ttk.Button(bt, text="Vérifier", command=self.refresh).pack(side="left")
        self.var_pnj = tk.BooleanVar(value=True); self.opt_pnj = True
        self.chk_pnj = ttk.Checkbutton(bt, text="Répliques de personnages (PNJ)", variable=self.var_pnj); self.chk_pnj.pack(side="left", padx=16)
        if not pnj_available():     # complément « PNJ » (fichier séparé) absent : case grisée
            self.var_pnj.set(False); self.chk_pnj.state(["disabled"]); self.chk_pnj.configure(text="PNJ : complément non installé (voir LISEZMOI)")
        ttk.Button(bt, text="Comment régler le jeu", command=self.show_help).pack(side="right")
        foot = ttk.Frame(self); foot.pack(side="bottom", fill="x", padx=10, pady=(0, 8))      # pied de fenêtre (packé avant le journal pour rester visible)
        ttk.Label(foot, text="Mod gratuit, fait avec plaisir. Un petit café pour la suite ?").pack(side="left")
        ttk.Button(foot, text="☕ Payez-moi un café", command=lambda: webbrowser.open("https://buymeacoffee.com/shan_aya")).pack(side="right")
        self.progress = ttk.Progressbar(self, mode="determinate"); self.progress.pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(self, height=18, state="disabled", font=("Consolas", 9)); self.log.pack(fill="both", expand=True, padx=10, pady=10)
        g, b = find_game()
        if g: self.var_game.set(g); self.say(f"Jeu détecté : {g} (build {b})")
        else: self.say("Jeu non détecté automatiquement : utilisez « Parcourir… » pour choisir le dossier qui contient enshrouded.exe.")
        self.refresh()

    # -- utilitaires d'interface
    def say(self, msg):
        def f():
            self.log.configure(state="normal"); self.log.insert("end", msg + "\n"); self.log.see("end"); self.log.configure(state="disabled")
        self.after(0, f)

    def set_progress(self, v, maxv=None):
        def f():
            if maxv: self.progress.configure(maximum=maxv)
            self.progress["value"] = v
        self.after(0, f)

    def browse(self):
        d = filedialog.askdirectory(title="Choisir le dossier d'Enshrouded (celui qui contient enshrouded.exe)")
        if d: self.var_game.set(os.path.normpath(d)); self.refresh()

    def state_path(self, game): return os.path.join(game, "vf_install.json")

    def installed(self, game):
        return os.path.isfile(self.state_path(game))

    def refresh(self):
        game = self.var_game.get().strip()
        if not is_game_dir(game):
            self.game = None; self.lbl_status.configure(text="⚠ Dossier du jeu invalide (enshrouded.exe / enshrouded.kfc introuvables)."); return
        self.game = game; b = game_build(game)
        parts = [f"Jeu : build {b}" + ("" if b in ("?", TESTED_BUILD) else f" (la VF a été testée sur le build {TESTED_BUILD} : elle peut ne pas fonctionner)")]
        parts.append("VF installée ✔" if self.installed(game) else "VF non installée")
        if game_running(): parts.append("⚠ le jeu est lancé : fermez-le avant d'installer ou de désinstaller")
        if not os.path.isfile(EMM) or not os.path.isdir(MOD_SRC): parts.append("⚠ fichiers du paquet introuvables à côté de l'installateur")
        self.lbl_status.configure(text="  —  ".join(parts))

    def run(self, fn):
        if self.busy: return
        self.refresh()
        if not self.game: messagebox.showwarning("VF Enshrouded", "Choisissez d'abord le dossier du jeu."); return
        if game_running(): messagebox.showwarning("VF Enshrouded", "Enshrouded est lancé. Fermez le jeu complètement puis réessayez."); return
        if not os.path.isfile(EMM) or not os.path.isdir(MOD_SRC): messagebox.showerror("VF Enshrouded", "Les fichiers du paquet (dossiers « emm » et « mod ») doivent rester à côté de l'installateur."); return
        self.opt_pnj = bool(self.var_pnj.get())     # lu ici (fil de l'interface) puis utilise par le fil de travail
        self.busy = True; self.btn_install.state(["disabled"]); self.btn_uninstall.state(["disabled"])
        def work():
            try: fn(self.game)
            except Exception as e: self.say(f"ERREUR : {e}")
            finally:
                self.busy = False
                self.after(0, lambda: (self.btn_install.state(["!disabled"]), self.btn_uninstall.state(["!disabled"]), self.refresh()))
        threading.Thread(target=work, daemon=True).start()

    def emm(self, args):
        p = subprocess.run([EMM] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NOWIN, cwd=os.path.dirname(EMM))
        out = re.sub(r"\x1b\[[0-9;]*m", "", (p.stdout or "") + (p.stderr or ""))
        return p.returncode, out

    # -- installation
    def do_install(self, game):
        has_pnj = pnj_available(); is_pnj = is_pnj_file
        pnj = self.opt_pnj and has_pnj
        light, full = lua_variant("mod_sans_pnj.lua"), lua_variant("mod_complet.lua")
        if has_pnj and not pnj and not os.path.isfile(light):
            self.say("Variante « sans PNJ » introuvable dans le paquet : installation complète à la place."); pnj = True
        self.say("Répliques de personnages (PNJ) : " + ("incluses." if pnj else ("NON incluses (pages de journal seules)." if has_pnj else "complément non présent : pages de journal seules.")))
        need = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(MOD_SRC) for f in fs if pnj or not is_pnj(f)) * 2 + 500 * 1024 * 1024
        free = shutil.disk_usage(game).free
        if free < need:
            self.say(f"Espace disque insuffisant : {free // 2**20} Mo libres, {need // 2**20} Mo nécessaires."); return
        if self.installed(game):
            self.say("Une installation existe déjà : retrait avant de réinstaller…"); self.do_uninstall(game, quiet=True)
        before = dat_files(game)
        dst = os.path.join(game, "mods", MOD_NAME)
        if os.path.isdir(dst): shutil.rmtree(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        files = [(r, f) for r, _, fs in os.walk(MOD_SRC) for f in fs if pnj or not is_pnj(f)]
        total = sum(os.path.getsize(os.path.join(r, f)) for r, f in files); done = 0
        self.say(f"Copie des fichiers audio ({total // 2**20} Mo)…"); self.set_progress(0, max(total, 1))
        for r, f in files:
            s = os.path.join(r, f); t = os.path.join(dst, os.path.relpath(s, MOD_SRC)); os.makedirs(os.path.dirname(t), exist_ok=True)
            shutil.copyfile(s, t); done += os.path.getsize(s); self.set_progress(done)
        # script du mod : avec complément -> mod_complet.lua (fourni par le complément) ; PNJ décochés sur un paquet complet -> mod_sans_pnj.lua ; paquet principal seul : src\mod.lua est déjà « journal seul »
        if pnj and os.path.isfile(full): shutil.copyfile(full, os.path.join(dst, "src", "mod.lua"))
        elif not pnj and has_pnj: shutil.copyfile(light, os.path.join(dst, "src", "mod.lua"))
        self.say("Application du patch (cela peut durer une à deux minutes)…"); self.after(0, lambda: (self.progress.configure(mode="indeterminate"), self.progress.start(12)))
        rc, out = self.emm(["run", "-p", "-g", game])
        self.after(0, lambda: (self.progress.stop(), self.progress.configure(mode="determinate"), self.progress.configure(value=0)))
        m = re.search(r"Applied (\d+) patches", out)
        if rc != 0 or not m:
            self.say("Le patch a échoué. Détail :\n" + out[-1500:]); shutil.rmtree(dst, ignore_errors=True)
            self.say("Les fichiers copiés ont été retirés. Si le jeu ne démarre plus : Steam → Propriétés → Fichiers installés → Vérifier l'intégrité."); return
        for ln in out.splitlines():
            mm = re.search(r"(VF : .*|ERREUR .*)", ln)
            if mm: self.say("   " + mm.group(1)[:300])
        after = dat_files(game)
        new = sorted(f for f, v in after.items() if before.get(f) != v)
        json.dump(dict(date=time.strftime("%Y-%m-%d %H:%M:%S"), version=VERSION, build=game_build(game), patches=int(m.group(1)), pnj=pnj, dat_changed=new),
                  open(self.state_path(game), "w", encoding="utf-8"), indent=1)
        self.say(f"Installation terminée ({m.group(1)} modifications appliquées).")
        self.say("Dans le jeu : Options → onglet JEU → « Langue du doublage » → « Français (VF) ». (Bouton « Comment régler le jeu » pour le détail.)")

    # -- désinstallation
    def do_uninstall(self, game, quiet=False):
        bak = os.path.join(game, "enshrouded.kfc.bak"); exe = os.path.join(game, "enshrouded.exe")
        stale = os.path.isfile(bak) and os.path.getmtime(exe) > os.path.getmtime(bak) + 1
        if not os.path.isfile(bak):
            self.say("Aucune sauvegarde d'origine (enshrouded.kfc.bak) : rien à restaurer automatiquement.")
        elif stale:
            self.say("⚠ Le jeu a été mis à jour depuis l'installation : la sauvegarde est périmée et ne doit PAS être restaurée.")
            self.say("   Pour retrouver le jeu d'origine : Steam → clic droit sur Enshrouded → Propriétés → Fichiers installés → Vérifier l'intégrité des fichiers.")
        else:
            self.say("Restauration des fichiers d'origine…")
            rc, out = self.emm(["restore", "-g", game])
            if rc != 0: self.say("La restauration a échoué :\n" + out[-1000:]); return
            try: extra = json.load(open(self.state_path(game), encoding="utf-8")).get("dat_changed", [])
            except Exception: extra = []
            n = 0
            for f in extra:
                m = re.fullmatch(r"enshrouded_(\d+)\.dat", f)
                if m and int(m.group(1)) >= 55:   # fichiers de données ajoutés par le patch (le jeu d'origine s'arrête à 054)
                    try: os.remove(os.path.join(game, f)); n += 1
                    except OSError: pass
            if n: self.say(f"{n} fichier(s) de données ajouté(s) par le patch supprimé(s).")
        shutil.rmtree(os.path.join(game, "mods", MOD_NAME), ignore_errors=True)
        try: os.remove(self.state_path(game))
        except OSError: pass
        if not quiet: self.say("Désinstallation terminée.")

    def show_help(self):
        w = tk.Toplevel(self); w.title("Comment régler le jeu"); w.geometry("640x520")
        t = scrolledtext.ScrolledText(w, wrap="word", font=("Segoe UI", 10)); t.pack(fill="both", expand=True)
        try: t.insert("1.0", open(HELP_TXT, encoding="utf-8").read())
        except OSError: t.insert("1.0", "LISEZMOI.txt introuvable.")
        t.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()
