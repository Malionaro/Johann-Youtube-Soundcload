import customtkinter as ctk
import ctypes
import tarfile
import shutil
import os
import json
import sys
import urllib.request
import subprocess
import platform
import threading
import webbrowser
import yt_dlp
import requests
from PIL import Image, ImageTk
from io import BytesIO
from tkinter import messagebox
import tkinter.filedialog as filedialog
from packaging import version
import time
import concurrent.futures
import datetime

# App-Konfiguration
APP_NAME = "SoundSync Downloader"
LOCAL_VERSION = "1.8.1"
GITHUB_REPO_URL = "https://github.com/Malionaro/Johann-Youtube-Soundcload"
GITHUB_RELEASES_URL = f"{GITHUB_REPO_URL}/releases/latest"
CONFIG_PATH = "config.json"
os.environ["PATH"] += os.pathsep + "/usr/local/bin"

# Theme-Einstellungen
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def check_ffmpeg_installed():
    """Prüft, ob FFmpeg bereits installiert ist."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "ffmpeg version" in (result.stdout + result.stderr).lower()
    except Exception:
        return False

def install_ffmpeg(log_func=print):
    if shutil.which("ffmpeg"):
        log_func("✅ FFmpeg ist bereits installiert.")
        return True

    if platform.system() == "Windows":
        log_func("🔧 Starte FFmpeg-Installation über winget...")
        try:
            subprocess.run(["winget", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            log_func("❌ Winget ist nicht verfügbar. Bitte FFmpeg manuell installieren.")
            return False

        try:
            result = subprocess.run(
                ["winget", "install", "--id=Gyan.FFmpeg", "-e", "--silent"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
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
            subprocess.run(['sudo', 'apt-get', 'update'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log_func("✅ FFmpeg wurde erfolgreich installiert.")
            return True
        except subprocess.CalledProcessError as e:
            log_func("❌ Fehler bei der Installation von FFmpeg unter Linux.")
            log_func(str(e))
            return False

    elif platform.system() == "Darwin":
        log_func("🔧 Starte FFmpeg-Installation ohne Homebrew...")
        if shutil.which("ffmpeg"):
            log_func("✅ FFmpeg ist bereits installiert.")
            return True

        try:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz"
            download_dir = "/tmp/ffmpeg"
            install_dir = "/usr/local/bin"

            log_func(f"⬇️ Lade FFmpeg herunter von {url}...")
            archive_path = os.path.join(download_dir, "ffmpeg.tar.xz")
            urllib.request.urlretrieve(url, archive_path)
            log_func("✅ Download abgeschlossen.")

            log_func("🔧 Entpacke FFmpeg...")
            with tarfile.open(archive_path, "r:xz") as archive:
                archive.extractall(download_dir)
            log_func("✅ Entpacken abgeschlossen.")

            ffmpeg_bin = os.path.join(download_dir, "ffmpeg-*-static", "ffmpeg")
            ffmpeg_dest = os.path.join(install_dir, "ffmpeg")
            log_func(f"🔧 Verschiebe FFmpeg nach {install_dir}...")
            shutil.move(ffmpeg_bin, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)

            if shutil.which("ffmpeg"):
                log_func("✅ FFmpeg wurde erfolgreich installiert.")
                return True
            else:
                log_func("❌ FFmpeg konnte nicht in den PATH eingefügt werden.")
                return False

        except Exception as e:
            log_func(f"❌ Fehler bei der Installation von FFmpeg: {str(e)}")
            return False
    else:
        log_func("⚠️ Plattform nicht unterstützt.")
        return False

class YTDLogger:
    def __init__(self, app):
        self.app = app

    def debug(self, msg):
        if msg.strip():
            self.app.log(f"[DEBUG] {msg}")

    def warning(self, msg):
        self.app.log(f"[WARNUNG] {msg}")

    def error(self, msg):
        self.app.log(f"[FEHLER] {msg}")

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)
        
        # Icon setzen
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        
        # Bereinigte Formatliste
        self.codec_map = {
            "mp3": "mp3", "m4a": "m4a", "wav": "wav", "flac": "flac", "aac": "aac",
            "ogg": "vorbis", "opus": "opus", "wma": "wma", "alac": "alac", "aiff": "aiff"
        }
        self.formate = [*self.codec_map.keys(), "mp4", "webm", "mkv", "avi", "mov", "flv", "wmv", "3gp"]
        self.formate.sort()
        self.format_var = ctk.StringVar(value="mp3")
        self.dark_mode = ctk.BooleanVar(value=True)
        self.abort_event = threading.Event()
        self.is_downloading = False
        self.total_tracks = 0
        self.completed_tracks = 0
        self.successful_downloads = 0
        self.downloaded_tracks = []
        self.thumbnail_cache = {}
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.start_time = None
        self.last_update_time = None
        self.last_downloaded_bytes = 0
        self.current_speed = 0
        self.cookies_path = ""
        self.current_thumbnail_frame = None

        # Hauptlayout mit 2 Spalten
        self.root.grid_columnconfigure(0, weight=3)  # Hauptbereich
        self.root.grid_columnconfigure(1, weight=1)  # Sidebar
        self.root.grid_rowconfigure(1, weight=1)

        # Header mit Logo und Titel
        header_frame = ctk.CTkFrame(self.root, corner_radius=0)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # App-Logo (Platzhalter)
        logo_label = ctk.CTkLabel(
            header_frame, 
            text="🎵", 
            font=("Arial", 24),
            width=50
        )
        logo_label.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="w")
        
        # App-Titel
        title_label = ctk.CTkLabel(
            header_frame,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold")
        )
        title_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Theme-Switch
        theme_switch = ctk.CTkSwitch(
            header_frame, 
            text="Dark Mode",
            variable=self.dark_mode,
            command=self.toggle_theme,
            button_color="#2CC985"
        )
        theme_switch.grid(row=0, column=2, padx=15, pady=10, sticky="e")

        # Hauptbereich (linke Spalte)
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Einstellungen und Fortschritt
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # URL-Eingabe
        url_frame = ctk.CTkFrame(settings_frame)
        url_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)
        url_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            url_frame,
            text="YouTube oder SoundCloud URL:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        url_input_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_input_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        url_input_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="https://www.youtube.com/... oder https://soundcloud.com/...",
            font=("Segoe UI", 12)
        )
        self.url_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        self.url_entry.bind("<KeyRelease>", self.update_download_button_state)

        ctk.CTkButton(
            url_input_frame,
            text="X",
            command=self.clear_url,
            width=40,
            font=("Segoe UI", 11, "bold"),
            fg_color="#C74B4B",
            hover_color="#A03A3A"
        ).grid(row=0, column=1, padx=0, pady=0)

        # Zielordner und Format in einer Zeile
        folder_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        folder_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            folder_frame,
            text="Zielordner:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.folder_entry = ctk.CTkEntry(
            folder_frame,
            placeholder_text="Wählen Sie einen Speicherort...",
            font=("Segoe UI", 12)
        )
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            folder_frame,
            text="Durchsuchen",
            command=self.choose_folder,
            width=100,
            font=("Segoe UI", 11),
            fg_color="#2A8C55",
            hover_color="#207244"
        ).grid(row=0, column=2, padx=(5, 10), pady=5)

        # Format und Cookies in einer Zeile
        format_cookies_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        format_cookies_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        format_cookies_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            format_cookies_frame,
            text="Format:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.format_combobox = ctk.CTkComboBox(
            format_cookies_frame,
            variable=self.format_var,
            values=self.formate,
            state="normal",
            width=120,
            font=("Segoe UI", 12),
            dropdown_fg_color="#2A3B4D"
        )
        self.format_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.format_combobox.set("mp3")

        ctk.CTkLabel(
            format_cookies_frame,
            text="Cookies:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")

        self.cookies_entry = ctk.CTkEntry(
            format_cookies_frame,
            placeholder_text="Pfad zu cookies.txt",
            font=("Segoe UI", 12),
            width=150
        )
        self.cookies_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            format_cookies_frame,
            text="Auswählen",
            command=self.choose_cookies_file,
            width=100,
            font=("Segoe UI", 11)
        ).grid(row=0, column=4, padx=(5, 10), pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")

        self.download_button = ctk.CTkButton(
            button_frame,
            text="Download starten",
            command=self.start_download_thread,
            state="disabled",
            font=("Segoe UI", 12, "bold"),
            height=40,
            fg_color="#2A8C55",
            hover_color="#207244"
        )
        self.download_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Abbrechen",
            command=self.cancel_download,
            state="disabled",
            font=("Segoe UI", 12),
            height=40,
            fg_color="#C74B4B",
            hover_color="#A03A3A"
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.update_button = ctk.CTkButton(
            button_frame,
            text="Auf Updates prüfen",
            command=lambda: threading.Thread(target=self.check_for_updates_gui).start(),
            font=("Segoe UI", 12),
            height=40
        )
        self.update_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Fortschrittsbalken
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        progress_frame.grid_columnconfigure(0, weight=1)
        progress_frame.grid_rowconfigure(0, weight=1)

        # Fortschritt für aktuellen Titel
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Bereit zum Starten",
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.progress = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20
        )
        self.progress.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.progress.set(0)

        # Konvertierungsfortschritt
        self.convert_label = ctk.CTkLabel(
            progress_frame,
            text="Konvertierung: Wartend...",
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.convert_label.grid(row=2, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.convert_progress = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20
        )
        self.convert_progress.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.convert_progress.set(0)

        # Gesamtfortschritt
        self.total_progress_label = ctk.CTkLabel(
            progress_frame,
            text="Gesamtfortschritt: 0% | ETA: --:--:--",
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.total_progress_label.grid(row=4, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.total_progress = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20
        )
        self.total_progress.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.total_progress.set(0)

        # Log-Ausgabe
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        # Titelzeile für Log mit "Log leeren"-Button
        log_title_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        log_title_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            log_title_frame,
            text="Aktivitätsprotokoll:",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # "Log leeren"-Button oben rechts
        self.clear_log_button = ctk.CTkButton(
            log_title_frame,
            text="Log leeren",
            command=self.clear_log,
            width=100,
            font=("Segoe UI", 10),
            fg_color="#3A7EBF",
            hover_color="#2E6399"
        )
        self.clear_log_button.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Log-Textbox
        self.log_output = ctk.CTkTextbox(
            log_frame,
            font=("Consolas", 11),
            wrap="word",
            activate_scrollbars=True
        )
        self.log_output.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_output.configure(state="disabled")

        # Sidebar (rechte Spalte)
        sidebar_frame = ctk.CTkFrame(self.root)
        sidebar_frame.grid(row=1, column=1, padx=(0, 10), pady=10, sticky="nsew")
        sidebar_frame.grid_columnconfigure(0, weight=1)
        sidebar_frame.grid_rowconfigure(1, weight=1)

        # Heruntergeladene Titel
        ctk.CTkLabel(
            sidebar_frame,
            text="Heruntergeladene Titel:",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Scrollable Frame für Thumbnails
        self.scrollable_frame = ctk.CTkScrollableFrame(
            sidebar_frame,
            orientation="vertical",
            width=300
        )
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Scroll-Button am Boden
        scroll_button_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        scroll_button_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        scroll_button_frame.grid_columnconfigure(0, weight=1)

        self.scroll_to_current_button = ctk.CTkButton(
            scroll_button_frame,
            text="Zum aktuellen Titel scrollen",
            command=self.scroll_to_current,
            font=("Segoe UI", 10),
            fg_color="#3A7EBF",
            hover_color="#2E6399"
        )
        self.scroll_to_current_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Statusbar
        statusbar = ctk.CTkFrame(self.root, height=30, corner_radius=0)
        statusbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 0))
        statusbar.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            statusbar,
            text="Bereit",
            font=("Segoe UI", 11),
            text_color="lightgreen",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=(15, 5), pady=0, sticky="w")

        # GitHub-Link
        self.github_button = ctk.CTkButton(
            statusbar,
            text="GitHub",
            command=lambda: webbrowser.open(GITHUB_REPO_URL),
            width=70,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color="#2A3B4D"
        )
        self.github_button.grid(row=0, column=1, padx=(0, 10), pady=0, sticky="e")

        self.version_label = ctk.CTkLabel(
            statusbar,
            text=f"Version: {LOCAL_VERSION}",
            font=("Segoe UI", 10),
            text_color="lightgray",
            anchor="e"
        )
        self.version_label.grid(row=0, column=2, padx=5, pady=0, sticky="e")

        # Initialisierung
        self.download_folder = self.load_download_folder() or os.path.expanduser("~")
        self.folder_entry.insert(0, self.download_folder)
        os.makedirs(self.download_folder, exist_ok=True)
        self.update_download_button_state()

    def toggle_theme(self):
        mode = "dark" if self.dark_mode.get() else "light"
        ctk.set_appearance_mode(mode)
        self.status_label.configure(text_color="lightgreen" if mode == "dark" else "green")

    def load_download_folder(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    self.cookies_path = config.get("cookies_path", "")
                    self.cookies_entry.insert(0, self.cookies_path)
                    return config.get("download_folder")
            except:
                pass
        return None

    def save_config(self):
        config = {
            "download_folder": self.download_folder,
            "cookies_path": self.cookies_path
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder, title="Wählen Sie einen Zielordner")
        if folder:
            self.download_folder = folder
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.save_config()
            self.log(f"✅ Zielordner gesetzt: {folder}")
            self.update_download_button_state()

    def choose_cookies_file(self):
        file_path = filedialog.askopenfilename(
            title="Wählen Sie eine Cookies-Datei",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")]
        )
        if file_path:
            self.cookies_path = file_path
            self.cookies_entry.delete(0, "end")
            self.cookies_entry.insert(0, file_path)
            self.save_config()
            self.log(f"🍪 Cookies-Datei ausgewählt: {file_path}")

    def update_download_button_state(self, event=None):
        url_filled = bool(self.url_entry.get().strip())
        folder_selected = bool(self.download_folder and os.path.isdir(self.download_folder))
        state = "normal" if url_filled and folder_selected and not self.is_downloading else "disabled"
        self.download_button.configure(state=state)

    def clear_url(self):
        self.url_entry.delete(0, "end")
        self.log("🧹 URL-Feld wurde geleert.")
        self.update_download_button_state()

    def clear_log(self):
        self.log_output.configure(state="normal")
        self.log_output.delete("1.0", "end")
        self.log_output.configure(state="disabled")
        self.log("🧹 Log wurde geleert.")

    def log(self, message):
        self.log_output.configure(state="normal")
        self.log_output.insert("end", message + "\n")
        self.log_output.see("end")
        self.log_output.configure(state="disabled")

    def start_download_thread(self):
        self.is_downloading = True
        self.format_combobox.configure(state="disabled")
        self.abort_event.clear()
        self.cancel_button.configure(state="normal")
        self.download_button.configure(state="disabled")
        self.total_tracks = 0
        self.completed_tracks = 0
        self.successful_downloads = 0
        self.downloaded_tracks = []
        self.thumbnail_cache = {}
        self.total_progress.set(0)
        self.convert_progress.set(0)
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded_bytes = 0
        self.current_speed = 0
        
        # Clear scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        threading.Thread(target=self.download_playlist, daemon=True).start()

    def cancel_download(self):
        if self.is_downloading:
            if messagebox.askyesno("Download abbrechen", "Möchten Sie den aktuellen Download wirklich abbrechen?", icon="warning"):
                self.abort_event.set()
                self.log("🛑 Download abgebrochen durch Benutzer")
                self.status_label.configure(text="❌ Abgebrochen", text_color="#FF6B6B")
                self.cancel_button.configure(state="disabled")
                self.is_downloading = False
        else:
            self.log("ℹ️ Es läuft kein Download, der abgebrochen werden könnte.")

    def scroll_to_current(self):
        if self.current_thumbnail_frame:
            self.scrollable_frame._parent_canvas.yview_moveto(1.0)

    def progress_hook(self, d):
        if self.abort_event.is_set():
            raise yt_dlp.utils.DownloadError("Download abgebrochen")
            
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                progress_value = downloaded / total
                self.progress.set(progress_value)
                percent = int(progress_value * 100)
                
                # Geschwindigkeitsberechnung
                if time_diff > 0.5:  # Alle 0.5 Sekunden aktualisieren
                    downloaded_diff = downloaded - self.last_downloaded_bytes
                    self.current_speed = downloaded_diff / time_diff
                    self.last_downloaded_bytes = downloaded
                    self.last_update_time = current_time
                
                # ETA für aktuellen Titel
                if self.current_speed > 0:
                    remaining_bytes = total - downloaded
                    eta_seconds = remaining_bytes / self.current_speed
                    eta_str = str(datetime.timedelta(seconds=int(eta_seconds)))
                    self.progress_label.configure(text=f"Fortschritt: {percent}% | Geschw: {self.format_speed(self.current_speed)} | ETA: {eta_str}")
                else:
                    self.progress_label.configure(text=f"Fortschritt: {percent}% | Geschw: berechne...")
            
        elif d['status'] == 'finished':
            self.progress.set(1.0)
            self.progress_label.configure(text="✅ Download abgeschlossen")
            self.log("✅ Download abgeschlossen.")
            
        # Post-Processing Fortschritt
        if d.get('postprocessor') and d.get('postprocessor') == 'FFmpegExtractAudio':
            self.convert_label.configure(text=f"Konvertierung: {d.get('postprocessor_args', [''])[-1]}")
            self.convert_progress.set(d.get('postprocessor_progress', 0))
        elif d.get('postprocessor') and d.get('postprocessor') == 'FFmpegVideoConvertor':
            self.convert_label.configure(text=f"Konvertierung: {d.get('postprocessor_args', [''])[-1]}")
            self.convert_progress.set(d.get('postprocessor_progress', 0))

    def format_speed(self, speed_bytes):
        """Formatiert Geschwindigkeit in lesbare Einheiten"""
        if speed_bytes < 1024:
            return f"{speed_bytes:.1f} B/s"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes / 1024:.1f} KB/s"
        else:
            return f"{speed_bytes / (1024 * 1024):.1f} MB/s"

    def update_status_label(self, text):
        self.status_label.configure(text=text)

    def update_total_progress(self):
        """Aktualisiert den Gesamtfortschrittsbalken und ETA"""
        if self.total_tracks > 0:
            progress_value = self.completed_tracks / self.total_tracks
            self.total_progress.set(progress_value)
            percent = int(progress_value * 100)
            
            # Gesamt-ETA berechnen
            if self.start_time and self.completed_tracks > 0:
                elapsed_time = time.time() - self.start_time
                avg_time_per_track = elapsed_time / self.completed_tracks
                remaining_tracks = self.total_tracks - self.completed_tracks
                total_eta_seconds = remaining_tracks * avg_time_per_track
                eta_str = str(datetime.timedelta(seconds=int(total_eta_seconds)))
                self.total_progress_label.configure(
                    text=f"Gesamtfortschritt: {percent}% | "
                         f"{self.completed_tracks}/{self.total_tracks} Titel | "
                         f"ETA: {eta_str}"
                )
            else:
                self.total_progress_label.configure(
                    text=f"Gesamtfortschritt: {percent}% | "
                         f"{self.completed_tracks}/{self.total_tracks} Titel | "
                         f"ETA: berechne..."
                )
        else:
            self.total_progress.set(0)
            self.total_progress_label.configure(text="Gesamtfortschritt: 0% | ETA: --:--:--")

    def load_thumbnail(self, url, title, index):
        """Lädt ein Thumbnail im Hintergrund und fügt es zur Liste hinzu"""
        try:
            if url in self.thumbnail_cache:
                self.root.after(0, self.add_thumbnail, self.thumbnail_cache[url], title, index)
                return
                
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            img = img.resize((120, 90), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Füge Thumbnail zur Liste hinzu
            self.root.after(0, self.add_thumbnail, photo, title, index)
            self.thumbnail_cache[url] = photo
            return photo
        except Exception as e:
            self.log(f"⚠️ Thumbnail-Fehler für '{title}': {e}")
            return None

    def add_thumbnail(self, photo, title, index):
        """Fügt ein Thumbnail zur Scrollable-Frame hinzu (im Hauptthread)"""
        if self.abort_event.is_set():
            return
            
        frame = ctk.CTkFrame(self.scrollable_frame, width=280, height=100)
        frame.grid_columnconfigure(1, weight=1)
        frame.pack(padx=5, pady=5, fill="x")
        
        label_img = ctk.CTkLabel(frame, image=photo, text="", width=120, height=90)
        label_img.image = photo  # Keep reference
        label_img.grid(row=0, column=0, padx=5, pady=5)
        
        label_title = ctk.CTkLabel(
            frame, 
            text=f"{index}. {title}",
            font=("Segoe UI", 11),
            anchor="w",
            wraplength=150
        )
        label_title.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Markiere aktuellen Frame
        if index == self.completed_tracks + 1:
            frame.configure(border_width=2, border_color="#2A8C55")
            self.current_thumbnail_frame = frame

    def download_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Fehler", "Bitte eine URL eingeben.")
            self.is_downloading = False
            return

        fmt = self.format_var.get()
        self.update_status_label("🔍 Analysiere URL...")
        self.log("🔍 Starte Analyse der URL...")
        self.progress_label.configure(text="Analysiere URL...")

        # Erweiterte Optionen für große Playlists
        playlist_opts = {
            'extract_flat': True,
            'playlistend': 10000,  # Bis zu 10.000 Titel
            'ignoreerrors': True,
            'quiet': True,
            'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None
        }

        # Korrigierte Optionen für Videoformate
        if fmt in self.codec_map:
            # Audio-Formate
            codec = self.codec_map[fmt]
            base_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': '192'
                }],
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.progress_hook]
            }
        else:
            # Video-Formate
            base_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': fmt,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': fmt
                }],
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.progress_hook]
            }

        try:
            # Step 1: Playlist-Informationen extrahieren
            with yt_dlp.YoutubeDL({**playlist_opts, 'logger': YTDLogger(self)}) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]
                
            self.total_tracks = len(entries)
            self.log(f"📂 {self.total_tracks} Titel gefunden.")
            self.progress_label.configure(text=f"{self.total_tracks} Titel gefunden")
            self.update_total_progress()

            # Step 2: Titel einzeln herunterladen
            for i, e in enumerate(entries, 1):
                if self.abort_event.is_set():
                    self.update_status_label("❌ Abgebrochen")
                    self.log("🛑 Der Download wurde abgebrochen.")
                    break

                title = e.get('title', f"Track {i}")
                link = e.get('url') or e.get('webpage_url', url)
                thumbnail = e.get('thumbnail') or e.get('thumbnails', [{}])[0].get('url') if isinstance(e.get('thumbnails'), list) else None

                # Thumbnail im Hintergrund laden
                if thumbnail:
                    self.thread_pool.submit(self.load_thumbnail, thumbnail, title, i)

                self.update_status_label(f"⬇️ Lade: {title} ({i}/{self.total_tracks})")
                self.log(f"⬇️ {i}/{self.total_tracks} – {title}")
                self.progress_label.configure(text=f"Lade Titel {i}/{self.total_tracks}")
                self.progress.set(0)
                self.convert_progress.set(0)
                self.convert_label.configure(text="Konvertierung: Wartend...")

                ydl_opts = {
                    **base_opts,
                    'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'ignoreerrors': True,
                    'noplaylist': True,
                    'logger': YTDLogger(self),
                    'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None
                }

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([link])
                    self.successful_downloads += 1
                    self.downloaded_tracks.append(title)
                except yt_dlp.utils.DownloadError as e:
                    if "Download abgebrochen" in str(e):
                        self.log(f"🛑 Download abgebrochen: {title}")
                        break
                    elif "Sign in to confirm you're not a bot" in str(e):
                        error_msg = (
                            "❌ YouTube verlangt Bestätigung, dass Sie kein Bot sind.\n\n"
                            "Bitte verwenden Sie die Cookies-Funktion:\n"
                            "1. Installieren Sie den 'Get Cookies.txt' Browser-Addon\n"
                            "2. Exportieren Sie Cookies von youtube.com\n"
                            "3. Wählen Sie die cookies.txt-Datei im Tool aus"
                        )
                        self.log(error_msg)
                        messagebox.showerror("YouTube Bot-Erkennung", error_msg)
                        break
                    else:
                        self.log(f"⚠️ Fehler beim Laden von {title}: {e}")
                except Exception as e:
                    self.log(f"⚠️ Unerwarteter Fehler beim Laden von {title}: {e}")
                finally:
                    self.completed_tracks = i
                    self.update_total_progress()

                if self.abort_event.is_set():
                    self.update_status_label("❌ Abgebrochen")
                    self.log("🛑 Der Download wurde abgebrochen.")
                    break

                # Pause zwischen Downloads, um Server nicht zu überlasten
                time.sleep(0.5)

        except Exception as e:
            self.update_status_label("❌ Fehler aufgetreten")
            self.progress_label.configure(text=f"Fehler: {str(e)[:50]}...")
            self.log(f"❌ Fehler beim Download: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Download:\n{e}")
        finally:
            self.format_combobox.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.download_button.configure(state="normal")
            self.is_downloading = False
            self.update_download_button_state()

        if not self.abort_event.is_set() and not any((self.abort_event.is_set(), "Fehler" in self.status_label.cget("text"))):
            self.update_status_label("✅ Download abgeschlossen!")
            self.progress_label.configure(text="Alle Downloads abgeschlossen")
            
            # Erfolgsstatistik anzeigen
            success_rate = (self.successful_downloads / self.total_tracks * 100) if self.total_tracks > 0 else 0
            self.log(f"🎉 Download abgeschlossen: {self.successful_downloads} von {self.total_tracks} Titeln erfolgreich geladen.")
            self.log(f"📊 Erfolgsrate: {success_rate:.1f}%")
            
            # Liste der heruntergeladenen Titel speichern
            list_path = os.path.join(self.download_folder, "download_list.txt")
            with open(list_path, 'w', encoding='utf-8') as f:
                for idx, title in enumerate(self.downloaded_tracks, 1):
                    f.write(f"{idx}. {title}\n")
            self.log(f"📝 Liste der heruntergeladenen Titel gespeichert: {list_path}")
            
            message = (
                f"Download abgeschlossen!\n\n"
                f"Erfolgreich geladene Titel: {self.successful_downloads} von {self.total_tracks}\n"
                f"Erfolgsrate: {success_rate:.1f}%\n\n"
                f"Eine Liste der Titel wurde gespeichert unter:\n{list_path}"
            )
            messagebox.showinfo("Fertig", message)

    def check_for_updates_gui(self):
        try:
            self.log("🔍 Suche nach Updates...")
            self.status_label.configure(text="🔍 Suche nach Updates...")
            r = requests.get(GITHUB_RELEASES_URL, timeout=10)
            r.raise_for_status()
            latest = r.json()
            ver = latest.get("tag_name", "").lstrip("v")
            if version.parse(ver) > version.parse(LOCAL_VERSION):
                self.log(f"⬆️ Neue Version verfügbar: {ver}")
                self.status_label.configure(text=f"⬆️ Update verfügbar: v{ver}")
                if messagebox.askyesno("Update verfügbar", f"Version {ver} verfügbar. Jetzt aktualisieren?"):
                    webbrowser.open(latest.get('html_url'))
            else:
                self.log("✅ Keine neue Version gefunden.")
                self.status_label.configure(text="✅ Aktuelle Version", text_color="lightgreen")
        except Exception as e:
            self.log(f"⚠️ Update-Fehler: {e}")
            self.status_label.configure(text="⚠️ Update-Prüfung fehlgeschlagen", text_color="#FF6B6B")


if __name__ == "__main__":
    root = ctk.CTk()
    app = DownloaderApp(root)
    
    # FFmpeg-Check in eigenem Thread starten
    def ffmpeg_check():
        if not check_ffmpeg_installed():
            if messagebox.askyesno("FFmpeg fehlt", "⚠️ FFmpeg ist nicht installiert. Möchten Sie es jetzt installieren?"):
                app.status_label.configure(text="🔧 Installiere FFmpeg...")
                success = install_ffmpeg(app.log)
                if success:
                    app.status_label.configure(text="✅ FFmpeg installiert", text_color="lightgreen")
                else:
                    app.status_label.configure(text="❌ FFmpeg-Installation fehlgeschlagen", text_color="#FF6B6B")
                    messagebox.showerror("Installation fehlgeschlagen", "❌ FFmpeg konnte nicht installiert werden. Bitte manuell installieren.")
            else:
                app.status_label.configure(text="⚠️ FFmpeg benötigt", text_color="orange")
                messagebox.showwarning("FFmpeg benötigt", "❗ Ohne FFmpeg funktioniert der Download nicht korrekt.")
    
    threading.Thread(target=ffmpeg_check, daemon=True).start()
    threading.Thread(target=app.check_for_updates_gui, daemon=True).start()
    
    root.mainloop()
