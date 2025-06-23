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
from PIL import Image, ImageTk, UnidentifiedImageError
from io import BytesIO
from tkinter import messagebox
import tkinter.filedialog as filedialog
from packaging import version
import time
import concurrent.futures
import datetime
import re
import glob
import mimetypes
import filetype
import locale
import gettext
import zipfile
import tempfile
import shutil
import traceback
from tkinter.scrolledtext import ScrolledText

# App-Konfiguration
APP_NAME = "SoundSync Downloader"
LOCAL_VERSION = "1.8.5"
GITHUB_REPO_URL = "https://github.com/Malionaro/Johann-Youtube-Soundcload"
GITHUB_API_URL = f"https://api.github.com/repos/Malionaro/Johann-Youtube-Soundcload/releases/latest"
CONFIG_PATH = "config.json"
os.environ["PATH"] += os.pathsep + "/usr/local/bin"

# Theme-Einstellungen
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Spracheinstellungen
SUPPORTED_LANGUAGES = ['en', 'de', 'pl']
DEFAULT_LANGUAGE = 'en'

# Versuche Systemsprache zu erkennen
try:
    system_lang = locale.getdefaultlocale()[0][:2]
    if system_lang not in SUPPORTED_LANGUAGES:
        system_lang = DEFAULT_LANGUAGE
except:
    system_lang = DEFAULT_LANGUAGE

# Sprachdateien laden
locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
lang_translations = {}

for lang in SUPPORTED_LANGUAGES:
    try:
        lang_translations[lang] = gettext.translation('app', localedir=locales_dir, languages=[lang])
    except:
        # Fallback: Englisch
        lang_translations[lang] = gettext.NullTranslations()

