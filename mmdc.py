import os
import re
import json
import zipfile
from collections import defaultdict
from typing import Iterable, Dict, Tuple, List

import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

APP_NAME = "Duplicate Name Scanner — by Star (Aniket)"
CONFIG_NAME = "mc_dupes_gui_config.json"

##############################
# Utility / Core logic
##############################

def prettify_from_id(item_id: str) -> str:
    if not isinstance(item_id, str):
        return "Unknown"
    s = item_id.split(":", 1)[1] if ":" in item_id else item_id
    s = s.strip().replace("/", "_")
    parts = re.split(r"[_\-\.]+", s)
    parts = [p for p in parts if p]
    return " ".join(w.capitalize() for w in parts) if parts else s.capitalize()

def infer_kind_from_path(path_str: str) -> str:
    p = path_str.lower().replace("\\", "/")
    if "block" in p:
        return "block"
    if "entity" in p or "mob" in p:
        return "entity"
    if "biome" in p:
        return "biome"
    if "worldgen" in p or "structure" in p or "feature" in p:
        return "worldgen"
    return "item"

def lang_key_for(kind: str, modid: str, path: str) -> str:
    if kind == "block":
        return f"block.{modid}.{path}"
    if kind == "entity":
        return f"entity.{modid}.{path}"
    if kind == "biome":
        return f"biome.{modid}.{path}"
    if kind == "worldgen":
        return f"worldgen.{modid}.{path}"
    return f"item.{modid}.{path}"

def extract_ids_from_json(obj) -> Iterable[str]:
    if isinstance(obj, list):
        for v in obj:
            if isinstance(v, str):
                yield v
            elif isinstance(v, dict):
                for k in ("id", "identifier", "registry_name", "registryName"):
                    if k in v and isinstance(v[k], str):
                        yield v[k]
    elif isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list):
                for x in extract_ids_from_json(v):
                    yield x
        for k in ("id", "identifier", "registry_name", "registryName"):
            if k in obj and isinstance(obj[k], str):
                yield obj[k]

def scan_registry_folder(registry_folder: str, treat_underscores_as_spaces: bool=False, case_insensitive: bool=False):
    """
    Returns list of entries: {id, modid, path, source_file}
    Display names are NOT resolved here; just the IDs.
    """
    entries = []
    for root, _, files in os.walk(registry_folder):
        for fn in files:
            if not fn.lower().endswith(".json"):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            for full_id in extract_ids_from_json(data):
                if not isinstance(full_id, str):
                    continue
                full_id = full_id.strip()
                if ":" in full_id:
                    modid, path = full_id.split(":", 1)
                else:
                    modid, path = "minecraft", full_id
                # optional normalization settings affect only name comparison later; keep raw id
                entries.append({
                    "id": f"{modid}:{path}",
                    "modid": modid,
                    "path": path,
                    "source_file": os.path.relpath(p, registry_folder)
                })
    return entries

def load_mod_langs(mods_folder: str) -> Dict[str, Dict[str, str]]:
    """
    modid -> { lang_key: text }
    """
    mod_langs: Dict[str, Dict[str, str]] = {}
    for fn in os.listdir(mods_folder):
        if not (fn.endswith(".jar") or fn.endswith(".zip")):
            continue
        jar_path = os.path.join(mods_folder, fn)
        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                for name in zf.namelist():
                    if not name.endswith("lang/en_us.json"):
                        continue
                    parts = name.split("/")
                    if len(parts) < 4 or parts[0] != "assets":
                        continue
                    modid = parts[1]
                    try:
                        with zf.open(name) as f:
                            lang = json.load(f)
                        mod_langs.setdefault(modid, {}).update(lang)
                    except Exception:
                        continue
        except Exception:
            continue
    return mod_langs

