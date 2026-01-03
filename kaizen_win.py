import tkinter as tk
from tkinter import messagebox, ttk
import shutil
import os
import sys
import time
import threading
import subprocess
import webbrowser
import json
import queue
import winsound
import keyboard
import math
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- MIDNIGHT MODULAR PALETTE ---
COLORS = {
    "bg": "#020205",        # Void Black (Background gaps)
    "module": "#0B0B14",    # Module Background (Panels)
    "fg": "#E0E0E0",        # Main Text
    "accent": "#7F00FF",    # Midnight Purple
    "accent_glow": "#B026FF", # Neon Purple
    "break_mode": "#4B0082",# Indigo
    "alert": "#FF0044",     # Red
    "dim": "#3A3A45",       # Dim Text
    "input": "#15151A",     # Input Fields
    "border": "#1A1A2E",    # Subtle borders
    "success": "#00FF41"    # Green
}

FONTS = {
    "header": ("Segoe UI", 9, "bold"),
    "timer": ("Consolas", 36, "bold"),
    "overlay": ("Consolas", 12, "bold"),
    "mono": ("Consolas", 10),
    "ui": ("Segoe UI", 8),
    "label": ("Segoe UI", 7, "bold")
}

CONFIG_FILE = Path.home() / ".kaizen_midnight_config.json"
NOTES_FILE = Path.home() / "kaizen_brain_dump.txt"

# --- UTILS ---
def hex_to_rgb(hex_val):
    hex_val = hex_val.lstrip('#')
    return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % tuple(map(int, rgb))

def interpolate_color(color1, color2, t):
    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)
    r = c1[0] + (c2[0] - c1[0]) * t
    g = c1[1] + (c2[1] - c1[1]) * t
    b = c1[2] + (c2[2] - c1[2]) * t
    return rgb_to_hex((r, g, b))

# --- CONFIG ---
class Config:
    def __init__(self):
        self.watch_paths = [str(Path.home() / "Downloads")]
        self.monk_urls = ["https://github.com"]
        self.monk_apps = ["code"]
        self.extensions = {
            "Images": [".jpg", ".png", ".webp", ".svg"],
            "Docs": [".pdf", ".docx", ".txt", ".md"],
            "Archives": [".zip", ".rar", ".7z"],
            "Code": [".py", ".js", ".cpp", ".html", ".json"],
            "Execs": [".exe", ".msi", ".bat"]
        }
        self.pomo_work = 25
        self.pomo_break = 5
        self.sound_enabled = True
        self.hotkey_start = "ctrl+shift+space"
        self.hotkey_notes = "ctrl+j"
        self.overlay_pos = "TOP_CENTER"
        
        self.stats = {
            "xp": 0, "level": 1, "files_moved": 0,
            "minutes_focused": 0, "sessions_completed": 0
        }
        self.load()

    def add_xp(self, amount):
        self.stats["xp"] += amount
        self.stats["level"] = 1 + (self.stats["xp"] // 1000)
        self.save()

    def save(self):
        try:
            data = self.__dict__.copy()
            with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)
        except: pass

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f: self.__dict__.update(json.load(f))
            except: pass

CONFIG = Config()

# --- SPLASH SCREEN ---
class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["bg"])
        
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 300, 300
        self.geometry(f"{w}x{h}+{ws//2 - w//2}+{hs//2 - h//2}")
        
        self.cv = tk.Canvas(self, width=w, height=h, bg=COLORS["bg"], highlightthickness=0)
        self.cv.pack()
        
        self.step = 0
        self.animate_rose()
        
    def animate_rose(self):
        center_x, center_y = 150, 150
        scale = 80
        k = 4 
        if self.step < 360:
            for i in range(12): 
                theta = math.radians(self.step)
                r = scale * math.cos(k * theta)
                x = center_x + r * math.cos(theta)
                y = center_y + r * math.sin(theta)
                col = interpolate_color(COLORS["accent"], COLORS["accent_glow"], (math.sin(theta)+1)/2)
                self.cv.create_oval(x, y, x+2, y+2, fill=col, outline="")
                self.step += 1
            self.after(5, self.animate_rose)
        else:
            self.cv.create_text(150, 260, text="KAIZEN // MIDNIGHT", fill=COLORS["fg"], font=FONTS["header"])
            self.after(1200, self.fade_out)

    def fade_out(self):
        alpha = self.attributes("-alpha")
        if alpha > 0:
            self.attributes("-alpha", alpha - 0.05)
            self.after(30, self.fade_out)
        else:
            self.destroy()

