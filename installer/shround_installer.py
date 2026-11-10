"""Installateur LÉGER de la VF d'Enshrouded (voix françaises, emplacement « Français (VF) » du menu Langue du doublage).
Interface française. Ne contient AUCUN fichier audio ni emm.exe : il utilise les archives téléchargées sur Nexus Mods
(fichier principal = pages de journal ; complément optionnel = répliques des personnages) et l'outil emm.exe d'EML (GitHub).
Il trouve le jeu (Steam), les archives et emm.exe, décompresse le mod dans <jeu>\\mods\\ShroundInFrench, applique le patch
(emm.exe run -p) ou restaure l'original. Aucun accès réseau ; rien n'est modifié hors du dossier du jeu."""
import json, os, re, shutil, subprocess, sys, threading, time, webbrowser, zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

VERSION = "2.0"
APPID = "1203620"
MOD_NAME = "ShroundInFrench"
MOD_PREFIX = f"mods/{MOD_NAME}/"
TESTED_BUILD = "26082781"   # build Steam (appmanifest) sur lequel la VF a été validée (version interne du jeu : 1273043)
EML_URL = "https://github.com/Brabb3l/kfc-parser/releases"
COFFEE_URL = "https://buymeacoffee.com/shan_aya"
BASE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

HELP = """RÉGLER LE JEU (à faire une fois)
1. Lancez Enshrouded. Options → onglet JEU.
2. « Langue » : Français (texte du jeu).
3. « Langue du doublage » : choisissez « Français (VF) » (dernier choix de la liste).
4. « Lire automatiquement les notes sur l'univers » : « Toujours jouer » pour que les pages de journal se lisent seules.

IMPORTANT
- « Français (VF) » prend la place de « Chinois » dans la liste : les voix chinoises ne sont plus accessibles tant que la VF est installée.
- Interjections, cris et répliques sans version française restent en anglais.
- Après une mise à jour du jeu (Steam), relancez cet installateur : « Installer la VF ».
- Si l'installateur dit que la sauvegarde est périmée : Steam → clic droit sur Enshrouded → Propriétés → Fichiers installés → « Vérifier l'intégrité des fichiers du jeu », puis relancez l'installateur.

CE QU'IL FAUT TÉLÉCHARGER
- Sur Nexus Mods : le fichier principal « ShroundInFrench » (pages de journal) et, si vous voulez la voix des personnages, le fichier optionnel « PNJ ». Laissez les .zip tels quels dans « Téléchargements » : l'installateur les trouve seul (sinon « Parcourir… »).
- emm.exe (outil d'EML, par Brabb3l) : bouton « Où le télécharger ? » → GitHub → dernière version → « Assets » → emm.exe.
"""


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


# ---------- détection des archives Nexus et d'emm.exe ----------
def search_dirs(game=None):
    home = os.path.expanduser("~")
    dirs = [BASE, os.path.dirname(BASE), os.path.join(home, "Downloads"), os.path.join(home, "Téléchargements"), os.path.join(home, "Desktop"), os.path.join(home, "Bureau")]
    if game: dirs.append(game)
    return [d for d in dict.fromkeys(os.path.normpath(d) for d in dirs) if os.path.isdir(d)]


def zip_kind(path):
    """'main' (contient mods/ShroundInFrench/mod.json), 'pnj' (fichiers n*.fqoa seuls) ou None. Lit seulement l'index du zip (rapide)."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except (zipfile.BadZipFile, OSError): return None
    if MOD_PREFIX + "mod.json" in names: return "main"
    if any(n.startswith(MOD_PREFIX + "n") and n.endswith(".fqoa") for n in names): return "pnj"
    return None


def find_archives(game=None):
    """Cherche dans Téléchargements, Bureau, dossier de l'installateur et du jeu les .zip de la VF (reconnus par leur contenu, pas par leur nom : Nexus renomme les fichiers)."""
    found = {"main": None, "pnj": None}; cands = []
    for d in search_dirs(game):
        try:
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if f.lower().endswith(".zip") and os.path.isfile(p) and 5 * 2**20 < os.path.getsize(p) < 3 * 2**30: cands.append(p)
        except OSError: pass
    for p in sorted(cands, key=os.path.getmtime, reverse=True)[:60]:     # les plus récents d'abord
        if all(found.values()): break
        k = zip_kind(p)
        if k and not found[k]: found[k] = p
    return found


def emm_version(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15, creationflags=NOWIN).stdout.strip()
        return out if "mod-manager" in out.lower() or "emm" in out.lower() else None
    except Exception: return None


