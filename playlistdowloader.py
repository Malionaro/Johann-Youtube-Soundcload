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
import re
import locale
import tempfile
import traceback
from tkinter.scrolledtext import ScrolledText
import pygetwindow as gw
import pyperclip
import psutil

# =============================================
# APP KONFIGURATION
# =============================================
APP_NAME = "SoundSync Downloader"
VERSION = "1.9.5"
APP_AUTHOR = "Malionaro"
GITHUB_USER = "Malionaro"
GITHUB_REPO = "Johann-Youtube-Soundcload"

# GitHub URLs für Updates
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"

# Pfade für Dateispeicherung
APP_DATA_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(APP_DATA_DIR, "sound_sync_config.json")
LOG_FILE = os.path.join(APP_DATA_DIR, "sound_sync_log.txt")
DOWNLOAD_DIR = os.path.join(APP_DATA_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Theme-Einstellungen
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# =============================================
# CHANGELOG
# =============================================
CHANGELOG = {
    "1.9.5": [
        "🔧 NEU: Separates Log-Fenster mit eigenem Öffnen/Schließen Button",
        "📋 NEU: Changelog-Button mit Versionshistorie",
        "🚀 NEU: Log-Fenster öffnet sich automatisch beim Programmstart",
        "🎨 VERBESSERT: Bessere Fenster-Organisation",
        "⚡ VERBESSERT: Performance-Optimierungen"
    ],
    "1.9.4": [
        "🔍 NEU: Verbesserte Browser-Überwachung mit pygetwindow",
        "🌐 NEU: Automatische URL-Erkennung in Browser-Tabs",
        "📋 NEU: Clipboard-Überwachung für kopierte URLs",
        "🎯 NEU: Test-Buttons für manuelle Überprüfung",
        "🔄 VERBESSERT: Zuverlässigere URL-Erkennung",
        "💾 VERBESSERT: Portable Speicherung aller Dateien"
    ],
    "1.9.3": [
        "🌍 NEU: Mehrsprachige Unterstützung (DE, EN, PL)",
        "🎨 NEU: Verbessertes Dark/Light Mode Design",
        "📱 NEU: Responsive Layout für verschiedene Bildschirmgrößen",
        "⚡ VERBESSERT: Schnellere Downloads mit Thread-Pool"
    ],
    "1.9.2": [
        "📁 NEU: Automatischer Download-Ordner",
        "🍪 NEU: Cookies.txt Unterstützung für YouTube",
        "🔄 NEU: Auto-Updater mit Fortschrittsanzeige",
        "📊 VERBESSERT: Detaillierte Fortschrittsanzeige"
    ],
    "1.9.1": [
        "🎵 NEU: SoundCloud Unterstützung",
        "📹 NEU: Video-Download in MP4, AVI, MKV",
        "🖼️ NEU: Thumbnail-Vorschau für heruntergeladene Titel",
        "📝 VERBESSERT: Bessere Fehlerbehandlung"
    ],
    "1.9.0": [
        "🚀 INITIALE VERSION",
        "⬇️ YouTube Audio/Video Downloads",
        "🎵 MP3, WAV, FLAC, AAC Support",
        "📋 Playlist-Unterstützung",
        "🎨 Modernes GUI mit CustomTkinter"
    ]
}

# =============================================
# VERBESSERTE SPRACHERKENNUNG
# =============================================
SUPPORTED_LANGUAGES = ['en', 'de', 'pl']
DEFAULT_LANGUAGE = 'en'

def get_system_language():
    """Ermittle Systemsprache"""
    try:
        # Methode 1: locale.getlocale()
        try:
            loc = locale.getlocale()
            if loc and loc[0]:
                lang = loc[0].split('_')[0]
                if lang in SUPPORTED_LANGUAGES:
                    return lang
        except:
            pass
        
        # Methode 2: Umgebungsvariablen
        env_vars = ['LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES']
        for var in env_vars:
            if var in os.environ:
                lang_value = os.environ[var].split('_')[0]
                if lang_value in SUPPORTED_LANGUAGES:
                    return lang_value
        
        # Methode 3: Windows-spezifisch
        if platform.system() == "Windows":
            try:
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()
                lang_map = {
                    0x0409: 'en',  # English
                    0x0407: 'de',  # German
                    0x0415: 'pl',  # Polish
                }
                lang = lang_map.get(lang_id & 0xFFFF, DEFAULT_LANGUAGE)
                if lang in SUPPORTED_LANGUAGES:
                    return lang
            except:
                pass
        
    except Exception:
        pass
    
    return DEFAULT_LANGUAGE

# Aktuelle Sprache setzen
current_language = get_system_language()

# =============================================
# ÜBERSETZUNGS-MANAGER
# =============================================
class TranslationManager:
    def __init__(self):
        self.current_lang = current_language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """Lade Übersetzungen"""
        self.translations = {
            'en': self.get_english_translations(),
            'de': self.get_german_translations(),
            'pl': self.get_polish_translations()
        }
    
    def get_english_translations(self):
        return {
            'app_title': 'SoundSync Downloader',
            'dark_mode': 'Dark Mode',
            'youtube_soundcloud_url': 'YouTube or SoundCloud URL:',
            'url_placeholder': 'https://www.youtube.com/... or https://soundcloud.com/...',
            'paste': 'Paste',
            'browser_monitoring': '🔍 Browser Monitoring:',
            'monitoring_enabled': 'ENABLED',
            'monitoring_disabled': 'DISABLED',
            'monitoring_info': 'Detects YouTube/SoundCloud URLs in browser tabs and clipboard',
            'test_url': '🔍 Test Current URL',
            'check_clipboard': '📋 Check Clipboard',
            'target_folder': 'Target folder:',
            'folder_placeholder': 'Choose a location...',
            'browse': 'Browse',
            'format': 'Format:',
            'cookies': 'Cookies:',
            'cookies_placeholder': 'Path to cookies.txt',
            'select': 'Select',
            'start_download': 'Start Download',
            'cancel': 'Cancel',
            'check_updates': 'Check for Updates',
            'ready': 'Ready',
            'analyzing_url': '🔍 Analyzing URL...',
            'tracks_found': 'tracks found',
            'loading_track': 'Loading track',
            'progress': 'Progress:',
            'speed': 'Speed:',
            'eta': 'ETA:',
            'download_complete': '✅ Download complete',
            'conversion_complete': '✅ Conversion complete',
            'conversion_waiting': 'Conversion: Waiting...',
            'converting': 'Converting:',
            'calculating': 'calculating...',
            'ready_to_start': 'Ready to start',
            'total_progress': 'Total progress:',
            'activity_log': 'Activity Log:',
            'open_log': '📋 Open Log',
            'close_log': '📋 Close Log',
            'clear_log': 'Clear Log',
            'changelog': '📜 Changelog',
            'downloaded_tracks': 'Downloaded Tracks:',
            'scroll_to_current': 'Scroll to current track',
            'version': 'Version:',
            'github': 'GitHub',
            'close': 'Close',
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'warning': 'Warning',
            'error': 'Error',
            'info': 'Information',
            'question': 'Question',
            'cancel_download_confirm': 'Do you really want to cancel the current download?',
            'update_available': 'Update available:',
            'update_check': 'Checking for updates...',
            'no_update': '✅ Current version',
            'update_failed': '⚠️ Update check failed',
            'ffmpeg_missing': 'FFmpeg missing',
            'installing_ffmpeg': '🔧 Installing FFmpeg...',
            'ffmpeg_installed': '✅ FFmpeg installed',
            'ffmpeg_failed': '❌ FFmpeg installation failed',
            'ffmpeg_required': '❗ FFmpeg required for proper operation',
            'url_detected': '🌐 URL detected:',
            'url_cleared': '🧹 URL field cleared',
            'log_cleared': '🧹 Log cleared',
            'folder_set': '✅ Target folder set:',
            'cookies_selected': '🍪 Cookies file selected:',
            'tracks_found_count': 'tracks found',
            'download_completed': '🎉 Download completed:',
            'success_rate': 'Success rate:',
            'list_saved': '📝 List of downloaded tracks saved:',
            'temp_files_cleaned': 'temporary files cleaned',
            'browser_monitoring_started': '🔍 Browser monitoring started',
            'browser_monitoring_stopped': '🔍 Browser monitoring stopped',
            'clipboard_url': '📋 URL pasted from clipboard',
            'language_changed': '🌐 Language changed to:',
            'monitoring_active': '🔍 Monitoring active',
            'select_folder': 'Select Folder',
            'cookies_file': 'Cookies File',
            'update_confirm': 'Version {} available. Download now?',
            'ffmpeg_confirm': '⚠️ FFmpeg is not installed. Do you want to install it now?',
            'bot_detection': 'YouTube requires confirmation that you are not a bot',
            'bot_detection_instructions': 'Please use the cookies function:\n1. Install the "Get Cookies.txt" browser addon\n2. Export cookies from youtube.com\n3. Select the cookies.txt file in the tool',
            'download_complete_message': 'Download completed!\n\nSuccessfully loaded tracks: {} of {}\nSuccess rate: {:.1f}%\n\nA list of tracks has been saved to:\n{}',
            'install_failed': '❌ Installation failed',
            'ffmpeg_manual': 'Please install FFmpeg manually',
            'unsupported_platform': '⚠️ Platform not supported',
            'update_downloading': '⬇️ Downloading update from:',
            'update_installing': '🔧 Installing update...',
            'update_restart': '🔄 Restarting application for update...',
            'update_error': '❌ Error during update installation:',
            'update_complete': '✅ Update downloaded successfully',
            'update_title': 'Software Update',
            'update_preparing': 'Preparing...',
            'update_status': 'Update status:',
            'downloaded_bytes': 'Downloaded: {}/{} bytes ({:.1%})',
            'test_browser_title': '📋 Browser Title:',
            'test_urls_found': '✅ {} URL(s) found',
            'test_no_urls': '❌ No URLs found in browser title',
            'test_no_window': '❌ No active window found',
            'clipboard_empty': '📋 Clipboard is empty',
            'clipboard_no_url': '❌ No valid URL in clipboard',
            'clipboard_url_found': '✅ URL found in clipboard',
            'browser_detected': '🌐 Browser detected:',
            'no_browser_detected': '❌ No browser detected',
            'monitoring_activated': '✅ Browser monitoring activated',
            'monitoring_deactivated': '⏸️ Browser monitoring deactivated',
            'changelog_title': '📜 SoundSync Downloader - Changelog',
            'version_history': 'Version History',
            'current_version': 'Current version:',
            'close_window': 'Close Window',
            'log_window_title': '📋 Activity Log',
            'show_log': 'Show Log Window',
            'hide_log': 'Hide Log Window',
        }
    
    def get_german_translations(self):
        return {
            'app_title': 'SoundSync Downloader',
            'dark_mode': 'Dark Mode',
            'youtube_soundcloud_url': 'YouTube oder SoundCloud URL:',
            'url_placeholder': 'https://www.youtube.com/... oder https://soundcloud.com/...',
            'paste': 'Einfügen',
            'browser_monitoring': '🔍 Browser-Überwachung:',
            'monitoring_enabled': 'AKTIVIERT',
            'monitoring_disabled': 'DEAKTIVIERT',
            'monitoring_info': 'Erkennt YouTube/SoundCloud URLs in Browser-Tabs und Clipboard',
            'test_url': '🔍 Aktuelle URL testen',
            'check_clipboard': '📋 Clipboard prüfen',
            'target_folder': 'Zielordner:',
            'folder_placeholder': 'Wählen Sie einen Speicherort...',
            'browse': 'Durchsuchen',
            'format': 'Format:',
            'cookies': 'Cookies:',
            'cookies_placeholder': 'Pfad zu cookies.txt',
            'select': 'Auswählen',
            'start_download': 'Download starten',
            'cancel': 'Abbrechen',
            'check_updates': 'Auf Updates prüfen',
            'ready': 'Bereit',
            'analyzing_url': '🔍 Analysiere URL...',
            'tracks_found': 'Titel gefunden',
            'loading_track': 'Lade Titel',
            'progress': 'Fortschritt:',
            'speed': 'Geschwindigkeit:',
            'eta': 'ETA:',
            'download_complete': '✅ Download abgeschlossen',
            'conversion_complete': '✅ Konvertierung abgeschlossen',
            'conversion_waiting': 'Konvertierung: Wartend...',
            'converting': 'Konvertierung:',
            'calculating': 'berechne...',
            'ready_to_start': 'Bereit zum Starten',
            'total_progress': 'Gesamtfortschritt:',
            'activity_log': 'Aktivitätsprotokoll:',
            'open_log': '📋 Log öffnen',
            'close_log': '📋 Log schließen',
            'clear_log': 'Log leeren',
            'changelog': '📜 Changelog',
            'downloaded_tracks': 'Heruntergeladene Titel:',
            'scroll_to_current': 'Zum aktuellen Titel scrollen',
            'version': 'Version:',
            'github': 'GitHub',
            'close': 'Schließen',
            'yes': 'Ja',
            'no': 'Nein',
            'ok': 'OK',
            'warning': 'Warnung',
            'error': 'Fehler',
            'info': 'Information',
            'question': 'Frage',
            'cancel_download_confirm': 'Möchten Sie den aktuellen Download wirklich abbrechen?',
            'update_available': 'Update verfügbar:',
            'update_check': 'Suche nach Updates...',
            'no_update': '✅ Aktuelle Version',
            'update_failed': '⚠️ Update-Prüfung fehlgeschlagen',
            'ffmpeg_missing': 'FFmpeg fehlt',
            'installing_ffmpeg': '🔧 Installiere FFmpeg...',
            'ffmpeg_installed': '✅ FFmpeg installiert',
            'ffmpeg_failed': '❌ FFmpeg-Installation fehlgeschlagen',
            'ffmpeg_required': '❗ FFmpeg wird für korrekte Funktion benötigt',
            'url_detected': '🌐 URL erkannt:',
            'url_cleared': '🧹 URL-Feld wurde geleert',
            'log_cleared': '🧹 Log wurde geleert',
            'folder_set': '✅ Zielordner gesetzt:',
            'cookies_selected': '🍪 Cookies-Datei ausgewählt:',
            'tracks_found_count': 'Titel gefunden',
            'download_completed': '🎉 Download abgeschlossen:',
            'success_rate': 'Erfolgsrate:',
            'list_saved': '📝 Liste der heruntergeladenen Titel gespeichert:',
            'temp_files_cleaned': 'temporäre Dateien gelöscht',
            'browser_monitoring_started': '🔍 Browser-Überwachung gestartet',
            'browser_monitoring_stopped': '🔍 Browser-Überwachung gestoppt',
            'clipboard_url': '📋 URL aus Clipboard eingefügt',
            'language_changed': '🌐 Sprache geändert zu:',
            'monitoring_active': '🔍 Überwachung aktiv',
            'select_folder': 'Ordner wählen',
            'cookies_file': 'Cookies-Datei',
            'update_confirm': 'Version {} verfügbar. Jetzt herunterladen?',
            'ffmpeg_confirm': '⚠️ FFmpeg ist nicht installiert. Möchten Sie es jetzt installieren?',
            'bot_detection': 'YouTube verlangt Bestätigung, dass Sie kein Bot sind',
            'bot_detection_instructions': 'Bitte verwenden Sie die Cookies-Funktion:\n1. Installieren Sie das "Get Cookies.txt" Browser-Addon\n2. Exportieren Sie Cookies von youtube.com\n3. Wählen Sie die cookies.txt-Datei im Tool aus',
            'download_complete_message': 'Download abgeschlossen!\n\nErfolgreich geladene Titel: {} von {}\nErfolgsrate: {:.1f}%\n\nEine Liste der Titel wurde gespeichert unter:\n{}',
            'install_failed': '❌ Installation fehlgeschlagen',
            'ffmpeg_manual': 'Bitte FFmpeg manuell installieren',
            'unsupported_platform': '⚠️ Plattform nicht unterstützt',
            'update_downloading': '⬇️ Lade Update herunter von:',
            'update_installing': '🔧 Installiere Update...',
            'update_restart': '🔄 Starte Anwendung für Update neu...',
            'update_error': '❌ Fehler bei der Update-Installation:',
            'update_complete': '✅ Update erfolgreich heruntergeladen',
            'update_title': 'Software-Update',
            'update_preparing': 'Vorbereitung...',
            'update_status': 'Update-Status:',
            'downloaded_bytes': 'Heruntergeladen: {}/{} Bytes ({:.1%})',
            'test_browser_title': '📋 Browser-Titel:',
            'test_urls_found': '✅ {} URL(s) gefunden',
            'test_no_urls': '❌ Keine URLs im Browser-Titel gefunden',
            'test_no_window': '❌ Kein aktives Fenster gefunden',
            'clipboard_empty': '📋 Clipboard ist leer',
            'clipboard_no_url': '❌ Keine gültige URL im Clipboard',
            'clipboard_url_found': '✅ URL im Clipboard gefunden',
            'browser_detected': '🌐 Browser erkannt:',
            'no_browser_detected': '❌ Kein Browser erkannt',
            'monitoring_activated': '✅ Browser-Überwachung aktiviert',
            'monitoring_deactivated': '⏸️ Browser-Überwachung deaktiviert',
            'changelog_title': '📜 SoundSync Downloader - Changelog',
            'version_history': 'Versionshistorie',
            'current_version': 'Aktuelle Version:',
            'close_window': 'Fenster schließen',
            'log_window_title': '📋 Aktivitätsprotokoll',
            'show_log': 'Log-Fenster anzeigen',
            'hide_log': 'Log-Fenster verbergen',
        }
    
    def get_polish_translations(self):
        return {
            'app_title': 'SoundSync Downloader',
            'dark_mode': 'Tryb ciemny',
            'youtube_soundcloud_url': 'YouTube lub SoundCloud URL:',
            'url_placeholder': 'https://www.youtube.com/... lub https://soundcloud.com/...',
            'paste': 'Wklej',
            'browser_monitoring': '🔍 Monitorowanie przeglądarki:',
            'monitoring_enabled': 'WŁĄCZONE',
            'monitoring_disabled': 'WYŁĄCZONE',
            'monitoring_info': 'Wykrywa URL YouTube/SoundCloud w kartach przeglądarki i schowku',
            'test_url': '🔍 Testuj bieżący URL',
            'check_clipboard': '📋 Sprawdź schowek',
            'target_folder': 'Folder docelowy:',
            'folder_placeholder': 'Wybierz lokalizację...',
            'browse': 'Przeglądaj',
            'format': 'Format:',
            'cookies': 'Ciasteczka:',
            'cookies_placeholder': 'Ścieżka do cookies.txt',
            'select': 'Wybierz',
            'start_download': 'Rozpocznij pobieranie',
            'cancel': 'Anuluj',
            'check_updates': 'Sprawdź aktualizacje',
            'ready': 'Gotowy',
            'analyzing_url': '🔍 Analizuję URL...',
            'tracks_found': 'utworów znaleziono',
            'loading_track': 'Ładuję utwór',
            'progress': 'Postęp:',
            'speed': 'Prędkość:',
            'eta': 'ETA:',
            'download_complete': '✅ Pobieranie zakończone',
            'conversion_complete': '✅ Konwersja zakończona',
            'conversion_waiting': 'Konwersja: Oczekiwanie...',
            'converting': 'Konwertowanie:',
            'calculating': 'obliczam...',
            'ready_to_start': 'Gotowy do startu',
            'total_progress': 'Postęp całkowity:',
            'activity_log': 'Dziennik aktywności:',
            'open_log': '📋 Otwórz log',
            'close_log': '📋 Zamknij log',
            'clear_log': 'Wyczyść log',
            'changelog': '📜 Historia zmian',
            'downloaded_tracks': 'Pobrane utwory:',
            'scroll_to_current': 'Przewiń do bieżącego utworu',
            'version': 'Wersja:',
            'github': 'GitHub',
            'close': 'Zamknij',
            'yes': 'Tak',
            'no': 'Nie',
            'ok': 'OK',
            'warning': 'Ostrzeżenie',
            'error': 'Błąd',
            'info': 'Informacja',
            'question': 'Pytanie',
            'cancel_download_confirm': 'Czy na pewno chcesz anulować bieżące pobieranie?',
            'update_available': 'Dostępna aktualizacja:',
            'update_check': 'Sprawdzam aktualizacje...',
            'no_update': '✅ Aktualna wersja',
            'update_failed': '⚠️ Sprawdzanie aktualizacji nie powiodło się',
            'ffmpeg_missing': 'FFmpeg brakuje',
            'installing_ffmpeg': '🔧 Instaluję FFmpeg...',
            'ffmpeg_installed': '✅ FFmpeg zainstalowany',
            'ffmpeg_failed': '❌ Instalacja FFmpeg nie powiodła się',
            'ffmpeg_required': '❗ FFmpeg wymagany do poprawnego działania',
            'url_detected': '🌐 Wykryto URL:',
            'url_cleared': '🧹 Pole URL wyczyszczone',
            'log_cleared': '🧹 Log wyczyszczony',
            'folder_set': '✅ Ustawiono folder docelowy:',
            'cookies_selected': '🍪 Wybrano plik ciasteczek:',
            'tracks_found_count': 'utworów znaleziono',
            'download_completed': '🎉 Pobieranie zakończone:',
            'success_rate': 'Wskaźnik sukcesu:',
            'list_saved': '📝 Lista pobranych utworów zapisana:',
            'temp_files_cleaned': 'pliki tymczasowe wyczyszczone',
            'browser_monitoring_started': '🔍 Rozpoczęto monitorowanie przeglądarki',
            'browser_monitoring_stopped': '🔍 Zatrzymano monitorowanie przeglądarki',
            'clipboard_url': '📋 URL wklejony ze schowka',
            'language_changed': '🌐 Zmieniono język na:',
            'monitoring_active': '🔍 Monitorowanie aktywne',
            'select_folder': 'Wybierz folder',
            'cookies_file': 'Plik ciasteczek',
            'update_confirm': 'Wersja {} dostępna. Pobrać teraz?',
            'ffmpeg_confirm': '⚠️ FFmpeg nie jest zainstalowany. Czy chcesz go teraz zainstalować?',
            'bot_detection': 'YouTube wymaga potwierdzenia, że nie jesteś botem',
            'bot_detection_instructions': 'Proszę użyć funkcji ciasteczek:\n1. Zainstaluj dodatek "Get Cookies.txt" do przeglądarki\n2. Wyeksportuj ciasteczka z youtube.com\n3. Wybierz plik cookies.txt w narzędziu',
            'download_complete_message': 'Pobieranie zakończone!\n\nPomyślnie załadowane utwory: {} z {}\nWskaźnik sukcesu: {:.1f}%\n\nLista utworów została zapisana w:\n{}',
            'install_failed': '❌ Instalacja nie powiodła się',
            'ffmpeg_manual': 'Proszę zainstalować FFmpeg ręcznie',
            'unsupported_platform': '⚠️ Platforma nieobsługiwana',
            'update_downloading': '⬇️ Pobieram aktualizację z:',
            'update_installing': '🔧 Instaluję aktualizację...',
            'update_restart': '🔄 Ponowne uruchamianie aplikacji dla aktualizacji...',
            'update_error': '❌ Błąd podczas instalacji aktualizacji:',
            'update_complete': '✅ Aktualizacja pobrana pomyślnie',
            'update_title': 'Aktualizacja oprogramowania',
            'update_preparing': 'Przygotowanie...',
            'update_status': 'Status aktualizacji:',
            'downloaded_bytes': 'Pobrano: {}/{} bajtów ({:.1%})',
            'test_browser_title': '📋 Tytuł przeglądarki:',
            'test_urls_found': '✅ Znaleziono {} URL(i)',
            'test_no_urls': '❌ Nie znaleziono URL w tytule przeglądarki',
            'test_no_window': '❌ Nie znaleziono aktywnego okna',
            'clipboard_empty': '📋 Schowek jest pusty',
            'clipboard_no_url': '❌ Brak prawidłowego URL w schowku',
            'clipboard_url_found': '✅ Znaleziono URL w schowku',
            'browser_detected': '🌐 Wykryto przeglądarkę:',
            'no_browser_detected': '❌ Nie wykryto przeglądarki',
            'monitoring_activated': '✅ Monitorowanie przeglądarki aktywowane',
            'monitoring_deactivated': '⏸️ Monitorowanie przeglądarki dezaktywowane',
            'changelog_title': '📜 SoundSync Downloader - Historia zmian',
            'version_history': 'Historia wersji',
            'current_version': 'Aktualna wersja:',
            'close_window': 'Zamknij okno',
            'log_window_title': '📋 Dziennik aktywności',
            'show_log': 'Pokaż okno loga',
            'hide_log': 'Ukryj okno loga',
        }
    
    def get(self, key):
        """Hole Übersetzung"""
        return self.translations.get(self.current_lang, {}).get(key, key)
    
    def set_language(self, lang_code):
        """Setze Sprache"""
        if lang_code in SUPPORTED_LANGUAGES:
            self.current_lang = lang_code

# Globale Übersetzungsinstanz
_ = TranslationManager()

# =============================================
# SYSTEM FUNKTIONEN
# =============================================
def resource_path(relative_path):
    """Ermittle Ressourcen-Pfad"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def check_ffmpeg_installed():
    """Prüfe FFmpeg Installation"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return "ffmpeg version" in (result.stdout + result.stderr).lower()
    except Exception:
        return False

def install_ffmpeg(log_func=print):
    """Installiere FFmpeg"""
    if shutil.which("ffmpeg"):
        log_func(_.get('ffmpeg_installed'))
        return True

    system = platform.system()
    
    if system == "Windows":
        log_func(_.get('installing_ffmpeg'))
        try:
            # Prüfe winget
            subprocess.run(["winget", "--version"], capture_output=True, check=True)
        except:
            log_func(_.get('ffmpeg_manual'))
            return False

        try:
            result = subprocess.run(
                ["winget", "install", "--id=Gyan.FFmpeg", "-e", "--silent"],
                check=True,
                capture_output=True,
                text=True
            )
            log_func(result.stdout)
            log_func(_.get('ffmpeg_installed'))
            return True
        except subprocess.CalledProcessError as e:
            log_func(_.get('ffmpeg_failed'))
            log_func(e.stderr)
            return False

    elif system == "Linux":
        log_func(_.get('installing_ffmpeg'))
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True, check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], capture_output=True, check=True)
            log_func(_.get('ffmpeg_installed'))
            return True
        except subprocess.CalledProcessError as e:
            log_func(_.get('ffmpeg_failed'))
            return False

    elif system == "Darwin":  # macOS
        log_func(_.get('installing_ffmpeg'))
        if shutil.which("ffmpeg"):
            log_func(_.get('ffmpeg_installed'))
            return True

        try:
            machine = platform.machine().lower()
            if machine in ["arm64", "x86_64"]:
                url = "https://evermeet.cx/ffmpeg/ffmpeg-6.0.7z"
            else:
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            
            download_dir = "/tmp/ffmpeg"
            install_dir = "/usr/local/bin"
            os.makedirs(download_dir, exist_ok=True)

            log_func(f"⬇️ Download FFmpeg from {url}...")
            archive_path = os.path.join(download_dir, "ffmpeg.7z" if "evermeet" in url else "ffmpeg.tar.xz")
            urllib.request.urlretrieve(url, archive_path)
            log_func("✅ Download complete")

            log_func("🔧 Extracting FFmpeg...")
            if archive_path.endswith(".7z"):
                subprocess.run(["7z", "x", archive_path, f"-o{download_dir}"], check=True)
                extracted_bin = os.path.join(download_dir, "ffmpeg")
            else:
                with tarfile.open(archive_path, "r:xz") as archive:
                    archive.extractall(download_dir)
                for root, dirs, files in os.walk(download_dir):
                    if "ffmpeg" in files:
                        extracted_bin = os.path.join(root, "ffmpeg")
                        break
            
            if not os.path.exists(extracted_bin):
                raise FileNotFoundError("FFmpeg binary not found")
                
            ffmpeg_dest = os.path.join(install_dir, "ffmpeg")
            log_func(f"🔧 Moving FFmpeg to {install_dir}...")
            shutil.move(extracted_bin, ffmpeg_dest)
            os.chmod(ffmpeg_dest, 0o755)

            if shutil.which("ffmpeg"):
                log_func(_.get('ffmpeg_installed'))
                return True
            else:
                log_func(_.get('ffmpeg_failed'))
                return False

        except Exception as e:
            log_func(f"❌ FFmpeg installation error: {str(e)}")
            return False
    else:
        log_func(_.get('unsupported_platform'))
        return False

