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

# --- CONFIGURATION (LINUX) ---
COLORS = {
    "bg": "#121212",
    "fg": "#E0E0E0",
    "accent": "#8A56CC",
    "alert": "#FF5252",
    "break": "#29B6F6",
    "panel": "#1E1E1E",
    "success": "#00C853",
    "input": "#2C2C2C"
}

# Linux Friendly Fonts (Fallback to Helvetica if others missing)
FONTS = {
    "main": ("DejaVu Sans", 9),
    "bold": ("DejaVu Sans", 9, "bold"),
    "timer": ("Liberation Mono", 20, "bold"), 
    "small": ("DejaVu Sans", 8),
}

QUOTES = [
    "We suffer more often in imagination than in reality. – Seneca",
    "Focus on the process, not the outcome. – Kaizen",
    "Discipline is freedom."
]

CONFIG_FILE = Path.home() / ".kaizen_hud_config.json"

class Config:
    def __init__(self):
        self.watch_paths = [str(Path.home() / "Downloads")]
        self.monk_urls = ["https://github.com"]
        self.extensions = {
            "Images": [".jpg", ".jpeg", ".png", ".webp", ".svg"],
            "Documents": [".pdf", ".docx", ".txt", ".md", ".csv"],
            "Archives": [".zip", ".tar.gz", ".7z", ".rar"],
            "Code": [".py", ".js", ".cpp", ".html", ".sh", ".json"],
            "Linux_Apps": [".AppImage", ".deb", ".rpm"] # Linux specific
        }
        self.pomo_work = 25
        self.pomo_break = 5
        self.stats = {"files_moved": 0, "minutes_focused": 0, "sessions_completed": 0}
        self.load()

    def to_dict(self): return self.__dict__
    
    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e: print(f"Config Error: {e}")

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.__dict__.update(json.load(f))
            except: pass

    def increment_stat(self, key):
        if key in self.stats:
            self.stats[key] += 1
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
        
        valid = 0
        for p in CONFIG.watch_paths:
            if os.path.isdir(p):
                self.observer.schedule(handler, p, recursive=False)
                valid += 1
        
        if valid > 0:
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
        if event.src_path.endswith(('.part', '.tmp', '.crdownload')): return
        threading.Thread(target=self.process_file, args=(Path(event.src_path),), daemon=True).start()

    def process_file(self, file_path: Path):
        time.sleep(1) # Short wait for Linux write finish
        try:
            if not file_path.exists(): return
            
            moved = False
            for cat, exts in CONFIG.extensions.items():
                if file_path.suffix.lower() in exts:
                    dest = Path.home() / "Desktop" / cat
                    dest.mkdir(parents=True, exist_ok=True)
                    
                    target = dest / file_path.name
                    c = 1
                    while target.exists():
                        target = dest / f"{file_path.stem}_{c}{file_path.suffix}"
                        c += 1
                    
                    shutil.move(str(file_path), str(target))
                    CONFIG.increment_stat("files_moved")
                    self.gui_queue.put(("notify", f"Kaizen: {file_path.name} -> {cat}"))
                    moved = True
                    break
        except Exception as e:
            print(f"Linux IO Error: {e}")

class CustomNotification(tk.Toplevel):
    def __init__(self, parent, message, color=COLORS["accent"]):
        super().__init__(parent)
        self.overrideredirect(True)
        # Linux specific: "splash" type hints to WM to avoid borders but keep on top
        self.attributes("-type", "splash") 
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["panel"])
        
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 300, 50
        # Top Right on Linux usually interferes less with Docks
        x = ws - w - 30
        y = 40 
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y")
        tk.Label(self, text=message, bg=COLORS["panel"], fg=COLORS["fg"], font=FONTS["small"]).pack(side="left", padx=10)
        self.after(3500, self.destroy)

class KaizenHUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.gui_queue = queue.Queue()
        self.automator = AutomationService(self.gui_queue)
        
        self.pomo_active = False
        self.seconds = CONFIG.pomo_work * 60
        self.mode = "WORK"

        self._init_window()
        self._init_ui()
        self.automator.start_watching()
        self.check_queue()
        self.deiconify()

    def _init_window(self):
        self.overrideredirect(True)
        self.geometry("260x170")
        self.configure(bg=COLORS["bg"])
        self.attributes("-topmost", True)
        # Try to fix "missing from taskbar" issue on some Linux WMs
        # self.attributes("-type", "dock") # Optional: Uncomment if using i3/sway
        
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(ws-260)//2}+{(hs-170)//2}")
        
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

    def _init_ui(self):
        # Simplistic UI for Linux
        tk.Label(self, text="KAIZEN LINUX", bg=COLORS["bg"], fg=COLORS["accent"], font=FONTS["bold"]).pack(pady=5)
        
        self.lbl_time = tk.Label(self, text="00:00", font=FONTS["timer"], bg=COLORS["bg"], fg=COLORS["fg"])
        self.lbl_time.pack()
        
        self.btn = tk.Button(self, text="START FOCUS", bg="#333", fg="white", 
                             command=self.toggle, relief="flat", font=FONTS["bold"])
        self.btn.pack(fill="x", padx=20, pady=10)
        
        tk.Button(self, text="EXIT", bg=COLORS["bg"], fg="#555", bd=0, 
                  command=self.quit_app).pack(side="bottom")

    def check_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg[0] == "notify": CustomNotification(self, msg[1])
        except queue.Empty: pass
        self.after(200, self.check_queue)

    def toggle(self):
        self.pomo_active = not self.pomo_active
        if self.pomo_active:
            self.btn.config(text="STOP", fg=COLORS["alert"])
            # Try running 'code' or 'code-oss'
            cmd = "code" if shutil.which("code") else "code-oss"
            if shutil.which(cmd): subprocess.Popen([cmd])
            self.tick()
        else:
            self.btn.config(text="START FOCUS", fg="white")

    def tick(self):
        if self.pomo_active and self.seconds > 0:
            self.seconds -= 1
            if self.mode == "WORK" and self.seconds % 60 == 0: CONFIG.increment_stat("minutes_focused")
            m, s = divmod(self.seconds, 60)
            self.lbl_time.config(text=f"{m:02}:{s:02}")
            self.after(1000, self.tick)
        elif self.pomo_active:
            # Linux Sound (System Bell or 'aplay' fallback could be added)
            print("\a") 
            self.mode = "BREAK" if self.mode == "WORK" else "WORK"
            self.seconds = (CONFIG.pomo_break if self.mode == "BREAK" else CONFIG.pomo_work) * 60
            CustomNotification(self, f"Switch to {self.mode}", COLORS["break"])
            self.tick()

    def start_move(self, e): self.x, self.y = e.x, e.y
    def do_move(self, e): self.geometry(f"+{self.winfo_x()+(e.x-self.x)}+{self.winfo_y()+(e.y-self.y)}")
    
    def quit_app(self):
        self.automator.stop_watching()
        sys.exit()

if __name__ == "__main__":
    app = KaizenHUD()
    app.mainloop()