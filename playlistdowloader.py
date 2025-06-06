import tkinter as tk
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
from tkinter import ttk, filedialog, scrolledtext
from packaging import version

LOCAL_VERSION = "1.6.2"
GITHUB_RELEASES_URL = "https://api.github.com/repos/Malionaro/Johann-Youtube-Soundcload/releases/latest"
CONFIG_PATH = "config.json"
os.environ["PATH"] += os.pathsep + "/usr/local/bin"

__version__ = "1.6.2"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def request_admin_rights():
    """Fordert Administratorrechte an, wenn sie fehlen."""
    if os.geteuid() != 0:
        print("Administratorrechte sind erforderlich. Bitte starte das Skript mit 'sudo'.")
        sys.exit(1)

def check_ffmpeg_installed():
    """Prüft, ob FFmpeg bereits installiert ist."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "ffmpeg version" in (result.stdout + result.stderr).lower()
    except Exception:
        return False


def install_ffmpeg(log_func=print):
    # Überprüfe, ob FFmpeg bereits installiert ist
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

    elif platform.system() == "Darwin":  # macOS
        log_func("🔧 Starte FFmpeg-Installation ohne Homebrew...")

        # Prüfen, ob FFmpeg bereits installiert ist
        if shutil.which("ffmpeg"):
            log_func("✅ FFmpeg ist bereits installiert.")
            return True

        try:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz"
            download_dir = "/tmp/ffmpeg"
            install_dir = "/usr/local/bin"

            # Lade das FFmpeg-Archiv herunter
            log_func(f"⬇️ Lade FFmpeg herunter von {url}...")
            archive_path = os.path.join(download_dir, "ffmpeg.tar.xz")
            urllib.request.urlretrieve(url, archive_path)
            log_func("✅ Download abgeschlossen.")

            # Entpacke das Archiv
            log_func("🔧 Entpacke FFmpeg...")
            with tarfile.open(archive_path, "r:xz") as archive:
                archive.extractall(download_dir)
            log_func("✅ Entpacken abgeschlossen.")

            # Bewege die FFmpeg-Dateien nach /usr/local/bin
            ffmpeg_bin = os.path.join(download_dir, "ffmpeg-*-static", "ffmpeg")
            ffmpeg_dest = os.path.join(install_dir, "ffmpeg")
            log_func(f"🔧 Verschiebe FFmpeg nach {install_dir}...")
            shutil.move(ffmpeg_bin, ffmpeg_dest)

            # Gebe dem ausführbaren Datei die richtigen Berechtigungen
            os.chmod(ffmpeg_dest, 0o755)

            # Prüfe, ob FFmpeg jetzt im PATH ist
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


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# if not is_admin():
#     from tkinter import messagebox
#     messagebox.showerror("Administratorrechte benötigt", "⚠️ Bitte starte dieses Programm mit Administratorrechten.")
#     sys.exit(1)

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
        self.root.title("🎵 Playlist Downloader – YouTube & SoundCloud")
        self.root.geometry("800x750")
        self.root.configure(bg="#1a1a1a")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        
        icon_path = resource_path("app_icon.ico")
        self.root.iconbitmap(icon_path)
        
        # log_and_list_frame = tk.Frame(root, bg="#1a1a1a")
        # log_and_list_frame.pack(pady=10, fill="both", expand=True)
        #
        # Log-Ausgabe (links)
        # self.log_output = tk.Text(
        #     log_and_list_frame, height=12, width=65, state='disabled',
        #     bg="#333333", fg="white", font=("Consolas", 11), wrap=tk.WORD
        # )
        # self.log_output.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # preview_frame = tk.Frame(root, bg="#1a1a1a", highlightthickness=1, highlightbackground="#444")
        # preview_frame.place(relx=1.0, rely=0.02, anchor="ne", x=-10)
        #
        # tk.Label(
        #     preview_frame, text="🎬 Geplante Titel",
        #     bg="#1a1a1a", fg="white", font=("Segoe UI", 11, "bold")
        # ).pack(anchor="w")
        #
        # RICHTIGE Listbox mit Scrollbar
        # scrollbar = tk.Scrollbar(preview_frame)
        # scrollbar.pack(side="right", fill="y")
        #
        # self.preview_listbox = tk.Listbox(
        #     preview_frame, height=30, width=40, bg="#2a2a2a", fg="white",
        #     font=("Segoe UI", 10), borderwidth=0, selectbackground="#444444",
        #     yscrollcommand=scrollbar.set
        # )
        # self.preview_listbox.pack(side="left", fill="y", padx=5, pady=5)
        # scrollbar.config(command=self.preview_listbox.yview)
        #
        # Scrollbar für Vorschau
        # scrollbar = tk.Scrollbar(log_and_list_frame, orient="vertical", command=self.preview_listbox.yview)
        # scrollbar.pack(side="right", fill="y")
        # self.preview_listbox.config(yscrollcommand=scrollbar.set)
        
        style.configure("Custom.TButton",
            background="#444444",  # dunkles Grau
            foreground="white",
            font=("Segoe UI", 12, "bold"),
            padding=8,
            borderwidth=0,
            relief="flat"
        )
        
        style.map("Custom.TButton",
            background=[("active", "#555555"), ("pressed", "#666666")],
            foreground=[("disabled", "#888888")]
        )       

        style.configure("TLabel",
            background="#1a1a1a",
            foreground="white",
            font=("Segoe UI", 12)
        )
        
        style.configure("TCombobox",
            font=("Segoe UI", 12)
        )
        
        # Mapping für Audio-Codecs
        self.codec_map = {
            "mp3": "mp3", "m4a": "m4a", "wav": "wav", "flac": "flac", "aac": "aac",
            "ogg": "vorbis", "opus": "opus", "wma": "wma", "alac": "alac", "aiff": "aiff", "mp2": "mp2"
        }

        self.formate = [*self.codec_map.keys(), "mp4", "webm", "mkv", "avi", "mov", "flv", "3gp", "wmv", "mpeg", "hevc", "h265"]
        self.formate.sort()  # sortiert alphabetisch

        self.format_var = tk.StringVar(value="mp3")


        # Frame für Ordner + Format
        folder_and_format_frame = tk.Frame(root, bg="#1a1a1a")
        folder_and_format_frame.pack(pady=(20, 5))

        self.choose_folder_button = ttk.Button(
            folder_and_format_frame,
            text="📁 Zielordner auswählen",
            command=self.choose_folder,
            style="Custom.TButton"
        )
        self.choose_folder_button.grid(row=0, column=0, padx=10)

        tk.Label(
            folder_and_format_frame,
            text="Format wählen:",
            foreground="white",
            background="#1a1a1a",
            font=("Segoe UI", 12)
        ).grid(row=0, column=1, padx=(20,5))

        self.format_combobox = ttk.Combobox(
            folder_and_format_frame,
            textvariable=self.format_var,
            values=self.formate,
            state="readonly",
            width=17,
            font=("Segoe UI", 14),
            style="Custom.TCombobox"
        )
        self.format_combobox.grid(row=0, column=2, padx=10)
        self.format_combobox.set("mp3")


        # URL-Eingabe
        self.url_label = ttk.Label(root, text="🎧 Playlist- oder Track-URL:")
        self.url_label.pack(pady=(30, 5))

        url_frame = tk.Frame(root, bg="#1a1a1a")
        url_frame.pack(pady=5)

        self.url_entry = ttk.Entry(
            url_frame, width=65, font=("Segoe UI", 12)
        )
        self.url_entry.pack(side="left", padx=10, ipady=5)
        self.url_entry.bind("<KeyRelease>", self.update_download_button_state)

        self.clear_url_button = ttk.Button(
            url_frame, text="❌ Clear URL", command=self.clear_url,
            style="Custom.TButton"
        )
        self.clear_url_button.pack(side="left", padx=10)

        # Buttons
        button_row2 = tk.Frame(root, bg="#1a1a1a")
        button_row2.pack(pady=(5, 20))

        self.download_button = ttk.Button(
            button_row2, text="⬇️ Download starten",
            command=self.start_download_thread,
            state="disabled",
            style="Custom.TButton"
        )   
        self.download_button.pack(side="left", padx=10)

        self.cancel_button = ttk.Button(
            button_row2, text="❌ Abbrechen",
            command=self.cancel_download,
            state="disabled",
            style="Custom.TButton"
        )
        self.cancel_button.pack(side="left", padx=10)

        self.update_button = ttk.Button(
            button_row2, text="🔄 Nach Updates suchen",
            command=lambda: threading.Thread(target=self.check_for_updates_gui).start(),
            style="Custom.TButton"
        )
        self.update_button.pack(side="left", padx=10)

        # Progress & Log
        self.progress = ttk.Progressbar(root, orient='horizontal', length=650, mode='determinate', style="TProgressbar")
        self.progress.pack(pady=5)

        self.status_label = ttk.Label(
            root, text="Bereit", font=("Segoe UI", 12), foreground="lightgreen", background="#1a1a1a"
        )
        self.status_label.pack(pady=5)

        self.log_output = tk.Text(
            root, height=12, width=85, state='disabled', bg="#333333", fg="white",
            font=("Consolas", 11), wrap=tk.WORD
        )
        self.log_output.pack(pady=10)

        self.version_label = ttk.Label(
            root, text=f"V{LOCAL_VERSION}", font=("Segoe UI", 10), foreground="lightgray", background="#1a1a1a"
        )
        self.version_label.pack(side="bottom", pady=5)

        self.download_folder = self.load_download_folder() or os.path.expanduser("~")
        os.makedirs(self.download_folder, exist_ok=True)
        self.abort_event = threading.Event()
        self.update_download_button_state()

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
            self.save_download_folder()
            self.log(f"✅ Zielordner gesetzt: {folder}")
            self.update_download_button_state()

    def update_download_button_state(self, event=None):
        url_filled = bool(self.url_entry.get().strip())
        folder_selected = bool(self.download_folder and os.path.isdir(self.download_folder))
        self.download_button.config(state="normal" if url_filled and folder_selected else "disabled")

    def clear_url(self):
        self.url_entry.delete(0, tk.END)
        self.log("🧹 URL-Feld wurde geleert.")
        self.update_download_button_state()

    def log(self, message):
        self.log_output.config(state='normal')
        self.log_output.insert(tk.END, message + "\n")
        self.log_output.see(tk.END)
        self.log_output.config(state='disabled')

    def start_download_thread(self):
        self.format_combobox.config(state="disabled")
        self.abort_event.clear()
        self.cancel_button.config(state='normal')
        threading.Thread(target=self.download_playlist).start()

    def cancel_download(self):
        # Bestätigungsdialog zeigen
        if messagebox.askyesno("Beenden", "Möchten Sie die Anwendung wirklich schließen?", icon='warning'):
            self.log("🛑 Die Anwendung wurde beendet.")
            self.root.quit()  # Beendet die Anwendung
            self.root.destroy()  # Zerstört das Fenster und beendet die Anwendung

    def progress_hook(self, d):
        if self.abort_event.is_set(): raise yt_dlp.utils.DownloadError("Download abgebrochen")
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                self.progress['value'] = downloaded / total * 100
                self.root.update_idletasks()
        elif d['status'] == 'finished':
            self.progress['value'] = 100
            self.root.update_idletasks()
            self.log("✅ Download abgeschlossen.")

    def log(self, message):
        # Um sicherzustellen, dass dies im Haupt-Thread passiert
        self.root.after(0, self._log_message, message)

    def _log_message(self, message):
        try:
            self.log_output.config(state='normal')
            self.log_output.insert(tk.END, message + "\n")
            self.log_output.yview(tk.END)
            self.log_output.config(state='disabled')
        except Exception as e:
            print(f"Fehler beim Loggen: {e}")

    def update_status_label(self, text):
        # Update die Statusanzeige im Haupt-Thread
        self.root.after(0, self._update_status_label, text)

    def _update_status_label(self, text):
        self.status_label.config(text=text)

    def download_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Fehler", "Bitte eine URL eingeben.")
            return

        # 👉 Formatwahl deaktivieren, um Änderungen während des Downloads zu verhindern
        self.format_combobox.config(state='disabled')

        fmt = self.format_var.get()
        self.status_label.config(text="🔍 Analysiere URL...")
        self.log("🔍 Starte Analyse der URL...")

        if fmt in self.codec_map:
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
            base_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': fmt,
                'recode_video': fmt,
            }

        try:
            preview_opts = {
                **base_opts,
                'outtmpl': '%(title)s.%(ext)s',
                'quiet': True,
                'ignoreerrors': True,
                'noplaylist': False,
                'logger': YTDLogger(self)
            }

            info = yt_dlp.YoutubeDL(preview_opts).extract_info(url, download=False)
            entries = info.get('entries', [info])
            self.log(f"📂 {len(entries)} Titel gefunden.")

            for i, e in enumerate(entries, 1):
                if not e:
                    continue
                if self.abort_event.is_set():
                    self.status_label.config(text="❌ Abgebrochen")
                    self.log("🛑 Der Download wurde abgebrochen.")
                    break

                title = e.get('title', f"Track {i}")
                link = e.get('webpage_url', url)

                self.status_label.config(text=f"⬇️ Lade: {title} ({i}/{len(entries)})")
                self.log(f"⬇️ {i}/{len(entries)} – {title}")
                self.progress['value'] = 0
                self.root.update_idletasks()

                ydl_opts = {
                    **base_opts,
                    'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'ignoreerrors': True,
                    'progress_hooks': [self.progress_hook],
                    'noplaylist': True,
                    'logger': YTDLogger(self)
                }

                def download_single():
                    try:
                        def progress_hook(d):
                            if self.abort_event.is_set():
                                raise yt_dlp.utils.DownloadError("Download abgebrochen")
                            self.progress_hook(d)

                        ydl_opts['progress_hooks'] = [progress_hook]

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([link])
                    except Exception as e:
                        if self.abort_event.is_set():
                            self.log(f"🛑 Download abgebrochen: {title}")
                        else:
                            self.log(f"⚠️ Fehler beim Laden von {title}: {e}")

                t = threading.Thread(target=download_single)
                t.start()

                while t.is_alive():
                    if self.abort_event.is_set():
                        break
                    self.root.update_idletasks()

                t.join()

                if self.abort_event.is_set():
                    self.status_label.config(text="❌ Abgebrochen")
                    self.log("🛑 Der Download wurde abgebrochen.")
                    break

        except Exception as e:
            self.root.after(0, self._update_status_label, "❌ Fehler aufgetreten")
            self.root.after(0, self._log_message, f"❌ Fehler beim Download: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Download:\n{e}")

        finally:
            # 👉 Formatwahl wieder aktivieren, egal ob Erfolg oder Fehler
            self.format_combobox.config(state="readonly")
            self.cancel_button.config(state='disabled')

        if self.abort_event.is_set():
            self.status_label.config(text="❌ Abgebrochen")
        else:
            self.status_label.config(text="✅ Download abgeschlossen!")
            self.progress['value'] = 1000
            self.log("🎉 Alle Titel erfolgreich geladen.")
            messagebox.showinfo("Fertig", "Alle Dateien wurden erfolgreich heruntergeladen.")

    def check_for_updates_gui(self):
        try:
            self.log("🔍 Suche nach Updates...")
            r = requests.get(GITHUB_RELEASES_URL, timeout=10)
            r.raise_for_status()
            latest = r.json()
            ver = latest.get("tag_name", "").lstrip("v")
            if version.parse(ver) > version.parse(LOCAL_VERSION):
                self.log(f"⬆️ Neue Version verfügbar: {ver}")
                if messagebox.askyesno("Update verfügbar", f"Version {ver} verfügbar. Jetzt aktualisieren? "): webbrowser.open(latest.get('html_url'))
            else:
                self.log("✅ Keine neue Version gefunden.")
        except Exception as e:
            self.log(f"⚠️ Update-Fehler: {e}")


if __name__ == "__main__":
    if not check_ffmpeg_installed():
        if messagebox.askyesno("FFmpeg fehlt", "⚠️ FFmpeg ist nicht installiert. Möchten Sie es jetzt installieren?"):
            success = install_ffmpeg(self.log)
            if not success:
                messagebox.showerror("Installation fehlgeschlagen", "❌ FFmpeg konnte nicht installiert werden. Bitte manuell installieren.")
        else:
            messagebox.showwarning("FFmpeg benötigt", "❗ Ohne FFmpeg funktioniert der Download nicht korrekt.")
    root = tk.Tk()
    app = DownloaderApp(root)
    threading.Thread(target=app.check_for_updates_gui, daemon=True).start()
    root.mainloop()