def find_emm(game=None):
    names = []
    for d in search_dirs(game):
        names += [os.path.join(d, "emm.exe"), os.path.join(d, "emm", "emm.exe")]
        try: names += [os.path.join(d, s, "emm.exe") for s in os.listdir(d) if os.path.isdir(os.path.join(d, s)) and s.lower() in ("eml", "emm", "enshrouded mod loader")]
        except OSError: pass
    for p in names:
        if os.path.isfile(p) and os.path.getsize(p) > 5 * 2**20: return p
    return None


def safe_members(z):
    """Entrées du zip autorisées : uniquement sous mods/ShroundInFrench/, sans « .. » ni chemin absolu."""
    out = []
    for i in z.infolist():
        n = i.filename.replace("\\", "/")
        if i.is_dir(): continue
        if not n.startswith(MOD_PREFIX) or ".." in n.split("/") or os.path.isabs(n) or ":" in n: continue
        out.append(i)
    return out


# ---------- fenêtre ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ShroundInFrench — installateur {VERSION}")
        self.geometry("780x880"); self.minsize(700, 760)
        self.game = None; self.busy = False; self.opt_pnj = True
        try:   # bandeau (illustration + logo Shan_ayA) embarqué dans l'exe (assets\entete.png)
            base = getattr(sys, "_MEIPASS", BASE)
            self.img_header = tk.PhotoImage(file=os.path.join(base, "assets", "entete.png"))
            tk.Label(self, image=self.img_header, borderwidth=0).pack(pady=(10, 0))
        except Exception: pass
        box = ttk.Frame(self, padding=(10, 8, 10, 0)); box.pack(fill="x"); box.columnconfigure(1, weight=1)
        self.var_game, self.var_emm, self.var_main, self.var_pnjzip = (tk.StringVar() for _ in range(4))
        ttk.Label(box, text="Dossier du jeu :").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_game).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_dir(self.var_game, "Dossier d'Enshrouded (celui qui contient enshrouded.exe)")).grid(row=0, column=2)
        ttk.Label(box, text="emm.exe (EML) :").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_emm).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_emm, "emm.exe", [("emm.exe", "emm.exe"), ("Programmes", "*.exe")])).grid(row=1, column=2)
        ttk.Button(box, text="Où le télécharger ?", command=lambda: webbrowser.open(EML_URL)).grid(row=1, column=3, padx=(6, 0))
        ttk.Label(box, text="Fichier principal :").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_main).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_main, "Archive principale « ShroundInFrench » (.zip)", [("Archives", "*.zip")])).grid(row=2, column=2)
        ttk.Label(box, text="Complément PNJ :").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_pnjzip).grid(row=3, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_pnjzip, "Archive optionnelle « PNJ » (.zip)", [("Archives", "*.zip")])).grid(row=3, column=2)
        self.lbl_status = ttk.Label(self, text="", padding=(10, 6), wraplength=740, justify="left"); self.lbl_status.pack(fill="x")
        bt = ttk.Frame(self, padding=(10, 0, 10, 8)); bt.pack(fill="x")
        self.btn_install = ttk.Button(bt, text="Installer la VF", command=lambda: self.run(self.do_install)); self.btn_install.pack(side="left")
        self.btn_uninstall = ttk.Button(bt, text="Désinstaller", command=lambda: self.run(self.do_uninstall)); self.btn_uninstall.pack(side="left", padx=8)
        ttk.Button(bt, text="Vérifier", command=self.refresh).pack(side="left")
        self.var_pnj = tk.BooleanVar(value=True)
        ttk.Checkbutton(bt, text="Répliques de personnages (PNJ)", variable=self.var_pnj).pack(side="left", padx=16)
        ttk.Button(bt, text="Comment régler le jeu", command=self.show_help).pack(side="right")
        foot = ttk.Frame(self); foot.pack(side="bottom", fill="x", padx=10, pady=(0, 8))      # pied de fenêtre (packé avant le journal pour rester visible)
        ttk.Label(foot, text="Mod gratuit, fait avec plaisir. Un petit café pour la suite ?").pack(side="left")
        ttk.Button(foot, text="☕ Payez-moi un café", command=lambda: webbrowser.open(COFFEE_URL)).pack(side="right")
        self.progress = ttk.Progressbar(self, mode="determinate"); self.progress.pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(self, height=12, state="disabled", font=("Consolas", 9)); self.log.pack(fill="both", expand=True, padx=10, pady=10)
        g, b = find_game()
        if g: self.var_game.set(g); self.say(f"Jeu détecté : {g} (build {b})")
        else: self.say("Jeu non détecté automatiquement : utilisez « Parcourir… » pour choisir le dossier qui contient enshrouded.exe.")
        self.autodetect(g)
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

    def browse_dir(self, var, title):
        d = filedialog.askdirectory(title=title)
        if d: var.set(os.path.normpath(d)); self.refresh()

    def browse_file(self, var, title, types):
        f = filedialog.askopenfilename(title=title, filetypes=types)
        if f: var.set(os.path.normpath(f)); self.refresh()

    def autodetect(self, game=None):
        if not self.var_emm.get():
            p = find_emm(game)
            if p: self.var_emm.set(p); self.say(f"emm.exe trouvé : {p}")
            else: self.say("emm.exe introuvable : téléchargez-le (bouton « Où le télécharger ? ») puis choisissez-le avec « Parcourir… ».")
        a = find_archives(game)
        if a["main"] and not self.var_main.get(): self.var_main.set(a["main"]); self.say(f"Fichier principal trouvé : {a['main']}")
        if a["pnj"] and not self.var_pnjzip.get(): self.var_pnjzip.set(a["pnj"]); self.say(f"Complément PNJ trouvé : {a['pnj']}")
        if not a["main"] and not self.var_main.get(): self.say("Fichier principal (.zip) non trouvé dans Téléchargements / Bureau : téléchargez-le sur Nexus Mods, ou choisissez-le avec « Parcourir… ».")

    def state_path(self, game): return os.path.join(game, "vf_install.json")
    def installed(self, game): return os.path.isfile(self.state_path(game))
    def mod_dir(self, game): return os.path.join(game, "mods", MOD_NAME)

    def refresh(self):
        game = self.var_game.get().strip()
        if not is_game_dir(game):
            self.game = None; self.lbl_status.configure(text="⚠ Dossier du jeu invalide (enshrouded.exe / enshrouded.kfc introuvables)."); return
        self.game = game; b = game_build(game)
        parts = [f"Jeu : build {b}" + ("" if b in ("?", TESTED_BUILD) else f" (la VF a été testée sur le build {TESTED_BUILD} : elle peut ne pas fonctionner)")]
        parts.append("VF installée ✔" if self.installed(game) else "VF non installée")
        if game_running(): parts.append("⚠ le jeu est lancé : fermez-le avant d'installer ou de désinstaller")
        emm = self.var_emm.get().strip()
        parts.append("emm.exe ✔" if os.path.isfile(emm) else "⚠ emm.exe manquant")
        m, p = self.var_main.get().strip(), self.var_pnjzip.get().strip()
        has_mod = os.path.isfile(os.path.join(self.mod_dir(game), "mod.json"))
        parts.append("principal ✔" if os.path.isfile(m) else ("principal : déjà dans le jeu ✔" if has_mod else "⚠ fichier principal manquant"))
        parts.append("PNJ ✔" if os.path.isfile(p) else "PNJ : absent (optionnel)")
        self.lbl_status.configure(text="  —  ".join(parts))

    def run(self, fn):
        if self.busy: return
        self.refresh()
        if not self.game: messagebox.showwarning("ShroundInFrench", "Choisissez d'abord le dossier du jeu."); return
        if game_running(): messagebox.showwarning("ShroundInFrench", "Enshrouded est lancé. Fermez le jeu complètement puis réessayez."); return
        if not os.path.isfile(self.var_emm.get().strip()): messagebox.showerror("ShroundInFrench", "emm.exe (EML) est introuvable.\nUtilisez « Où le télécharger ? », puis « Parcourir… »."); return
        self.opt_pnj = bool(self.var_pnj.get())
        self.emm_path = self.var_emm.get().strip(); self.zip_main = self.var_main.get().strip(); self.zip_pnj = self.var_pnjzip.get().strip()
        self.busy = True; self.btn_install.state(["disabled"]); self.btn_uninstall.state(["disabled"])
        def work():
            try: fn(self.game)
            except Exception as e: self.say(f"ERREUR : {e}")
            finally:
                self.busy = False
                self.after(0, lambda: (self.btn_install.state(["!disabled"]), self.btn_uninstall.state(["!disabled"]), self.refresh()))
        threading.Thread(target=work, daemon=True).start()

    def emm(self, args):
        p = subprocess.run([self.emm_path] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NOWIN, cwd=os.path.dirname(self.emm_path))
        out = re.sub(r"\x1b\[[0-9;]*m", "", (p.stdout or "") + (p.stderr or ""))
        return p.returncode, out

    def extract(self, zpath, game, done, total):
        with zipfile.ZipFile(zpath) as z:
            for i in safe_members(z):
                t = os.path.join(game, *i.filename.replace("\\", "/").split("/")); os.makedirs(os.path.dirname(t), exist_ok=True)
                with z.open(i) as src, open(t, "wb") as dst:
                    while True:
                        buf = src.read(1 << 20)
                        if not buf: break
                        dst.write(buf); done += len(buf); self.set_progress(done)
        return done

    # -- installation
    def do_install(self, game):
        main, pnjz = self.zip_main, self.zip_pnj
        have_main_zip, have_pnj_zip = os.path.isfile(main), os.path.isfile(pnjz)
        mod_dst = self.mod_dir(game); pre_existing = os.path.isfile(os.path.join(mod_dst, "mod.json")) and not self.installed(game)
        if not have_main_zip and not pre_existing:
            self.say("Fichier principal introuvable : téléchargez « ShroundInFrench » sur Nexus Mods (ou choisissez le .zip avec « Parcourir… »)."); return
        if have_main_zip and zip_kind(main) != "main": self.say("Le fichier choisi comme « principal » n'est pas l'archive principale de la VF."); return
        if have_pnj_zip and zip_kind(pnjz) != "pnj": self.say("Le fichier choisi comme « PNJ » n'est pas l'archive des répliques de personnages."); return
        use_pnj = self.opt_pnj
        self.say("Répliques de personnages (PNJ) : " + ("incluses." if use_pnj and (have_pnj_zip or pre_existing) else ("demandées mais fichier PNJ absent : pages de journal seules." if use_pnj else "NON incluses (pages de journal seules).")))
        zips = ([main] if have_main_zip else []) + ([pnjz] if (use_pnj and have_pnj_zip) else [])
        total = 0
        for zp in zips:
            with zipfile.ZipFile(zp) as z: total += sum(i.file_size for i in safe_members(z))
        need = total * 2 + 900 * 1024 * 1024
        free = shutil.disk_usage(game).free
        if free < need: self.say(f"Espace disque insuffisant : {free // 2**20} Mo libres, {need // 2**20} Mo nécessaires."); return
        if self.installed(game):
            self.say("Une installation existe déjà : retrait avant de réinstaller…"); self.do_uninstall(game, quiet=True)
        before = dat_files(game)
        if zips:
            if os.path.isdir(mod_dst): shutil.rmtree(mod_dst)
            self.say(f"Décompression des fichiers du mod dans le jeu ({total // 2**20} Mo)…"); self.set_progress(0, max(total, 1)); done = 0
            for zp in zips: done = self.extract(zp, game, done, total)
        if not use_pnj:                                   # PNJ décochés : on retire d'éventuels fichiers n*.fqoa déjà présents (le script du mod ignore les fichiers PNJ absents)
            for f in os.listdir(mod_dst):
                if f.startswith("n") and f.endswith(".fqoa"): os.remove(os.path.join(mod_dst, f))
        self.say("Application du patch (cela peut durer une à deux minutes)…"); self.after(0, lambda: (self.progress.configure(mode="indeterminate"), self.progress.start(12)))
        rc, out = self.emm(["run", "-p", "-g", game])
        self.after(0, lambda: (self.progress.stop(), self.progress.configure(mode="determinate"), self.progress.configure(value=0)))
        m = re.search(r"Applied (\d+) patches", out)
        if rc != 0 or not m:
            self.say("Le patch a échoué. Détail :\n" + out[-1500:])
            if zips: shutil.rmtree(mod_dst, ignore_errors=True); self.say("Les fichiers décompressés ont été retirés.")
            self.say("Si le jeu ne démarre plus : Steam → Propriétés → Fichiers installés → Vérifier l'intégrité."); return
        for ln in out.splitlines():
            mm = re.search(r"(VF : .*|ERREUR .*)", ln)
            if mm: self.say("   " + mm.group(1)[:300])
        after = dat_files(game)
        new = sorted(f for f, v in after.items() if before.get(f) != v)
        json.dump(dict(date=time.strftime("%Y-%m-%d %H:%M:%S"), version=VERSION, build=game_build(game), patches=int(m.group(1)), pnj=bool(use_pnj), dat_changed=new),
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
        shutil.rmtree(self.mod_dir(game), ignore_errors=True)
        try: os.remove(self.state_path(game))
        except OSError: pass
        if not quiet: self.say("Désinstallation terminée.")

    def show_help(self):
        w = tk.Toplevel(self); w.title("Comment régler le jeu"); w.geometry("640x520")
        t = scrolledtext.ScrolledText(w, wrap="word", font=("Segoe UI", 10)); t.pack(fill="both", expand=True)
        t.insert("1.0", HELP); t.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()