# =============================================
# VERBESSERTE BROWSER-ÜBERWACHUNG
# =============================================
class EnhancedBrowserMonitor:
    def __init__(self, app):
        self.app = app
        self.monitoring = False
        self.last_clipboard = ""
        self.last_window_title = ""
        self.browser_processes = [
            "chrome", "firefox", "msedge", "opera", 
            "brave", "vivaldi", "safari", "iexplore"
        ]
        self.url_patterns = [
            # YouTube Patterns
            r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&\S*)?)',
            r'(https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+)',
            r'(https?://(?:www\.)?youtu\.be/[\w-]+)',
            r'(https?://(?:www\.)?youtube\.com/shorts/[\w-]+)',
            # SoundCloud Patterns
            r'(https?://(?:www\.)?soundcloud\.com/[\w/-]+)',
            r'(https?://(?:www\.)?soundcloud\.com/[^/]+/sets/[^/]+)',
            r'(https?://(?:www\.)?soundcloud\.com/[^/]+/[^/]+)'
        ]
        
    def start_monitoring(self):
        """Starte erweiterte Browser-Überwachung"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.app.log(_.get('browser_monitoring_started'))
        
        try:
            # Starte periodische Überprüfung
            self.start_periodic_check()
            
        except Exception as e:
            self.app.log(f"⚠️ Monitoring start error: {e}")
            self.monitoring = False
            
    def stop_monitoring(self):
        """Stoppe Browser-Überwachung"""
        self.monitoring = False
        self.app.log(_.get('browser_monitoring_stopped'))
            
    def start_periodic_check(self):
        """Starte periodische Überprüfung"""
        if not self.monitoring:
            return
            
        try:
            # 1. Prüfe aktives Browser-Fenster
            self.check_active_browser()
            
            # 2. Prüfe Clipboard
            self.check_clipboard()
            
        except Exception as e:
            pass
            
        # Nächste Überprüfung in 3 Sekunden
        if self.monitoring:
            threading.Timer(3, self.start_periodic_check).start()
            
    def check_active_browser(self):
        """Überprüfe aktives Browser-Fenster"""
        try:
            # Aktives Fenster mit pygetwindow
            windows = gw.getWindowsWithTitle("")
            if not windows:
                return
                
            # Finde aktives/zuletzt aktives Fenster
            active_window = None
            for window in windows:
                if window.isActive:
                    active_window = window
                    break
            
            if not active_window:
                # Nimm zuletzt fokussiertes Fenster
                active_window = windows[0]
                
            window_title = active_window.title
            if not window_title or window_title == self.last_window_title:
                return
                
            self.last_window_title = window_title
            
            # Prüfe ob Browser-Fenster
            if self.is_browser_window(active_window):
                # Extrahiere URLs
                urls = self.extract_urls_from_title(window_title)
                for url in urls:
                    if self.is_valid_url(url):
                        self.app.detected_url(url, source="browser")
                        return
                        
        except Exception as e:
            pass
            
    def is_browser_window(self, window):
        """Prüfe ob Browser-Fenster"""
        try:
            title_lower = window.title.lower()
            
            # Browser-Keywords im Titel
            browser_keywords = [
                'chrome', 'firefox', 'edge', 'opera', 'brave',
                'safari', 'internet explorer', 'youtube', 'soundcloud'
            ]
            
            for keyword in browser_keywords:
                if keyword in title_lower:
                    return True
                    
            # Browser-Prozessnamen
            try:
                process = psutil.Process(window._hWnd)
                exe_name = process.name().lower()
                
                for browser in self.browser_processes:
                    if browser in exe_name:
                        return True
            except:
                pass
                
        except Exception:
            pass
            
        return False
        
    def check_clipboard(self):
        """Überprüfe Clipboard"""
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard and current_clipboard != self.last_clipboard:
                self.last_clipboard = current_clipboard
                
                # Extrahiere URLs
                urls = self.extract_urls_from_title(current_clipboard)
                for url in urls:
                    if self.is_valid_url(url):
                        self.app.detected_url(url, source="clipboard")
                        return
                        
        except Exception:
            pass
            
    def extract_urls_from_title(self, text):
        """Extrahiere URLs aus Text"""
        urls = []
        
        if not text:
            return urls
            
        # Direkte URL-Erkennung
        for pattern in self.url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
            
        # YouTube-Titel Muster
        if 'youtube.com/watch' in text.lower():
            # Extrahiere Video-ID
            match = re.search(r'v=([\w-]+)', text, re.IGNORECASE)
            if match:
                urls.append(f"https://www.youtube.com/watch?v={match.group(1)}")
                
        # SoundCloud Muster
        if 'soundcloud.com' in text.lower():
            match = re.search(r'(soundcloud\.com/[\w/-]+)', text, re.IGNORECASE)
            if match:
                urls.append(f"https://{match.group(1)}")
                
        return list(set(urls))  # Entferne Duplikate
        
    def is_valid_url(self, url):
        """Validiere URL"""
        if not url:
            return False
            
        # Grundlegende Validierung
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
        if not url_pattern.match(url):
            return False
            
        # Plattform-spezifische Validierung
        valid_domains = ['youtube.com', 'youtu.be', 'soundcloud.com']
        url_lower = url.lower()
        
        for domain in valid_domains:
            if domain in url_lower:
                return True
                
        return False
        
    def test_current_browser(self):
        """Teste aktuelles Browser-Fenster (manuell)"""
        try:
            windows = gw.getWindowsWithTitle("")
            if not windows:
                return None, []
                
            # Aktives Fenster finden
            active_window = None
            for window in windows:
                if window.isActive:
                    active_window = window
                    break
                    
            if not active_window:
                active_window = windows[0]
                
            window_title = active_window.title
            urls = self.extract_urls_from_title(window_title)
            
            # Browser-Typ identifizieren
            browser_type = "Unknown"
            title_lower = window_title.lower()
            
            if 'chrome' in title_lower:
                browser_type = "Chrome"
            elif 'firefox' in title_lower:
                browser_type = "Firefox"
            elif 'edge' in title_lower:
                browser_type = "Edge"
            elif 'opera' in title_lower:
                browser_type = "Opera"
            elif 'brave' in title_lower:
                browser_type = "Brave"
            elif 'safari' in title_lower:
                browser_type = "Safari"
            elif 'youtube' in title_lower:
                browser_type = "YouTube"
            elif 'soundcloud' in title_lower:
                browser_type = "SoundCloud"
                
            return browser_type, urls
            
        except Exception as e:
            return None, []

# =============================================
# YOUTUBE-DL LOGGER
# =============================================
class YTDLogger:
    def __init__(self, app):
        self.app = app

    def debug(self, msg):
        if msg.strip():
            self.app.log(f"[DEBUG] {msg}")

    def warning(self, msg):
        self.app.log(f"[WARNING] {msg}")

    def error(self, msg):
        self.app.log(f"[ERROR] {msg}")

# =============================================
# LOG FENSTER
# =============================================
class LogWindow:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.window = None
        self.text_widget = None
        self.create_window()
        
    def create_window(self):
        """Erstelle Log-Fenster"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title(_.get('log_window_title'))
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        
        # Position neben Hauptfenster
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        
        self.window.geometry(f"+{parent_x + parent_width + 10}+{parent_y}")
        
        # Verhindere Schließen des Hauptfensters beim Schließen des Logs
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Haupt-Frame
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Toolbar-Frame
        toolbar_frame = ctk.CTkFrame(main_frame, height=40)
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 5))
        toolbar_frame.grid_columnconfigure(0, weight=1)
        
        # Titel
        title_label = ctk.CTkLabel(
            toolbar_frame,
            text=_.get('activity_log'),
            font=("Segoe UI", 12, "bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Buttons
        button_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        self.clear_button = ctk.CTkButton(
            button_frame,
            text=_.get('clear_log'),
            command=self.clear_log,
            width=100,
            height=30,
            font=("Segoe UI", 10)
        )
        self.clear_button.grid(row=0, column=0, padx=5)
        
        self.close_button = ctk.CTkButton(
            button_frame,
            text=_.get('close_log'),
            command=self.hide,
            width=100,
            height=30,
            font=("Segoe UI", 10),
            fg_color="#C74B4B",
            hover_color="#A03A3A"
        )
        self.close_button.grid(row=0, column=1, padx=5)
        
        # Text-Widget
        text_frame = ctk.CTkFrame(main_frame)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)
        
        self.text_widget = ctk.CTkTextbox(
            text_frame,
            font=("Consolas", 10),
            wrap="word",
            activate_scrollbars=True
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Statusbar
        status_frame = ctk.CTkFrame(main_frame, height=25)
        status_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(5, 0))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Log messages will appear here...",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=10)
        
        # Standardmäßig sichtbar
        self.window.deiconify()
        
    def show(self):
        """Zeige Log-Fenster"""
        if self.window:
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()
            except:
                self.create_window()
        else:
            self.create_window()
            
    def hide(self):
        """Verberge Log-Fenster"""
        if self.window:
            self.window.withdraw()
            
    def log(self, message):
        """Füge Nachricht zum Log hinzu"""
        if self.text_widget:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", message + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
            
            # Update Status
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.status_label.configure(text=f"Last message: {timestamp}")
            
    def clear_log(self):
        """Leere das Log"""
        if self.text_widget:
            self.text_widget.configure(state="normal")
            self.text_widget.delete("1.0", "end")
            self.text_widget.configure(state="disabled")
            self.status_label.configure(text="Log cleared")
            
    def is_visible(self):
        """Prüfe ob Fenster sichtbar ist"""
        if self.window:
            try:
                return self.window.winfo_viewable()
            except:
                return False
        return False

# =============================================
# CHANGELOG FENSTER
# =============================================
class ChangelogWindow:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.window = None
        
    def show(self):
        """Zeige Changelog Fenster"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title(_.get('changelog_title'))
        self.window.geometry("700x800")
        self.window.resizable(True, True)
        
        # Zentriere das Fenster
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        window_width = 700
        window_height = 800
        x = parent_x + (parent_width // 2) - (window_width // 2)
        y = parent_y + (parent_height // 2) - (window_height // 2)
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Haupt-Frame
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Titel
        title_label = ctk.CTkLabel(
            main_frame,
            text=_.get('changelog_title'),
            font=("Segoe UI", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Aktuelle Version
        version_label = ctk.CTkLabel(
            main_frame,
            text=f"{_.get('current_version')} {VERSION}",
            font=("Segoe UI", 12),
            text_color="#2A8C55"
        )
        version_label.grid(row=1, column=0, pady=(0, 20))
        
        # Scrollable Frame
        scroll_frame = ctk.CTkScrollableFrame(
            main_frame,
            label_text=_.get('version_history'),
            label_font=("Segoe UI", 12, "bold")
        )
        scroll_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Changelog Inhalt (rückwärts sortiert, neueste zuerst)
        sorted_versions = sorted(
            CHANGELOG.keys(),
            key=lambda v: version.parse(v),
            reverse=True
        )
        
        row = 0
        for ver in sorted_versions:
            # Version Frame
            version_frame = ctk.CTkFrame(scroll_frame, border_width=2, border_color="#3A7EBF")
            version_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
            version_frame.grid_columnconfigure(0, weight=1)
            
            # Version Header
            header_frame = ctk.CTkFrame(version_frame, fg_color="#2A2A2A")
            header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
            
            version_header = ctk.CTkLabel(
                header_frame,
                text=f"Version {ver}",
                font=("Segoe UI", 13, "bold"),
                text_color="white"
            )
            version_header.pack(padx=10, pady=8)
            
            # Changes List
            changes_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
            changes_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=10)
            
            for change in CHANGELOG[ver]:
                change_label = ctk.CTkLabel(
                    changes_frame,
                    text=f"• {change}",
                    font=("Segoe UI", 11),
                    anchor="w",
                    justify="left",
                    wraplength=600
                )
                change_label.pack(anchor="w", padx=5, pady=2)
            
            row += 1
        
        # Close Button
        close_button = ctk.CTkButton(
            main_frame,
            text=_.get('close_window'),
            command=self.window.destroy,
            width=120,
            height=40,
            font=("Segoe UI", 12),
            fg_color="#2A8C55",
            hover_color="#207244"
        )
        close_button.grid(row=3, column=0, pady=10)

# =============================================
# AUTO UPDATER
# =============================================
class AutoUpdater:
    def __init__(self, app):
        self.app = app
        self.update_window = None
        
    def check_for_updates(self, silent=False):
        """Prüfe auf Updates"""
        try:
            if not silent:
                self.app.log(_.get('update_check'))
                self.app.update_status(_.get('update_check'))
            
            headers = {"User-Agent": "SoundSync-Downloader"}
            response = requests.get(GITHUB_API_LATEST, headers=headers, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data.get("tag_name", "").lstrip("v")
            
            version_match = re.search(r'\d+\.\d+\.\d+', latest_version)
            if not version_match:
                if not silent:
                    self.app.log("⚠️ No valid version found")
                return False, None, None
                
            latest_version = version_match.group(0)
            
            if version.parse(latest_version) > version.parse(VERSION):
                if not silent:
                    self.app.log(f"⬆️ {_.get('update_available')} v{latest_version}")
                    self.app.update_status(f"⬆️ {_.get('update_available')} v{latest_version}", "yellow")
                
                # Passendes Asset finden
                asset = None
                for a in release_data.get('assets', []):
                    asset_name = a['name'].lower()
                    system = platform.system().lower()
                    
                    if system == "windows" and ".exe" in asset_name:
                        asset = a
                        break
                    elif system == "linux" and ".tar" in asset_name:
                        asset = a
                        break
                    elif system == "darwin" and ".dmg" in asset_name:
                        asset = a
                        break
                
                if asset:
                    return True, latest_version, asset['browser_download_url']
                else:
                    self.app.log("⚠️ No suitable download found")
            else:
                if not silent:
                    self.app.log(_.get('no_update'))
                    self.app.update_status(_.get('no_update'), "lightgreen")
            
            return False, None, None
            
        except requests.exceptions.RequestException as e:
            if not silent:
                self.app.log(f"⚠️ Network error: {e}")
                self.app.update_status(_.get('update_failed'), "#FF6B6B")
        except Exception as e:
            if not silent:
                self.app.log(f"⚠️ Update error: {e}")
                self.app.update_status(_.get('update_failed'), "#FF6B6B")
        
        return False, None, None
    
    def show_update_dialog(self, version, download_url):
        """Zeige Update-Dialog"""
        if messagebox.askyesno(
            _.get('update_title'),
            _.get('update_confirm').format(version),
            icon="question"
        ):
            self.download_and_install_update(download_url)
    
    def download_and_install_update(self, download_url):
        """Lade Update herunter"""
        self.update_window = UpdateProgressWindow(self.app.root, self.app)
        self.update_window.start_download(download_url)

# =============================================
# UPDATE PROGRESS WINDOW
# =============================================
class UpdateProgressWindow(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title(_.get('update_title'))
        self.geometry("500x300")
        self.transient(parent)
        self.grab_set()
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text=_.get('update_title'),
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text=_.get('update_preparing'),
            font=("Segoe UI", 12)
        )
        self.status_label.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            main_frame,
            mode="determinate",
            height=20,
            width=400
        )
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)
        
        # Progress text
        self.progress_text = ctk.CTkLabel(
            main_frame,
            text="0%",
            font=("Segoe UI", 10)
        )
        self.progress_text.pack(pady=5)
        
        # Log textbox
        self.log_text = ctk.CTkTextbox(
            main_frame,
            height=100,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True, pady=10)
        self.log_text.configure(state="disabled")
        
        # Close button
        self.close_button = ctk.CTkButton(
            main_frame,
            text=_.get('close'),
            command=self.destroy,
            state="disabled"
        )
        self.close_button.pack(pady=10)
    
    def log(self, message):
        """Füge Log-Eintrag hinzu"""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()
    
    def start_download(self, download_url):
        """Starte Download"""
        threading.Thread(target=self.download_update, args=(download_url,), daemon=True).start()
    
    def download_update(self, download_url):
        """Download Update"""
        try:
            # Temp directory
            temp_dir = tempfile.mkdtemp(prefix="soundsync_update_")
            
            # Filename based on platform
            if platform.system() == "Windows":
                filename = "update_installer.exe"
            elif platform.system() == "Darwin":
                filename = "update_installer.dmg"
            else:
                filename = "update_installer.tar.gz"
            
            download_path = os.path.join(temp_dir, filename)
            
            # Start download
            self.status_label.configure(text=_.get('update_downloading'))
            self.log(f"⬇️ {_.get('update_downloading')} {download_url}")
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if total_size > 0:
                            progress = downloaded / total_size
                            self.progress_bar.set(progress)
                            self.progress_text.configure(text=f"{progress*100:.1f}%")
                            self.log(_.get('downloaded_bytes').format(downloaded, total_size, progress))
            
            self.log(_.get('update_complete'))
            self.status_label.configure(text=_.get('update_installing'))
            
            # Install update
            if platform.system() == "Windows":
                self.log(_.get('update_restart'))
                subprocess.Popen([download_path], shell=True)
                self.after(2000, self.app.root.destroy)
            else:
                self.log("⚠️ Manual installation required")
                self.status_label.configure(text="Please install manually")
                self.close_button.configure(state="normal")
                
        except Exception as e:
            self.log(f"{_.get('update_error')} {str(e)}")
            self.status_label.configure(text=_.get('error'))
            self.close_button.configure(state="normal")

# =============================================
# HAUPTPROGRAMM
# =============================================
class SoundSyncDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        
        # Farbpaletten
        self.dark_colors = {
            "bg1": "#121212",
            "bg2": "#1E1E1E",
            "bg3": "#2A2A2A",
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
        
        # App-Icon
        try:
            if platform.system() == "Windows":
                self.root.iconbitmap(default=resource_path("app_icon.ico"))
        except:
            pass
        
        # Codec-Mapping
        self.codec_map = {
            "mp3": "mp3", "m4a": "m4a", "wav": "wav", "flac": "flac", "aac": "aac",
            "ogg": "vorbis", "opus": "opus", "wma": "wma", "alac": "alac", "aiff": "aiff"
        }
        
        self.formats = sorted([*self.codec_map.keys(), "mp4", "webm", "mkv", "avi", "mov", "flv", "wmv", "3gp"])
        self.format_var = ctk.StringVar(value="mp3")
        self.dark_mode = ctk.BooleanVar(value=True)
        
        # Download-Variablen
        self.abort_event = threading.Event()
        self.is_downloading = False
        self.total_tracks = 0
        self.completed_tracks = 0
        self.successful_downloads = 0
        self.downloaded_tracks = []
        self.thumbnail_cache = {}
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Performance-Variablen
        self.start_time = None
        self.last_update_time = None
        self.last_downloaded_bytes = 0
        self.current_speed = 0
        self.last_converted_file = None
        
        # VERBESSERT: Enhanced Browser Monitor
        self.browser_monitor = EnhancedBrowserMonitor(self)
        self.monitoring_enabled = False
        
        # Auto-Updater
        self.auto_updater = AutoUpdater(self)
        
        # NEU: Log-Fenster
        self.log_window = LogWindow(self.root, self)
        self.log_window_visible = True
        
        # NEU: Changelog-Fenster
        self.changelog_window = ChangelogWindow(self.root, self)
        
        # Cookies-Pfad
        self.cookies_path = ""
        
        # Sprachauswahl
        self.language_var = ctk.StringVar(value=_.current_lang)
        self.language_options = {
            'en': 'English',
            'de': 'Deutsch',
            'pl': 'Polski'
        }
        
        # GUI erstellen
        self.create_gui()
        
        # Konfiguration laden
        self.load_config()
        
        # Theme initialisieren
        self.update_theme_colors()
        
        # Automatische Update-Prüfung
        threading.Thread(target=self.auto_check_updates, daemon=True).start()
    
    def create_gui(self):
        """Erstelle GUI"""
        # Hauptlayout
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Header
        self.create_header()
        
        # Hauptbereich
        self.create_main_area()
        
        # Sidebar
        self.create_sidebar()
        
        # Statusbar
        self.create_statusbar()
    
    def create_header(self):
        """Erstelle Header"""
        self.header_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color=self.colors["bg2"])
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Logo
        self.logo_label = ctk.CTkLabel(
            self.header_frame,
            text="🎵",
            font=("Arial", 24),
            width=50
        )
        self.logo_label.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="w")
        
        # Titel
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=_.get('app_title'),
            font=("Segoe UI", 20, "bold")
        )
        self.title_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # NEU: Log-Button
        self.log_button = ctk.CTkButton(
            self.header_frame,
            text=_.get('close_log'),
            command=self.toggle_log_window,
            width=100,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.log_button.grid(row=0, column=2, padx=5, pady=10, sticky="e")
        
        # NEU: Changelog-Button
        self.changelog_button = ctk.CTkButton(
            self.header_frame,
            text=_.get('changelog'),
            command=self.show_changelog,
            width=100,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.changelog_button.grid(row=0, column=3, padx=5, pady=10, sticky="e")
        
        # Dark Mode
        self.theme_switch = ctk.CTkSwitch(
            self.header_frame,
            text=_.get('dark_mode'),
            variable=self.dark_mode,
            command=self.toggle_theme,
            button_color="#2CC985",
            progress_color="#2CC985"
        )
        self.theme_switch.grid(row=0, column=4, padx=10, pady=10, sticky="e")
        
        # Sprachauswahl
        self.language_menu = ctk.CTkComboBox(
            self.header_frame,
            variable=self.language_var,
            values=[self.language_options[lang] for lang in SUPPORTED_LANGUAGES],
            command=self.change_language,
            width=120
        )
        self.language_menu.grid(row=0, column=5, padx=(0, 15), pady=10, sticky="e")
    
    def create_main_area(self):
        """Erstelle Hauptbereich"""
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg1"])
        self.main_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Einstellungen Frame
        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["bg2"])
        self.settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)
        
        # URL-Eingabe
        self.create_url_section()
        
        # Browser Monitoring
        self.create_monitoring_section()
        
        # Ordner-Auswahl
        self.create_folder_section()
        
        # Format & Cookies
        self.create_format_section()
        
        # Buttons
        self.create_buttons_section()
        
        # Fortschrittsbalken
        self.create_progress_section()
        
        # ENTFERNT: Log-Ausgabe wurde in eigenes Fenster verschoben
    
    def create_url_section(self):
        """Erstelle URL-Eingabe"""
        url_frame = ctk.CTkFrame(self.settings_frame, fg_color=self.colors["bg2"])
        url_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew", columnspan=2)
        url_frame.grid_columnconfigure(0, weight=1)
        
        # Label
        url_label = ctk.CTkLabel(
            url_frame,
            text=_.get('youtube_soundcloud_url'),
            font=("Segoe UI", 12)
        )
        url_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Eingabe-Frame
        input_frame = ctk.CTkFrame(url_frame, fg_color=self.colors["bg2"])
        input_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # URL Entry
        self.url_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text=_.get('url_placeholder'),
            font=("Segoe UI", 12),
            height=40
        )
        self.url_entry.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")
        self.url_entry.bind("<KeyRelease>", self.update_download_button_state)
        
        # Buttons Frame
        buttons_frame = ctk.CTkFrame(input_frame, fg_color=self.colors["bg2"])
        buttons_frame.grid(row=0, column=1, padx=0, pady=0)
        
        # Paste Button
        self.paste_button = ctk.CTkButton(
            buttons_frame,
            text=_.get('paste'),
            command=self.paste_from_clipboard,
            width=80,
            height=40,
            font=("Segoe UI", 11),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.paste_button.grid(row=0, column=0, padx=2, pady=0)
        
        # Clear Button
        self.clear_url_button = ctk.CTkButton(
            buttons_frame,
            text="X",
            command=self.clear_url,
            width=40,
            height=40,
            font=("Segoe UI", 11, "bold"),
            fg_color=self.colors["accent3"],
            hover_color=self.colors["accent3_hover"]
        )
        self.clear_url_button.grid(row=0, column=1, padx=2, pady=0)
    
    def create_monitoring_section(self):
        """Erstelle verbessertes Monitoring"""
        monitor_frame = ctk.CTkFrame(self.settings_frame, fg_color=self.colors["bg2"])
        monitor_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew", columnspan=2)
        monitor_frame.grid_columnconfigure(0, weight=1)
        
        # Überschrift
        monitor_header = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        monitor_header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        
        monitor_icon = ctk.CTkLabel(
            monitor_header,
            text="🔍",
            font=("Arial", 14)
        )
        monitor_icon.grid(row=0, column=0, padx=(10, 5), pady=5)
        
        monitor_label = ctk.CTkLabel(
            monitor_header,
            text=_.get('browser_monitoring'),
            font=("Segoe UI", 12, "bold")
        )
        monitor_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Switch
        self.monitor_switch = ctk.CTkSwitch(
            monitor_header,
            text="",
            command=self.toggle_browser_monitoring,
            width=40
        )
        self.monitor_switch.grid(row=0, column=2, padx=5, pady=5)
        
        # Status Label
        self.monitor_status = ctk.CTkLabel(
            monitor_header,
            text=_.get('monitoring_disabled'),
            font=("Segoe UI", 10),
            text_color="red"
        )
        self.monitor_status.grid(row=0, column=3, padx=(10, 20), pady=5)
        
        # Info Frame
        info_frame = ctk.CTkFrame(monitor_frame, fg_color=self.colors["bg3"], corner_radius=5)
        info_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="ew")
        
        info_text = _.get('monitoring_info')
        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Segoe UI", 9),
            justify="left",
            wraplength=500
        )
        info_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Button Frame
        button_frame = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="ew")
        
        # Test Button
        self.test_button = ctk.CTkButton(
            button_frame,
            text=_.get('test_url'),
            command=self.test_current_url,
            width=150,
            height=30,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.test_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Clipboard Button
        self.clipboard_button = ctk.CTkButton(
            button_frame,
            text=_.get('check_clipboard'),
            command=self.check_clipboard_now,
            width=150,
            height=30,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.clipboard_button.grid(row=0, column=1, padx=5, pady=5)
    
    def create_folder_section(self):
        """Erstelle Ordner-Auswahl"""
        folder_frame = ctk.CTkFrame(self.settings_frame, fg_color=self.colors["bg2"])
        folder_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)
        
        # Label
        folder_label = ctk.CTkLabel(
            folder_frame,
            text=_.get('target_folder'),
            font=("Segoe UI", 12)
        )
        folder_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Entry
        self.folder_entry = ctk.CTkEntry(
            folder_frame,
            placeholder_text=_.get('folder_placeholder'),
            font=("Segoe UI", 12)
        )
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.folder_entry.insert(0, DOWNLOAD_DIR)
        
        # Browse Button
        self.browse_button = ctk.CTkButton(
            folder_frame,
            text=_.get('browse'),
            command=self.choose_folder,
            width=100,
            font=("Segoe UI", 11),
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.browse_button.grid(row=0, column=2, padx=(5, 10), pady=5)
    
    def create_format_section(self):
        """Erstelle Format & Cookies"""
        format_frame = ctk.CTkFrame(self.settings_frame, fg_color=self.colors["bg2"])
        format_frame.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        format_frame.grid_columnconfigure(1, weight=1)
        
        # Format Label
        format_label = ctk.CTkLabel(
            format_frame,
            text=_.get('format'),
            font=("Segoe UI", 12)
        )
        format_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Format ComboBox
        self.format_combobox = ctk.CTkComboBox(
            format_frame,
            variable=self.format_var,
            values=self.formats,
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
        
        # Cookies Label
        cookies_label = ctk.CTkLabel(
            format_frame,
            text=_.get('cookies'),
            font=("Segoe UI", 12)
        )
        cookies_label.grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        
        # Cookies Entry
        self.cookies_entry = ctk.CTkEntry(
            format_frame,
            placeholder_text=_.get('cookies_placeholder'),
            font=("Segoe UI", 12),
            width=150
        )
        self.cookies_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Cookies Button
        self.cookies_button = ctk.CTkButton(
            format_frame,
            text=_.get('select'),
            command=self.choose_cookies_file,
            width=100,
            font=("Segoe UI", 11)
        )
        self.cookies_button.grid(row=0, column=4, padx=(5, 10), pady=5)
    
    def create_buttons_section(self):
        """Erstelle Buttons"""
        button_frame = ctk.CTkFrame(self.settings_frame, fg_color=self.colors["bg2"])
        button_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")
        
        # Download Button
        self.download_button = ctk.CTkButton(
            button_frame,
            text=_.get('start_download'),
            command=self.start_download_thread,
            state="disabled",
            font=("Segoe UI", 12, "bold"),
            height=40,
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.download_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Cancel Button
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text=_.get('cancel'),
            command=self.cancel_download,
            state="disabled",
            font=("Segoe UI", 12),
            height=40,
            fg_color=self.colors["accent3"],
            hover_color=self.colors["accent3_hover"]
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Update Button
        self.update_button = ctk.CTkButton(
            button_frame,
            text=_.get('check_updates'),
            command=self.check_updates,
            font=("Segoe UI", 12),
            height=40
        )
        self.update_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
    
    def create_progress_section(self):
        """Erstelle Fortschrittsbalken"""
        progress_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["bg2"])
        progress_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Aktueller Fortschritt
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text=_.get('ready_to_start'),
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress1"]
        )
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)
        
        # Konvertierungsfortschritt
        self.convert_label = ctk.CTkLabel(
            progress_frame,
            text=_.get('conversion_waiting'),
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.convert_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        self.convert_bar = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress1"]
        )
        self.convert_bar.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.convert_bar.set(0)
        
        # Gesamtfortschritt
        self.total_progress_label = ctk.CTkLabel(
            progress_frame,
            text=f"{_.get('total_progress')} 0% | ETA: --:--:--",
            font=("Segoe UI", 12),
            anchor="w"
        )
        self.total_progress_label.grid(row=4, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        self.total_progress_bar = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20,
            progress_color=self.colors["progress2"]
        )
        self.total_progress_bar.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.total_progress_bar.set(0)
    
    def create_sidebar(self):
        """Erstelle Sidebar"""
        self.sidebar_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg1"])
        self.sidebar_frame.grid(row=1, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(1, weight=1)
        
        # Titel
        sidebar_title = ctk.CTkLabel(
            self.sidebar_frame,
            text=_.get('downloaded_tracks'),
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        sidebar_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Scrollable Frame
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            orientation="vertical",
            width=300,
            fg_color=self.colors["bg3"]
        )
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Scroll Button
        scroll_button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color=self.colors["bg1"])
        scroll_button_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        scroll_button_frame.grid_columnconfigure(0, weight=1)
        
        self.scroll_button = ctk.CTkButton(
            scroll_button_frame,
            text=_.get('scroll_to_current'),
            command=self.scroll_to_current,
            font=("Segoe UI", 10),
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.scroll_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    
    def create_statusbar(self):
        """Erstelle Statusbar"""
        self.statusbar = ctk.CTkFrame(self.root, height=30, corner_radius=0, fg_color=self.colors["bg3"])
        self.statusbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 0))
        self.statusbar.grid_columnconfigure(1, weight=1)
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text=_.get('ready'),
            font=("Segoe UI", 11),
            text_color="lightgreen",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=(15, 5), pady=0, sticky="w")
        
        # GitHub Button
        self.github_button = ctk.CTkButton(
            self.statusbar,
            text=_.get('github'),
            command=lambda: webbrowser.open(GITHUB_REPO_URL),
            width=70,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=self.colors["bg2"]
        )
        self.github_button.grid(row=0, column=1, padx=(0, 10), pady=0, sticky="e")
        
        # Version Label
        self.version_label = ctk.CTkLabel(
            self.statusbar,
            text=f"{_.get('version')} {VERSION}",
            font=("Segoe UI", 10),
            text_color="lightgray",
            anchor="e"
        )
        self.version_label.grid(row=0, column=2, padx=5, pady=0, sticky="e")
    
    # =============================================
    # NEUE FUNKTIONEN FÜR LOG-FENSTER
    # =============================================
    def toggle_log_window(self):
        """Öffne/Schließe Log-Fenster"""
        if self.log_window.is_visible():
            self.log_window.hide()
            self.log_button.configure(text=_.get('open_log'))
            self.log_window_visible = False
        else:
            self.log_window.show()
            self.log_button.configure(text=_.get('close_log'))
            self.log_window_visible = True
        
        self.save_config()
    
    def show_changelog(self):
        """Zeige Changelog"""
        self.changelog_window.show()
    
    # =============================================
    # KONFIGURATIONS-FUNKTIONEN
    # =============================================
    def load_config(self):
        """Lade Konfiguration"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Sprache
                lang = config.get('language', _.current_lang)
                if lang in SUPPORTED_LANGUAGES:
                    _.set_language(lang)
                    self.language_var.set(self.language_options[lang])
                
                # Cookies Pfad
                self.cookies_path = config.get('cookies_path', '')
                if self.cookies_path:
                    self.cookies_entry.delete(0, "end")
                    self.cookies_entry.insert(0, self.cookies_path)
                
                # Download Ordner
                download_folder = config.get('download_folder', '')
                if download_folder and os.path.isdir(download_folder):
                    self.folder_entry.delete(0, "end")
                    self.folder_entry.insert(0, download_folder)
                else:
                    self.folder_entry.delete(0, "end")
                    self.folder_entry.insert(0, DOWNLOAD_DIR)
                
                # Browser Monitoring
                monitoring = config.get('browser_monitoring', False)
                if monitoring:
                    self.monitoring_enabled = True
                    self.monitor_switch.select()
                    self.browser_monitor.start_monitoring()
                    self.monitor_status.configure(text=_.get('monitoring_enabled'), text_color="lightgreen")
                
                # Theme
                dark_mode = config.get('dark_mode', True)
                self.dark_mode.set(dark_mode)
                self.toggle_theme()
                
                # Log-Fenster Sichtbarkeit
                self.log_window_visible = config.get('log_window_visible', True)
                if not self.log_window_visible:
                    self.log_window.hide()
                    self.log_button.configure(text=_.get('open_log'))
                else:
                    self.log_button.configure(text=_.get('close_log'))
                
        except Exception as e:
            self.log(f"⚠️ Config load error: {e}")
    
    def save_config(self):
        """Speichere Konfiguration"""
        try:
            config = {
                'language': _.current_lang,
                'cookies_path': self.cookies_path,
                'download_folder': self.folder_entry.get(),
                'browser_monitoring': self.monitoring_enabled,
                'dark_mode': self.dark_mode.get(),
                'log_window_visible': self.log_window_visible,
                'version': VERSION
            }
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            self.log(f"⚠️ Config save error: {e}")
    
    # =============================================
    # GUI FUNKTIONEN
    # =============================================
    def toggle_theme(self):
        """Wechsle Theme"""
        mode = "dark" if self.dark_mode.get() else "light"
        ctk.set_appearance_mode(mode)
        self.colors = self.dark_colors if mode == "dark" else self.light_colors
        self.update_theme_colors()
        self.save_config()
    
    def update_theme_colors(self):
        """Aktualisiere Theme-Farben"""
        # Header
        self.header_frame.configure(fg_color=self.colors["bg2"])
        
        # Hauptbereich
        self.root.configure(fg_color=self.colors["bg1"])
        self.main_frame.configure(fg_color=self.colors["bg1"])
        self.settings_frame.configure(fg_color=self.colors["bg2"])
        
        # Sidebar
        self.sidebar_frame.configure(fg_color=self.colors["bg1"])
        self.scrollable_frame.configure(fg_color=self.colors["bg3"])
        
        # Statusbar
        self.statusbar.configure(fg_color=self.colors["bg3"])
        
        # Buttons
        self.clear_url_button.configure(
            fg_color=self.colors["accent3"],
            hover_color=self.colors["accent3_hover"]
        )
        self.paste_button.configure(
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
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
        self.scroll_button.configure(
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.test_button.configure(
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.clipboard_button.configure(
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        self.log_button.configure(
            fg_color=self.colors["accent2"],
            hover_color=self.colors["accent2_hover"]
        )
        self.changelog_button.configure(
            fg_color=self.colors["accent1"],
            hover_color=self.colors["accent1_hover"]
        )
        
        # Fortschrittsbalken
        self.progress_bar.configure(progress_color=self.colors["progress1"])
        self.convert_bar.configure(progress_color=self.colors["progress1"])
        self.total_progress_bar.configure(progress_color=self.colors["progress2"])
        
        # Textfarbe
        text_color = self.colors["text"]
        self.title_label.configure(text_color=text_color)
        self.status_label.configure(text_color="lightgreen" if self.dark_mode.get() else "green")
    
    def change_language(self, choice):
        """Ändere Sprache"""
        reverse_mapping = {v: k for k, v in self.language_options.items()}
        lang_code = reverse_mapping.get(choice)
        
        if lang_code and lang_code in SUPPORTED_LANGUAGES:
            _.set_language(lang_code)
            self.refresh_ui()
            self.save_config()
            self.log(f"{_.get('language_changed')} {lang_code}")
    
    def refresh_ui(self):
        """Aktualisiere UI-Texte"""
        # Header
        self.theme_switch.configure(text=_.get('dark_mode'))
        self.title_label.configure(text=_.get('app_title'))
        
        # URL Section
        self.url_entry.configure(placeholder_text=_.get('url_placeholder'))
        self.paste_button.configure(text=_.get('paste'))
        
        # Monitoring
        if self.monitoring_enabled:
            self.monitor_status.configure(text=_.get('monitoring_enabled'), text_color="lightgreen")
        else:
            self.monitor_status.configure(text=_.get('monitoring_disabled'), text_color="red")
        
        self.test_button.configure(text=_.get('test_url'))
        self.clipboard_button.configure(text=_.get('check_clipboard'))
        
        # Folder
        self.folder_entry.configure(placeholder_text=_.get('folder_placeholder'))
        self.browse_button.configure(text=_.get('browse'))
        
        # Format
        self.cookies_entry.configure(placeholder_text=_.get('cookies_placeholder'))
        self.cookies_button.configure(text=_.get('select'))
        
        # Buttons
        self.download_button.configure(text=_.get('start_download'))
        self.cancel_button.configure(text=_.get('cancel'))
        self.update_button.configure(text=_.get('check_updates'))
        
        # Progress
        self.progress_label.configure(text=_.get('ready_to_start'))
        self.convert_label.configure(text=_.get('conversion_waiting'))
        
        # Log Button
        if self.log_window_visible:
            self.log_button.configure(text=_.get('close_log'))
        else:
            self.log_button.configure(text=_.get('open_log'))
        
        # Changelog Button
        self.changelog_button.configure(text=_.get('changelog'))
        
        # Sidebar
        self.scroll_button.configure(text=_.get('scroll_to_current'))
        
        # Statusbar
        self.status_label.configure(text=_.get('ready'))
        self.github_button.configure(text=_.get('github'))
        self.version_label.configure(text=f"{_.get('version')} {VERSION}")
    
    # =============================================
    # DATEI FUNKTIONEN
    # =============================================
    def choose_folder(self):
        """Wähle Ordner"""
        folder = filedialog.askdirectory(
            initialdir=self.folder_entry.get(),
            title=_.get('select_folder')
        )
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.save_config()
            self.log(f"{_.get('folder_set')} {folder}")
            self.update_download_button_state()
    
    def choose_cookies_file(self):
        """Wähle Cookies-Datei"""
        file_path = filedialog.askopenfilename(
            title=_.get('cookies_file'),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.cookies_path = file_path
            self.cookies_entry.delete(0, "end")
            self.cookies_entry.insert(0, file_path)
            self.save_config()
            self.log(f"{_.get('cookies_selected')} {file_path}")
    
    def paste_from_clipboard(self):
        """Füge aus Clipboard ein"""
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_content)
                self.update_download_button_state()
                self.log(_.get('clipboard_url'))
        except Exception as e:
            self.log(f"⚠️ Clipboard error: {e}")
    
    def clear_url(self):
        """Leere URL-Feld"""
        self.url_entry.delete(0, "end")
        self.log(_.get('url_cleared'))
        self.update_download_button_state()
    
    # =============================================
    # LOG FUNKTIONEN
    # =============================================
    def log(self, message):
        """Füge Log-Eintrag hinzu"""
        # Sende an Log-Fenster
        self.log_window.log(message)
        
        # Speichere in Datei
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except:
            pass
    
    # =============================================
    # DOWNLOAD FUNKTIONEN
    # =============================================
    def update_download_button_state(self, event=None):
        """Aktualisiere Download-Button"""
        url_filled = bool(self.url_entry.get().strip())
        folder_filled = bool(self.folder_entry.get().strip())
        state = "normal" if url_filled and folder_filled and not self.is_downloading else "disabled"
        self.download_button.configure(state=state)
    
    def start_download_thread(self):
        """Starte Download-Thread"""
        if self.is_downloading:
            return
        
        self.is_downloading = True
        self.abort_event.clear()
        
        # Reset Variablen
        self.total_tracks = 0
        self.completed_tracks = 0
        self.successful_downloads = 0
        self.downloaded_tracks = []
        self.thumbnail_cache = {}
        
        # Reset Fortschrittsbalken
        self.progress_bar.set(0)
        self.convert_bar.set(0)
        self.total_progress_bar.set(0)
        
        # Clear Sidebar
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Startzeit
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded_bytes = 0
        self.current_speed = 0
        
        # Buttons aktualisieren
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.format_combobox.configure(state="disabled")
        
        # Starte Thread
        threading.Thread(target=self.download_playlist, daemon=True).start()
    
    def download_playlist(self):
        """Haupt-Download-Funktion"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror(_.get('error'), "Please enter a URL")
            self.reset_download_state()
            return
        
        format = self.format_var.get()
        
        # Log Start
        self.log(_.get('analyzing_url'))
        self.update_status(_.get('analyzing_url'), "lightblue")
        self.progress_label.configure(text=_.get('analyzing_url'))
        
        # YouTube-DL Optionen
        playlist_opts = {
            'extract_flat': True,
            'playlistend': 10000,
            'ignoreerrors': True,
            'quiet': True,
            'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None,
            'noprogress': True,
            'concurrent_fragment_downloads': 2,
            'buffer_size': 65536,
            'http_chunk_size': 10485760,
        }
        
        if format in self.codec_map:
            codec = self.codec_map[format]
            download_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': '192'
                }],
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.progress_hook],
                'outtmpl': os.path.join(self.folder_entry.get(), '%(title)s.%(ext)s'),
                'quiet': True,
                'ignoreerrors': True,
                'noplaylist': True,
                'logger': YTDLogger(self),
                'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None,
                'noprogress': True,
                'concurrent_fragment_downloads': 2,
                'buffer_size': 65536,
                'http_chunk_size': 10485760,
                'sleep_interval_requests': 1,
            }
        else:
            download_opts = {
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': format,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': format
                }],
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.progress_hook],
                'outtmpl': os.path.join(self.folder_entry.get(), '%(title)s.%(ext)s'),
                'quiet': True,
                'ignoreerrors': True,
                'noplaylist': True,
                'logger': YTDLogger(self),
                'cookiefile': self.cookies_path if self.cookies_path and os.path.exists(self.cookies_path) else None,
                'noprogress': True,
                'concurrent_fragment_downloads': 2,
                'buffer_size': 65536,
                'http_chunk_size': 10485760,
                'sleep_interval_requests': 1,
            }
        
        try:
            # Extrahiere Playlist-Info
            with yt_dlp.YoutubeDL({**playlist_opts, 'logger': YTDLogger(self)}) as ydl:
                info = ydl.extract_info(url, download=False)
            
            entries = info['entries'] if 'entries' in info else [info]
            self.total_tracks = len(entries)
            
            self.log(f"📂 {self.total_tracks} {_.get('tracks_found_count')}")
            self.progress_label.configure(text=f"{self.total_tracks} {_.get('tracks_found')}")
            self.update_total_progress()
            
            # Lade jeden Track
            for i, entry in enumerate(entries, 1):
                if self.abort_event.is_set():
                    break
                
                title = entry.get('title', f"Track {i}")
                link = entry.get('url') or entry.get('webpage_url', url)
                thumbnail = entry.get('thumbnail') or (entry.get('thumbnails', [{}])[0].get('url') if isinstance(entry.get('thumbnails'), list) else None)
                
                # Lade Thumbnail
                if thumbnail:
                    self.thread_pool.submit(self.load_thumbnail, thumbnail, title, i)
                
                # Update Status
                status_text = f"⬇️ {_.get('loading_track')} {i}/{self.total_tracks}: {title[:50]}"
                self.update_status(status_text, "lightblue")
                self.log(f"⬇️ {i}/{self.total_tracks} - {title}")
                self.progress_label.configure(text=f"{_.get('loading_track')} {i}/{self.total_tracks}")
                
                self.progress_bar.set(0)
                self.convert_bar.set(0)
                self.convert_label.configure(text=_.get('conversion_waiting'))
                
                # Download Track
                try:
                    with yt_dlp.YoutubeDL(download_opts) as ydl:
                        ydl.download([link])
                    self.successful_downloads += 1
                    self.downloaded_tracks.append(title)
                except yt_dlp.utils.DownloadError as e:
                    if "Download abgebrochen" in str(e):
                        self.log(f"🛑 {_.get('cancel')}: {title}")
                        break
                    elif "Sign in to confirm you're not a bot" in str(e):
                        error_msg = f"{_.get('bot_detection')}\n\n{_.get('bot_detection_instructions')}"
                        self.log(error_msg)
                        messagebox.showerror(_.get('bot_detection'), error_msg)
                        break
                    else:
                        self.log(f"⚠️ {_.get('error')} {title}: {e}")
                except Exception as e:
                    self.log(f"⚠️ {_.get('error')} {title}: {e}")
                finally:
                    self.completed_tracks = i
                    self.update_total_progress()
                
                if self.abort_event.is_set():
                    break
                
                time.sleep(0.1)
            
            if self.abort_event.is_set():
                self.update_status(_.get('cancel'), "#FF6B6B")
                self.log("🛑 Download aborted")
            else:
                self.finalize_download()
                
        except Exception as e:
            self.update_status(_.get('error'), "#FF6B6B")
            self.progress_label.configure(text=f"{_.get('error')}: {str(e)[:50]}")
            self.log(f"❌ {_.get('error')}: {e}")
            messagebox.showerror(_.get('error'), f"{_.get('error')}:\n{e}")
        finally:
            self.reset_download_state()
            self.cleanup_temp_files()
    
    def progress_hook(self, d):
        """Fortschritts-Callback"""
        if self.abort_event.is_set():
            raise yt_dlp.utils.DownloadError("Download aborted")
        
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                self.progress_bar.configure(mode="determinate")
                progress = downloaded / total
                self.progress_bar.set(progress)
                percent = int(progress * 100)
                
                if time_diff > 0.5:
                    downloaded_diff = downloaded - self.last_downloaded_bytes
                    self.current_speed = downloaded_diff / time_diff
                    self.last_downloaded_bytes = downloaded
                    self.last_update_time = current_time
                
                if self.current_speed > 0:
                    remaining_bytes = total - downloaded
                    eta_seconds = remaining_bytes / self.current_speed
                    eta_str = str(datetime.timedelta(seconds=int(eta_seconds)))
                    speed_str = self.format_speed(self.current_speed)
                    self.progress_label.configure(text=f"{_.get('progress')} {percent}% | {_.get('speed')}: {speed_str} | {_.get('eta')}: {eta_str}")
                else:
                    self.progress_label.configure(text=f"{_.get('progress')} {percent}% | {_.get('speed')}: {_.get('calculating')}")
            else:
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
        
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.progress_label.configure(text=_.get('download_complete'))
            if self.progress_bar.cget("mode") == "indeterminate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
        
        # Konvertierungsfortschritt
        if d.get('postprocessor') and d.get('postprocessor') in ['FFmpegExtractAudio', 'FFmpegVideoConvertor']:
            filename = d.get('info_dict', {}).get('filepath', _.get('error'))
            if filename:
                if filename != self.last_converted_file or d.get('postprocessor_progress', 0) == 0:
                    short_name = os.path.basename(filename)
                    self.convert_label.configure(text=f"{_.get('converting')}: {short_name[:30]}")
                    self.last_converted_file = filename
            
            if d.get('postprocessor_progress') is not None:
                progress = d['postprocessor_progress']
                self.convert_bar.set(progress)
                
                if d['status'] == 'finished':
                    self.convert_bar.set(1.0)
                    self.convert_label.configure(text=_.get('conversion_complete'))
    
    def format_speed(self, speed_bytes):
        """Formatiere Geschwindigkeit"""
        if speed_bytes < 1024:
            return f"{speed_bytes:.1f} B/s"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes/1024:.1f} KB/s"
        else:
            return f"{speed_bytes/(1024*1024):.1f} MB/s"
    
    def update_total_progress(self):
        """Aktualisiere Gesamtfortschritt"""
        if self.total_tracks > 0:
            progress = self.completed_tracks / self.total_tracks
            self.total_progress_bar.set(progress)
            percent = int(progress * 100)
            
            if self.start_time and self.completed_tracks > 0:
                elapsed = time.time() - self.start_time
                avg_time = elapsed / self.completed_tracks
                remaining = self.total_tracks - self.completed_tracks
                eta_seconds = remaining * avg_time
                eta_str = str(datetime.timedelta(seconds=int(eta_seconds)))
                self.total_progress_label.configure(text=f"{_.get('total_progress')} {percent}% | {self.completed_tracks}/{self.total_tracks} | ETA: {eta_str}")
            else:
                self.total_progress_label.configure(text=f"{_.get('total_progress')} {percent}% | {self.completed_tracks}/{self.total_tracks} | ETA: {_.get('calculating')}")
        else:
            self.total_progress_label.configure(text=f"{_.get('total_progress')} 0% | ETA: --:--:--")
    
    def finalize_download(self):
        """Finalisiere Download"""
        self.update_status(_.get('download_complete'), "lightgreen")
        self.progress_label.configure(text=_.get('download_complete'))
        
        success_rate = (self.successful_downloads / self.total_tracks * 100) if self.total_tracks > 0 else 0
        self.log(f"🎉 {_.get('download_completed')} {self.successful_downloads} of {self.total_tracks} {_.get('tracks_found')}")
        self.log(f"📊 {_.get('success_rate')}: {success_rate:.1f}%")
        
        # Speichere Track-Liste
        list_path = os.path.join(self.folder_entry.get(), "download_list.txt")
        try:
            with open(list_path, 'w', encoding='utf-8') as f:
                for idx, title in enumerate(self.downloaded_tracks, 1):
                    f.write(f"{idx}. {title}\n")
            self.log(f"📝 {_.get('list_saved')} {list_path}")
        except Exception as e:
            self.log(f"⚠️ {_.get('error')} saving list: {e}")
        
        # Zeige Erfolgsmeldung
        messagebox.showinfo(
            _.get('info'),
            _.get('download_complete_message').format(
                self.successful_downloads, 
                self.total_tracks, 
                success_rate, 
                list_path
            )
        )
    
    def reset_download_state(self):
        """Setze Download-Status zurück"""
        self.is_downloading = False
        self.download_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.format_combobox.configure(state="readonly")
        self.update_download_button_state()
    
    def cancel_download(self):
        """Breche Download ab"""
        if self.is_downloading:
            if messagebox.askyesno(_.get('warning'), _.get('cancel_download_confirm'), icon="warning"):
                self.abort_event.set()
                self.is_downloading = False
                self.log("🛑 Download canceled")
                self.update_status(_.get('cancel'), "#FF6B6B")
                self.cancel_button.configure(state="disabled")
    
    # =============================================
    # THUMBNAIL FUNKTIONEN - KORRIGIERT
    # =============================================
    def load_thumbnail(self, url, title, index):
        """Lade Thumbnail"""
        try:
            if url in self.thumbnail_cache:
                self.root.after(0, self.add_thumbnail, self.thumbnail_cache[url], title, index)
                return
            
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            img = img.resize((120, 90), Image.Resampling.LANCZOS)
            
            # VERÄNDERT: Verwende CTkImage anstelle von ImageTk.PhotoImage
            photo = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(120, 90)
            )
            
            self.root.after(0, self.add_thumbnail, photo, title, index)
            self.thumbnail_cache[url] = photo
            
        except Exception as e:
            self.log(f"⚠️ Thumbnail error for '{title}': {e}")
    
    def add_thumbnail(self, photo, title, index):
        """Füge Thumbnail hinzu"""
        if self.abort_event.is_set():
            return
        
        frame = ctk.CTkFrame(self.scrollable_frame, width=280, height=100)
        frame.grid_columnconfigure(1, weight=1)
        frame.pack(padx=5, pady=5, fill="x")
        
        # Thumbnail Bild - VERÄNDERT: Kein .image mehr nötig da CTkImage
        img_label = ctk.CTkLabel(frame, image=photo, text="", width=120, height=90)
        img_label.grid(row=0, column=0, padx=5, pady=5)
        
        # Titel
        title_label = ctk.CTkLabel(
            frame,
            text=f"{index}. {title[:30]}",
            font=("Segoe UI", 11),
            anchor="w",
            wraplength=150
        )
        title_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Markiere aktuellen Track
        if index == self.completed_tracks + 1:
            frame.configure(border_width=2, border_color="#2A8C55")
    
    def scroll_to_current(self):
        """Scrolle zu aktuellem Track"""
        self.scrollable_frame._parent_canvas.yview_moveto(1.0)
    
    # =============================================
    # BROWSER MONITORING FUNKTIONEN
    # =============================================
    def toggle_browser_monitoring(self):
        """Aktiviere/Deaktiviere Browser Monitoring"""
        self.monitoring_enabled = not self.monitoring_enabled
        
        if self.monitoring_enabled:
            self.browser_monitor.start_monitoring()
            self.monitor_switch.select()
            self.monitor_status.configure(text=_.get('monitoring_enabled'), text_color="lightgreen")
            self.update_status(_.get('monitoring_active'), "lightblue")
            self.log(_.get('monitoring_activated'))
            
            # Info-Meldung
            messagebox.showinfo(
                "Browser-Überwachung aktiviert",
                "Die Browser-Überwachung ist jetzt aktiv!\n\n"
                "Funktionen:\n"
                "• URLs werden automatisch erkannt, wenn Sie YouTube/SoundCloud besuchen\n"
                "• URLs werden beim Kopieren (STRG+C) erkannt\n"
                "• Sie können jederzeit mit 'Aktuelle URL testen' manuell prüfen"
            )
        else:
            self.browser_monitor.stop_monitoring()
            self.monitor_switch.deselect()
            self.monitor_status.configure(text=_.get('monitoring_disabled'), text_color="red")
            self.update_status(_.get('ready'), "lightgreen")
            self.log(_.get('monitoring_deactivated'))
        
        self.save_config()
    
    def test_current_url(self):
        """Teste aktuelle URL"""
        try:
            self.log("🔍 Testing current browser URL...")
            
            # Browser und URLs identifizieren
            browser_type, urls = self.browser_monitor.test_current_browser()
            
            if browser_type:
                self.log(f"{_.get('browser_detected')} {browser_type}")
            else:
                self.log(_.get('no_browser_detected'))
            
            if urls:
                self.log(f"{_.get('test_urls_found').format(len(urls))}")
                for url in urls:
                    self.log(f"   • {url}")
                    if self.browser_monitor.is_valid_url(url):
                        self.detected_url(url, source="manual", auto_download=False)
                        return
            else:
                self.log(_.get('test_no_urls'))
                
        except Exception as e:
            self.log(f"⚠️ {_.get('error')}: {e}")
    
    def check_clipboard_now(self):
        """Prüfe Clipboard"""
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                self.log(f"📋 {_.get('test_browser_title')} {clipboard_content[:100]}...")
                
                urls = self.browser_monitor.extract_urls_from_title(clipboard_content)
                if urls:
                    self.log(f"{_.get('clipboard_url_found')}")
                    for url in urls:
                        self.log(f"   • {url}")
                        if self.browser_monitor.is_valid_url(url):
                            self.detected_url(url, source="clipboard", auto_download=False)
                            return
                else:
                    self.log(_.get('clipboard_no_url'))
            else:
                self.log(_.get('clipboard_empty'))
        except Exception as e:
            self.log(f"⚠️ {_.get('error')}: {e}")
    
    def detected_url(self, url, source="auto", auto_download=True):
        """URL erkannt"""
        if not self.is_downloading:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, url)
            self.update_download_button_state()
            
            self.log(f"🌐 {_.get('url_detected')} {url} ({source})")
            
            # Frage nach Download (nur bei automatischer Erkennung)
            if auto_download and self.monitoring_enabled:
                response = messagebox.askyesno(
                    _.get('question'),
                    f"URL erkannt:\n\n{url[:80]}...\n\nMöchten Sie den Download starten?",
                    icon="question"
                )
                if response:
                    self.start_download_thread()
            elif not auto_download:
                messagebox.showinfo(
                    _.get('info'),
                    f"URL erkannt:\n\n{url}\n\nDie URL wurde in das Eingabefeld eingefügt."
                )
    
    # =============================================
    # UPDATE FUNKTIONEN
    # =============================================
    def auto_check_updates(self):
        """Automatische Update-Prüfung"""
        has_update, version, url = self.auto_updater.check_for_updates(silent=True)
        if has_update:
            self.root.after(1000, lambda: self.auto_updater.show_update_dialog(version, url))
    
    def check_updates(self):
        """Manuelle Update-Prüfung"""
        has_update, version, url = self.auto_updater.check_for_updates(silent=False)
        if has_update:
            self.auto_updater.show_update_dialog(version, url)
    
    def update_status(self, text, color="lightgreen"):
        """Aktualisiere Status"""
        self.status_label.configure(text=text, text_color=color)
    
    # =============================================
    # CLEANUP FUNKTIONEN
    # =============================================
    def cleanup_temp_files(self):
        """Bereinige temporäre Dateien"""
        temp_extensions = ['.part', '.tmp', '.ytdl']
        deleted = 0
        
        download_folder = self.folder_entry.get()
        if os.path.isdir(download_folder):
            for root, dirs, files in os.walk(download_folder):
                for file in files:
                    if any(file.endswith(ext) for ext in temp_extensions):
                        try:
                            os.remove(os.path.join(root, file))
                            deleted += 1
                        except Exception as e:
                            self.log(f"⚠️ Could not delete temp file {file}: {e}")
        
        if deleted > 0:
            self.log(f"🧹 {deleted} {_.get('temp_files_cleaned')}")

# =============================================
# HAUPTPROGRAMM
# =============================================
def main():
    """Hauptfunktion"""
    # Root-Fenster
    root = ctk.CTk()
    
    try:
        # App erstellen
        app = SoundSyncDownloader(root)
        
        # FFmpeg Check
        def check_ffmpeg():
            if not check_ffmpeg_installed():
                if messagebox.askyesno(
                    _.get('ffmpeg_missing'),
                    _.get('ffmpeg_confirm'),
                    icon="warning"
                ):
                    app.update_status(_.get('installing_ffmpeg'), "lightblue")
                    success = install_ffmpeg(app.log)
                    if success:
                        app.update_status(_.get('ffmpeg_installed'), "lightgreen")
                    else:
                        app.update_status(_.get('ffmpeg_failed'), "#FF6B6B")
                        messagebox.showerror(
                            _.get('install_failed'),
                            _.get('ffmpeg_manual')
                        )
                else:
                    app.update_status(_.get('ffmpeg_required'), "orange")
                    messagebox.showwarning(
                        _.get('warning'),
                        _.get('ffmpeg_required')
                    )
        
        threading.Thread(target=check_ffmpeg, daemon=True).start()
        
        # Hauptloop starten
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror(
            "Kritischer Fehler",
            f"Die Anwendung konnte nicht gestartet werden:\n\n{str(e)}\n\n"
            f"Bitte stellen Sie sicher, dass alle benötigten Pakete installiert sind."
        )
        print(f"Kritischer Fehler: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