def load_resource_pack_langs(rp_path: str) -> Dict[str, str]:
    """
    Merge all assets/*/lang/en_us.json files found in a resource pack folder or zip/jar.
    Return lang_key -> string (RP overrides).
    """
    overrides: Dict[str, str] = {}
    if not rp_path or rp_path.lower() == "none":
        return overrides
    if os.path.isdir(rp_path):
        for root, _, files in os.walk(rp_path):
            for fn in files:
                if fn.lower() != "en_us.json":
                    continue
                p = os.path.join(root, fn)
                if "assets" not in p.replace("\\","/").lower():
                    continue
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        lang = json.load(f)
                    overrides.update(lang)
                except Exception:
                    pass
    else:
        try:
            with zipfile.ZipFile(rp_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("lang/en_us.json") and "/assets/" in f"/{name}":
                        try:
                            with zf.open(name) as f:
                                lang = json.load(f)
                            overrides.update(lang)
                        except Exception:
                            continue
        except Exception:
            pass
    return overrides

def normalize_name_for_compare(text: str, case_insensitive: bool, treat_underscores_as_spaces: bool) -> str:
    t = text.replace("_", " ") if treat_underscores_as_spaces else text
    return t.lower() if case_insensitive else t

global check_missing_lang_global
def compute_display_names(kind: str,
                          entries,
                          mod_langs: Dict[str, Dict[str, str]],
                          rp_overrides: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Returns (before_names, after_names): id -> name
    """
    before = {}
    after = {}
    for e in entries:
        modid, path = e["modid"], e["path"]
        key = lang_key_for(kind, modid, path)
        base_name = None
        if modid in mod_langs and key in mod_langs[modid]:
            base_name = mod_langs[modid][key]
        if not base_name:
            if check_missing_lang_global:
                print(f"[WARN] Missing lang key for {e['id']} ({key})")
            base_name = prettify_from_id(e["id"])
        before[e["id"]] = base_name
        new_name = rp_overrides.get(key, base_name)
        after[e["id"]] = new_name
    return before, after

def group_dupes_by_name(ids_to_names: Dict[str, str],
                        case_insensitive: bool,
                        treat_underscores_as_spaces: bool) -> Dict[str, List[str]]:
    name_groups = defaultdict(list)
    for item_id, nm in ids_to_names.items():
        k = normalize_name_for_compare(nm, case_insensitive, treat_underscores_as_spaces)
        name_groups[k].append(item_id)
    return {n: lst for n, lst in name_groups.items() if len(lst) >= 2}

def build_mod_index(dupe_groups: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
    per_mod = defaultdict(lambda: defaultdict(list))
    for norm_name, ids in dupe_groups.items():
        mods_present = {i.split(":",1)[0] for i in ids}
        if len(mods_present) < 2:
            continue
        for m in mods_present:
            per_mod[m][norm_name] = ids
    return per_mod

def write_reports(output_dir: str,
                  registry_folder: str,
                  kind: str,
                  before_names: Dict[str,str],
                  after_names: Dict[str,str],
                  case_insensitive: bool,
                  treat_underscores_as_spaces: bool) -> Tuple[str, str, str, str]:
    os.makedirs(output_dir, exist_ok=True)

    before_dupes = group_dupes_by_name(before_names, case_insensitive, treat_underscores_as_spaces)
    after_dupes = group_dupes_by_name(after_names, case_insensitive, treat_underscores_as_spaces)

    # 1) Baseline master
    base_master = os.path.join(output_dir, "BASELINE_duplicates.txt")
    with open(base_master, "w", encoding="utf-8") as f:
        f.write(f"# Baseline duplicates by name (before RP) | kind={kind} | scanned: {os.path.abspath(registry_folder)}\n")
        f.write(f"# Compare settings: case_insensitive={case_insensitive}, underscores_as_spaces={treat_underscores_as_spaces}\n\n")
        for norm_name in sorted(before_dupes.keys(), key=lambda s: s.lower()):
            # show one representative titleized form for readability
            display = next(iter(before_dupes[norm_name]))
            f.write(f"{norm_name}\n")
            for item_id in sorted(before_dupes[norm_name]):
                f.write(f"  - {item_id}\n")
            f.write("\n")

    # 2) After-RP master
    after_master = os.path.join(output_dir, "AFTER_RP_duplicates.txt")
    with open(after_master, "w", encoding="utf-8") as f:
        f.write(f"# Duplicates by name AFTER applying RP overrides | kind={kind}\n")
        f.write(f"# Compare settings: case_insensitive={case_insensitive}, underscores_as_spaces={treat_underscores_as_spaces}\n\n")
        for norm_name in sorted(after_dupes.keys(), key=lambda s: s.lower()):
            f.write(f"{norm_name}\n")
            for item_id in sorted(after_dupes[norm_name]):
                base = before_names.get(item_id, "")
                now = after_names.get(item_id, "")
                mark = " (changed)" if base != now else ""
                f.write(f"  - {item_id}  -> \"{now}\"{mark}\n")
            f.write("\n")

    # 3) Per-mod after-RP
    per_mod = build_mod_index(after_dupes)
    by_mod_dir = os.path.join(output_dir, "by_mod_AFTER_RP")
    os.makedirs(by_mod_dir, exist_ok=True)
    index_path = os.path.join(by_mod_dir, "_index.txt")
    with open(index_path, "w", encoding="utf-8") as idx:
        idx.write("# Per-Mod duplicate report (AFTER RP)\n")
        for modid in sorted(per_mod.keys(), key=lambda s: s.lower()):
            idx.write(f"{modid}: {modid}.txt\n")
    for modid in sorted(per_mod.keys(), key=lambda s: s.lower()):
        mod_file = os.path.join(by_mod_dir, f"{modid}.txt")
        with open(mod_file, "w", encoding="utf-8") as f:
            f.write(f"# Duplicates for mod AFTER RP: {modid}\n\n")
            for norm_name in sorted(per_mod[modid].keys(), key=lambda s: s.lower()):
                f.write(f"{norm_name}\n")
                for item_id in sorted(per_mod[modid][norm_name]):
                    base = before_names.get(item_id, "")
                    now = after_names.get(item_id, "")
                    mark = " (changed)" if base != now else ""
                    f.write(f"  - {item_id}  -> \"{now}\"{mark}\n")
                f.write("\n")

    # 4) Diff of changes
    changed_file = os.path.join(output_dir, "RP_changes_diff.txt")
    with open(changed_file, "w", encoding="utf-8") as f:
        f.write("# Items whose display name changed due to RP\n\n")
        for item_id in sorted(before_names.keys() | after_names.keys()):
            b = before_names.get(item_id)
            a = after_names.get(item_id)
            if b != a:
                f.write(f"{item_id}\n  BEFORE: {b}\n  AFTER : {a}\n\n")

    return base_master, after_master, by_mod_dir, changed_file

##############################
# Config IO
##############################

def load_config(script_dir: str) -> dict:
    cfg_path = os.path.join(script_dir, CONFIG_NAME)
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(script_dir: str, data: dict) -> bool:
    cfg_path = os.path.join(script_dir, CONFIG_NAME)
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

##############################
# GUI
##############################

class App(tb.Window):
    def __init__(self):
        # Load config BEFORE creating the window
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.cfg = load_config(self.script_dir)

        # Determine theme using plain Python values
        dark_pref = self.cfg.get("dark_mode", True)
        theme = "darkly" if dark_pref else "flatly"

        # Now create the window
        super().__init__(title=APP_NAME, themename=theme)
        self.geometry("900x640")

        # Now create Tk variables (window already exists)
        self.case_insensitive = tk.BooleanVar(value=self.cfg.get("case_insensitive", True))
        self.underscores_as_spaces = tk.BooleanVar(value=self.cfg.get("underscores_as_spaces", True))

        self.enable_rp = tk.BooleanVar(value=self.cfg.get("enable_rp", True))
        self.check_missing_lang = tk.BooleanVar(value=self.cfg.get("check_missing_lang", False))
        self.exclude_mods = tk.StringVar(value=self.cfg.get("exclude_mods", ""))

        self.dark_mode = tk.BooleanVar(value=dark_pref)

        # Path vars
        self.dump_root = tk.StringVar(value=self.cfg.get("dump_root", ""))
        self.registry_folder = tk.StringVar(value=self.cfg.get("registry_folder", ""))
        self.mods_folder = tk.StringVar(value=self.cfg.get("mods_folder", ""))
        self.rp_path = tk.StringVar(value=self.cfg.get("rp_path", ""))
        self.output_folder = tk.StringVar(value=self.cfg.get("output_folder", ""))

        self.kind_inferred = tk.StringVar(value="(auto)")


        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.frame_home = ttk.Frame(nb)
        self.frame_settings = ttk.Frame(nb)
        self.frame_help = ttk.Frame(nb)
        nb.add(self.frame_home, text="Scan")
        nb.add(self.frame_settings, text="Settings")
        nb.add(self.frame_help, text="Help / About")

        self.build_home()
        self.build_settings()
        self.build_help()

        self.update_kind_label()

    def build_home(self):
        f = self.frame_home

        # Dump root + registry picker
        row = 0
        ttk.Label(f, text="Dump Root:").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(f, textvariable=self.dump_root, width=80).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(f, text="Browse", command=self.pick_dump_root).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(f, text="Registry Folder (auto from Dump Root):").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        self.registry_combo = ttk.Combobox(f, textvariable=self.registry_folder, width=77, values=[])
        self.registry_combo.grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(f, text="Scan Dump Root", command=self.scan_dump_root_for_candidates).grid(row=row, column=2, padx=6, pady=6)

        # Mods / RP / Output
        row += 1
        ttk.Label(f, text="Mods Folder (.jar files):").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(f, textvariable=self.mods_folder, width=80).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(f, text="Browse", command=self.pick_mods_folder).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(f, text="Resource Pack (zip/folder, optional):").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(f, textvariable=self.rp_path, width=80).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(f, text="Browse", command=self.pick_rp_path).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(f, text="Output Folder:").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(f, textvariable=self.output_folder, width=80).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(f, text="Browse", command=self.pick_output_folder).grid(row=row, column=2, padx=6, pady=6)

        # Kind + actions
        row += 1
        ttk.Label(f, text="Inferred kind:").grid(row=row, column=0, sticky="e", padx=6, pady=6)
        ttk.Label(f, textvariable=self.kind_inferred).grid(row=row, column=1, sticky="w", padx=6, pady=6)

        row += 1
        actions = ttk.Frame(f)
        actions.grid(row=row, column=0, columnspan=3, sticky="we", padx=6, pady=6)
        ttk.Button(actions, text="Start Scan", command=self.do_scan).pack(side="left", padx=4)
        ttk.Button(actions, text="Save Defaults", command=self.save_defaults).pack(side="left", padx=4)

        # Log box
        row += 1
        ttk.Label(f, text="Run Log:").grid(row=row, column=0, sticky="ne", padx=6, pady=6)
        self.log_text = tk.Text(f, height=14)
        self.log_text.grid(row=row, column=1, columnspan=2, sticky="nsew", padx=6, pady=6)
        f.grid_columnconfigure(1, weight=1)
        f.grid_rowconfigure(row, weight=1)

    def build_settings(self):
        f = self.frame_settings
        ttk.Checkbutton(f, text="Case-insensitive name comparison", variable=self.case_insensitive).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        ttk.Checkbutton(f, text="Treat underscores as spaces during comparison", variable=self.underscores_as_spaces).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        ttk.Label(f, text="Tip: These settings only affect how duplicates are detected, not how names are written.").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        row = 3
        ttk.Checkbutton(f, text="Enable Resource Pack filtering", variable=self.enable_rp)\
        .grid(row=row, column=0, sticky="w", padx=10, pady=10)

        row += 1
        ttk.Checkbutton(f, text="Check for missing lang keys (warn)", variable=self.check_missing_lang)\
            .grid(row=row, column=0, sticky="w", padx=10, pady=10)

        row += 1
        ttk.Label(f, text="Exclude Mods (comma-separated):").grid(row=row, column=0, sticky="w", padx=10)
        row += 1
        ttk.Entry(f, textvariable=self.exclude_mods, width=60).grid(row=row, column=0, sticky="w", padx=10)

        row += 1
        ttk.Checkbutton(f, text="Dark Mode (restart required)", variable=self.dark_mode)\
            .grid(row=row, column=0, sticky="w", padx=10, pady=10)

    def build_help(self):
        f = self.frame_help
        txt = tk.Text(f, wrap="word")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        msg = (
            "How to use:\n"
            "1) Use a registry dump mod to export IDs. Recommended: 'Registry Dump' on Modrinth (tested with this).\n"
            "2) Click 'Browse' next to Dump Root, then 'Scan Dump Root' and pick the subfolder (items/blocks/entities...)\n"
            "3) Pick your Mods folder (where .jar files are), Resource Pack path (zip/folder, optional), and Output folder.\n"
            "4) Click 'Start Scan'. Reports will be written to the Output folder.\n\n"
            "Reports generated:\n"
            "• BASELINE_duplicates.txt — duplicates by name BEFORE resource pack overrides.\n"
            "• AFTER_RP_duplicates.txt — duplicates by name AFTER applying RP's en_us.json overrides. Lines marked (changed) were renamed by RP.\n"
            "• by_mod_AFTER_RP/ — per-mod breakdown of duplicates after RP.\n"
            "• RP_changes_diff.txt — list of IDs whose display names changed (before vs after RP).\n\n"
            "Notes:\n"
            "• Only cross-mod duplicates are kept (same display name used by 2+ different mods).\n"
            "• If a mod lacks lang entries, we fall back to a prettified ID path (e.g., 'pear_jelly_block' -> 'Pear Jelly Block').\n"
            "• This tool compares *names*, not IDs. If two different names are used, they won't count as duplicates.\n\n"
            "Link (copy/paste in browser): https://modrinth.com/mod/registry-dump\n"
            "Made for Star (Aniket). Have fun fixing the multiverse of Pears 🍐.\n"
        )
        txt.insert("1.0", msg)
        txt.configure(state="disabled")

    ##############################
    # Actions
    ##############################

    def append_log(self, line: str):
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.update_idletasks()

    def pick_dump_root(self):
        p = filedialog.askdirectory(title="Choose Dump Root (folder that contains items/blocks/etc)")
        if p:
            self.dump_root.set(p)
            self.scan_dump_root_for_candidates()

    def pick_mods_folder(self):
        p = filedialog.askdirectory(title="Choose Mods folder (.jar files)")
        if p:
            self.mods_folder.set(p)

    def pick_rp_path(self):
        # allow either file or folder
        p = filedialog.askopenfilename(title="Choose Resource Pack (zip/jar)")
        if not p:
            p = filedialog.askdirectory(title="Or choose a Resource Pack folder")
        if p:
            self.rp_path.set(p)

    def pick_output_folder(self):
        p = filedialog.askdirectory(title="Choose Output folder")
        if p:
            self.output_folder.set(p)

    def scan_dump_root_for_candidates(self):
        root = self.dump_root.get().strip()
        if not root or not os.path.isdir(root):
            messagebox.showerror("Error", "Dump Root not found.")
            return
        # Find likely registry subfolders with JSON files
        candidates: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            if any(fn.lower().endswith(".json") for fn in filenames):
                candidates.append(dirpath)
        candidates = sorted(set(candidates))
        self.registry_combo["values"] = candidates
        # auto-pick common ones if present
        pick = ""
        for guess in ("items", "item", "blocks", "block", "entities", "entity", "worldgen"):
            for c in candidates:
                if c.lower().endswith(guess):
                    pick = c; break
            if pick:
                break
        if not pick and candidates:
            pick = candidates[0]
        if pick:
            self.registry_folder.set(pick)
        self.update_kind_label()

    def update_kind_label(self):
        self.kind_inferred.set(infer_kind_from_path(self.registry_folder.get()))

    def save_defaults(self):
        data = {
            "dump_root": self.dump_root.get(),
            "registry_folder": self.registry_folder.get(),
            "mods_folder": self.mods_folder.get(),
            "rp_path": self.rp_path.get(),
            "output_folder": self.output_folder.get(),
            "case_insensitive": bool(self.case_insensitive.get()),
            "underscores_as_spaces": bool(self.underscores_as_spaces.get()),
            "enable_rp": bool(self.enable_rp.get()),
            "check_missing_lang": bool(self.check_missing_lang.get()),
            "exclude_mods": self.exclude_mods.get(),
            "dark_mode": bool(self.dark_mode.get())
        }
        ok = save_config(self.script_dir, data)
        if ok:
            messagebox.showinfo("Saved", "Defaults saved.")
        else:
            messagebox.showerror("Error", "Failed to save defaults.")

    def do_scan(self):
        global check_missing_lang_global
        check_missing_lang_global = bool(self.check_missing_lang.get())
        # Validate
        reg = self.registry_folder.get().strip()
        mods = self.mods_folder.get().strip()
        out = self.output_folder.get().strip()
        rp = self.rp_path.get().strip()

        if not os.path.isdir(reg):
            messagebox.showerror("Error", f"Registry folder not found:\n{reg}")
            return
        if not os.path.isdir(mods):
            messagebox.showerror("Error", f"Mods folder not found:\n{mods}")
            return
        if rp and not (os.path.isdir(rp) or os.path.isfile(rp)):
            messagebox.showerror("Error", f"Resource pack path not found:\n{rp}")
            return
        if not out:
            messagebox.showerror("Error", "Choose an Output folder.")
            return
        os.makedirs(out, exist_ok=True)

        self.append_log("Scanning registry folder...")
        entries = scan_registry_folder(
            reg,
            treat_underscores_as_spaces=bool(self.underscores_as_spaces.get()),
            case_insensitive=bool(self.case_insensitive.get())
        )
        exclude_list = [m.strip() for m in self.exclude_mods.get().split(",") if m.strip()]
        if exclude_list:
            before_count = len(entries)
            entries = [e for e in entries if e["modid"] not in exclude_list]
            self.append_log(f"Excluded mods: {exclude_list} ({before_count - len(entries)} entries removed)")
        if not entries:
            messagebox.showinfo("No IDs", "No IDs found in the selected registry folder.")
            return

        self.append_log(f"Found {len(entries)} IDs. Loading mod langs...")
        mod_langs = load_mod_langs(mods)
        self.append_log(f"Loaded langs for {len(mod_langs)} mods.")

        rp_overrides = {}
        if bool(self.enable_rp.get()):
            if rp:
                self.append_log("RP filtering enabled, loading overrides…")
                rp_overrides = load_resource_pack_langs(rp)
                self.append_log(f"Loaded {len(rp_overrides)} RP override entries.")
            else:
                self.append_log("RP filtering enabled but no RP selected.")
        else:
            self.append_log("RP filtering disabled (ignored).")

        kind = infer_kind_from_path(reg)
        self.kind_inferred.set(kind)

        self.append_log("Computing display names...")
        before, after = compute_display_names(kind, entries, mod_langs, rp_overrides)

        self.append_log("Writing reports...")
        base_master, after_master, by_mod_dir, changed_file = write_reports(
            out, reg, kind, before, after,
            case_insensitive=bool(self.case_insensitive.get()),
            treat_underscores_as_spaces=bool(self.underscores_as_spaces.get())
        )

        self.append_log("Done.")
        messagebox.showinfo("Done", f"Reports written:\n- {base_master}\n- {after_master}\n- {by_mod_dir}\n- {changed_file}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
