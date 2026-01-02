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
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CYBERPUNK THEME ---
COLORS = {
    "bg": "#050505",
    "panel": "#101010",
    "fg": "#E0E0E0",
    "accent": "#00FF41",    # Matrix Green
    "gold": "#FFD700",
    "neon": "#D300C5",
    "alert": "#FF2A2A",
    "dim": "#333333",
    "input": "#1A1A1A",
    "border": "#444444"
}

FONTS = {
    "header": ("Segoe UI", 10, "bold"),
    "timer": ("Consolas", 28, "bold"),
    "overlay": ("Consolas", 12, "bold"),
    "mono": ("Consolas", 9),
    "ui": ("Segoe UI", 8),
    "small": ("Segoe UI", 7)
}

CONFIG_FILE = Path.home() / ".kaizen_custom_config.json"
POSITIONS = ["TOP_CENTER", "TOP_LEFT", "TOP_RIGHT", "BOTTOM_RIGHT", "BOTTOM_LEFT", "BOTTOM_CENTER"]

# --- RANKING LOGIC ---
RANKS = [
    (0, "INITIATE"), (500, "DATA JANITOR"), (1500, "SCRIPT KIDDIE"),
    (3000, "CODE RONIN"), (6000, "CYBER MONK"), (10000, "10X ENGINEER"),
    (20000, "SYSTEM ARCHITECT"), (50000, "ONE-PERSON UNICORN")
]