# Aktuelle Sprache setzen
current_language = system_lang
lang_translations[current_language].install()
_ = lang_translations[current_language].gettext

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
        log_func(_("✅ FFmpeg ist bereits installiert."))
        return True

    if platform.system() == "Windows":
        log_func(_("🔧 Starte FFmpeg-Installation über winget..."))
        try:
            subprocess.run(["winget", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            log_func(_("❌ Winget ist nicht verfügbar. Bitte FFmpeg manuell installieren."))
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
            log_func(_("✅ FFmpeg wurde erfolgreich installiert."))
            return True
        except subprocess.CalledProcessError as e:
            log_func(_("❌ Fehler bei der Installation von FFmpeg mit winget."))
            log_func(e.stderr)
            return False

    elif platform.system() == "Linux":
        log_func(_("🔧 Starte FFmpeg-Installation über apt..."))
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log_func(_("✅ FFmpeg wurde erfolgreich installiert."))
            return True
        except subprocess.CalledProcessError as e:
            log_func(_("❌ Fehler bei der Installation von FFmpeg unter Linux."))
            log_func(str(e))
            return False

    elif platform.system() == "Darwin":
        log_func(_("🔧 Starte FFmpeg-Installation ohne Homebrew..."))
        if shutil.which("ffmpeg"):
            log_func(_("✅ FFmpeg ist bereits installiert."))
            return True

        try:
            # Architektur-basierte Auswahl
            machine = platform.machine().lower()
            if machine in ["arm64", "x86_64"]:
                url = f"https://evermeet.cx/ffmpeg/ffmpeg-6.0.7z"
            else:
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            
            download_dir = "/tmp/ffmpeg"
            install_dir = "/usr/local/bin"
            os.makedirs(download_dir, exist_ok=True)

            log_func(_("⬇️ Lade FFmpeg herunter von {url}...").format(url=url))
            archive_path = os.path.join(download_dir, "ffmpeg.7z" if "evermeet" in url else "ffmpeg.tar.xz")
            urllib.request.urlretrieve(url, archive_path)
            log_func(_("✅ Download abgeschlossen."))

            log_func(_("🔧 Entpacke FFmpeg..."))
            if archive_path.endswith(".7z"):
                subprocess.run(["7z", "x", archive_path, f"-o{download_dir}"], check=True)
                extracted_bin = os.path.join(download_dir, "ffmpeg")
            else:
                with tarfile.open(archive_path, "r:xz") as archive:
                    archive.extractall(download_dir)
                # Binärdatei finden
                for root, dirs, files in os.walk(download_dir):
                    if "ffmpeg" in files:
                        extracted_bin = os.path.join(root, "ffmpeg")
                        break
            
            if not os.path.exists(extracted_bin):
                raise FileNotFoundError(_("FFmpeg-Binärdatei nach dem Entpacken nicht gefunden"))
                
            ffmpeg_dest = os.path.join(install_dir, "ffmpeg")
            log_func(_("🔧 Verschiebe FFmpeg nach {install_dir}...").format(install_dir=install_dir))
            shutil.move(extracted_bin, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)

            if shutil.which("ffmpeg"):
                log_func(_("✅ FFmpeg wurde erfolgreich installiert."))
                return True
            else:
                log_func(_("❌ FFmpeg konnte nicht in den PATH eingefügt werden."))
                return False

        except Exception as e:
            log_func(_("❌ Fehler bei der Installation von FFmpeg: {error}").format(error=str(e)))
            return False
    else:
        log_func(_("⚠️ Plattform nicht unterstützt."))
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

class ChangeLogWindow(ctk.CTkToplevel):
    def __init__(self, parent, changelog):
        super().__init__(parent)
        self.title(_("Änderungsprotokoll"))
        self.geometry("700x500")
        self.grab_set()
        
        # Hauptframe
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titel
        title = ctk.CTkLabel(
            main_frame,
            text=_("Neueste Änderungen"),
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=10)
        
        # Textbereich für Changelog
        self.text_area = ScrolledText(
            main_frame,
            wrap="word",
            font=("Consolas", 11),
            bg="#2C2C2C",
            fg="white"
        )
        self.text_area.pack(fill="both", expand=True, padx=10, pady=5)
        self.text_area.insert("1.0", changelog)
        self.text_area.configure(state="disabled")
        
        # Option zum Deaktivieren von Benachrichtigungen
        self.disable_var = ctk.BooleanVar(value=False)
        disable_check = ctk.CTkCheckBox(
            main_frame,
            text=_("Änderungsprotokolle nicht mehr anzeigen"),
            variable=self.disable_var
        )
        disable_check.pack(pady=10)
        
        # OK-Button
        ok_button = ctk.CTkButton(
            main_frame,
            text=_("OK"),
            command=self.destroy,
            width=100
        )
        ok_button.pack(pady=10)
        
        # Speichere die Option beim Schließen
        self.bind("<Destroy>", self.save_preference)
    
    def save_preference(self, event):
        if self.disable_var.get():
            # Speichere Präferenz in Konfigurationsdatei
            config = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, "r") as f:
                        config = json.load(f)
                except:
                    pass
            
            config["disable_changelog"] = True
            
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f)

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)
        
        # Farbpalette für Themes
        self.dark_colors = {
            "bg1": "#1E2A38",
            "bg2": "#253341",
            "bg3": "#1A2430",
            "text": "white",
            "accent1": "#2A8C55",
            "accent2": "#3A7EBF",
            "accent3": "#C74B4B",
            "accent1_hover": "#207244",
            "accent2_hover": "#2E6399",
            "accent3_hover": "#A03A3A",
            "progress1": "#3A7EBF",
            "progress2": "#2A8C55"
        }
        
        self.light_colors = {
            "bg1": "#F0F0F0",
            "bg2": "#E5E5E5",
            "bg3": "#D5D5D5",
            "text": "black",
            "accent1": "#2A8C55",
            "accent2": "#3A7EBF",
            "accent3": "#C74B4B",
            "accent1_hover": "#207244",
            "accent2_hover": "#2E6399",
            "accent3_hover": "#A03A3A",
            "progress1": "#3A7EBF",
            "progress2": "#2A8C55"
        }
        
        self.colors = self.dark_colors
        
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
        self.ydl_process = None
        self.language_var = ctk.StringVar(value=current_language)

        # Hauptlayout mit 2 Spalten
        self.root.grid_columnconfigure(0, weight=3)  # Hauptbereich
        self.root.grid_columnconfigure(1, weight=1)  # Sidebar
        self.root.grid_rowconfigure(1, weight=1)

        # Header mit Logo und Titel
        self.header_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # App-Logo (Platzhalter)
        self.logo_label = ctk.CTkLabel(
            self.header_frame, 
            text="🎵", 
            font=("Arial", 24),
            width=50
        )
        self.logo_label.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="w")
        
        # App-Titel
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold")
        )
        self.title_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Theme-Switch
        self.theme_switch = ctk.CTkSwitch(
            self.header_frame, 
            text=_("Dark Mode"),
            variable=self.dark_mode,
            command=self.toggle_theme,
            button_color="#2CC985",
            progress_color="#2CC985"
        )
        self.theme_switch.grid(row=0, column=2, padx=15, pady=10, sticky="e")
        
        # Sprachauswahl
        self.language_menu = ctk.CTkComboBox(
            self.header_frame,
            variable=self.language_var,
            values=[("English", "en"), ("Deutsch", "de"), ("Polski", "pl")],
            command=self.change_language,
            width=120
        )
        self.language_menu.grid(row=0, column=3, padx=10, pady=10, sticky="e")

        # Hauptbereich (linke Spalte)
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Einstellungen und Fortschritt
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        # URL-Eingabe
        self.url_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_label = ctk.CTkLabel(
            self.url_frame,
            text=_("YouTube oder SoundCloud URL:"),
            font=("Segoe UI", 12)
        )
        self.url_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.url_input_frame = ctk.CTkFrame(self.url_frame, fg_color="transparent")
        self.url_input_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.url_input_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self.url_input_frame,
            placeholder_text=_("https://www.youtube.com/... oder https://soundcloud.com/..."),
            font=("Segoe UI", 12),
            height=40
        )
        self.url_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        self.url_entry.bind("<KeyRelease>", self.update_download_button_state)

        self.clear_url_button = ctk.CTkButton(
            self.url_input_frame,
            text="X",
            command=self.clear_url,
            width=40,
            height=40,
            font=("Segoe UI", 11, "bold"),
            fg_color=self.colors["accent3"],
            hover_color=self.colors["accent3_hover"]
        )
        self.clear_url_button.grid(row=0, column=1, padx=0, pady=0)

        # Zielordner und Format in einer Zeile
        self.folder_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.folder_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.folder_frame.grid_columnconfigure(1, weight=1)

        self.folder_label = ctk.CTkLabel(
            self.folder_frame,
            text=_("Zielordner:"),
            font=("Segoe UI", 12)
        )
        self.folder_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.folder_entry = ctk.CTkEntry(
            self.folder_frame,
            placeholder_text=_("Wählen Sie einen Speicherort..."),
            font=("Segoe UI", 12)
        )
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.browse_button = ctk.CTkButton(
            self.folder_frame,
            text=_("Durchsuchen"),
            command=self.choose_folder,
            width=100,
            font=("Segoe UI", 11),
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.browse_button.grid(row=0, column=2, padx=(5, 10), pady=5)

        # Format und Cookies in einer Zeile
        self.format_cookies_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.format_cookies_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.format_cookies_frame.grid_columnconfigure(1, weight=1)

        self.format_label = ctk.CTkLabel(
            self.format_cookies_frame,
            text=_("Format:"),
            font=("Segoe UI", 12)
        )
        self.format_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        # Modernes Dropdown mit Read-Only-Funktion
        self.format_combobox = ctk.CTkComboBox(
            self.format_cookies_frame,
            variable=self.format_var,
            values=self.formate,
            state="readonly",
            width=140,
            font=("Segoe UI", 12),
            dropdown_fg_color=self.colors["bg3"],
            dropdown_hover_color=self.colors["accent2"],
            button_color=self.colors["accent1"],
            button_hover_color=self.colors["accent1_hover"],
            corner_radius=6,
            border_color=self.colors["accent2"],
            border_width=1,
            dropdown_font=("Segoe UI", 11)
        )
        self.format_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.format_combobox.set("mp3")

        self.cookies_label = ctk.CTkLabel(
            self.format_cookies_frame,
            text=_("Cookies:"),
            font=("Segoe UI", 12)
        )
        self.cookies_label.grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")

        self.cookies_entry = ctk.CTkEntry(
            self.format_cookies_frame,
            placeholder_text=_("Pfad zu cookies.txt"),
            font=("Segoe UI", 12),
            width=150
        )
        self.cookies_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        self.cookies_button = ctk.CTkButton(
            self.format_cookies_frame,
            text=_("Auswählen"),
            command=self.choose_cookies_file,
            width=100,
            font=("Segoe UI", 11)
        )
        self.cookies_button.grid(row=0, column=4, padx=(5, 10), pady=5)

        # Buttons
        self.button_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="group1")

        self.download_button = ctk.CTkButton(
            self.button_frame,
            text=_("Download starten"),
            command=self.start_download_thread,
            state="disabled",
            font=("Segoe UI", 12, "bold"),
            height=40,
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.download_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text=_("Abbrechen"),
            command=self.cancel_download,
            state="disabled",
            font=("Segoe UI", 12),
            height=40,
            fg_color=self.colors["accent3"],
            hover_color=self.colors["accent3_hover"]
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.update_button = ctk.CTkButton(
            self.button_frame,
            text=_("Auf Updates prüfen"),
            command=lambda: threading.Thread(target=self.check_for_updates_gui).start(),
            font=("Segoe UI", 12),
            height=40
        )
        self.update_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # Button für Konvertierung
        self.convert_button = ctk.CTkButton(
            self.button_frame,
            text=_("Datei konvertieren"),
            command=self.open_conversion_window,
            font=("Segoe UI", 12),
            height=40,
            fg_color="#9B59B6",  # Premium-Farbe
            hover_color="#8E44AD"  # Dunklere Premium-Farbe
        )
        self.convert_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Fortschrittsbalken
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame.grid_rowconfigure(0, weight=1)

        # Fortschritt für aktuellen Titel
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text=_("Bereit zum Starten"),
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.progress = ctk.CTkProgressBar(
            self.progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress1"]
        )
        self.progress.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.progress.set(0)

        # Konvertierungsfortschritt
        self.convert_label = ctk.CTkLabel(
            self.progress_frame,
            text=_("Konvertierung: Wartend..."),
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.convert_label.grid(row=2, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.convert_progress = ctk.CTkProgressBar(
            self.progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress1"]
        )
        self.convert_progress.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.convert_progress.set(0)

        # Gesamtfortschritt
        self.total_progress_label = ctk.CTkLabel(
            self.progress_frame,
            text=_("Gesamtfortschritt: 0% | ETA: --:--:--"),
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.total_progress_label.grid(row=4, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.total_progress = ctk.CTkProgressBar(
            self.progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress2"]
        )
        self.total_progress.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.total_progress.set(0)

        # Log-Ausgabe
        self.log_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.log_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        # Titelzeile für Log mit "Log leeren"-Button
        self.log_title_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        self.log_title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.log_title_frame.grid_columnconfigure(1, weight=1)

        self.log_title_label = ctk.CTkLabel(
            self.log_title_frame,
            text=_("Aktivitätsprotokoll:"),
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        self.log_title_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # "Log leeren"-Button oben rechts
        self.clear_log_button = ctk.CTkButton(
            self.log_title_frame,
            text=_("Log leeren"),
            command=self.clear_log,
            width=100,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.clear_log_button.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Log-Textbox
        self.log_output = ctk.CTkTextbox(
            self.log_frame,
            font=("Consolas", 11),
            wrap="word",
            activate_scrollbars=True
        )
        self.log_output.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_output.configure(state="disabled")

        # Sidebar (rechte Spalte)
        self.sidebar_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.sidebar_frame.grid(row=1, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        # Heruntergeladene Titel
        self.sidebar_title_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=_("Heruntergeladene Titel:"),
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        self.sidebar_title_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Scrollable Frame für Thumbnails
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            orientation="vertical",
            width=300
        )
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Scroll-Button am Boden
        self.scroll_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.scroll_button_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.scroll_button_frame.grid_columnconfigure(0, weight=1)

        self.scroll_to_current_button = ctk.CTkButton(
            self.scroll_button_frame,
            text=_("Zum aktuellen Titel scrollen"),
            command=self.scroll_to_current,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.scroll_to_current_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Statusbar
        self.statusbar = ctk.CTkFrame(self.root, height=30, corner_radius=0)
        self.statusbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 0))
        self.statusbar.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text=_("Bereit"),
            font=("Segoe UI", 11),
            text_color="lightgreen",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=(15, 5), pady=0, sticky="w")

        # GitHub-Link
        self.github_button = ctk.CTkButton(
            self.statusbar,
            text="GitHub",
            command=lambda: webbrowser.open(GITHUB_REPO_URL),
            width=70,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=self.colors["bg2"]
        )
        self.github_button.grid(row=0, column=1, padx=(0, 10), pady=0, sticky="e")

        self.version_label = ctk.CTkLabel(
            self.statusbar,
            text=_("Version: {version}").format(version=LOCAL_VERSION),
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
        
        # Theme initialisieren
        self.update_theme_colors()
        
        # Beim Start: Änderungsprotokoll anzeigen, wenn nicht deaktiviert
        self.show_changelog_on_start()

    def change_language(self, choice):
        """Wechselt die Sprache der Anwendung"""
        lang_code = choice.split(":")[1].strip() if ":" in choice else choice
        global current_language, _
        
        if lang_code in SUPPORTED_LANGUAGES:
            current_language = lang_code
            lang_translations[current_language].install()
            _ = lang_translations[current_language].gettext
            
            # GUI aktualisieren
            self.update_ui_texts()
            
            # Konfiguration speichern
            self.save_config()
            
            self.log(_("🌐 Sprache geändert zu: {language}").format(language=current_language))

    def update_ui_texts(self):
        """Aktualisiert alle Texte in der GUI nach Sprachwechsel"""
        # Header
        self.theme_switch.configure(text=_("Dark Mode"))
        self.title_label.configure(text=APP_NAME)
        
        # URL-Eingabe
        self.url_label.configure(text=_("YouTube oder SoundCloud URL:"))
        self.url_entry.configure(
            placeholder_text=_("https://www.youtube.com/... oder https://soundcloud.com/...")
        )
        
        # Zielordner
        self.folder_label.configure(text=_("Zielordner:"))
        self.folder_entry.configure(placeholder_text=_("Wählen Sie einen Speicherort..."))
        self.browse_button.configure(text=_("Durchsuchen"))
        
        # Format und Cookies
        self.format_label.configure(text=_("Format:"))
        self.cookies_label.configure(text=_("Cookies:"))
        self.cookies_entry.configure(placeholder_text=_("Pfad zu cookies.txt"))
        self.cookies_button.configure(text=_("Auswählen"))
        
        # Buttons
        self.download_button.configure(text=_("Download starten"))
        self.cancel_button.configure(text=_("Abbrechen"))
        self.update_button.configure(text=_("Auf Updates prüfen"))
        self.convert_button.configure(text=_("Datei konvertieren"))
        
        # Fortschrittsbalken
        self.progress_label.configure(text=_("Bereit zum Starten"))
        self.convert_label.configure(text=_("Konvertierung: Wartend..."))
        self.total_progress_label.configure(text=_("Gesamtfortschritt: 0% | ETA: --:--:--"))
        
        # Log
        self.log_title_label.configure(text=_("Aktivitätsprotokoll:"))
        self.clear_log_button.configure(text=_("Log leeren"))
        
        # Sidebar
        self.sidebar_title_label.configure(text=_("Heruntergeladene Titel:"))
        self.scroll_to_current_button.configure(text=_("Zum aktuellen Titel scrollen"))
        
        # Statusbar
        self.status_label.configure(text=_("Bereit"))
        self.version_label.configure(text=_("Version: {version}").format(version=LOCAL_VERSION))

    def show_changelog_on_start(self):
        """Zeigt das Änderungsprotokoll beim Start an, wenn nicht deaktiviert"""
        # Prüfen, ob Changelog deaktiviert wurde
        disable_changelog = False
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    disable_changelog = config.get("disable_changelog", False)
            except:
                pass
        
        if not disable_changelog:
            # Beispiel-Changelog - sollte durch echten Inhalt ersetzt werden
            changelog = _("""Version 1.8.5 - Änderungsprotokoll

Neue Funktionen:
- Sprachauswahl für Englisch, Deutsch und Polnisch
- Automatische Updates mit Fortschrittsanzeige
- Änderungsprotokoll beim ersten Start
- Option zum Deaktivieren von Benachrichtigungen

Verbesserungen:
- Verbesserte Fortschrittsanzeige für lange Downloads
- Universal-Konvertierungstool für alle Dateitypen
- Sofortiger Download-Abbruch

Fehlerbehebungen:
- Diverse Stabilitätsverbesserungen
- Behebung von Speicherlecks""")
            
            # Zeige Changelog nach kurzer Verzögerung
            self.root.after(1000, lambda: ChangeLogWindow(self.root, changelog))

    def update_theme_colors(self):
        """Aktualisiert die Farben basierend auf dem aktuellen Theme"""
        mode = "dark" if self.dark_mode.get() else "light"
        self.colors = self.dark_colors if mode == "dark" else self.light_colors
        
        # Hintergrundfarben
        bg_color = self.colors["bg1"]
        self.root.configure(fg_color=bg_color)
        self.header_frame.configure(fg_color=self.colors["bg2"])
        self.main_frame.configure(fg_color=bg_color)
        self.settings_frame.configure(fg_color=self.colors["bg2"])
        self.progress_frame.configure(fg_color=self.colors["bg2"])
        self.log_frame.configure(fg_color=self.colors["bg2"])
        self.sidebar_frame.configure(fg_color=self.colors["bg2"])
        self.statusbar.configure(fg_color=self.colors["bg3"])
        self.scrollable_frame.configure(fg_color=self.colors["bg3"])
        self.log_output.configure(fg_color=self.colors["bg3"])
        
        # Buttons
        self.clear_url_button.configure(
            fg_color=self.colors["accent3"], 
            hover_color=self.colors["accent3_hover"]
        )
        self.browse_button.configure(
            fg_color=self.colors["accent1"], 
            hover_color=self.colors["accent1_hover"]
        )
        self.download_button.configure(
            fg_color=self.colors["accent1"], 
            hover_color=self.colors["accent1_hover"]
        )
        self.cancel_button.configure(
            fg_color=self.colors["accent3"], 
            hover_color=self.colors["accent3_hover"]
        )
        self.clear_log_button.configure(
            fg_color=self.colors["accent2"], 
            hover_color=self.colors["accent2_hover"]
        )
        self.scroll_to_current_button.configure(
            fg_color=self.colors["accent2"], 
            hover_color=self.colors["accent2_hover"]
        )
        self.format_combobox.configure(
            dropdown_fg_color=self.colors["bg3"],
            dropdown_hover_color=self.colors["accent2"],
            button_color=self.colors["accent1"],
            button_hover_color=self.colors["accent1_hover"],
            border_color=self.colors["accent2"]
        )
        self.convert_button.configure(
            fg_color="#9B59B6",
            hover_color="#8E44AD"
        )
        
        # Fortschrittsbalken
        self.progress.configure(progress_color=self.colors["progress1"])
        self.convert_progress.configure(progress_color=self.colors["progress1"])
        self.total_progress.configure(progress_color=self.colors["progress2"])
        
        # Textfarben anpassen
        text_color = self.colors["text"]
        self.url_label.configure(text_color=text_color)
        self.folder_label.configure(text_color=text_color)
        self.format_label.configure(text_color=text_color)
        self.cookies_label.configure(text_color=text_color)
        self.progress_label.configure(text_color=text_color)
        self.convert_label.configure(text_color=text_color)
        self.total_progress_label.configure(text_color=text_color)
        self.log_title_label.configure(text_color=text_color)
        self.sidebar_title_label.configure(text_color=text_color)
        self.title_label.configure(text_color=text_color)
        self.version_label.configure(text_color=text_color)
        self.log_output.configure(text_color=text_color)
        
        # Statusleiste
        status_color = "lightgreen" if mode == "dark" else "green"
        self.status_label.configure(text_color=status_color)
        self.github_button.configure(hover_color=self.colors["bg2"])

    def toggle_theme(self):
        mode = "dark" if self.dark_mode.get() else "light"
        ctk.set_appearance_mode(mode)
        self.update_theme_colors()

    def cleanup_temp_files(self):
        """Löscht temporäre Dateien im Download-Verzeichnis"""
        temp_extensions = ['.part', '.tmp', '.ytdl']
        deleted = 0
        
        for root, dirs, files in os.walk(self.download_folder):
            for file in files:
                if any(file.endswith(ext) for ext in temp_extensions):
                    try:
                        os.remove(os.path.join(root, file))
                        deleted += 1
                    except Exception as e:
                        self.log(_("⚠️ Konnte temporäre Datei nicht löschen: {file} - {error}").format(file=file, error=e))
        
        if deleted > 0:
            self.log(_("🧹 {count} temporäre Dateien gelöscht").format(count=deleted))

    def load_download_folder(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    self.cookies_path = config.get("cookies_path", "")
                    self.cookies_entry.insert(0, self.cookies_path)
                    
                    # Sprachkonfiguration laden
                    lang = config.get("language", system_lang)
                    if lang in SUPPORTED_LANGUAGES:
                        self.language_var.set(lang)
                        self.change_language(lang)
                    
                    return config.get("download_folder")
            except:
                pass
        return None

    def save_config(self):
        config = {
            "download_folder": self.download_folder,
            "cookies_path": self.cookies_path,
            "language": current_language
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder, title=_("Wählen Sie einen Zielordner"))
        if folder:
            self.download_folder = folder
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.save_config()
            self.log(_("✅ Zielordner gesetzt: {folder}").format(folder=folder))
            self.update_download_button_state()

    def choose_cookies_file(self):
        file_path = filedialog.askopenfilename(
            title=_("Wählen Sie eine Cookies-Datei"),
            filetypes=[(_("Textdateien"), "*.txt"), (_("Alle Dateien"), "*.*")]
        )
        if file_path:
            self.cookies_path = file_path
            self.cookies_entry.delete(0, "end")
            self.cookies_entry.insert(0, file_path)
            self.save_config()
            self.log(_("🍪 Cookies-Datei ausgewählt: {file}").format(file=file_path))

    def update_download_button_state(self, event=None):
        url_filled = bool(self.url_entry.get().strip())
        folder_selected = bool(self.download_folder and os.path.isdir(self.download_folder))
        state = "normal" if url_filled and folder_selected and not self.is_downloading else "disabled"
        self.download_button.configure(state=state)

    def clear_url(self):
        self.url_entry.delete(0, "end")
        self.log(_("🧹 URL-Feld wurde geleert."))
        self.update_download_button_state()

    def clear_log(self):
        self.log_output.configure(state="normal")
        self.log_output.delete("1.0", "end")
        self.log_output.configure(state="disabled")
        self.log(_("🧹 Log wurde geleert."))

    def log(self, message):
        self.log_output.configure(state="normal")
        self.log_output.insert("end", message + "\n")
        self.log_output.see("end")
        self.log_output.configure(state="disabled")

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror(_("Fehler"), _("Bitte eine URL eingeben."))
            self.is_downloading = False
            return

        fmt = self.format_var.get()
        self.update_status_label(_("🔍 Analysiere URL..."))
        self.log(_("🔍 Starte Analyse der URL..."))
        self.progress_label.configure(text=_("Analysiere URL..."))
        self.progress.configure(mode="determinate")  # Standardmodus setzen

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
            self.log(_("📂 {count} Titel gefunden.").format(count=self.total_tracks))
            self.progress_label.configure(text=_("{count} Titel gefunden").format(count=self.total_tracks))
            self.update_total_progress()

            # Step 2: Titel einzeln herunterladen
            for i, e in enumerate(entries, 1):
                if self.abort_event.is_set():
                    self.update_status_label(_("❌ Abgebrochen"))
                    self.log(_("🛑 Der Download wurde abgebrochen."))
                    break

                title = e.get('title', _("Track {number}").format(number=i))
                link = e.get('url') or e.get('webpage_url', url)
                thumbnail = e.get('thumbnail') or e.get('thumbnails', [{}])[0].get('url') if isinstance(e.get('thumbnails'), list) else None

                # Thumbnail im Hintergrund laden
                if thumbnail:
                    self.thread_pool.submit(self.load_thumbnail, thumbnail, title, i)

                self.update_status_label(_("⬇️ Lade: {title} ({current}/{total})").format(
                    title=title, current=i, total=self.total_tracks))
                self.log(_("⬇️ {current}/{total} – {title}").format(
                    current=i, total=self.total_tracks, title=title))
                self.progress_label.configure(text=_("Lade Titel {current}/{total}").format(
                    current=i, total=self.total_tracks))
                self.progress.set(0)
                self.convert_progress.set(0)
                self.convert_label.configure(text=_("Konvertierung: Wartend..."))

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
                    if _("Download abgebrochen") in str(e):
                        self.log(_("🛑 Download abgebrochen: {title}").format(title=title))
                        break
                    elif "Sign in to confirm you're not a bot" in str(e):
                        error_msg = _(
                            "❌ YouTube verlangt Bestätigung, dass Sie kein Bot sind.\n\n"
                            "Bitte verwenden Sie die Cookies-Funktion:\n"
                            "1. Installieren Sie den 'Get Cookies.txt' Browser-Addon\n"
                            "2. Exportieren Sie Cookies von youtube.com\n"
                            "3. Wählen Sie die cookies.txt-Datei im Tool aus"
                        )
                        self.log(error_msg)
                        messagebox.showerror(_("YouTube Bot-Erkennung"), error_msg)
                        break
                    else:
                        self.log(_("⚠️ Fehler beim Laden von {title}: {error}").format(title=title, error=e))
                except Exception as e:
                    self.log(_("⚠️ Unerwarteter Fehler beim Laden von {title}: {error}").format(title=title, error=e))
                finally:
                    self.completed_tracks = i
                    self.update_total_progress()

                if self.abort_event.is_set():
                    self.update_status_label(_("❌ Abgebrochen"))
                    self.log(_("🛑 Der Download wurde abgebrochen."))
                    break

                # Pause zwischen Downloads, um Server nicht zu überlasten
                time.sleep(0.5)

        except Exception as e:
            self.update_status_label(_("❌ Fehler aufgetreten"))
            self.progress_label.configure(text=_("Fehler: {error}...").format(error=str(e)[:50]))
            self.log(_("❌ Fehler beim Download: {error}").format(error=e))
            messagebox.showerror(_("Fehler"), _("Fehler beim Download:\n{error}").format(error=e))
        finally:
            self.format_combobox.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            self.download_button.configure(state="normal")
            self.is_downloading = False
            self.update_download_button_state()

            # Bereinige temporäre Dateien nach Abbruch
            if self.abort_event.is_set():
                self.cleanup_temp_files()

        if not self.abort_event.is_set() and not any((self.abort_event.is_set(), "Fehler" in self.status_label.cget("text"))):
            self.update_status_label(_("✅ Download abgeschlossen!"))
            self.progress_label.configure(text=_("Alle Downloads abgeschlossen"))
            
            # Erfolgsstatistik anzeigen
            success_rate = (self.successful_downloads / self.total_tracks * 100) if self.total_tracks > 0 else 0
            self.log(_("🎉 Download abgeschlossen: {success} von {total} Titeln erfolgreich geladen.").format(
                success=self.successful_downloads, total=self.total_tracks))
            self.log(_("📊 Erfolgsrate: {rate:.1f}%").format(rate=success_rate))
            
            # Liste der heruntergeladenen Titel speichern
            list_path = os.path.join(self.download_folder, "download_list.txt")
            with open(list_path, 'w', encoding='utf-8') as f:
                for idx, title in enumerate(self.downloaded_tracks, 1):
                    f.write(f"{idx}. {title}\n")
            self.log(_("📝 Liste der heruntergeladenen Titel gespeichert: {path}").format(path=list_path))
            
            message = _(
                "Download abgeschlossen!\n\n"
                "Erfolgreich geladene Titel: {success} von {total}\n"
                "Erfolgsrate: {rate:.1f}%\n\n"
                "Eine Liste der Titel wurde gespeichert unter:\n{path}"
            ).format(success=self.successful_downloads, total=self.total_tracks, rate=success_rate, path=list_path)
            messagebox.showinfo(_("Fertig"), message)
            
            # Bereinige temporäre Dateien nach Abschluss
            self.cleanup_temp_files()

    def progress_hook(self, d):
        if self.abort_event.is_set():
            raise yt_dlp.utils.DownloadError(_("Download abgebrochen"))
            
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                # Bestimmter Modus
                self.progress.configure(mode="determinate")
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
                    self.progress_label.configure(text=_("Fortschritt: {percent}% | Geschw: {speed} | ETA: {eta}").format(
                        percent=percent, speed=self.format_speed(self.current_speed), eta=eta_str))
                else:
                    self.progress_label.configure(text=_("Fortschritt: {percent}% | Geschw: berechne...").format(percent=percent))
            else:
                # Unbestimmter Modus
                self.progress.configure(mode="indeterminate")
                self.progress.start()
                # Geschwindigkeitsberechnung nur mit heruntergeladenen Bytes
                if time_diff > 0.5:
                    downloaded_diff = downloaded - self.last_downloaded_bytes
                    self.current_speed = downloaded_diff / time_diff
                    self.last_downloaded_bytes = downloaded
                    self.last_update_time = current_time
                    self.progress_label.configure(text=_("Läuft... | Geschw: {speed}").format(speed=self.format_speed(self.current_speed)))
            
        elif d['status'] == 'finished':
            self.progress.set(1.0)
            self.progress_label.configure(text=_("✅ Download abgeschlossen"))
            self.log(_("✅ Download abgeschlossen."))
            # Falls unbestimmt, zurück zu bestimmt und anhalten
            if self.progress.cget("mode") == "indeterminate":
                self.progress.stop()
                self.progress.configure(mode="determinate")
        
        # Post-Processing Fortschritt
        if d.get('postprocessor') and d.get('postprocessor') in ['FFmpegExtractAudio', 'FFmpegVideoConvertor']:
            # Extrahiere den Dateinamen für die Anzeige
            filename = d.get('info_dict', {}).get('filepath', _('Unbekannte Datei'))
            if filename:
                # Kürze den Dateinamen für die Anzeige
                short_filename = os.path.basename(filename)
                self.convert_label.configure(text=_("Konvertierung: {file}").format(file=short_filename))
            
            # Fortschrittsbalken aktualisieren
            if d.get('postprocessor_progress') is not None:
                progress = d['postprocessor_progress']
                self.convert_progress.set(progress)
                
                # Bei Abschluss auf 100% setzen
                if d['status'] == 'finished':
                    self.convert_progress.set(1.0)
                    self.convert_label.configure(text=_("✅ Konvertierung abgeschlossen"))

    def format_speed(self, speed_bytes):
        """Formatiert Geschwindigkeit in lesbare Einheiten"""
        if speed_bytes < 1024:
            return _("{bytes:.1f} B/s").format(bytes=speed_bytes)
        elif speed_bytes < 1024 * 1024:
            return _("{kb:.1f} KB/s").format(kb=speed_bytes / 1024)
        else:
            return _("{mb:.1f} MB/s").format(mb=speed_bytes / (1024 * 1024))

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
                    text=_("Gesamtfortschritt: {percent}% | {completed}/{total} Titel | ETA: {eta}").format(
                        percent=percent, completed=self.completed_tracks, total=self.total_tracks, eta=eta_str)
                )
            else:
                self.total_progress_label.configure(
                    text=_("Gesamtfortschritt: {percent}% | {completed}/{total} Titel | ETA: berechne...").format(
                        percent=percent, completed=self.completed_tracks, total=self.total_tracks)
                )
        else:
            self.total_progress.set(0)
            self.total_progress_label.configure(text=_("Gesamtfortschritt: 0% | ETA: --:--:--"))

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
            self.log(_("⚠️ Thumbnail-Fehler für '{title}': {error}").format(title=title, error=e))
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

    def cancel_download(self):
        """Verbesserte Abbruchfunktion, die sofort stoppt"""
        if self.is_downloading:
            if messagebox.askyesno(_("Download abbrechen"), _("Möchten Sie den aktuellen Download wirklich abbrechen?"), icon="warning"):
                # Stoppt alle Threads und Prozesse sofort
                self.abort_event.set()
                self.is_downloading = False
                
                # Beendet den yt-dlp Prozess gewaltsam
                if self.ydl_process:
                    try:
                        self.ydl_process.terminate()
                        self.log(_("🔴 Prozess wurde gewaltsam beendet."))
                    except:
                        pass
                
                self.log(_("🛑 Download sofort abgebrochen"))
                self.status_label.configure(text=_("❌ Abgebrochen"), text_color="#FF6B6B")
                self.cancel_button.configure(state="disabled")
                self.cleanup_temp_files()
        else:
            self.log(_("ℹ️ Es läuft kein Download, der abgebrochen werden könnte."))

    def scroll_to_current(self):
        if self.current_thumbnail_frame:
            self.scrollable_frame._parent_canvas.yview_moveto(1.0)
            
    def open_conversion_window(self):
        """Öffnet das Premium-Konvertierungsfenster"""
        ConversionWindow(self.root, self.download_folder)

    def check_for_updates_gui(self, auto_check=False):
        try:
            if not auto_check:
                self.log(_("🔍 Suche nach Updates..."))
                self.status_label.configure(text=_("🔍 Suche nach Updates..."))
            
            # Setze User-Agent Header, da GitHub dies erfordert
            headers = {
                "User-Agent": "SoundSync-Downloader"
            }
            
            r = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            r.raise_for_status()
            
            # Versuche, die Antwort als JSON zu interpretieren
            try:
                latest = r.json()
            except json.JSONDecodeError:
                self.log(_("⚠️ Ungültige JSON-Antwort: {text}...").format(text=r.text[:100]))
                if not auto_check:
                    self.status_label.configure(text=_("⚠️ Update-Prüfung fehlgeschlagen"), text_color="#FF6B6B")
                return
                
            ver = latest.get("tag_name", "").lstrip("v")
            
            # Version aus Tag extrahieren
            version_match = re.search(r'\d+\.\d+\.\d+', ver)
            if not version_match:
                self.log(_("⚠️ Keine gültige Version gefunden"))
                if not auto_check:
                    self.status_label.configure(text=_("⚠️ Update-Prüfung fehlgeschlagen"), text_color="#FF6B6B")
                return
                
            ver = version_match.group(0)
            
            if version.parse(ver) > version.parse(LOCAL_VERSION):
                self.log(_("⬆️ Neue Version verfügbar: {version}").format(version=ver))
                self.status_label.configure(text=_("⬆️ Update verfügbar: v{version}").format(version=ver), text_color="#FFD700")
                
                if not auto_check or messagebox.askyesno(
                    _("Update verfügbar"), 
                    _("Version {version} verfügbar. Jetzt herunterladen?").format(version=ver),
                    icon="question"
                ):
                    self.download_update(latest)
            else:
                if not auto_check:
                    self.log(_("✅ Keine neue Version gefunden."))
                    self.status_label.configure(text=_("✅ Aktuelle Version"), text_color="lightgreen")
        except requests.exceptions.RequestException as e:
            self.log(_("⚠️ Netzwerkfehler bei Update-Prüfung: {error}").format(error=e))
            if not auto_check:
                self.status_label.configure(text=_("⚠️ Update-Prüfung fehlgeschlagen"), text_color="#FF6B6B")
        except Exception as e:
            self.log(_("⚠️ Update-Fehler: {error}").format(error=e))
            if not auto_check:
                self.status_label.configure(text=_("⚠️ Update-Prüfung fehlgeschlagen"), text_color="#FF6B6B")

    def download_update(self, release_info):
        """Lädt das Update herunter und installiert es"""
        # Finde die richtige Asset-Datei (z.B. .exe für Windows)
        asset = None
        for a in release_info.get('assets', []):
            if "win" in a['name'].lower() and "exe" in a['name'].lower():
                asset = a
                break
            elif "linux" in a['name'].lower() and "tar" in a['name'].lower():
                asset = a
                break
            elif "mac" in a['name'].lower() and "dmg" in a['name'].lower():
                asset = a
                break
        
        if not asset:
            self.log(_("❌ Keine passende Installationsdatei gefunden"))
            messagebox.showerror(_("Fehler"), _("Keine passende Installationsdatei für dieses System gefunden."))
            return
        
        download_url = asset['browser_download_url']
        self.log(_("⬇️ Lade Update herunter von: {url}").format(url=download_url))
        
        # Öffne das Update-Fenster
        UpdateWindow(self.root, download_url)

class UpdateWindow(ctk.CTkToplevel):
    def __init__(self, parent, download_url):
        super().__init__(parent)
        self.title(_("Update wird installiert"))
        self.geometry("600x400")
        self.download_url = download_url
        self.grab_set()
        
        # Hauptframe
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Titel
        title = ctk.CTkLabel(
            main_frame,
            text=_("Software-Update"),
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=10)
        
        # Statusanzeige
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=_("Vorbereitung..."),
            font=("Segoe UI", 12)
        )
        self.status_label.pack(pady=5)
        
        # Fortschrittsbalken
        self.progress = ctk.CTkProgressBar(
            main_frame,
            mode="determinate",
            height=20,
            width=500
        )
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        # Debug-Konsole
        self.console = ctk.CTkTextbox(
            main_frame,
            font=("Consolas", 10),
            wrap="word",
            height=200
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=10)
        self.console.configure(state="disabled")
        
        # Starte den Download im Hintergrund
        threading.Thread(target=self.download_and_install, daemon=True).start()
    
    def log(self, message):
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")
    
    def download_and_install(self):
        try:
            # Temporäres Verzeichnis erstellen
            temp_dir = tempfile.mkdtemp()
            download_path = os.path.join(temp_dir, "update_package")
            
            if platform.system() == "Windows":
                download_path += ".exe"
            elif platform.system() == "Darwin":
                download_path += ".dmg"
            else:
                download_path += ".tar.gz"
            
            # Download starten
            self.status_label.configure(text=_("Lade Update herunter..."))
            self.log(_("⬇️ Starte Download von: {}").format(self.download_url))
            
            with requests.get(self.download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Fortschritt aktualisieren
                            progress = downloaded / total_size
                            self.progress.set(progress)
                            self.log(_("⬇️ Heruntergeladen: {downloaded}/{total} Bytes ({percent:.1%})").format(
                                downloaded=downloaded, total=total_size, percent=progress))
            
            self.log(_("✅ Download abgeschlossen"))
            self.status_label.configure(text=_("Installiere Update..."))
            
            # Installationsprozess starten
            if platform.system() == "Windows":
                # Für Windows: EXE-Datei ausführen
                self.log(_("🔧 Starte Installationsprogramm..."))
                subprocess.Popen([download_path], shell=True)
                
                # Beende die aktuelle Anwendung
                self.log(_("🔄 Beende Anwendung für Update..."))
                self.master.destroy()
                
            elif platform.system() == "Darwin":
                # Für macOS: DMG einhängen und Anwendung kopieren
                self.log(_("🔧 Installiere auf macOS..."))
                # Hier müsste der spezifische Installationscode für macOS stehen
                self.log(_("❌ macOS-Installation noch nicht implementiert"))
                self.status_label.configure(text=_("Fehler: Nicht implementiert"))
                
            else:
                # Für Linux: Archiv entpacken
                self.log(_("🔧 Installiere auf Linux..."))
                # Hier müsste der spezifische Installationscode für Linux stehen
                self.log(_("❌ Linux-Installation noch nicht implementiert"))
                self.status_label.configure(text=_("Fehler: Nicht implementiert"))
            
        except Exception as e:
            self.log(_("�️ Fehler bei der Update-Installation: {}").format(str(e)))
            self.log(traceback.format_exc())
            self.status_label.configure(text=_("Fehler bei der Installation"))

class ConversionWindow(ctk.CTkToplevel):
    def __init__(self, parent, download_folder):
        super().__init__(parent)
        self.title(_("Premium Konvertierung"))
        self.geometry("600x450")
        self.download_folder = download_folder
        self.grab_set()  # Modal-Fenster
        self.file_path = ""
        
        # Premium-Farben
        self.premium_colors = {
            "bg": "#2C3E50",
            "button": "#9B59B6",
            "button_hover": "#8E44AD",
            "text": "#ECF0F1"
        }
        
        self.configure(fg_color=self.premium_colors["bg"])
        
        # Hauptframe
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Titel
        title = ctk.CTkLabel(
            main_frame,
            text=_("🔧 Premium Dateikonvertierung"),
            font=("Segoe UI", 16, "bold"),
            text_color="#F1C40F"
        )
        title.pack(pady=(0, 20))
        
        # Dateiauswahl
        file_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        file_frame.pack(fill="x", pady=5)
        
        self.file_label = ctk.CTkLabel(
            file_frame,
            text=_("Datei auswählen:"),
            font=("Segoe UI", 12),
            width=100
        )
        self.file_label.grid(row=0, column=0, padx=5)
        
        self.file_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text=_("Wählen Sie eine Datei..."),
            font=("Segoe UI", 12),
            width=300
        )
        self.file_entry.grid(row=0, column=1, padx=5)
        
        self.browse_button = ctk.CTkButton(
            file_frame,
            text=_("Durchsuchen"),
            command=self.choose_file,
            width=100,
            fg_color=self.premium_colors["button"],
            hover_color=self.premium_colors["button_hover"]
        )
        self.browse_button.grid(row=0, column=2, padx=5)
        
        # Format-Auswahl
        format_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        format_frame.pack(fill="x", pady=5)
        
        format_label = ctk.CTkLabel(
            format_frame,
            text=_("Zielformat:"),
            font=("Segoe UI", 12),
            width=100
        )
        format_label.grid(row=0, column=0, padx=5)
        
        self.format_var = ctk.StringVar(value="mp3")
        self.format_menu = ctk.CTkComboBox(
            format_frame,
            variable=self.format_var,
            values=[
                "mp3", "wav", "flac", "m4a", "ogg", "aac", 
                "mp4", "avi", "mov", "mkv", "flv",
                "jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp",
                "pdf", "docx", "pptx", "xlsx", "txt", "html"
            ],
            state="readonly",
            width=150,
            fg_color=self.premium_colors["bg"],
            button_color=self.premium_colors["button"],
            button_hover_color=self.premium_colors["button_hover"]
        )
        self.format_menu.grid(row=0, column=1, padx=5)
        
        # Konvertierungsoptionen
        options_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=10)
        
        self.quality_var = ctk.StringVar(value=_("Hoch"))
        quality_label = ctk.CTkLabel(
            options_frame,
            text=_("Qualität:"),
            font=("Segoe UI", 12),
            width=100
        )
        quality_label.grid(row=0, column=0, padx=5)
        
        quality_menu = ctk.CTkComboBox(
            options_frame,
            variable=self.quality_var,
            values=[_("Niedrig"), _("Mittel"), _("Hoch"), _("Maximal")],
            state="readonly",
            width=150,
            fg_color=self.premium_colors["bg"],
            button_color=self.premium_colors["button"],
            button_hover_color=self.premium_colors["button_hover"]
        )
        quality_menu.grid(row=0, column=1, padx=5)
        
        # Konvertierungsbutton
        convert_button = ctk.CTkButton(
            main_frame,
            text=_("Konvertierung starten"),
            command=self.start_conversion,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=self.premium_colors["button"],
            hover_color=self.premium_colors["button_hover"]
        )
        convert_button.pack(pady=20)
        
        # Statusanzeige
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=_("Bereit zur Konvertierung"),
            font=("Segoe UI", 11),
            text_color="#2ECC71"
        )
        self.status_label.pack(pady=10)
        
        # Fortschrittsbalken
        self.progress = ctk.CTkProgressBar(
            main_frame,
            mode="indeterminate",
            height=20,
            width=500,
            progress_color="#3498DB"
        )
        
        # Info-Label für Premium-Features
        info_label = ctk.CTkLabel(
            main_frame,
            text=_("ℹ️ Hochwertige Konvertierung mit erhaltener Qualität"),
            font=("Segoe UI", 10),
            text_color="#BDC3C7"
        )
        info_label.pack(pady=10)

    def choose_file(self):
        """Datei für Konvertierung auswählen"""
        file_path = filedialog.askopenfilename(
            initialdir=self.download_folder,
            title=_("Datei auswählen"),
            filetypes=[(_("Alle Dateien"), "*.*")]
        )
        
        if file_path:
            self.file_path = file_path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            
            # Versuche den Dateityp zu erkennen
            try:
                file_type = filetype.guess(file_path)
                if file_type is None:
                    file_type = _("Unbekannter Typ")
                else:
                    file_type = file_type.mime
            except Exception:
                file_type = _("Unbekannter Typ")
            
            self.status_label.configure(
                text=_("Datei ausgewählt: {file} ({type})").format(file=os.path.basename(file_path), type=file_type),
                text_color="#2ECC71"
            )

    def start_conversion(self):
        """Startet die Konvertierung in einem eigenen Thread"""
        if not self.file_path or not os.path.exists(self.file_path):
            messagebox.showerror(_("Fehler"), _("Bitte wählen Sie eine gültige Datei aus."))
            return
            
        threading.Thread(target=self.convert_file, daemon=True).start()

    def convert_file(self):
        """Führt die Dateikonvertierung durch"""
        try:
            self.progress.pack(pady=10)
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self.status_label.configure(text=_("Konvertierung läuft..."), text_color="#3498DB")
            
            # Dateinamen vorbereiten
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            target_format = self.format_var.get()
            output_path = os.path.join(
                os.path.dirname(self.file_path),
                f"{base_name}_konvertiert.{target_format}"
            )
            
            # Qualitätseinstellungen
            quality = self.quality_var.get()
            quality_args = []
            
            if quality == _("Niedrig"):
                quality_args = ["-compression_level", "1"]
            elif quality == _("Mittel"):
                quality_args = ["-compression_level", "5"]
            elif quality == _("Hoch"):
                quality_args = ["-compression_level", "8"]
            elif quality == _("Maximal"):
                quality_args = ["-compression_level", "12"]
            
            # FFmpeg-Kommando erstellen
            cmd = [
                'ffmpeg', 
                '-i', self.file_path,
                '-y'  # Überschreiben ohne Nachfrage
            ] + quality_args + [output_path]
            
            # Prozess ausführen
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Wir können den Fortschritt nicht verfolgen, also warten wir einfach
            process.communicate()
            
            if process.returncode == 0:
                self.status_label.configure(
                    text=_("✅ Konvertierung abgeschlossen: {file}").format(file=os.path.basename(output_path)),
                    text_color="#2ECC71"
                )
                messagebox.showinfo(
                    _("Konvertierung erfolgreich"),
                    _("Datei wurde erfolgreich konvertiert:\n{path}").format(path=output_path)
                )
            else:
                self.status_label.configure(
                    text=_("❌ Konvertierung fehlgeschlagen"),
                    text_color="#E74C3C"
                )
                messagebox.showerror(
                    _("Fehler"),
                    _("Konvertierung fehlgeschlagen. Bitte überprüfen Sie die Datei und das Format.")
                )
        except Exception as e:
            self.status_label.configure(
                text=_("❌ Fehler: {error}").format(error=str(e)),
                text_color="#E74C3C"
            )
        finally:
            self.progress.stop()
            self.progress.pack_forget()

if __name__ == "__main__":
    root = ctk.CTk()
    app = DownloaderApp(root)
    
    # FFmpeg-Check in eigenem Thread starten
    def ffmpeg_check():
        if not check_ffmpeg_installed():
            if messagebox.askyesno(_("FFmpeg fehlt"), _("⚠️ FFmpeg ist nicht installiert. Möchten Sie es jetzt installieren?")):
                app.status_label.configure(text=_("🔧 Installiere FFmpeg..."))
                success = install_ffmpeg(app.log)
                if success:
                    app.status_label.configure(text=_("✅ FFmpeg installiert"), text_color="lightgreen")
                else:
                    app.status_label.configure(text=_("❌ FFmpeg-Installation fehlgeschlagen"), text_color="#FF6B6B")
                    messagebox.showerror(_("Installation fehlgeschlagen"), _("❌ FFmpeg konnte nicht installiert werden. Bitte manuell installieren."))
            else:
                app.status_label.configure(text=_("⚠️ FFmpeg benötigt"), text_color="orange")
                messagebox.showwarning(_("FFmpeg benötigt"), _("❗ Ohne FFmpeg funktioniert der Download nicht korrekt."))
    
    threading.Thread(target=ffmpeg_check, daemon=True).start()
    
    # Automatische Update-Prüfung beim Start
    threading.Thread(target=lambda: app.check_for_updates_gui(auto_check=True), daemon=True).start()
    
    root.mainloop()