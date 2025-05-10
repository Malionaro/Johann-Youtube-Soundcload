import ctypes
import os
import sys
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
import platform
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import yt_dlp
from pathlib import Path
import requests
from packaging import version

LOCAL_VERSION = "1.4"
GITHUB_RELEASES_URL = "https://api.github.com/repos/Malionaro/Johann-Youtube-Soundcload/releases/latest"

__version__ = "1.4"

def check_for_updates(log_func):
    try:
        log_func("🔍 Suche nach Updates...")

        response = requests.get(GITHUB_RELEASES_URL, timeout=10)
        response.raise_for_status()
        latest = response.json()
        latest_version = latest["tag_name"].lstrip("v")

        if version.parse(latest_version) > version.parse(LOCAL_VERSION):
            log_func(f"⬆️ Neue Version verfügbar: {latest_version}")
            exe_asset = next((a for a in latest["assets"] if a["name"].endswith(".exe")), None)
            if not exe_asset:
                log_func("⚠️ Keine EXE-Datei im Release gefunden.")
                return

            download_url = exe_asset["browser_download_url"]
            exe_name = exe_asset["name"]

            log_func(f"⬇️ Lade {exe_name} herunter...")

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as tmp_file:
                    for chunk in r.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)
                    exe_path = tmp_file.name

            log_func("🚀 Starte das Update...")
            subprocess.Popen([exe_path], shell=True)
            sys.exit(0)

        else:
            log_func("✅ Keine neue Version gefunden.")
    except Exception as e:
        log_func(f"⚠️ Fehler bei der Update-Prüfung: {e}")