class Config:
    def __init__(self):
        # Default Settings
        self.watch_paths = [str(Path.home() / "Downloads")]
        self.monk_urls = ["https://github.com"]
        self.monk_apps = ["code"] # Apps to launch
        self.extensions = {
            "Images": [".jpg", ".png", ".webp", ".svg"],
            "Docs": [".pdf", ".docx", ".txt", ".md"],
            "Archives": [".zip", ".rar", ".7z"],
            "Code": [".py", ".js", ".cpp", ".html", ".json"],
            "Execs": [".exe", ".msi", ".bat"]
        }
        self.pomo_work = 25
        self.pomo_break = 5
        
        # Customization
        self.sound_enabled = True
        self.overlay_pos = "TOP_CENTER"
        self.hotkey_start = "ctrl+shift+space"
        self.hotkey_panic = "ctrl+shift+q"
        
        # Stats
        self.stats = {
            "xp": 0, "level": 1, "files_moved": 0,
            "minutes_focused": 0, "sessions_completed": 0,
            "current_streak": 0, "last_session_date": ""
        }
        self.load()

    def get_rank(self):
        xp = self.stats["xp"]
        current = RANKS[0][1]
        for threshold, name in RANKS:
            if xp >= threshold: current = name
            else: break
        return current

    def add_xp(self, amount):
        self.stats["xp"] += amount
        self.stats["level"] = 1 + (self.stats["xp"] // 1000)
        self.save()

    def to_dict(self): return self.__dict__
    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(self.to_dict(), f, indent=4)
        except: pass
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f: self.__dict__.update(json.load(f))
            except: pass

CONFIG = Config()

# --- SETTINGS WINDOW (UPDATED) ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("SYSTEM CONFIG")
        self.configure(bg=COLORS["bg"])
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("400x550")
        
        # Center
        x = parent.winfo_x() - 50
        y = parent.winfo_y() - 100
        self.geometry(f"+{x}+{y}")
        
        # Border
        tk.Frame(self, bg=COLORS["neon"], width=2).pack(side="left", fill="y")
        self._build_ui()

    def _build_ui(self):
        # Header
        h = tk.Frame(self, bg=COLORS["panel"], height=30)
        h.pack(fill="x")
        tk.Label(h, text="CONFIGURATION", bg=COLORS["panel"], fg=COLORS["fg"], font=FONTS["header"]).pack(side="left", padx=10)
        tk.Button(h, text="×", bg=COLORS["panel"], fg="#666", bd=0, command=self.destroy, cursor="hand2").pack(side="right", padx=5)

        # Content Scroll
        container = tk.Frame(self, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=15, pady=10)

        # --- SECTION 1: SYSTEM ---
        self._lbl(container, "/// SYSTEM OVERRIDE", COLORS["accent"])
        
        # Sound
        self.var_sound = tk.BooleanVar(value=CONFIG.sound_enabled)
        chk = tk.Checkbutton(container, text="AUDIO FEEDBACK", variable=self.var_sound, 
                             bg=COLORS["bg"], fg="white", selectcolor=COLORS["panel"], activebackground=COLORS["bg"], activeforeground="white")
        chk.pack(anchor="w", pady=2)

        # Hotkeys
        self._lbl(container, "HOTKEYS (Start/Stop | Panic)")
        hk_frame = tk.Frame(container, bg=COLORS["bg"])
        hk_frame.pack(fill="x")
        self.ent_hk_start = self._inp(hk_frame, CONFIG.hotkey_start, width=18)
        self.ent_hk_start.pack(side="left", padx=(0, 5))
        self.ent_hk_panic = self._inp(hk_frame, CONFIG.hotkey_panic, width=18)
        self.ent_hk_panic.pack(side="left")

        # --- SECTION 2: MONK MODE ---
        self._lbl(container, "/// MONK PROTOCOLS", COLORS["neon"])
        
        # Timer
        self._lbl(container, "TIMER (Work | Break)")
        tm_frame = tk.Frame(container, bg=COLORS["bg"])
        tm_frame.pack(fill="x")
        self.ent_work = self._inp(tm_frame, str(CONFIG.pomo_work), width=10)
        self.ent_work.pack(side="left", padx=(0, 5))
        self.ent_break = self._inp(tm_frame, str(CONFIG.pomo_break), width=10)
        self.ent_break.pack(side="left")

        # Overlay Position
        self._lbl(container, "OVERLAY POSITION")
        self.var_pos = tk.StringVar(value=CONFIG.overlay_pos)
        opt = tk.OptionMenu(container, self.var_pos, *POSITIONS)
        opt.config(bg=COLORS["input"], fg="white", bd=0, highlightthickness=0)
        opt["menu"].config(bg=COLORS["panel"], fg="white")
        opt.pack(fill="x", pady=2)

        # Apps & URLs
        self._lbl(container, "APPS TO LAUNCH (; separated)")
        self.ent_apps = self._inp(container, ";".join(CONFIG.monk_apps))
        
        self._lbl(container, "URLS TO OPEN (; separated)")
        self.ent_urls = self._inp(container, ";".join(CONFIG.monk_urls))

        # --- SECTION 3: AUTOMATION ---
        self._lbl(container, "/// SEIRI AUTOMATION", COLORS["gold"])
        self._lbl(container, "WATCH PATHS (; separated)")
        self.ent_paths = self._inp(container, ";".join(CONFIG.watch_paths))

        # Save
        tk.Button(self, text="APPLY CONFIGURATION", bg=COLORS["panel"], fg=COLORS["accent"], 
                  font=FONTS["header"], bd=0, cursor="hand2", command=self.save).pack(fill="x", side="bottom", ipady=10)

    def _lbl(self, parent, text, color="#888"):
        tk.Label(parent, text=text, bg=COLORS["bg"], fg=color, font=FONTS["ui"]).pack(anchor="w", pady=(10, 2))

    def _inp(self, parent, val, width=None):
        e = tk.Entry(parent, bg=COLORS["input"], fg="white", font=FONTS["mono"], insertbackground="white", bd=0)
        if width: e.config(width=width)
        e.insert(0, val)
        e.pack(fill="x" if not width else "none", ipady=4)
        return e

    def save(self):
        CONFIG.sound_enabled = self.var_sound.get()
        CONFIG.hotkey_start = self.ent_hk_start.get()
        CONFIG.hotkey_panic = self.ent_hk_panic.get()
        CONFIG.overlay_pos = self.var_pos.get()
        
        CONFIG.watch_paths = [x.strip() for x in self.ent_paths.get().split(";") if x.strip()]
        CONFIG.monk_urls = [x.strip() for x in self.ent_urls.get().split(";") if x.strip()]
        CONFIG.monk_apps = [x.strip() for x in self.ent_apps.get().split(";") if x.strip()]
        
        try:
            CONFIG.pomo_work = int(self.ent_work.get())
            CONFIG.pomo_break = int(self.ent_break.get())
        except: pass
        
        CONFIG.save()
        self.callback()
        self.destroy()

# --- OVERLAY ---
class TacticalOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.85)
        self.configure(bg="black")
        self.lbl = tk.Label(self, text="init...", bg="black", fg=COLORS["accent"], font=FONTS["overlay"])
        self.lbl.pack(fill="both", expand=True)
        self.reposition()

    def reposition(self):
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w, h = 400, 30
        pad = 20
        
        pos = CONFIG.overlay_pos
        x, y = 0, 0
        
        if "TOP" in pos: y = 0
        elif "BOTTOM" in pos: y = hs - h
        
        if "LEFT" in pos: x = pad
        elif "RIGHT" in pos: x = ws - w - pad
        elif "CENTER" in pos: x = (ws - w) // 2
        
        self.geometry(f"{w}x{h}+{x}+{y}")

    def update_status(self, text, color):
        self.lbl.config(text=text, fg=color)

