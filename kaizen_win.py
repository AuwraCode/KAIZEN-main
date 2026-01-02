import tkinter as tk
from tkinter import messagebox
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
from datetime import datetime, timedelta
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CYBERPUNK PALETTE ---
COLORS = {
    "bg": "#090909",        # Deep Black
    "panel": "#141414",     # Dark Grey
    "fg": "#E0E0E0",
    "accent": "#00FF41",    # Matrix Green
    "neon": "#BC13FE",      # Cyberpunk Purple
    "alert": "#FF0055",     # Neon Red
    "dim": "#444444",
    "input": "#1A1A1A",
    "border": "#333333"
}

FONTS = {
    "header": ("Segoe UI", 10, "bold"),
    "timer": ("Consolas", 26, "bold"),
    "mono": ("Consolas", 9),
    "ui": ("Segoe UI", 8),
    "label": ("Segoe UI", 8, "bold")
}

CONFIG_FILE = Path.home() / ".kaizen_v2_config.json"

class Config:
    def __init__(self):
        self.watch_paths = [str(Path.home() / "Downloads")]
        self.monk_urls = ["https://github.com"]
        self.extensions = {
            "Images": [".jpg", ".jpeg", ".png", ".webp", ".svg"],
            "Docs": [".pdf", ".docx", ".txt", ".xlsx", ".md", ".csv"],
            "Archives": [".zip", ".rar", ".7z"],
            "Code": [".py", ".js", ".cpp", ".html", ".css", ".json", ".sql"],
            "Execs": [".exe", ".msi", ".bat"]
        }
        self.pomo_work = 25
        self.pomo_break = 5
        self.stats = {
            "files_moved": 0,
            "minutes_focused": 0,
            "last_session_date": "",
            "current_streak": 0
        }
        self.load()

    def to_dict(self): return self.__dict__
    
    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
        except: pass

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.__dict__.update(data)
            except: pass

    def update_streak(self):
        today = datetime.now().strftime("%Y-%m-%d")
        last = self.stats.get("last_session_date", "")
        if last != today:
            self.stats["current_streak"] = self.stats.get("current_streak", 0) + 1
            self.stats["last_session_date"] = today
            self.save()

CONFIG = Config()

# --- SETTINGS WINDOW (NEW) ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, callback_refresh):
        super().__init__(parent)
        self.callback = callback_refresh
        self.title("SYSTEM CONFIG")
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)
        self.overrideredirect(True) # Borderless styling
        self.geometry("350x420")
        
        # Center relative to parent
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

        pad = 15
        container = tk.Frame(self, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=pad, pady=pad)

        # Paths
        self._add_label(container, "WATCH PATHS (; separated)")
        self.ent_paths = self._add_input(container, ";".join(CONFIG.watch_paths))

        # URLs
        self._add_label(container, "MONK MODE URLs (; separated)")
        self.ent_urls = self._add_input(container, ";".join(CONFIG.monk_urls))

        # Timer Grid
        t_frame = tk.Frame(container, bg=COLORS["bg"])
        t_frame.pack(fill="x", pady=10)
        
        tk.Label(t_frame, text="WORK (min)", bg=COLORS["bg"], fg=COLORS["accent"], font=FONTS["ui"]).grid(row=0, column=0, sticky="w")
        tk.Label(t_frame, text="BREAK (min)", bg=COLORS["bg"], fg=COLORS["alert"], font=FONTS["ui"]).grid(row=0, column=1, sticky="w")
        
        self.ent_work = tk.Entry(t_frame, bg=COLORS["input"], fg="white", width=10, insertbackground="white", bd=0)
        self.ent_work.insert(0, str(CONFIG.pomo_work))
        self.ent_work.grid(row=1, column=0, padx=(0, 10), ipady=3)
        
        self.ent_break = tk.Entry(t_frame, bg=COLORS["input"], fg="white", width=10, insertbackground="white", bd=0)
        self.ent_break.insert(0, str(CONFIG.pomo_break))
        self.ent_break.grid(row=1, column=1, ipady=3)

        # Save Button
        tk.Button(self, text="APPLY CHANGES", bg=COLORS["panel"], fg=COLORS["accent"], 
                  font=FONTS["header"], bd=0, cursor="hand2", command=self.save_and_close).pack(fill="x", side="bottom", ipady=10)

    def _add_label(self, parent, text):
        tk.Label(parent, text=text, bg=COLORS["bg"], fg="#888", font=FONTS["ui"]).pack(anchor="w", pady=(5, 2))

    def _add_input(self, parent, value):
        e = tk.Entry(parent, bg=COLORS["input"], fg="white", font=FONTS["mono"], insertbackground="white", bd=0)
        e.insert(0, value)
        e.pack(fill="x", ipady=4, pady=(0, 10))
        return e

    def save_and_close(self):
        CONFIG.watch_paths = [p.strip() for p in self.ent_paths.get().split(";") if p.strip()]
        CONFIG.monk_urls = [u.strip() for u in self.ent_urls.get().split(";") if u.strip()]
        try:
            CONFIG.pomo_work = int(self.ent_work.get())
            CONFIG.pomo_break = int(self.ent_break.get())
        except ValueError: pass
        
        CONFIG.save()
        self.callback() # Refresh main app
        self.destroy()

