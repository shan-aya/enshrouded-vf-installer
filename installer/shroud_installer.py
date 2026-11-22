"""Installateur LÉGER de la VF d'Enshrouded (voix françaises, emplacement « Français (VF) » du menu Langue du doublage).
Interface française. Ne contient AUCUN fichier audio ni emm.exe : il utilise les archives téléchargées sur Nexus Mods
(fichier principal = pages de journal + narration d'introduction ; complément optionnel = répliques des personnages) et l'outil emm.exe d'EML (GitHub).
Il trouve le jeu (Steam), les archives et emm.exe, décompresse le mod dans <jeu>\\mods\\ShroudInFrench, applique le patch
(emm.exe run -p) ou restaure l'original. Accède à GitHub pour récupérer la dernière version de emm.exe ; rien n’est modifié hors du dossier du jeu et du cache EML du profil utilisateur."""
# safe-modify v16 — 2026-11-22 — fenêtre ancrée en haut et adaptée à l'écran (agrandissement Windows 250 % : bas de l'application masqué).
# safe-modify v15 — 2026-11-22 — l'intro est incluse dans l'archive principale (un seul dossier ShroudInFrench) ; l'ancien complément « ShroudInFrenchIntro » est retiré à la mise à jour.
# safe-modify v9 — 2026-11-21 — téléchargement automatique vérifié de la dernière version officielle de emm.exe.
# safe-modify v10 — 2026-11-21 — ouverture maximisée pour garder les commandes du bas visibles.
# safe-modify v12 — 2026-11-21 — fenêtre compacte fixe, sans maximisation.
# safe-modify v13 — 2026-11-21 — largeur fixe portée à 860 px pour les cases de l’interface.
# safe-modify v14 — 2026-11-21 — retour de la ligne d’état adapté à la largeur de la fenêtre.
# safe-modify v11 — 2026-11-21 — cache EML hors-ligne utilisé seulement après contrôle d’empreinte.
# safe-modify v8 — 2026-11-21 — bouton « Comment régler le jeu » déplacé dans une ligne dédiée pour rester visible.
# safe-modify v7 — 2026-11-20 : état PNJ exact lors d'une mise à jour Intro seule.
# safe-modify v6 — 2026-11-20 : mises à jour sélectives PNJ/Intro sans supprimer les autres dossiers VF.
# safe-modify v5 — 2026-11-20 : ajout du complément optionnel Intro VF et désinstallation conjointe.
# safe-modify v4 — 2026-11-19 : mise à jour/désinstallation en reconstruisant le patch EML avec les autres mods.
# v3 — 2026-11-19 : refuse aussi une mise à jour si la désinstallation préalable est bloquée.
# v2 — 2026-11-19 : restauration contrôlée, retrait des caches/données EML et garde-fou pour les autres mods.
import filecmp, hashlib, json, os, re, shutil, subprocess, sys, threading, time, urllib.request, urllib.parse, webbrowser, zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