# --- CORE APP ---
class KaizenHUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.queue = queue.Queue()
        self.observer = Observer()
        self.overlay = None
        self.settings_win = None
        
        self.pomo_active = False
        self.mode = "WORK"
        self.time_left = CONFIG.pomo_work * 60
        self.total_time = self.time_left

        self._init_file_handler()
        self._setup_window()
        self._build_ui()
        self._reload_system() # Setup hotkeys and observers
        
        self.deiconify()
        self._sound("STARTUP")

    def _init_file_handler(self):
        self.handler = FileSystemEventHandler()
        self.handler.on_created = self._on_file_created

    def _on_file_created(self, event):
        if not event.is_directory: 
            threading.Thread(target=self._process_file, args=(Path(event.src_path),), daemon=True).start()

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
                    
                    CONFIG.add_xp(10)
                    CONFIG.stats["files_moved"] += 1
                    self.queue.put(("notify", f"+10 XP | MOVED: {path.name}"))
                    return
        except Exception as e: print(e)

    def _setup_window(self):
        self.overrideredirect(True)
        self.geometry("300x280")
        self.configure(bg=COLORS["bg"], highlightthickness=1, highlightbackground=COLORS["dim"])
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.96)
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{ws-320}+{hs-320}")
        self.bind("<ButtonPress-1>", lambda e: setattr(self, 'drag_data', (e.x, e.y)))
        self.bind("<B1-Motion>", self._do_drag)

    def _do_drag(self, e):
        x = self.winfo_x() + (e.x - self.drag_data[0])
        y = self.winfo_y() + (e.y - self.drag_data[1])
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Header
        h = tk.Frame(self, bg=COLORS["panel"], height=28)
        h.pack(fill="x")
        tk.Label(h, text="KAIZEN OS // ULTIMATE", bg=COLORS["panel"], fg=COLORS["neon"], font=FONTS["header"]).pack(side="left", padx=10)
        
        ctrls = tk.Frame(h, bg=COLORS["panel"])
        ctrls.pack(side="right")
        
        # Settings Icon
        btn_set = tk.Label(ctrls, text="⚙", fg="#888", bg=COLORS["panel"], cursor="hand2")
        btn_set.pack(side="left", padx=5)
        btn_set.bind("<Button-1>", lambda e: self.open_settings())

        # Close Icon
        btn_cls = tk.Label(ctrls, text="×", fg="#888", bg=COLORS["panel"], cursor="hand2")
        btn_cls.pack(side="left", padx=5)
        btn_cls.bind("<Button-1>", lambda e: self.quit_app())

        # Stats
        self.lbl_rank = tk.Label(self, text="RANK: LOADING...", bg=COLORS["bg"], fg=COLORS["gold"], font=FONTS["ui"])
        self.lbl_rank.pack(anchor="w", padx=15, pady=(5,0))
        self.lbl_xp = tk.Label(self, text="XP: 0", bg=COLORS["bg"], fg=COLORS["dim"], font=FONTS["small"])
        self.lbl_xp.pack(anchor="w", padx=15)
        
        # XP Bar
        self.cv_xp = tk.Canvas(self, bg=COLORS["panel"], height=4, width=270, highlightthickness=0)
        self.cv_xp.pack(pady=5)
        self.xp_fill = self.cv_xp.create_rectangle(0, 0, 0, 4, fill=COLORS["gold"], width=0)
        
        # Mission
        self.ent_mission = tk.Entry(self, bg=COLORS["input"], fg=COLORS["accent"], 
                                  insertbackground="white", font=FONTS["mono"], justify="center", bd=0)
        self.ent_mission.insert(0, "ENTER MISSION")
        self.ent_mission.pack(fill="x", padx=15, pady=5, ipady=4)
        self.ent_mission.bind("<FocusIn>", lambda e: self.ent_mission.delete(0, "end") if "MISSION" in self.ent_mission.get() else None)

        # Timer
        self.cv_timer = tk.Canvas(self, bg=COLORS["bg"], height=60, width=240, highlightthickness=0)
        self.cv_timer.pack(pady=5)
        self.txt_timer = self.cv_timer.create_text(120, 25, text="00:00", fill=COLORS["fg"], font=FONTS["timer"])
        self.bar_fg = self.cv_timer.create_rectangle(0, 55, 0, 58, fill=COLORS["accent"], width=0)

        # Button
        self.btn_act = tk.Button(self, text="INITIATE", bg=COLORS["panel"], fg=COLORS["accent"],
                               bd=0, font=FONTS["header"], command=self.toggle_session)
        self.btn_act.pack(fill="x", side="bottom", padx=15, pady=10, ipady=5)
        
        self._update_stats_ui()

    def _reload_system(self):
        # 1. Hotkeys
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(CONFIG.hotkey_start, lambda: self.queue.put(("toggle", None)))
            keyboard.add_hotkey(CONFIG.hotkey_panic, self.quit_app)
        except Exception as e: print(f"Hotkey Error: {e}")
        
        # 2. Watcher
        if self.observer: self.observer.stop()
        self.observer = Observer()
        for p in CONFIG.watch_paths:
            if os.path.exists(p): self.observer.schedule(self.handler, p, recursive=False)
        self.observer.start()
        
        # 3. Queue Loop
        self.after(200, self._poll_queue)

        # 4. Button Text update
        self.btn_act.config(text=f"INITIATE ({CONFIG.hotkey_start})")

    def open_settings(self):
        if not self.settings_win or not self.settings_win.winfo_exists():
            self.settings_win = SettingsWindow(self, self._reload_system)

    def toggle_session(self):
        self.pomo_active = not self.pomo_active
        if self.pomo_active:
            self.mode = "WORK"
            self.time_left = CONFIG.pomo_work * 60
            self.total_time = self.time_left
            
            # UI Lock
            self.ent_mission.config(state="disabled")
            self.btn_act.config(text="ABORT", fg=COLORS["alert"])
            
            # Overlay
            if not self.overlay: self.overlay = TacticalOverlay(self)
            self.overlay.deiconify()
            self.overlay.reposition() # Update pos from config
            
            # Launch
            self._sound("ENGAGE")
            for url in CONFIG.monk_urls: webbrowser.open(url)
            for app in CONFIG.monk_apps:
                if shutil.which(app): subprocess.Popen(app, shell=True)
                else: subprocess.Popen(app, shell=True) # Try shell execution
            
            self._tick()
        else:
            self.ent_mission.config(state="normal")
            self.btn_act.config(text=f"INITIATE ({CONFIG.hotkey_start})", fg=COLORS["accent"])
            if self.overlay: self.overlay.withdraw()
            self.cv_timer.itemconfig(self.txt_timer, text="00:00", fill=COLORS["fg"])

    def _tick(self):
        if self.pomo_active and self.time_left > 0:
            self.time_left -= 1
            
            # Logic
            if self.mode == "WORK" and self.time_left % 60 == 0:
                CONFIG.stats["minutes_focused"] += 1
                CONFIG.add_xp(5)
                self._update_stats_ui()

            # Visuals
            m, s = divmod(self.time_left, 60)
            t_str = f"{m:02}:{s:02}"
            self.cv_timer.itemconfig(self.txt_timer, text=t_str)
            
            prog = (self.total_time - self.time_left) / self.total_time
            self.cv_timer.coords(self.bar_fg, 0, 55, 240 * prog, 58)
            
            if self.overlay:
                color = COLORS["accent"] if self.mode == "WORK" else COLORS["neon"]
                self.overlay.update_status(f"[{self.mode}] {t_str} :: {self.ent_mission.get()}", color)
            
            self.after(1000, self._tick)
        elif self.pomo_active:
            self._switch_phase()

    def _switch_phase(self):
        self._sound("ALERT")
        if self.mode == "WORK":
            self.mode = "BREAK"
            self.time_left = CONFIG.pomo_break * 60
            CONFIG.add_xp(50)
            CONFIG.stats["sessions_completed"] += 1
            col = COLORS["neon"]
        else:
            self.mode = "WORK"
            self.time_left = CONFIG.pomo_work * 60
            col = COLORS["accent"]
        
        self.total_time = self.time_left
        self.cv_timer.itemconfig(self.txt_timer, fill=col)
        self.cv_timer.itemconfig(self.bar_fg, fill=col)
        self._update_stats_ui()
        self._tick()

    def _update_stats_ui(self):
        rank = CONFIG.get_rank()
        xp = CONFIG.stats["xp"]
        lvl = CONFIG.stats["level"]
        self.lbl_rank.config(text=f"RANK: {rank}")
        self.lbl_xp.config(text=f"LVL {lvl} | XP: {xp}")
        
        # Bar calculation
        prog = (xp % 1000) / 1000
        self.cv_xp.coords(self.xp_fill, 0, 0, 270 * prog, 4)

    def _sound(self, type):
        if not CONFIG.sound_enabled: return
        try:
            if type == "ENGAGE": winsound.Beep(600, 150)
            elif type == "ALERT": winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif type == "STARTUP": winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except: pass

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "notify": 
                    self.lbl_rank.config(text=msg[1]) # Quick notify in rank area
                    self.after(3000, self._update_stats_ui)
                elif msg[0] == "toggle":
                    self.toggle_session()
        except queue.Empty: pass
        self.after(200, self._poll_queue)

    def quit_app(self):
        CONFIG.save()
        if self.observer: self.observer.stop()
        self.destroy()
        try: keyboard.unhook_all()
        except: pass
        sys.exit()

if __name__ == "__main__":
    KaizenHUD().mainloop()