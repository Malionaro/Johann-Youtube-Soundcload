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

# App-Konfiguration
APP_NAME = "SoundSync Downloader"
LOCAL_VERSION = "1.8"
GITHUB_RELEASES_URL = "https://api.github.com/repos/Malionaro/Johann-Youtube-Soundcload/releases/latest"
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
        self.root.geometry("1000x977")
        self.root.minsize(900, 750)
        
        # Icon setzen
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        
        # Mapping für Audio-Codecs
        self.codec_map = {
            "mp3": "mp3", "m4a": "m4a", "wav": "wav", "flac": "flac", "aac": "aac",
            "ogg": "vorbis", "opus": "opus", "wma": "wma", "alac": "alac", "aiff": "aiff", "mp2": "mp2"
        }
        self.formate = [*self.codec_map.keys(), "mp4", "webm", "mkv", "avi", "mov", "flv", "3gp", "wmv", "mpeg", "hevc", "h265"]
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

        # Hauptlayout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        # Header mit Logo und Titel
        header_frame = ctk.CTkFrame(self.root, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
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

        # Hauptinhalt Frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(4, weight=1)

        # Zielordner und Format
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # Zielordner Auswahl
        ctk.CTkLabel(
            settings_frame,
            text="Zielordner:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.folder_entry = ctk.CTkEntry(
            settings_frame,
            placeholder_text="Wählen Sie einen Speicherort...",
            font=("Segoe UI", 12)
        )
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkButton(
            settings_frame,
            text="Durchsuchen",
            command=self.choose_folder,
            width=100,
            font=("Segoe UI", 11),
            fg_color="#2A8C55",
            hover_color="#207244"
        ).grid(row=0, column=2, padx=(5, 10), pady=5)

        # Format Auswahl
        ctk.CTkLabel(
            settings_frame,
            text="Ausgabeformat:",
            font=("Segoe UI", 12)
        ).grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.format_combobox = ctk.CTkComboBox(
            settings_frame,
            variable=self.format_var,
            values=self.formate,
            state="readonly",
            width=120,
            font=("Segoe UI", 12),
            dropdown_fg_color="#2A3B4D"
        )
        self.format_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.format_combobox.set("mp3")

        # URL-Eingabe
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
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

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
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
        progress_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

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

        # Gesamtfortschritt
        self.total_progress_label = ctk.CTkLabel(
            progress_frame,
            text="Gesamtfortschritt: 0%",
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.total_progress_label.grid(row=2, column=0, padx=10, pady=(5, 0), sticky="ew")

        self.total_progress = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20
        )
        self.total_progress.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.total_progress.set(0)

        # Heruntergeladene Titel
        downloaded_frame = ctk.CTkFrame(main_frame)
        downloaded_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")
        downloaded_frame.grid_columnconfigure(0, weight=1)
        downloaded_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            downloaded_frame,
            text="Heruntergeladene Titel:",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Scrollable Frame für Thumbnails
        self.scrollable_frame = ctk.CTkScrollableFrame(
            downloaded_frame,
            orientation="horizontal",
            height=140
        )
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Log-Ausgabe
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            log_frame,
            text="Aktivitätsprotokoll:",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.log_output = ctk.CTkTextbox(
            log_frame,
            font=("Consolas", 11),
            wrap="word",
            activate_scrollbars=True
        )
        self.log_output.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_output.configure(state="disabled")

        # Statusbar
        statusbar = ctk.CTkFrame(self.root, height=30, corner_radius=0)
        statusbar.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 0))
        statusbar.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            statusbar,
            text="Bereit",
            font=("Segoe UI", 11),
            text_color="lightgreen",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=(15, 5), pady=0, sticky="w")

        self.version_label = ctk.CTkLabel(
            statusbar,
            text=f"Version: {LOCAL_VERSION}",
            font=("Segoe UI", 10),
            text_color="lightgray",
            anchor="e"
        )
        self.version_label.grid(row=0, column=1, padx=5, pady=0, sticky="e")

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
            with open(CONFIG_PATH, "r") as f:
                return json.load(f).get("download_folder")
        return None

    def save_download_folder(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump({"download_folder": self.download_folder}, f)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder, title="Wählen Sie einen Zielordner")
        if folder:
            self.download_folder = folder
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.save_download_folder()
            self.log(f"✅ Zielordner gesetzt: {folder}")
            self.update_download_button_state()

    def update_download_button_state(self, event=None):
        url_filled = bool(self.url_entry.get().strip())
        folder_selected = bool(self.download_folder and os.path.isdir(self.download_folder))
        state = "normal" if url_filled and folder_selected and not self.is_downloading else "disabled"
        self.download_button.configure(state=state)

    def clear_url(self):
        self.url_entry.delete(0, "end")
        self.log("🧹 URL-Feld wurde geleert.")
        self.update_download_button_state()

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
        self.total_progress_label.configure(text="Gesamtfortschritt: 0%")
        
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

    def progress_hook(self, d):
        if self.abort_event.is_set():
            raise yt_dlp.utils.DownloadError("Download abgebrochen")
            
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                progress_value = downloaded / total
                self.progress.set(progress_value)
                percent = int(progress_value * 100)
                self.progress_label.configure(text=f"Fortschritt: {percent}%")
        elif d['status'] == 'finished':
            self.progress.set(1.0)
            self.progress_label.configure(text="✅ Download abgeschlossen")
            self.log("✅ Download abgeschlossen.")

    def update_status_label(self, text):
        self.status_label.configure(text=text)

    def update_total_progress(self):
        """Aktualisiert den Gesamtfortschrittsbalken und das Label"""
        if self.total_tracks > 0:
            progress_value = self.completed_tracks / self.total_tracks
            self.total_progress.set(progress_value)
            percent = int(progress_value * 100)
            self.total_progress_label.configure(text=f"Gesamtfortschritt: {percent}% - "
                                                    f"{self.completed_tracks}/{self.total_tracks} Titel")
        else:
            self.total_progress.set(0)
            self.total_progress_label.configure(text="Gesamtfortschritt: 0%")

    def load_thumbnail(self, url, title):
        """Lädt ein Thumbnail im Hintergrund und fügt es zur Liste hinzu"""
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((120, 90), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Füge Thumbnail zur Liste hinzu
            self.root.after(0, self.add_thumbnail, photo, title)
            self.thumbnail_cache[url] = photo
            return photo
        except Exception as e:
            self.log(f"⚠️ Thumbnail-Fehler für '{title}': {e}")
            return None

    def add_thumbnail(self, photo, title):
        """Fügt ein Thumbnail zur Scrollable-Frame hinzu (im Hauptthread)"""
        if self.abort_event.is_set():
            return
            
        frame = ctk.CTkFrame(self.scrollable_frame, width=140, height=120)
        frame.pack_propagate(False)
        frame.pack(side="left", padx=5, pady=5)
        
        label_img = ctk.CTkLabel(frame, image=photo, text="")
        label_img.image = photo  # Keep reference
        label_img.pack(padx=5, pady=(5, 0))
        
        label_title = ctk.CTkLabel(
            frame, 
            text=title[:20] + "..." if len(title) > 20 else title,
            font=("Segoe UI", 10),
            wraplength=130
        )
        label_title.pack(padx=5, pady=(0, 5))

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
            'playlistend': 10000,  # Max 10.000 Titel
            'ignoreerrors': True,
            'quiet': True
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
            }
        else:
            # Video-Formate
            base_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': fmt,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': fmt
                }]
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
                    self.thread_pool.submit(self.load_thumbnail, thumbnail, title)

                self.update_status_label(f"⬇️ Lade: {title} ({i}/{self.total_tracks})")
                self.log(f"⬇️ {i}/{self.total_tracks} – {title}")
                self.progress_label.configure(text=f"Lade Titel {i}/{self.total_tracks}")
                self.progress.set(0)

                ydl_opts = {
                    **base_opts,
                    'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'ignoreerrors': True,
                    'progress_hooks': [self.progress_hook],
                    'noplaylist': True,
                    'logger': YTDLogger(self)
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
                for title in self.downloaded_tracks:
                    f.write(f"{title}\n")
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