VERSION = "2.4.1"
APPID = "1203620"
MOD_NAME = "ShroudInFrench"
MOD_PREFIX = f"mods/{MOD_NAME}/"
INTRO_MOD_NAME = "ShroudInFrenchIntro"
INTRO_PREFIX = f"mods/{INTRO_MOD_NAME}/"      # ancien complément séparé : seulement pour le nettoyer
INTRO_AUDIO = "intro_fr_damien_stereo.fqoa"   # narration de l'intro, incluse dans le fichier principal depuis la 2.3.0
TESTED_BUILD = "26430625"   # build Steam testé (version interne du jeu : 1287369)
EML_URL = "https://github.com/Brabb3l/kfc-parser/releases"
EML_LATEST_API = "https://api.github.com/repos/Brabb3l/kfc-parser/releases/latest"
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
- Sur Nexus Mods : le fichier principal « ShroudInFrench » (pages de journal et narration d'introduction), et en option « PNJ » (dialogues). Laissez les .zip tels quels dans « Téléchargements » : l'installateur les trouve seul (sinon « Parcourir… »).
- L'outil EML `emm.exe` est téléchargé et mis à jour automatiquement depuis la dernière release officielle GitHub. Une connexion Internet est nécessaire au premier lancement ou lorsqu'une nouvelle version sort. En cas d'indisponibilité, un `emm.exe` local reste utilisable.
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
    """Reconnaît le principal ou le complément PNJ par le contenu du zip (l'ancien complément Intro séparé n'est plus utilisé)."""
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
                if f.lower().endswith(".zip") and os.path.isfile(p) and 100 * 2**10 < os.path.getsize(p) < 3 * 2**30: cands.append(p)
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



def eml_cache_root():
    """Return the EML cache in the user profile, outside the game folder."""
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(root, "ShroudInFrench", "EML")


def download_latest_emm():
    """Download emm.exe from the latest official EML release and verify SHA-256."""
    request = urllib.request.Request(EML_LATEST_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ShroudInFrench-Installer",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        release = json.loads(response.read().decode("utf-8"))
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise RuntimeError("invalid EML release tag")
    asset = next((item for item in release.get("assets", []) if item.get("name") == "emm.exe"), None)
    if not asset:
        raise RuntimeError(f"emm.exe missing from EML release {tag}")
    url = asset.get("browser_download_url", "")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith("/Brabb3l/kfc-parser/releases/download/"):
        raise RuntimeError("unexpected EML download URL")
    digest = asset.get("digest", "")
    match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", digest)
    size = asset.get("size")
    if not match or not isinstance(size, int) or size < 5 * 2**20:
        raise RuntimeError("official SHA-256 or emm.exe size unavailable")
    expected = match.group(1).lower()
    folder = os.path.join(eml_cache_root(), tag)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, "emm.exe")

    def valid_file(path):
        if not os.path.isfile(path) or os.path.getsize(path) != size:
            return False
        h = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest() == expected and emm_version(path) is not None

    if valid_file(target):
        with open(target + ".sha256", "w", encoding="ascii") as sidecar:
            sidecar.write(f"{expected} {size}")
        return target, tag, False
    part = target + ".part"
    h = hashlib.sha256()
    received = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ShroudInFrench-Installer"})
        with urllib.request.urlopen(request, timeout=30) as response, open(part, "wb") as output:
            while True:
                block = response.read(1 << 20)
                if not block:
                    break
                received += len(block)
                if received > size:
                    raise RuntimeError("emm.exe exceeds the size announced by GitHub")
                h.update(block)
                output.write(block)
        if received != size or h.hexdigest() != expected:
            raise RuntimeError("emm.exe size or SHA-256 does not match GitHub")
        os.replace(part, target)
        if not emm_version(target):
            os.remove(target)
            raise RuntimeError("downloaded file is not a recognized emm.exe")
        with open(target + ".sha256", "w", encoding="ascii") as sidecar:
            sidecar.write(f"{expected} {size}")
        return target, tag, True
    finally:
        try:
            if os.path.exists(part):
                os.remove(part)
        except OSError:
            pass


def cached_emm():
    """Return a cached EML executable only when its saved SHA-256 and size still match."""
    root = eml_cache_root()
    try:
        tags = sorted(os.listdir(root), reverse=True)
    except OSError:
        return None
    for tag in tags:
        path = os.path.join(root, tag, "emm.exe")
        try:
            parts = open(path + ".sha256", encoding="ascii").read().split()
            if len(parts) != 2 or os.path.getsize(path) != int(parts[1]):
                continue
            h = hashlib.sha256()
            with open(path, "rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    h.update(block)
            if h.hexdigest() == parts[0].lower() and emm_version(path):
                return path
        except (OSError, ValueError):
            continue
    return None

def find_emm(game=None):
    names = []
    for d in search_dirs(game):
        names += [os.path.join(d, "emm.exe"), os.path.join(d, "emm", "emm.exe")]
        try: names += [os.path.join(d, s, "emm.exe") for s in os.listdir(d) if os.path.isdir(os.path.join(d, s)) and s.lower() in ("eml", "emm", "enshrouded mod loader")]
        except OSError: pass
    for p in names:
        if os.path.isfile(p) and os.path.getsize(p) > 5 * 2**20: return p
    return cached_emm()


def safe_members(z):
    """N'accepte que le dossier correspondant au type d'archive, sans traversal."""
    out = []
    names = {i.filename.replace("\\", "/") for i in z.infolist()}
    prefix = MOD_PREFIX
    for i in z.infolist():
        n = i.filename.replace("\\", "/")
        if i.is_dir(): continue
        if not n.startswith(prefix) or ".." in n.split("/") or os.path.isabs(n) or ":" in n: continue
        out.append(i)
    return out


# ---------- fenêtre ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ShroudInFrench — installateur {VERSION}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(860, sw - 24)
        self.geometry(f"{width}x{min(760, sh - 96)}+{max(0, (sw - width) // 2)}+4")    # ancrée en haut de l'écran ; ajustée ensuite par fit_window()
        self.header_label = None
        self.game = None; self.busy = False; self.emm_updating = False; self.opt_pnj = True
        try:   # bandeau (illustration + logo Shan_ayA) embarqué dans l'exe (assets\entete.png)
            base = getattr(sys, "_MEIPASS", BASE)
            self.img_header = tk.PhotoImage(file=os.path.join(base, "assets", "entete.png"))
            self.header_label = tk.Label(self, image=self.img_header, borderwidth=0); self.header_label.pack(pady=(10, 0))
        except Exception: pass
        box = ttk.Frame(self, padding=(10, 8, 10, 0)); box.pack(fill="x"); box.columnconfigure(1, weight=1)
        self.var_game, self.var_emm, self.var_main, self.var_pnjzip = (tk.StringVar() for _ in range(4))
        ttk.Label(box, text="Dossier du jeu :").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_game).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_dir(self.var_game, "Dossier d'Enshrouded (celui qui contient enshrouded.exe)")).grid(row=0, column=2)
        ttk.Label(box, text="emm.exe (EML) :").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_emm).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_emm, "emm.exe", [("emm.exe", "emm.exe"), ("Programmes", "*.exe")])).grid(row=1, column=2)
        ttk.Button(box, text="Récupérer EML", command=self.update_emm).grid(row=1, column=3, padx=(6, 0))
        ttk.Label(box, text="Fichier principal :").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_main).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_main, "Archive principale « ShroudInFrench » (.zip)", [("Archives", "*.zip")])).grid(row=2, column=2)
        ttk.Label(box, text="Complément PNJ :").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(box, textvariable=self.var_pnjzip).grid(row=3, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Parcourir…", command=lambda: self.browse_file(self.var_pnjzip, "Archive optionnelle « PNJ » (.zip)", [("Archives", "*.zip")])).grid(row=3, column=2)
        self.lbl_status = ttk.Label(self, text="", padding=(10, 6), wraplength=max(400, width - 40), justify="left"); self.lbl_status.pack(fill="x")
        # safe-modify v8: put help on a dedicated full-width row so it stays visible at normal window sizes.
        helpbar = ttk.Frame(self, padding=(10, 0, 10, 4)); helpbar.pack(fill="x")
        ttk.Button(helpbar, text="Comment régler le jeu", command=self.show_help).pack(side="left")
        bt = ttk.Frame(self, padding=(10, 0, 10, 8)); bt.pack(fill="x")
        self.btn_install = ttk.Button(bt, text="Installer la VF", command=lambda: self.run(self.do_install)); self.btn_install.pack(side="left")
        self.btn_uninstall = ttk.Button(bt, text="Désinstaller", command=lambda: self.run(self.do_uninstall)); self.btn_uninstall.pack(side="left", padx=8)
        ttk.Button(bt, text="Vérifier", command=self.refresh).pack(side="left")
        self.var_pnj = tk.BooleanVar(value=True)
        ttk.Checkbutton(bt, text="Répliques de personnages (PNJ)", variable=self.var_pnj).pack(side="left", padx=16)
        foot = ttk.Frame(self); foot.pack(side="bottom", fill="x", padx=10, pady=(0, 8))      # pied de fenêtre (packé avant le journal pour rester visible)
        ttk.Label(foot, text="Mod gratuit, fait avec plaisir. Un petit café pour la suite ?").pack(side="left")
        ttk.Button(foot, text="☕ Payez-moi un café", command=lambda: webbrowser.open(COFFEE_URL)).pack(side="right")
        self.progress = ttk.Progressbar(self, mode="determinate"); self.progress.pack(fill="x", padx=10)
        self.log = scrolledtext.ScrolledText(self, height=8, state="disabled", font=("Consolas", 9)); self.log.pack(fill="both", expand=True, padx=10, pady=10)
        self.fit_window()
        g, b = find_game()
        if g: self.var_game.set(g); self.say(f"Jeu détecté : {g} (build {b})")
        else: self.say("Jeu non détecté automatiquement : utilisez « Parcourir… » pour choisir le dossier qui contient enshrouded.exe.")
        self.autodetect(g)
        self.refresh()
        self.after(150, self.update_emm)

    def fit_window(self):
        """Adapte la fenêtre à l'écran : avec un agrandissement Windows de 200-250 %, l'écran « logique » est petit (ex. 1536×864, voire moins) et une fenêtre
        fixe de 760 px débordait en bas, sans être ancrée en haut. On ancre la fenêtre en haut, on réduit le bandeau puis le journal si besoin,
        et la fenêtre reste redimensionnable."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        avail_w, avail_h = sw - 24, sh - 96                     # barre des tâches + barre de titre
        width = min(860, avail_w)
        self.lbl_status.configure(wraplength=max(300, width - 40))
        steps = [lambda: None,
                 lambda: self.header_label.pack_forget() if self.header_label else None,
                 lambda: self.log.configure(height=4),
                 lambda: self.log.configure(height=2)]
        used = 0
        for used, step in enumerate(steps):
            step(); self.update_idletasks()
            if self.winfo_reqheight() <= avail_h: break
        height = min(self.winfo_reqheight(), avail_h)
        if used == 0: height = min(max(height, 760), avail_h)      # écran normal : hauteur habituelle (le journal prend l'espace libre)
        self.geometry(f"{width}x{height}+{max(0, (sw - width) // 2)}+4")
        self.minsize(min(width, 560), min(height, 260)); self.resizable(True, True)

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
            else: self.say("emm.exe absent : recherche et téléchargement automatiques de la dernière version officielle d’EML…")
        a = find_archives(game)
        if a["main"] and not self.var_main.get(): self.var_main.set(a["main"]); self.say(f"Fichier principal trouvé : {a['main']}")
        if a["pnj"] and not self.var_pnjzip.get(): self.var_pnjzip.set(a["pnj"]); self.say(f"Complément PNJ trouvé : {a['pnj']}")
        if not a["main"] and not self.var_main.get(): self.say("Fichier principal (.zip) non trouvé dans Téléchargements / Bureau : téléchargez-le sur Nexus Mods, ou choisissez-le avec « Parcourir… ».")

    def update_emm(self):
        """Récupère en arrière-plan le emm.exe de la dernière release officielle EML."""
        if self.emm_updating:
            return
        self.emm_updating = True
        existing = self.var_emm.get().strip()
        self.say("Vérification de la dernière version EML sur GitHub…")

        def worker():
            try:
                path, tag, downloaded = download_latest_emm()
                message = f"emm.exe EML {tag} " + ("téléchargé et vérifié (SHA-256)." if downloaded else "déjà à jour (SHA-256 vérifié).")
            except Exception as exc:
                path = existing if existing and os.path.isfile(existing) else find_emm(self.game)
                if path and emm_version(path):
                    message = f"GitHub indisponible ({exc}) ; utilisation du emm.exe local : {path}"
                else:
                    path = ""
                    message = f"Téléchargement EML impossible : {exc}. Vérifiez la connexion ou choisissez emm.exe avec « Parcourir… »."

            def finish():
                if path:
                    self.var_emm.set(path)
                self.emm_updating = False
                self.say(message)
                self.refresh()
            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def state_path(self, game): return os.path.join(game, "vf_install.json")
    def installed(self, game): return os.path.isfile(self.state_path(game))
    def mod_dir(self, game): return os.path.join(game, "mods", MOD_NAME)
    def intro_mod_dir(self, game): return os.path.join(game, "mods", INTRO_MOD_NAME)

    def other_eml_mods(self, game):
        """Mods EML installés, hors VF. Les dossiers sans mod.json ne sont pas des mods EML."""
        root = os.path.join(game, "mods")
        try:
            return [n for n in os.listdir(root)
                    if n.casefold() not in (MOD_NAME.casefold(), INTRO_MOD_NAME.casefold())
                    and os.path.isfile(os.path.join(root, n, "mod.json"))]
        except OSError:
            return []

    def patch_eml(self, game):
        rc, out = self.emm(["run", "-p", "-f", "-g", game])
        applied = re.search(r"Applied (\d+) patches", out)
        return rc == 0 and applied is not None, out, (int(applied.group(1)) if applied else None)

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
        if os.path.isdir(self.intro_mod_dir(game)): parts.append("ancien complément Intro détecté : il sera retiré à l'installation (l'intro est dans le fichier principal)")
        elif has_mod and not os.path.isfile(os.path.join(self.mod_dir(game), INTRO_AUDIO)): parts.append("⚠ intro absente : utilisez le fichier principal 2.3.0 ou plus récent")
        self.lbl_status.configure(text="  —  ".join(parts))

    def run(self, fn):
        if self.busy: return
        self.refresh()
        if not self.game: messagebox.showwarning("ShroudInFrench", "Choisissez d'abord le dossier du jeu."); return
        if game_running(): messagebox.showwarning("ShroudInFrench", "Enshrouded est lancé. Fermez le jeu complètement puis réessayez."); return
        if self.emm_updating: messagebox.showinfo("ShroudInFrench", "Attendez la fin de la vérification ou du téléchargement d’EML."); return
        if not os.path.isfile(self.var_emm.get().strip()): messagebox.showerror("ShroudInFrench", "emm.exe (EML) est introuvable.\nVérifiez la connexion ou choisissez-le avec « Parcourir… »."); return
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
        intro_dst = self.intro_mod_dir(game)
        if not have_main_zip and not pre_existing and not self.installed(game):
            self.say("Fichier principal introuvable : téléchargez « ShroudInFrench » sur Nexus Mods (ou choisissez le .zip avec « Parcourir… »)."); return
        if have_main_zip and zip_kind(main) != "main": self.say("Le fichier choisi comme « principal » n'est pas l'archive principale de la VF."); return
        if have_pnj_zip and zip_kind(pnjz) != "pnj": self.say("Le fichier choisi comme « PNJ » n'est pas l'archive des répliques de personnages."); return
        use_pnj = self.opt_pnj
        pnj_present = os.path.isdir(mod_dst) and any(f.startswith("n") and f.endswith(".fqoa") for f in os.listdir(mod_dst))
        self.say("Répliques de personnages (PNJ) : " + ("incluses." if use_pnj and (have_pnj_zip or pnj_present) else ("demandées mais fichier PNJ absent : pages de journal seules." if use_pnj else "NON incluses (pages de journal seules).")))
        # L'intro est dans le fichier principal (>= 2.3.0). L'ancien dossier mods\ShroudInFrenchIntro est retiré (sauvegardé le temps de l'installation,
        # restauré en cas d'échec) uniquement si le principal installé contient l'intro : sinon on le laisse en place.
        main_has_intro = False
        if have_main_zip:
            try:
                with zipfile.ZipFile(main) as zm: main_has_intro = (MOD_PREFIX + INTRO_AUDIO) in {n.replace("\\", "/") for n in zm.namelist()}
            except (zipfile.BadZipFile, OSError): main_has_intro = False
        elif os.path.isfile(os.path.join(mod_dst, INTRO_AUDIO)): main_has_intro = True
        migrate_intro = os.path.isdir(intro_dst) and main_has_intro
        self.say("Narration de l'intro : " + ("incluse dans le fichier principal." + (" L'ancien complément Intro séparé sera retiré." if migrate_intro else "") if main_has_intro else "ABSENTE de ce fichier principal (utilisez la version 2.3.0 ou plus récente)" + (" ; l'ancien complément Intro est conservé." if os.path.isdir(intro_dst) else ".")))
        zips = ([main] if have_main_zip else []) + ([pnjz] if (use_pnj and have_pnj_zip) else [])
        total = 0
        for zp in zips:
            with zipfile.ZipFile(zp) as z: total += sum(i.file_size for i in safe_members(z))
        need = total * 2 + 900 * 1024 * 1024
        free = shutil.disk_usage(game).free
        if free < need: self.say(f"Espace disque insuffisant : {free // 2**20} Mo libres, {need // 2**20} Mo nécessaires."); return
        # Une archive optionnelle ne doit jamais effacer les autres composants déjà installés.
        # Le dossier journal/PNJ est modifié uniquement si l'archive principale/PNJ change
        # ou si la case PNJ est décochée.
        mod_touched = have_main_zip or (use_pnj and have_pnj_zip) or not use_pnj
        old_state = {}
        old_mod_backup = None
        old_intro_backup = None
        was_installed = self.installed(game)
        backup_kfc = os.path.join(game, "enshrouded.kfc.bak")
        game_exe = os.path.join(game, "enshrouded.exe")
        if was_installed:
            try: old_state = json.load(open(self.state_path(game), encoding="utf-8"))
            except Exception: old_state = {}
            if not os.path.isfile(backup_kfc) or os.path.getmtime(game_exe) > os.path.getmtime(backup_kfc) + 1:
                self.say("Mise à jour arrêtée : la sauvegarde EML est absente ou périmée. Vérifiez les fichiers du jeu dans Steam avant de réessayer.")
                return
        if mod_touched and os.path.isdir(mod_dst):
            old_mod_backup = os.path.join(game, f".ShroudInFrench_update_{int(time.time())}")
            if os.path.exists(old_mod_backup):
                self.say("Mise à jour arrêtée : un dossier de sauvegarde temporaire existe déjà.")
                return
            shutil.move(mod_dst, old_mod_backup)
        if migrate_intro:
            old_intro_backup = os.path.join(game, f".ShroudInFrenchIntro_update_{int(time.time())}")
            if os.path.exists(old_intro_backup):
                if old_mod_backup: shutil.move(old_mod_backup, mod_dst)
                self.say("Mise à jour arrêtée : un dossier temporaire Intro existe déjà.")
                return
            shutil.move(intro_dst, old_intro_backup)
        before = dat_files(game)
        try:
            if zips:
                self.say(f"Décompression des fichiers du mod dans le jeu ({total // 2**20} Mo)…"); self.set_progress(0, max(total, 1)); done = 0
                if have_main_zip:
                    if os.path.isdir(mod_dst): shutil.rmtree(mod_dst)
                    done = self.extract(main, game, done, total)
                elif mod_touched and old_mod_backup and os.path.isdir(old_mod_backup):
                    # Pour un remplacement PNJ seul (ou une désactivation PNJ), repartir
                    # d'une copie de l'ancien dossier permet un retour arrière complet.
                    shutil.copytree(old_mod_backup, mod_dst)
                if use_pnj and have_pnj_zip:
                    done = self.extract(pnjz, game, done, total)
                elif have_main_zip and use_pnj and old_mod_backup and os.path.isdir(old_mod_backup):
                    # Mise à jour principale seule : garder les fichiers PNJ déjà installés.
                    os.makedirs(mod_dst, exist_ok=True)
                    for f in os.listdir(old_mod_backup):
                        if f.startswith("n") and f.endswith(".fqoa"):
                            shutil.copy2(os.path.join(old_mod_backup, f), os.path.join(mod_dst, f))
            elif mod_touched and old_mod_backup and os.path.isdir(old_mod_backup):
                shutil.copytree(old_mod_backup, mod_dst)
            if not use_pnj:  # PNJ décochés : retirer les voix optionnelles du paquet installé.
                if os.path.isdir(mod_dst):
                    for f in os.listdir(mod_dst):
                        if f.startswith("n") and f.endswith(".fqoa"): os.remove(os.path.join(mod_dst, f))
        except Exception:
            if mod_touched: shutil.rmtree(mod_dst, ignore_errors=True)
            if old_mod_backup:
                shutil.move(old_mod_backup, mod_dst)
            if old_intro_backup:
                shutil.move(old_intro_backup, intro_dst)
            if old_mod_backup or self.other_eml_mods(game):
                self.patch_eml(game)
            raise
        self.say("Application du patch (cela peut durer une à deux minutes)…"); self.after(0, lambda: (self.progress.configure(mode="indeterminate"), self.progress.start(12)))
        ok, out, patch_count = self.patch_eml(game)
        self.after(0, lambda: (self.progress.stop(), self.progress.configure(mode="determinate"), self.progress.configure(value=0)))
        if not ok:
            self.say("Le patch a échoué. Détail :\n" + out[-1500:])
            if mod_touched: shutil.rmtree(mod_dst, ignore_errors=True)
            if old_mod_backup:
                os.makedirs(os.path.dirname(mod_dst), exist_ok=True)
                shutil.move(old_mod_backup, mod_dst)
            if old_intro_backup:
                os.makedirs(os.path.dirname(intro_dst), exist_ok=True)
                shutil.move(old_intro_backup, intro_dst)
            self.say("Fichiers VF précédents restaurés." if (old_mod_backup or old_intro_backup) else "Fichiers VF retirés après l'échec.")
            # Reconstitue le patch à partir des fichiers restaurés et des autres mods.
            if old_mod_backup or old_intro_backup or self.other_eml_mods(game):
                restored, restore_out, _ = self.patch_eml(game)
                if not restored: self.say("⚠ EML n'a pas pu reconstruire le patch restauré :\n" + restore_out[-1000:])
            self.say("Aucun fichier de données partagé ni cache EML n'a été supprimé.")
            return
        for ln in out.splitlines():
            mm = re.search(r"(VF : .*|ERREUR .*)", ln)
            if mm: self.say("   " + mm.group(1)[:300])
        after = dat_files(game)
        new = sorted(f for f, v in after.items() if before.get(f) != v)
        dat_cleanup_safe = (not self.other_eml_mods(game)
                            and old_state.get("dat_cleanup_safe", not bool(old_state)))
        tracked_dat = (sorted(set(old_state.get("dat_changed", [])) | set(new))
                       if dat_cleanup_safe else [])
        with open(self.state_path(game), "w", encoding="utf-8") as sf:
            json.dump(dict(date=time.strftime("%Y-%m-%d %H:%M:%S"), version=VERSION,
                           build=game_build(game), patches=patch_count,
                           pnj=bool(use_pnj and os.path.isdir(mod_dst) and any(f.startswith("n") and f.endswith(".fqoa") for f in os.listdir(mod_dst))), intro=bool(os.path.isfile(os.path.join(mod_dst, INTRO_AUDIO))), dat_changed=tracked_dat,
                           dat_cleanup_safe=dat_cleanup_safe), sf, indent=1)
        if old_mod_backup: shutil.rmtree(old_mod_backup, ignore_errors=True)
        if old_intro_backup: shutil.rmtree(old_intro_backup, ignore_errors=True)
        self.say(f"Installation terminée ({patch_count} modifications appliquées, autres mods EML conservés).")
        self.say("Dans le jeu : Options → onglet JEU → « Langue du doublage » → « Français (VF) ». (Bouton « Comment régler le jeu » pour le détail.)")

    # -- désinstallation
    def do_uninstall(self, game, quiet=False):
        bak = os.path.join(game, "enshrouded.kfc.bak")
        exe = os.path.join(game, "enshrouded.exe")
        mod_dst = self.mod_dir(game)
        intro_dst = self.intro_mod_dir(game)
        other_mods = self.other_eml_mods(game)
        try:
            state = json.load(open(self.state_path(game), encoding="utf-8"))
        except Exception:
            state = {}
        stale = os.path.isfile(bak) and os.path.getmtime(exe) > os.path.getmtime(bak) + 1
        if not os.path.isfile(bak):
            self.say("Sauvegarde d'origine absente. Le mod VF va être retiré, mais les fichiers du jeu ne peuvent pas être restaurés automatiquement. Lancez ensuite la vérification Steam.")
            shutil.rmtree(mod_dst, ignore_errors=True)
            shutil.rmtree(intro_dst, ignore_errors=True)
            try: os.remove(self.state_path(game))
            except OSError: pass
            return False
        if stale:
            self.say("⚠ Le jeu a été mis à jour depuis la sauvegarde. Elle n'est pas restaurée. Le mod VF va être retiré; utilisez ensuite la vérification Steam pour réparer le jeu.")
            shutil.rmtree(mod_dst, ignore_errors=True)
            shutil.rmtree(intro_dst, ignore_errors=True)
            try: os.remove(self.state_path(game))
            except OSError: pass
            return False
        if other_mods:
            # Retire seulement la VF, puis EML rebâtit le KFC à partir de l'original
            # et des mods qui restent. Garder .dat et .cache, qui peuvent leur appartenir.
            backup_root = os.path.join(game, f".ShroudInFrench_uninstall_{int(time.time())}")
            if os.path.exists(backup_root):
                self.say("Désinstallation arrêtée : un dossier temporaire existe déjà.")
                return False
            had_mod_dir = os.path.isdir(mod_dst)
            had_intro_dir = os.path.isdir(intro_dst)
            if had_mod_dir:
                try:
                    os.makedirs(backup_root)
                    shutil.move(mod_dst, os.path.join(backup_root, MOD_NAME))
                except OSError as e:
                    self.say(f"Impossible de mettre la VF de côté : {e}"); return False
            if had_intro_dir:
                try:
                    if not os.path.isdir(backup_root): os.makedirs(backup_root)
                    shutil.move(intro_dst, os.path.join(backup_root, INTRO_MOD_NAME))
                except OSError as e:
                    if had_mod_dir and os.path.isdir(os.path.join(backup_root, MOD_NAME)):
                        shutil.move(os.path.join(backup_root, MOD_NAME), mod_dst)
                    shutil.rmtree(backup_root, ignore_errors=True)
                    self.say(f"Impossible de mettre le complément Intro de côté : {e}"); return False
            ok, out, count = self.patch_eml(game)
            if not ok:
                if had_mod_dir:
                    try: shutil.move(os.path.join(backup_root, MOD_NAME), mod_dst)
                    except OSError: pass
                if had_intro_dir:
                    try: shutil.move(os.path.join(backup_root, INTRO_MOD_NAME), intro_dst)
                    except OSError: pass
                shutil.rmtree(backup_root, ignore_errors=True)
                self.say("La reconstruction avec les autres mods a échoué. La VF a été remise en place. Détail :\n" + out[-1500:])
                return False
            shutil.rmtree(backup_root, ignore_errors=True)
            try: os.remove(self.state_path(game))
            except OSError: pass
            self.say(f"VF retirée. Patch EML reconstruit avec les {len(other_mods)} autre(s) mod(s) ; leurs fichiers de données et leur cache ont été conservés.")
            return True

        self.say("Aucun autre mod EML détecté : restauration des fichiers d'origine…")
        rc, out = self.emm(["restore", "-g", game])
        if rc != 0:
            self.say("La restauration a échoué :\n" + out[-1000:])
            return False

        shutil.rmtree(mod_dst, ignore_errors=True)
        shutil.rmtree(intro_dst, ignore_errors=True)
        names = set(state.get("dat_changed", [])) if state.get("dat_cleanup_safe", False) else set()
        # Une installation antérieure ou manuelle peut ne pas avoir de marqueur.
        # Le balayage n'est donc permis que sur le build testé, sans autre mod.
        if not state and game_build(game) == TESTED_BUILD:
            try:
                names = {n for n in os.listdir(game) if re.fullmatch(r"enshrouded_(\d+)\.dat", n) and int(re.fullmatch(r"enshrouded_(\d+)\.dat", n).group(1)) >= 55}
            except OSError:
                names = set()
        removed = 0
        for name in names:
            m = re.fullmatch(r"enshrouded_(\d+)\.dat", name)
            if m and int(m.group(1)) >= 55:
                try:
                    os.remove(os.path.join(game, name)); removed += 1
                except OSError:
                    pass
        if removed:
            self.say(f"{removed} fichier(s) de données EML ajouté(s) supprimé(s).")
        cache = os.path.join(game, ".cache")
        if os.path.isdir(cache):
            shutil.rmtree(cache, ignore_errors=True)
            self.say("Cache EML supprimé (il sera recréé si EML est réutilisé).")
        kfc = os.path.join(game, "enshrouded.kfc")
        if os.path.isfile(bak) and os.path.isfile(kfc):
            try:
                if filecmp.cmp(kfc, bak, shallow=False):
                    os.remove(bak)
                    self.say("Sauvegarde .kfc identique à l'original restauré supprimée.")
            except OSError:
                pass
        try: os.remove(self.state_path(game))
        except OSError: pass
        if not quiet:
            self.say("Désinstallation terminée : jeu restauré, dossier VF, cache EML et fichiers de patch retirés.")
        return True

    def show_help(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = tk.Toplevel(self); w.title("Comment régler le jeu"); w.geometry(f"{min(640, sw - 24)}x{min(520, sh - 96)}+{max(0, (sw - min(640, sw - 24)) // 2)}+4")
        t = scrolledtext.ScrolledText(w, wrap="word", font=("Segoe UI", 10)); t.pack(fill="both", expand=True)
        t.insert("1.0", HELP); t.configure(state="disabled")


if __name__ == "__main__":
    App().mainloop()