# --- AUTOMATION CORE ---
class FileHandler(FileSystemEventHandler):
    def __init__(self, gui_queue): self.gui_queue = gui_queue
    def on_created(self, event):
        if not event.is_directory: 
            threading.Thread(target=self.process, args=(Path(event.src_path),), daemon=True).start()
    
    def process(self, path):
        # Retry logic for file locks
        retries = 3
        while retries > 0:
            try:
                time.sleep(1.0) # Wait for download/copy to finish
                if not path.exists(): return
                
                moved = False
                for cat, exts in CONFIG.extensions.items():
                    if path.suffix.lower() in exts:
                        dest = Path.home() / "Desktop" / cat
                        dest.mkdir(parents=True, exist_ok=True)
                        
                        new_path = dest / path.name
                        if new_path.exists(): 
                            new_path = dest / f"{path.stem}_{int(time.time())}{path.suffix}"
                        
                        shutil.move(str(path), str(new_path))
                        
                        # Update Config atomically? Ideally yes, but here simple increment
                        CONFIG.stats["files_moved"] += 1 
                        CONFIG.save()
                        
                        self.gui_queue.put(("notify", f"SEIRI: {path.name} -> {cat}"))
                        moved = True
                        break
                
                if moved: break
                else: return # Not in extension list, ignore
            except PermissionError:
                retries -= 1
                time.sleep(1)
            except Exception as e:
                print(e)
                break

class KaizenHUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.queue = queue.Queue()
        self.observer = None
        self.handler = FileHandler(self.queue)
        
        # State
        self.pomo_active = False
        self.mode = "WORK"
        self.total_time = CONFIG.pomo_work * 60
        self.time_left = self.total_time
        self.settings_window = None
        
        self._setup_window()
        self._build_ui()
        self._restart_observer()
        self._poll_queue()
        self.deiconify()
        
        winsound.MessageBeep(winsound.MB_ICONASTERISK)

    def _setup_window(self):
        self.overrideredirect(True)
        self.geometry("280x200")
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)
        
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{ws-300}+{hs-250}")
        
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

    def _build_ui(self):
        # Header
        self.header = tk.Frame(self, bg=COLORS["panel"], height=28)
        self.header.pack(fill="x")
        
        tk.Label(self.header, text="KAIZEN OS", bg=COLORS["panel"], fg=COLORS["neon"], font=FONTS["header"]).pack(side="left", padx=10)
        
        # Controls
        ctrls = tk.Frame(self.header, bg=COLORS["panel"])
        ctrls.pack(side="right", padx=5)
        
        # Buttons with explicit lambda bindings
        btn_clean = tk.Label(ctrls, text="⟳", fg=COLORS["fg"], bg=COLORS["panel"], cursor="hand2")
        btn_clean.pack(side="left", padx=5)
        btn_clean.bind("<Button-1>", lambda e: self.manual_clean_thread())

        btn_set = tk.Label(ctrls, text="⚙", fg=COLORS["fg"], bg=COLORS["panel"], cursor="hand2")
        btn_set.pack(side="left", padx=5)
        btn_set.bind("<Button-1>", lambda e: self.open_settings())

        btn_close = tk.Label(ctrls, text="×", fg="#888", bg=COLORS["panel"], cursor="hand2")
        btn_close.pack(side="left", padx=5)
        btn_close.bind("<Button-1>", lambda e: self.quit_app())

        # Main Content
        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(fill="both", expand=True, padx=15, pady=10)

        self.ent_mission = tk.Entry(self.main, bg=COLORS["input"], fg=COLORS["accent"], 
                                  insertbackground="white", font=FONTS["mono"], justify="center", bd=0)
        self.ent_mission.insert(0, "ENTER MISSION OBJECTIVE")
        self.ent_mission.pack(fill="x", pady=(0, 10), ipady=3)
        self.ent_mission.bind("<FocusIn>", lambda e: self.ent_mission.delete(0, "end") if "MISSION" in self.ent_mission.get() else None)

        self.cv_timer = tk.Canvas(self.main, bg=COLORS["bg"], height=60, width=240, highlightthickness=0)
        self.cv_timer.pack(pady=5)
        
        self.txt_timer = self.cv_timer.create_text(120, 25, text="00:00", fill=COLORS["fg"], font=FONTS["timer"])
        self.bar_bg = self.cv_timer.create_rectangle(0, 55, 240, 58, fill=COLORS["dim"], width=0)
        self.bar_fg = self.cv_timer.create_rectangle(0, 55, 0, 58, fill=COLORS["accent"], width=0)

        # Stats
        stats_frame = tk.Frame(self.main, bg=COLORS["bg"])
        stats_frame.pack(fill="x", pady=5)
        self.lbl_streak = tk.Label(stats_frame, text=f"🔥 {CONFIG.stats['current_streak']} DAY STREAK", 
                                 bg=COLORS["bg"], fg="#FFA500", font=FONTS["ui"])
        self.lbl_streak.pack(side="left")
        
        self.lbl_stats = tk.Label(stats_frame, text=f"📂 {CONFIG.stats['files_moved']}", 
                                bg=COLORS["bg"], fg=COLORS["dim"], font=FONTS["ui"])
        self.lbl_stats.pack(side="right")

        self.btn_action = tk.Button(self, text="INITIATE SEQUENCE", bg=COLORS["panel"], fg=COLORS["accent"],
                                  bd=0, font=FONTS["header"], cursor="hand2", command=self.toggle_session,
                                  activebackground=COLORS["accent"], activeforeground="black")
        self.btn_action.pack(fill="x", side="bottom", ipady=8)

    # --- LOGIC ---
    def manual_clean_thread(self):
        # FIX: Run in separate thread to prevent freezing
        threading.Thread(target=self._manual_clean_worker, daemon=True).start()

    def _manual_clean_worker(self):
        count = 0
        try:
            for path_str in CONFIG.watch_paths:
                p = Path(path_str)
                if p.exists():
                    # Snapshot of files to avoid iteration issues
                    files = [f for f in p.iterdir() if f.is_file()]
                    for f in files:
                        self.handler.process(f) # Logic inside process is robust
                        count += 1
            # Send result back to UI thread via Queue
            self.queue.put(("notify", f"SYSTEM PURGE: {count} scanned."))
        except Exception as e:
            print(f"Clean Error: {e}")

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self._on_settings_saved)

    def _on_settings_saved(self):
        # Update Timer if not active
        if not self.pomo_active:
            self.total_time = CONFIG.pomo_work * 60
            self.time_left = self.total_time
            self._update_timer_visuals()
        self._restart_observer()
        self.show_notif("SYSTEM CONFIG UPDATED")

    def _restart_observer(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.observer = Observer()
        valid = False
        for p in CONFIG.watch_paths:
            if os.path.exists(p):
                self.observer.schedule(self.handler, p, recursive=False)
                valid = True
        
        if valid: self.observer.start()

    # --- TIMER LOGIC ---
    def toggle_session(self):
        if not self.pomo_active: self.start_session()
        else: self.stop_session()

    def start_session(self):
        self.pomo_active = True
        self.mode = "WORK"
        self.time_left = CONFIG.pomo_work * 60
        self.total_time = self.time_left
        
        self.ent_mission.configure(state="disabled", disabledbackground=COLORS["bg"], disabledforeground=COLORS["accent"])
        self.btn_action.configure(text="ABORT", fg=COLORS["alert"])
        self.cv_timer.itemconfig(self.bar_fg, fill=COLORS["accent"])
        
        winsound.Beep(500, 200)
        CONFIG.update_streak()
        self.lbl_streak.configure(text=f"🔥 {CONFIG.stats['current_streak']} DAY STREAK")
        
        for url in CONFIG.monk_urls: webbrowser.open(url)
        if shutil.which("code"): subprocess.Popen("code", shell=True)
        
        self.tick()

    def stop_session(self):
        self.pomo_active = False
        self.ent_mission.configure(state="normal", bg=COLORS["input"])
        self.btn_action.configure(text="INITIATE SEQUENCE", fg=COLORS["accent"])
        self.cv_timer.coords(self.bar_fg, 0, 55, 0, 58)
        self.cv_timer.itemconfig(self.txt_timer, text="00:00", fill=COLORS["fg"])

    def tick(self):
        if self.pomo_active and self.time_left > 0:
            self.time_left -= 1
            if self.mode == "WORK" and self.time_left % 60 == 0: CONFIG.stats["minutes_focused"] += 1
            self._update_timer_visuals()
            self.after(1000, self.tick)
        elif self.pomo_active:
            self.switch_phase()

    def _update_timer_visuals(self):
        m, s = divmod(self.time_left, 60)
        self.cv_timer.itemconfig(self.txt_timer, text=f"{m:02}:{s:02}")
        if self.total_time > 0:
            progress = (self.total_time - self.time_left) / self.total_time
            self.cv_timer.coords(self.bar_fg, 0, 55, 240 * progress, 58)

    def switch_phase(self):
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        if self.mode == "WORK":
            self.mode = "BREAK"
            self.time_left = CONFIG.pomo_break * 60
            color = COLORS["neon"] # Purple for break
            self.show_notif("OBJECTIVE COMPLETE. RECOVER.")
        else:
            self.mode = "WORK"
            self.time_left = CONFIG.pomo_work * 60
            color = COLORS["accent"]
            self.show_notif("ENGAGE.")
        
        self.cv_timer.itemconfig(self.txt_timer, fill=color)
        self.cv_timer.itemconfig(self.bar_fg, fill=color)
        self.total_time = self.time_left
        self.tick()

    def show_notif(self, msg):
        self.lbl_stats.configure(text=msg)
        self.after(3000, lambda: self.lbl_stats.configure(text=f"📂 {CONFIG.stats['files_moved']}"))

    def _poll_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "notify": self.show_notif(msg[1])
        except queue.Empty: pass
        self.after(500, self._poll_queue)

    def start_move(self, e): self.x, self.y = e.x, e.y
    def do_move(self, e): 
        x = self.winfo_x() + (e.x - self.x)
        y = self.winfo_y() + (e.y - self.y)
        self.geometry(f"+{x}+{y}")

    def quit_app(self):
        CONFIG.save()
        if self.observer: self.observer.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    KaizenHUD().mainloop()