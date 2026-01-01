# KAIZEN HUD

> "Efficiency is doing things right; effectiveness is doing the right things."

**KAIZEN HUD** is a minimalist, Always-On-Top desktop dashboard designed for high-performance workflows. It combines automated file organization (Seiri) with a deep work focus timer (Monk Mode) in a non-intrusive interface.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Key Features

* **🕵️ Background Automation:** Automatically watches `Downloads`. Instantly organizes files into Images, Documents, Code, and Installers upon creation.
* **🧘 Monk Mode:** One-click "Deep Work" environment. Launches tools (VS Code, URLs) and starts a focus timer.
* **🎨 OS-Native Design:**
    * **Windows:** Optimized for NTFS, uses Segoe UI, seamless borderless window.
    * **Linux:** Optimized for GNOME/KDE, uses DejaVu/Liberation fonts, XDG compliant.
* **📊 ROI Stats:** Tracks files organized and minutes spent in deep focus.
* **🚀 Zero Bloat:** Built with pure Python `tkinter` and `watchdog`.

## 🛠️ Tech Stack

* **Core:** Python 3
* **GUI:** Tkinter (Custom drawn, DPI aware)
* **System:** `watchdog` (File monitoring), `threading` (Async I/O)

## 📦 Installation

1.  **Clone the repository:**

    git clone [https://github.com/your-username/kaizen-hud.git](https://github.com/your-username/kaizen-hud.git)
    cd kaizen-hud

2.  **Install dependencies:**

    pip install -r requirements.txt

    *(Note for Linux Users: If you encounter errors, ensure Tkinter is installed system-wide: `sudo apt-get install python3-tk`)*

## 🎮 Usage

### Windows
Run the Windows-optimized version. To hide the console window, rename the file extension to `.pyw`.

    python kaizen_win.py

### Linux
Run the Linux-optimized version.

    python3 kaizen_linux.py

### Interface Controls
* **Move:** Drag the window by the top bar.
* **Monk Mode:** Click `MONK MODE` to start the timer and launch apps.
* **Settings:** Click `[SETTINGS]` to configure paths, URLs, and timer duration.
* **Exit:** Click `×` or use the Exit button.

## ⚙️ Configuration

The app creates a lightweight config file at `~/.kaizen_hud_config.json`. You can edit this via the **[SETTINGS]** menu in the app or manually:

* **watch_paths:** List of folders to monitor (separated by `;`).
* **monk_urls:** List of websites to open on Focus Start.
* **pomo_work/break:** Timer duration in minutes.

---
*Built with discipline.*