# --- OVERLAY ---
class TacticalOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.90)
        if os.name == 'nt':
            self.attributes("-transparentcolor", "#000001")
            self.configure(bg="#000001")
            self.bg_col = "#000001"
        else:
            self.configure(bg="black")
            self.bg_col = "black"

        self.lbl = tk.Label(self, text="INIT...", bg=self.bg_col, fg=COLORS["accent"], font=FONTS["overlay"])
        self.lbl.pack(fill="both", expand=True)
        self.reposition()

    def reposition(self):
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w, h = 500, 40
        pad = 20
        pos = CONFIG.overlay_pos
        x, y = (ws - w) // 2, 0 
        
        if "TOP" in pos: y = 0
        elif "BOTTOM" in pos: y = hs - h
        if "LEFT" in pos: x = pad
        elif "RIGHT" in pos: x = ws - w - pad
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def update_status(self, text, color):
        self.lbl.config(text=text, fg=color)

# --- SEIRI EDITOR ---
class SeiriEditor(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["module"])
        self.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Treeview with dark style
        cols = ("Category", "Extensions")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        self.tree.heading("Category", text="CATEGORY")
        self.tree.heading("Extensions", text="EXTENSIONS")
        self.tree.column("Category", width=120)
        self.tree.column("Extensions", width=250)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["input"], foreground="white", fieldbackground=COLORS["input"], borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["bg"], foreground="white", relief="flat")
        style.map("Treeview", background=[("selected", COLORS["accent"])])
        
        self.tree.pack(fill="both", expand=True, pady=(0, 10))
        self.populate()
        
        # Input Area (Fixed Labels)
        ctrl = tk.Frame(self, bg=COLORS["module"])
        ctrl.pack(fill="x", pady=5)
        
        # Category Input
        f1 = tk.Frame(ctrl, bg=COLORS["module"])
        f1.pack(side="left", padx=(0, 10))
        tk.Label(f1, text="CATEGORY NAME", bg=COLORS["module"], fg=COLORS["dim"], font=FONTS["label"]).pack(anchor="w")
        self.ent_cat = tk.Entry(f1, bg=COLORS["input"], fg="white", insertbackground="white", width=15, bd=0)
        self.ent_cat.pack(ipady=4)
        
        # Ext Input
        f2 = tk.Frame(ctrl, bg=COLORS["module"])
        f2.pack(side="left", padx=(0, 10))
        tk.Label(f2, text="EXTENSIONS (e.g. .py, .exe)", bg=COLORS["module"], fg=COLORS["dim"], font=FONTS["label"]).pack(anchor="w")
        self.ent_ext = tk.Entry(f2, bg=COLORS["input"], fg="white", insertbackground="white", width=20, bd=0)
        self.ent_ext.pack(ipady=4)
        
        # Buttons
        btn_f = tk.Frame(ctrl, bg=COLORS["module"])
        btn_f.pack(side="right", fill="y")
        tk.Button(btn_f, text="ADD", bg=COLORS["bg"], fg=COLORS["success"], bd=0, command=self.add_entry, font=FONTS["header"]).pack(side="top", fill="x", pady=1)
        tk.Button(btn_f, text="DELETE", bg=COLORS["bg"], fg=COLORS["alert"], bd=0, command=self.delete_entry, font=FONTS["header"]).pack(side="bottom", fill="x", pady=1)

    def populate(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for cat, exts in CONFIG.extensions.items():
            self.tree.insert("", "end", values=(cat, ", ".join(exts)))

    def add_entry(self):
        cat = self.ent_cat.get().strip()
        exts_str = self.ent_ext.get().strip()
        if cat and exts_str:
            CONFIG.extensions[cat] = [e.strip() for e in exts_str.split(",") if e.strip()]
            self.populate()

    def delete_entry(self):
        sel = self.tree.selection()
        if sel:
            cat = self.tree.item(sel[0])['values'][0]
            if cat in CONFIG.extensions:
                del CONFIG.extensions[cat]
                self.populate()

# --- SETTINGS WINDOW (FIXED VISUALS) ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("MIDNIGHT CONFIG")
        self.configure(bg=COLORS["bg"])
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Center on screen
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 450, 550
        self.geometry(f"{w}x{h}+{ws//2 - w//2}+{hs//2 - h//2}")
        
        self.current_frame = None
        self._build_ui()

    def _build_ui(self):
        # Header
        h = tk.Frame(self, bg=COLORS["bg"], height=40)
        h.pack(fill="x")
        tk.Label(h, text="SYSTEM CONFIGURATION", bg=COLORS["bg"], fg="white", font=FONTS["header"]).pack(side="left", padx=15)
        tk.Button(h, text="×", bg=COLORS["bg"], fg="#666", bd=0, font=("Arial", 12), command=self.destroy).pack(side="right", padx=10)

        # Custom Nav Bar (Replaces Tabs to fix ugly colors)
        nav = tk.Frame(self, bg=COLORS["bg"])
        nav.pack(fill="x", padx=15, pady=(0, 10))
        
        self.btn_gen = tk.Button(nav, text="GENERAL", bg=COLORS["accent"], fg="white", bd=0, width=15, command=lambda: self.switch_tab("gen"))
        self.btn_gen.pack(side="left", padx=(0, 5))
        
        self.btn_seiri = tk.Button(nav, text="SEIRI EDITOR", bg=COLORS["module"], fg="#888", bd=0, width=15, command=lambda: self.switch_tab("seiri"))
        self.btn_seiri.pack(side="left")

        # Container
        self.container = tk.Frame(self, bg=COLORS["module"])
        self.container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Init Tab
        self.switch_tab("gen")

        # Footer
        tk.Button(self, text="APPLY & REBOOT", bg=COLORS["accent"], fg="white", bd=0, font=FONTS["header"], command=self.save).pack(fill="x", side="bottom", ipady=12)

    def switch_tab(self, tab):
        if self.current_frame: self.current_frame.destroy()
        
        if tab == "gen":
            self.btn_gen.config(bg=COLORS["accent"], fg="white")
            self.btn_seiri.config(bg=COLORS["module"], fg="#888")
            self.current_frame = tk.Frame(self.container, bg=COLORS["module"], padx=15, pady=15)
            self.current_frame.pack(fill="both", expand=True)
            self._build_general(self.current_frame)
        else:
            self.btn_gen.config(bg=COLORS["module"], fg="#888")
            self.btn_seiri.config(bg=COLORS["accent"], fg="white")
            self.current_frame = SeiriEditor(self.container)

    def _build_general(self, p):
        lbl = lambda t: tk.Label(p, text=t, bg=COLORS["module"], fg=COLORS["dim"], font=FONTS["label"]).pack(anchor="w", pady=(10, 2))
        
        lbl("WATCH PATHS (; separated)")
        self.ent_paths = self._mk_entry(p, ";".join(CONFIG.watch_paths))
        lbl("APPS TO LAUNCH (; separated)")
        self.ent_apps = self._mk_entry(p, ";".join(CONFIG.monk_apps))
        lbl("URLS (; separated)")
        self.ent_urls = self._mk_entry(p, ";".join(CONFIG.monk_urls))
        
        fr = tk.Frame(p, bg=COLORS["module"])
        fr.pack(fill="x", pady=10)
        
        f1 = tk.Frame(fr, bg=COLORS["module"]); f1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Label(f1, text="WORK (min)", bg=COLORS["module"], fg=COLORS["accent"], font=FONTS["label"]).pack(anchor="w")
        self.ent_work = self._mk_entry(f1, CONFIG.pomo_work)
        
        f2 = tk.Frame(fr, bg=COLORS["module"]); f2.pack(side="left", fill="x", expand=True, padx=(5, 0))
        tk.Label(f2, text="BREAK (min)", bg=COLORS["module"], fg=COLORS["break_mode"], font=FONTS["label"]).pack(anchor="w")
        self.ent_break = self._mk_entry(f2, CONFIG.pomo_break)

        lbl("OVERLAY POSITION")
        self.ent_pos = self._mk_entry(p, CONFIG.overlay_pos)

    def _mk_entry(self, p, v):
        e = tk.Entry(p, bg=COLORS["input"], fg="white", insertbackground="white", 
                     font=FONTS["mono"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"])
        if v is not None: e.insert(0, str(v))
        e.pack(fill="x", ipady=5)
        return e

    def save(self):
        CONFIG.watch_paths = [x.strip() for x in self.ent_paths.get().split(";") if x.strip()]
        CONFIG.monk_apps = [x.strip() for x in self.ent_apps.get().split(";") if x.strip()]
        CONFIG.monk_urls = [x.strip() for x in self.ent_urls.get().split(";") if x.strip()]
        CONFIG.overlay_pos = self.ent_pos.get().strip()
        try:
            CONFIG.pomo_work = int(self.ent_work.get())
            CONFIG.pomo_break = int(self.ent_break.get())
        except: pass
        CONFIG.save()
        self.callback()
        self.destroy()

# --- BRAIN DUMP ---
class BrainDump(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("300x400")
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{ws-320}+{hs//2 - 200}")
        self.configure(bg=COLORS["module"])
        
        h = tk.Frame(self, bg=COLORS["bg"], height=30)
        h.pack(fill="x")
        tk.Label(h, text="BRAIN DUMP", bg=COLORS["bg"], fg=COLORS["accent"], font=FONTS["header"]).pack(side="left", padx=10)
        tk.Button(h, text="SAVE", bg=COLORS["bg"], fg="white", bd=0, command=self.hide).pack(side="right", padx=5)
        
        self.text = tk.Text(self, bg=COLORS["module"], fg="white", insertbackground="white", 
                            font=("Consolas", 10), bd=0, padx=10, pady=10)
        self.text.pack(fill="both", expand=True)
        if NOTES_FILE.exists():
            with open(NOTES_FILE, "r", encoding="utf-8") as f: self.text.insert("1.0", f.read())

    def hide(self):
        with open(NOTES_FILE, "w", encoding="utf-8") as f: f.write(self.text.get("1.0", "end-1c"))
        self.withdraw()

# --- MAIN APP (MODULAR DESIGN) ---
class KaizenMidnight(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        
        splash = SplashScreen(self)
        self.wait_window(splash) 
        
        self.queue = queue.Queue()
        self.observer = Observer()
        self.settings_win = None
        self.brain_dump = BrainDump(self); self.brain_dump.withdraw()
        self.overlay = None 
        
        self.pomo_active = False
        self.mode = "WORK"
        self.time_left = CONFIG.pomo_work * 60
        self.total_time = self.time_left
        self.pulse_phase = 0.0
        
        self._init_file_handler()
        self._setup_window()
        self._build_modular_ui()
        self._reload_system()
        self.deiconify()
        self._animate_pulse()

    def _init_file_handler(self):
        self.handler = FileSystemEventHandler()
        self.handler.on_created = lambda e: threading.Thread(target=self._process_file, args=(Path(e.src_path),), daemon=True).start() if not e.is_directory else None

    def _process_file(self, path):
        time.sleep(1.5)
        try:
            if not path.exists(): return
            for cat, exts in CONFIG.extensions.items():
                if path.suffix.lower() in exts:
                    dest = Path.home() / "Desktop" / cat
                    dest.mkdir(parents=True, exist_ok=True)
                    new_path = dest / path.name
                    if new_path.exists(): new_path = dest / f"{path.stem}_{int(time.time())}{path.suffix}"
                    shutil.move(str(path), str(new_path))
                    CONFIG.add_xp(15)
                    CONFIG.stats["files_moved"] += 1
                    self.queue.put(("notify", f"SEIRI: {path.name}"))
                    return
        except: pass

    def _setup_window(self):
        self.overrideredirect(True)
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)
        
        # CENTER WINDOW LOGIC
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 360, 420 # Larger, Modular Size
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.bind("<ButtonPress-1>", lambda e: setattr(self, 'd', (e.x, e.y)))
        self.bind("<B1-Motion>", lambda e: self.geometry(f"+{self.winfo_x()+(e.x-self.d[0])}+{self.winfo_y()+(e.y-self.d[1])}"))

    def _animate_pulse(self):
        if self.pomo_active:
            val = (math.sin(self.pulse_phase) + 1) / 2
            target = COLORS["accent"] if self.mode == "WORK" else COLORS["break_mode"]
            
            # Pulse visual elements
            glow = interpolate_color(COLORS["module"], target, val * 0.3)
            self.mod_timer.config(bg=glow) # Pulse Timer Module BG
            self.cv_timer.config(bg=glow)
            self.pulse_phase += 0.15
        else:
            self.mod_timer.config(bg=COLORS["module"])
            self.cv_timer.config(bg=COLORS["module"])
        self.after(50, self._animate_pulse)

    def _build_modular_ui(self):
        # 1. STATUS MODULE (TOP)
        self.mod_status = tk.Frame(self, bg=COLORS["module"], height=40)
        self.mod_status.pack(fill="x", padx=2, pady=2)
        
        tk.Label(self.mod_status, text="KAIZEN // MIDNIGHT", bg=COLORS["module"], fg=COLORS["accent"], font=FONTS["header"]).pack(side="left", padx=10, pady=10)
        
        ctrls = tk.Frame(self.mod_status, bg=COLORS["module"])
        ctrls.pack(side="right", padx=5)
        def mk_icon(t, c): tk.Label(ctrls, text=t, fg="#888", bg=COLORS["module"], cursor="hand2").pack(side="left", padx=5); ctrls.children["!label" + ("" if t=="⚙" else ("2" if t=="🧠" else "3"))].bind("<Button-1>", lambda e: c())
        
        mk_icon("⚙", self.open_settings)
        mk_icon("🧠", self.toggle_brain_dump)
        mk_icon("×", self.quit_app)

        # XP Bar tiny
        self.cv_xp = tk.Canvas(self, bg=COLORS["bg"], height=2, highlightthickness=0)
        self.cv_xp.pack(fill="x")
        self.xp_fill = self.cv_xp.create_rectangle(0,0,0,2, fill=COLORS["accent_glow"], width=0)

        # 2. CORE TIMER MODULE (CENTER)
        self.mod_timer = tk.Frame(self, bg=COLORS["module"])
        self.mod_timer.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.lbl_stats = tk.Label(self.mod_timer, text="READY", bg=COLORS["module"], fg=COLORS["dim"], font=FONTS["label"])
        self.lbl_stats.pack(pady=(15, 0))
        
        self.cv_timer = tk.Canvas(self.mod_timer, bg=COLORS["module"], height=100, width=300, highlightthickness=0)
        self.cv_timer.pack(pady=10)
        self.txt_timer = self.cv_timer.create_text(150, 50, text="00:00", fill=COLORS["fg"], font=FONTS["timer"])
        # Circular or Bar progress? Let's stick to bar for modular look
        self.bar_bg = self.cv_timer.create_rectangle(50, 90, 250, 94, fill=COLORS["bg"], width=0)
        self.bar_fg = self.cv_timer.create_rectangle(50, 90, 50, 94, fill=COLORS["accent"], width=0)

        # 3. MISSION MODULE
        self.mod_mission = tk.Frame(self, bg=COLORS["module"])
        self.mod_mission.pack(fill="x", padx=2, pady=2)
        
        self.ent_mission = tk.Entry(self.mod_mission, bg=COLORS["input"], fg="white", insertbackground="white", 
                                  font=FONTS["mono"], justify="center", bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        self.ent_mission.insert(0, "ENTER DIRECTIVE")
        self.ent_mission.pack(fill="x", padx=15, pady=15, ipady=8)
        self.ent_mission.bind("<FocusIn>", lambda e: self.ent_mission.delete(0, "end") if "DIRECTIVE" in self.ent_mission.get() else None)

        # 4. CONTROL MODULE
        self.mod_ctrl = tk.Frame(self, bg=COLORS["module"])
        self.mod_ctrl.pack(fill="x", padx=2, pady=2)
        
        self.btn = tk.Button(self.mod_ctrl, text="ENGAGE SYSTEM", bg=COLORS["bg"], fg=COLORS["accent"], bd=0, 
                             font=FONTS["header"], command=self.toggle_session, cursor="hand2")
        self.btn.pack(fill="x", padx=2, pady=2, ipady=12)

    def open_settings(self):
        if not self.settings_win or not self.settings_win.winfo_exists():
            self.settings_win = SettingsWindow(self, self._reload_system)

    def toggle_brain_dump(self):
        if self.brain_dump.winfo_viewable(): self.brain_dump.hide()
        else: self.brain_dump.deiconify(); self.brain_dump.text.focus_set()

    def _reload_system(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(CONFIG.hotkey_start, lambda: self.queue.put(("toggle", None)))
            keyboard.add_hotkey(CONFIG.hotkey_notes, lambda: self.queue.put(("notes", None)))
        except: pass
        
        if self.observer: self.observer.stop()
        self.observer = Observer()
        for p in CONFIG.watch_paths:
            if os.path.exists(p): self.observer.schedule(self.handler, p, recursive=False)
        self.observer.start()
        
        self.btn.config(text=f"ENGAGE ({CONFIG.hotkey_start})")
        self.after(200, self._poll_queue)
        self._update_stats()

    def _update_stats(self):
        xp = CONFIG.stats["xp"]
        lvl = CONFIG.stats["level"]
        self.lbl_stats.config(text=f"LVL {lvl} // XP: {xp}")
        # XP Bar logic
        prog = (xp % 1000) / 1000
        w = self.winfo_width()
        self.cv_xp.coords(self.xp_fill, 0, 0, w * prog, 2)

    def toggle_session(self):
        self.pomo_active = not self.pomo_active
        if self.pomo_active:
            self.mode = "WORK"
            self.time_left = CONFIG.pomo_work * 60
            self.total_time = self.time_left
            self.btn.config(text="TERMINATE", fg=COLORS["alert"], bg=COLORS["module"])
            self.ent_mission.config(state="disabled")
            
            # SHOW OVERLAY
            if not self.overlay: self.overlay = TacticalOverlay(self)
            self.overlay.deiconify()
            self.overlay.reposition()
            
            if CONFIG.sound_enabled: winsound.Beep(400, 200)
            for app in CONFIG.monk_apps: subprocess.Popen(app, shell=True)
            for url in CONFIG.monk_urls: webbrowser.open(url)
            
            self._tick()
        else:
            self.btn.config(text=f"ENGAGE ({CONFIG.hotkey_start})", fg=COLORS["accent"], bg=COLORS["bg"])
            self.ent_mission.config(state="normal")
            if self.overlay: self.overlay.withdraw()
            self.mod_timer.config(bg=COLORS["module"]) # Reset glow

    def _tick(self):
        if self.pomo_active and self.time_left > 0:
            self.time_left -= 1
            if self.mode == "WORK" and self.time_left % 60 == 0:
                CONFIG.add_xp(5)
                self._update_stats()
            
            m, s = divmod(self.time_left, 60)
            t_str = f"{m:02}:{s:02}"
            self.cv_timer.itemconfig(self.txt_timer, text=t_str)
            
            pct = (self.total_time - self.time_left) / self.total_time
            w = 200 * pct
            self.cv_timer.coords(self.bar_fg, 50, 90, 50 + w, 94)
            col = COLORS["accent"] if self.mode == "WORK" else COLORS["break_mode"]
            self.cv_timer.itemconfig(self.bar_fg, fill=col)
            
            if self.overlay:
                self.overlay.update_status(f"[{self.mode}] {t_str} :: {self.ent_mission.get()}", col)
            
            self.after(1000, self._tick)
        elif self.pomo_active:
            self._switch_phase()

    def _switch_phase(self):
        if CONFIG.sound_enabled: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        if self.mode == "WORK":
            self.mode = "BREAK"
            self.time_left = CONFIG.pomo_break * 60
            CONFIG.add_xp(50)
            CONFIG.stats["sessions_completed"] += 1
        else:
            self.mode = "WORK"
            self.time_left = CONFIG.pomo_work * 60
        
        self.total_time = self.time_left
        self._update_stats()
        self._tick()

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "notify": self.lbl_stats.config(text=msg[1]); self.after(3000, self._update_stats)
                elif msg[0] == "toggle": self.toggle_session()
                elif msg[0] == "notes": self.toggle_brain_dump()
        except: pass
        self.after(200, self._poll_queue)

    def quit_app(self):
        CONFIG.save()
        self.observer.stop()
        try: keyboard.unhook_all()
        except: pass
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    KaizenMidnight().mainloop()