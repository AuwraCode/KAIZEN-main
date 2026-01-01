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
import random
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION (WINDOWS) ---
COLORS = {
    "bg": "#121212",
    "fg": "#E0E0E0",
    "accent": "#8A56CC",    # PURPLE
    "alert": "#FF5252",     # RED
    "break": "#29B6F6",     # BLUE
    "panel": "#1E1E1E",
    "success": "#00C853",   # GREEN
    "input": "#2C2C2C"
}

# Windows Native Fonts
FONTS = {
    "main": ("Segoe UI", 9),
    "bold": ("Segoe UI", 9, "bold"),
    "timer": ("Consolas", 22, "bold"),
    "small": ("Segoe UI", 8),
}

QUOTES = [
    "We suffer more often in imagination than in reality. – Seneca",
    "Discipline is doing what you hate to do, but doing it like you love it.",
    "Waste no more time arguing what a good man should be. Be one. – Aurelius",
    "Focus on the process, not the outcome. – Kaizen",
    "You have power over your mind - not outside events. – Aurelius"
]

CONFIG_FILE = Path.home() / ".kaizen_hud_config.json"

class Config:
    def __init__(self):
        # Windows standard path handling
        self.watch_paths = [str(Path.home() / "Downloads")]
        self.monk_urls = ["https://github.com", "https://chatgpt.com"]
        self.extensions = {
            "Images": [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"],
            "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx", ".md"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"],
            "Code": [".py", ".ipynb", ".js", ".cpp", ".html", ".css", ".json", ".sql"],
            "Media": [".mp3", ".wav", ".mp4", ".mkv"],
            "Installers": [".exe", ".msi", ".bat", ".ps1"] # Windows specific extensions
        }
        self.pomo_work = 25
        self.pomo_break = 5
        self.stats = {"files_moved": 0, "minutes_focused": 0, "sessions_completed": 0}
        self.load()

    def to_dict(self):
        return self.__dict__

    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            print(f"Config Save Error: {e}")

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.__dict__.update(data)
            except Exception as e:
                print(f"Config Load Error: {e}")

    def increment_stat(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value
            self.save()

CONFIG = Config()

class AutomationService:
    def __init__(self, gui_queue):
        self.gui_queue = gui_queue
        self.observer = None
        self._is_running = False

    def start_watching(self):
        if self._is_running: self.stop_watching()
        self.observer = Observer()
        handler = FileHandler(self.gui_queue)
        
        valid_paths = 0
        for path_str in CONFIG.watch_paths:
            path = Path(path_str)
            if path.exists() and path.is_dir():
                try:
                    self.observer.schedule(handler, str(path), recursive=False)
                    valid_paths += 1
                except Exception as e:
                    print(f"Error scheduling {path}: {e}")
        
        if valid_paths > 0:
            self.observer.start()
            self._is_running = True

    def stop_watching(self):
        if self._is_running and self.observer:
            self.observer.stop()
            self.observer.join()
            self._is_running = False

class FileHandler(FileSystemEventHandler):
    def __init__(self, gui_queue):
        self.gui_queue = gui_queue

    def on_created(self, event):
        if event.is_directory: return
        if event.src_path.endswith(('.crdownload', '.part', '.tmp', '.download')): return
        # Daemon thread for file processing
        threading.Thread(target=self.process_file, args=(Path(event.src_path),), daemon=True).start()

    def process_file(self, file_path: Path):
        retries = 5
        while retries > 0:
            try:
                if not file_path.exists(): return
                time.sleep(1.0) # Wait for Windows file handle release
                
                moved = False
                for category, exts in CONFIG.extensions.items():
                    if file_path.suffix.lower() in exts:
                        dest_dir = Path.home() / "Desktop" / category
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        final_path = dest_dir / file_path.name
                        counter = 1
                        while final_path.exists():
                            final_path = dest_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                            counter += 1
                        
                        shutil.move(str(file_path), str(final_path))
                        CONFIG.increment_stat("files_moved")
                        self.gui_queue.put(("notify", f"Moved: {file_path.name}"))
                        moved = True
                        break
                
                if moved: break
            except PermissionError:
                retries -= 1
                time.sleep(1.5)
            except Exception as e:
                print(f"Error: {e}")
                break

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, automator):
        super().__init__(parent)
        self.automator = automator
        self.title("Kaizen Config")
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)
        self.geometry("320x350")
        self._build_ui()

    def _build_ui(self):
        pad = 10
        tk.Label(self, text="WATCH PATHS (;)", bg=COLORS["bg"], fg="#888", font=FONTS["small"]).pack(anchor="w", padx=pad)
        self.ent_paths = tk.Entry(self, bg=COLORS["input"], fg=COLORS["fg"], bd=1, relief="solid", insertbackground="white")
        self.ent_paths.insert(0, ";".join(CONFIG.watch_paths))
        self.ent_paths.pack(fill="x", padx=pad, pady=(0, 10))

        tk.Label(self, text="MONK URLS (;)", bg=COLORS["bg"], fg="#888", font=FONTS["small"]).pack(anchor="w", padx=pad)
        self.ent_urls = tk.Entry(self, bg=COLORS["input"], fg=COLORS["fg"], bd=1, relief="solid", insertbackground="white")
        self.ent_urls.insert(0, ";".join(CONFIG.monk_urls))
        self.ent_urls.pack(fill="x", padx=pad, pady=(0, 10))

        tk.Label(self, text=f"Stats: {CONFIG.stats['files_moved']} files | {CONFIG.stats['minutes_focused']} mins", 
                 bg=COLORS["bg"], fg="#666", font=FONTS["small"]).pack(pady=10)

        tk.Button(self, text="SAVE", bg=COLORS["accent"], fg="black", font=FONTS["bold"], 
                  command=self.save_config).pack(fill="x", padx=pad, side="bottom", pady=pad)

    def save_config(self):
        CONFIG.watch_paths = [p.strip() for p in self.ent_paths.get().split(";") if p.strip()]
        CONFIG.monk_urls = [u.strip() for u in self.ent_urls.get().split(";") if u.strip()]
        CONFIG.save()
        self.automator.start_watching()
        self.destroy()