# === Hilfsfunktionen ===
def check_ffmpeg_installed():
    """Überprüft, ob FFmpeg korrekt installiert und nutzbar ist."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout.lower() + result.stderr.lower()
        return "ffmpeg version" in output
    except Exception:
        return False

def install_ffmpeg(log_func=print):
    """Installiert FFmpeg unter Windows oder Linux."""
    if platform.system() == "Windows":
        log_func("🔧 Starte FFmpeg-Installation über winget...")
        try:
            result = subprocess.run(["winget", "install", "--id=Gyan.FFmpeg", "-e", "--silent"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            log_func(result.stdout)
            log_func("✅ FFmpeg wurde erfolgreich installiert.")
            return True
        except subprocess.CalledProcessError as e:
            log_func("❌ Fehler bei der Installation von FFmpeg mit winget.")
            log_func(e.stderr)
            return False
    elif platform.system() == "Linux":
        log_func("🔧 Starte FFmpeg-Installation über apt...")
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True)
            log_func("✅ FFmpeg wurde erfolgreich installiert.")
            return True
        except subprocess.CalledProcessError as e:
            log_func("❌ Fehler bei der Installation von FFmpeg unter Linux.")
            log_func(str(e))
            return False
    else:
        log_func("⚠️ Plattform nicht unterstützt.")
        return False


def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

# === GUI Klasse ===
class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Playlist Downloader – YouTube & SoundCloud")
        self.root.geometry("750x720")
        self.root.configure(bg="#2a2a2a")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", foreground="white", background="#2a2a2a", font=("Segoe UI", 12))
        style.configure("TButton", font=("Segoe UI", 12), width=20)
        style.configure("TProgressbar",
                thickness=20,
                length=650,
                maximum=100,
                background="#4caf50",  # Grüne Farbe für den Fortschrittsbalken
                )

        try:
            self.root.iconbitmap("app_icon.ico")
        except:
            pass

        self.header_label = ttk.Label(root, text="🎧 Playlist Downloader", font=("Segoe UI", 16), foreground="lightblue", background="#2a2a2a")
        self.header_label.pack(pady=(20, 10))

        self.url_label = ttk.Label(root, text="🎧 Playlist- oder Track-URL:")
        self.url_label.pack(pady=(30, 5))

        self.url_entry = tk.Entry(root, width=85, font=("Segoe UI", 12), borderwidth=2, relief="solid")
        self.url_entry.pack(pady=5, ipady=5)

        folder_url_frame = tk.Frame(root, bg="#2a2a2a")
        folder_url_frame.pack(pady=(10, 5))

        self.choose_folder_button = ttk.Button(folder_url_frame, text="📁 Zielordner auswählen", command=self.choose_folder)
        self.choose_folder_button.pack(side="left", padx=(0, 10))

        self.clear_url_button = ttk.Button(folder_url_frame, text="🧹 URL leeren", command=self.clear_url)
        self.clear_url_button.pack(side="left")


        self.download_button = ttk.Button(root, text="⬇️  Download starten", command=self.start_download_thread, state="disabled")
        self.download_button.pack(pady=(20, 10))

        self.cancel_button = ttk.Button(root, text="❌ Abbrechen", command=self.cancel_download, state='disabled')
        self.cancel_button.pack(pady=(5, 10))

        self.warning_label = ttk.Label(root, text="", foreground="yellow", background="#2a2a2a", font=("Segoe UI", 12))
        self.warning_label.pack(pady=(5, 15))

        self.progress = ttk.Progressbar(root, orient='horizontal', length=650, mode='determinate', style="TProgressbar")
        self.progress.pack(pady=5)

        self.status_label = ttk.Label(root, text="Bereit", font=("Segoe UI", 12), foreground="lightgreen", background="#2a2a2a")
        self.status_label.pack(pady=5)

        self.log_output = scrolledtext.ScrolledText(root, height=12, width=85, state='disabled', bg="#333333", fg="white", font=("Consolas", 11))
        self.log_output.pack(pady=10)

        self.version_label = ttk.Label(root, text="V1.4", font=("Segoe UI", 10), foreground="lightgray", background="#2a2a2a")
        self.version_label.pack(side="bottom", pady=5)

        self.download_folder = os.path.expanduser("~")
        os.makedirs("downloads", exist_ok=True)
        self.download_thread = None
        self.abort_event = threading.Event()

    def clear_url(self):
        self.url_entry.delete(0, tk.END)
        self.log("🧹 URL-Feld wurde geleert.")

    def log(self, message):
        self.log_output.config(state='normal')
        self.log_output.insert(tk.END, message + "\n")
        self.log_output.see(tk.END)
        self.log_output.config(state='disabled')

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder, title="Wählen Sie einen Zielordner")
        if folder:
            self.download_folder = folder
            self.log(f"✅ Zielordner gesetzt: {folder}")
            self.download_button.config(state="normal")

    def start_download_thread(self):
        self.cancel_button.config(state='normal')
        self.download_button.config(state='disabled')
        self.abort_event.clear()
        self.download_thread = threading.Thread(target=self.download_playlist)
        self.download_thread.start()

    def cancel_download(self):
        response = messagebox.askyesno("Abbrechen", "Möchten Sie das Programm wirklich beenden?", icon='warning')
        if response:
            self.root.quit()  # Beendet die Tkinter-Anwendung
            sys.exit()        # Beendet das gesamte Programm


    def progress_hook(self, d):
        if self.abort_event.is_set():
            raise yt_dlp.utils.DownloadError("Download abgebrochen")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                self.progress['value'] = percent
                self.root.update_idletasks()
        elif d['status'] == 'finished':
            self.progress['value'] = 100
            self.root.update_idletasks()
            self.log("✅ Download abgeschlossen.")

    def download_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Fehler", "Bitte eine URL eingeben.")
            return

        self.status_label.config(text="🔍 Analysiere URL...")
        self.log("🔍 Starte Analyse der URL...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'ignoreerrors': True,
            'progress_hooks': [self.progress_hook],
            'noplaylist': False,
            'logger': YTDLogger(self),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    entries = info['entries']
                    total = len(entries)
                    self.log(f"📂 {total} Titel gefunden.")
                    for i, entry in enumerate(entries, start=1):
                        if entry is None or self.abort_event.is_set():
                            break
                        title = entry.get('title', f"Track {i}")
                        link = entry.get('webpage_url')
                        self.status_label.config(text=f"⬇️ Lade: {title} ({i}/{total})")
                        self.log(f"⬇️ {i}/{total} – {title}")
                        self.progress['value'] = 0
                        self.root.update_idletasks()
                        ydl.download([link])
                else:
                    title = info.get('title', "Track")
                    self.status_label.config(text=f"⬇️ Lade: {title}")
                    self.log(f"⬇️ Lade Einzeltrack: {title}")
                    ydl.download([url])

        except Exception as e:
            error_msg = f"❌ Fehler beim Download:\n{str(e)}"
            self.status_label.config(text="❌ Fehler aufgetreten")
            self.log(error_msg)
            messagebox.showerror("Fehler", error_msg)
            return

        self.status_label.config(text="✅ Download abgeschlossen!")
        self.progress['value'] = 100
        self.log("🎉 Alle Titel erfolgreich geladen.")
        messagebox.showinfo("Fertig", "Alle Titel wurden als MP3 heruntergeladen.")

class YTDLogger:
    def __init__(self, app):
        self.app = app

    def debug(self, msg):
        if msg.strip():
            self.app.log("[DEBUG] " + msg)

    def warning(self, msg):
        self.app.log("[WARNUNG] " + msg)

    def error(self, msg):
        self.app.log("[FEHLER] " + msg)

# === Startpunkt ===
def startup_log(msg):
    print(msg.encode("ascii", "ignore").decode())  # vermeidet UnicodeEncodeError in der Konsole
    
if __name__ == "__main__":
    check_for_updates(startup_log)

    if not check_ffmpeg_installed():
        messagebox.showinfo("FFmpeg fehlt", "FFmpeg wird jetzt installiert...")
        if not install_ffmpeg():
            messagebox.showerror("Fehler", "FFmpeg konnte nicht installiert werden.")
            sys.exit(1)

    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()