class CustomNotification(tk.Toplevel):
    def __init__(self, parent, message, color=COLORS["accent"]):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["panel"])
        
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w, h = 300, 45
        # Bottom Right Corner for Windows
        x = ws - w - 20
        y = hs - h - 50 
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y")
        tk.Label(self, text=message, bg=COLORS["panel"], fg=COLORS["fg"], font=FONTS["small"]).pack(side="left", padx=10)
        self.after(4000, self.destroy)

class KaizenHUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.gui_queue = queue.Queue()
        self.automator = AutomationService(self.gui_queue)
        
        self.pomo_active = False
        self.pomo_state = "WORK"
        self.pomo_seconds_left = CONFIG.pomo_work * 60
        self.settings_ref = None

        self._setup_window()
        self._setup_ui()
        self.automator.start_watching()
        self.check_queue()
        self.deiconify()

    def _setup_window(self):
        self.overrideredirect(True) # Borderless on Windows works well
        self.geometry("250x160")
        self.configure(bg=COLORS["bg"], highlightthickness=1, highlightbackground="#333")
        self.attributes("-topmost", True)
        
        # Center Screen
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        self.geometry(f"+{(ws-250)//2}+{(hs-160)//2}")

        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

    def _setup_ui(self):
        # Header
        h_frame = tk.Frame(self, bg=COLORS["panel"], height=24)
        h_frame.pack(fill="x")
        tk.Label(h_frame, text=" KAIZEN", bg=COLORS["panel"], fg=COLORS["accent"], font=FONTS["bold"]).pack(side="left")
        
        close = tk.Label(h_frame, text=" × ", bg=COLORS["panel"], fg="#888", cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.quit_app())
        
        # Content
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_timer = tk.Label(self.content, text="00:00", font=FONTS["timer"], bg=COLORS["bg"], fg=COLORS["fg"])
        self.lbl_timer.pack(pady=5)
        
        self.btn_act = tk.Button(self.content, text="MONK MODE", bg="#222", fg=COLORS["accent"], 
                               bd=0, font=FONTS["bold"], command=self.toggle_monk, cursor="hand2")
        self.btn_act.pack(fill="x", pady=5)

        tk.Label(self, text="[SETTINGS]", bg=COLORS["bg"], fg="#444", font=FONTS["small"], cursor="hand2").pack(side="bottom", pady=5)
        self.bind("<Button-1>", lambda e: self.open_settings() if e.widget.cget("text") == "[SETTINGS]" else None)

    def check_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg[0] == "notify": CustomNotification(self, msg[1])
        except queue.Empty: pass
        self.after(200, self.check_queue)

    def toggle_monk(self):
        if not self.pomo_active:
            self.pomo_active = True
            self.btn_act.config(text="STOP", fg=COLORS["alert"])
            CustomNotification(self, random.choice(QUOTES))
            for url in CONFIG.monk_urls: webbrowser.open(url)
            # Windows specific call for VS Code
            if shutil.which("code"): subprocess.Popen("code", shell=True) 
            self.tick()
        else:
            self.pomo_active = False
            self.btn_act.config(text="MONK MODE", fg=COLORS["accent"])
            self.lbl_timer.config(text="00:00", fg=COLORS["fg"])

    def tick(self):
        if self.pomo_active and self.pomo_seconds_left > 0:
            self.pomo_seconds_left -= 1
            if self.pomo_state == "WORK" and self.pomo_seconds_left % 60 == 0:
                CONFIG.increment_stat("minutes_focused")
            mins, secs = divmod(self.pomo_seconds_left, 60)
            self.lbl_timer.config(text=f"{mins:02}:{secs:02}")
            self.after(1000, self.tick)
        elif self.pomo_active:
            self.bell()
            if self.pomo_state == "WORK":
                self.pomo_state = "BREAK"
                self.pomo_seconds_left = CONFIG.pomo_break * 60
                CustomNotification(self, "Rest.", COLORS["success"])
            else:
                self.pomo_state = "WORK"
                self.pomo_seconds_left = CONFIG.pomo_work * 60
                CustomNotification(self, "Work.", COLORS["alert"])
            self.tick()

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self.x)
        y = self.winfo_y() + (event.y - self.y)
        self.geometry(f"+{x}+{y}")

    def open_settings(self):
        if not self.settings_ref or not self.settings_ref.winfo_exists():
            self.settings_ref = SettingsWindow(self, self.automator)

    def quit_app(self):
        self.automator.stop_watching()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = KaizenHUD()
    app.mainloop()