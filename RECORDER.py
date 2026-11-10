#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECORDER v10.0 — HACKERS TCHAD EDITION
Auteur    : HACKERS TCHAD
Style     : Green / Red Cyberpunk Terminal
Licence   : Usage personnel / éducatif
Fichier   : RECORDER.py (single-file application)

Fonctionnalités :
  • Enregistrement de l'écran (full screen ou moniteur sélectionné)
  • Enregistrement de la webcam avec ouverture/fermeture manuelle
  • Modes composites : écran seul, caméra seule, écran + webcam (PiP),
    webcam + écran (PiP)
  • Minuterie programmable (arrêt automatique après N minutes)
  • Pause / reprise de l'enregistrement
  • Capture d'écran instantanée
  • Audio microphone optionnel (si PyAudio disponible)
  • Overlay texte personnalisable, watermark, horodatage, indicateur REC
  • Choix de la résolution, du FPS, du codec et de la qualité
  • Historique des fichiers + ouverture directe
  • Journal système en temps réel
  • Raccourcis clavier : F9, F10, F11, F12
  • Thèmes green / red / blue / amber
  • Interface tkinter single-page avec onglets
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
import os
import sys
import time
import json
import wave
import queue
import threading
import datetime
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk

try:
    import pyautogui
    HAVE_PYAUTOGUI = True
except Exception:
    HAVE_PYAUTOGUI = False

try:
    from screeninfo import get_monitors
    HAVE_SCREENINFO = True
except Exception:
    HAVE_SCREENINFO = False

try:
    import pyaudio
    HAVE_PYAUDIO = True
except Exception:
    HAVE_PYAUDIO = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES & CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════
APP_NAME = "RECORDER"
VERSION = "10.0"
AUTHOR = "HACKERS TCHAD"

DEFAULT_BG = "#050505"
DEFAULT_FG = "#00FF41"
ACCENT_RED = "#FF1A1A"
ACCENT_DIM = "#003B00"
FONT_FAMILY = "Consolas"
MONO_FONT = "Courier New"
CONFIG_FILE = "recorder_config.json"

LOGGER = None  # initialisé plus tard


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════
def get_desktop_path():
    """Retourne le chemin du Bureau quel que soit la langue du système."""
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "Bureau",
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Bureau",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return str(c)
    return str(home)


def ensure_dir(path):
    """Crée le dossier s'il n'existe pas."""
    Path(path).mkdir(parents=True, exist_ok=True)


def safe_filename(name):
    """Nettoie une chaîne pour l'utiliser comme nom de fichier."""
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(c if c in keep else "_" for c in name) or "capture"


def format_duration(seconds):
    """Formate une durée en HH:MM:SS."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def format_size(size_bytes):
    """Formate une taille en B/KB/MB/GB/TB."""
    if size_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def hex_to_rgb(hex_color):
    """Convertit une couleur hex en tuple BGR."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def now_str():
    """Retourne un timestamp compact."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_resolution(text):
    """Parse une chaîne '1920x1080' en tuple."""
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except Exception:
        return 1920, 1080


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION PERSISTANTE
# ═══════════════════════════════════════════════════════════════════════════════
class Config:
    """Gère la sauvegarde et le chargement de la configuration JSON."""

    def __init__(self, path=CONFIG_FILE):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        defaults = {
            "output_dir": get_desktop_path(),
            "filename": "RECORDER_capture",
            "fps": 30,
            "quality": "Haute",
            "mode": "Écran seul",
            "resolution": "1920x1080",
            "monitor": 0,
            "pip_position": "bottom-right",
            "pip_scale": 0.25,
            "webcam_shape": "rectangle",
            "show_watermark": True,
            "show_timestamp": True,
            "show_rec_indicator": True,
            "overlay_text": "HACKERS TCHAD",
            "theme": "green",
            "audio_enabled": True,
            "timer_enabled": False,
            "timer_minutes": 5,
            "window_geometry": "1280x800+100+50",
        }
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                defaults.update(loaded)
        except Exception as exc:
            if LOGGER:
                LOGGER.error(f"Config load : {exc}")
        self.data = defaults

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            if LOGGER:
                LOGGER.error(f"Config save : {exc}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# JOURNAL SYSTÈME
# ═══════════════════════════════════════════════════════════════════════════════
class Logger:
    """Journal thread-safe avec historique circulaire et listeners."""

    def __init__(self, capacity=500):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.lock = threading.Lock()
        self.listeners = []

    def add_listener(self, callback):
        with self.lock:
            self.listeners.append(callback)

    def log(self, level, message):
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{stamp}] [{level}] {message}"
        with self.lock:
            self.buffer.append(line)
            listeners = list(self.listeners)
        for cb in listeners:
            try:
                cb(line)
            except Exception:
                pass

    def info(self, msg):
        self.log("INFO", msg)

    def warn(self, msg):
        self.log("WARN", msg)

    def error(self, msg):
        self.log("ERROR", msg)

    def get_lines(self, n=200):
        with self.lock:
            return list(self.buffer)[-n:]


LOGGER = Logger()


# ═══════════════════════════════════════════════════════════════════════════════
# ENREGISTREMENT AUDIO (optionnel)
# ═══════════════════════════════════════════════════════════════════════════════
class AudioRecorder:
    """Capture le microphone via PyAudio si disponible."""

    def __init__(self):
        self.recording = False
        self.frames = []
        self.thread = None
        self.audio = None
        self.stream = None
        self.sample_rate = 44100
        self.channels = 2
        self.chunk = 1024

    def start(self):
        if not HAVE_PYAUDIO:
            LOGGER.warn("PyAudio absent — audio désactivé")
            return False
        try:
            self.audio = pyaudio.PyAudio()
            self.frames = []
            self.recording = True
            self.thread = threading.Thread(target=self._capture, daemon=True)
            self.thread.start()
            LOGGER.info("Audio démarré")
            return True
        except Exception as exc:
            LOGGER.error(f"Audio start : {exc}")
            return False

    def _capture(self):
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
            while self.recording:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
        except Exception as exc:
            LOGGER.error(f"Audio capture : {exc}")

    def stop(self, output_path):
        if not self.recording:
            return
        self.recording = False
        if self.thread:
            self.thread.join(timeout=2)
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                with wave.open(output_path, "wb") as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b"".join(self.frames))
                LOGGER.info(f"Audio sauvegardé : {output_path}")
        except Exception as exc:
            LOGGER.error(f"Audio save : {exc}")
        finally:
            if self.audio:
                self.audio.terminate()
            self.stream = None
            self.audio = None
            self.frames = []


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCES VIDÉO
# ═══════════════════════════════════════════════════════════════════════════════
class ScreenSource:
    """Capture de l'écran avec pyautogui."""

    def __init__(self, monitor_index=0, region=None):
        self.monitor_index = monitor_index
        self.region = region
        self._size = self._compute_size()

    def _compute_size(self):
        if self.region:
            return self.region[2], self.region[3]
        if HAVE_SCREENINFO:
            try:
                monitors = get_monitors()
                idx = max(0, min(self.monitor_index, len(monitors) - 1))
                m = monitors[idx]
                return m.width, m.height
            except Exception:
                pass
        if HAVE_PYAUTOGUI:
            return pyautogui.size()
        return 1920, 1080

    def read(self):
        if not HAVE_PYAUTOGUI:
            return None
        try:
            if self.region:
                img = pyautogui.screenshot(region=self.region)
            else:
                img = pyautogui.screenshot()
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            LOGGER.error(f"Screen capture : {exc}")
            return None

    def get_size(self):
        return self._size

    def list_monitors(self):
        if HAVE_SCREENINFO:
            try:
                return [f"{i}: {m.width}x{m.height}" for i, m in enumerate(get_monitors())]
            except Exception:
                pass
        return ["0: principal"]


class CameraSource:
    """Capture de la webcam avec OpenCV."""

    def __init__(self, index=0, width=1280, height=720):
        self.index = index
        self.width = width
        self.height = height
        self.cap = None
        self.active = False

    def start(self):
        try:
            self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        except Exception:
            self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            self.active = False
            LOGGER.error(f"Caméra {self.index} inaccessible")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.active = True
        LOGGER.info(f"Caméra {self.index} active")
        return True

    def stop(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.active = False
        LOGGER.info("Caméra fermée")

    def read(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

    def get_size(self):
        if self.cap and self.cap.isOpened():
            return (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        return self.width, self.height


# ═══════════════════════════════════════════════════════════════════════════════
# RENDU COMPOSITE (écran + caméra)
# ═══════════════════════════════════════════════════════════════════════════════
class CompositeRenderer:
    """Combine écran et webcam selon le mode choisi."""

    MODES = [
        "Écran seul",
        "Caméra seule",
        "Écran + webcam (PiP)",
        "Webcam + écran (PiP)",
    ]

    def __init__(self, mode="Écran seul"):
        self.mode = mode
        self.pip_position = "bottom-right"
        self.pip_scale = 0.25
        self.webcam_shape = "rectangle"
        self.show_watermark = True
        self.show_timestamp = True
        self.show_rec_indicator = True
        self.overlay_text = ""
        self.border_color = DEFAULT_FG
        self.bg_fallback = np.zeros((1080, 1920, 3), dtype=np.uint8)

    def set_mode(self, mode):
        if mode in self.MODES:
            self.mode = mode

    def render(self, screen_frame, cam_frame, is_recording, elapsed):
        if self.mode == "Caméra seule":
            canvas = self._camera_canvas(cam_frame)
        elif self.mode == "Écran seul":
            canvas = self._screen_canvas(screen_frame)
        elif self.mode == "Écran + webcam (PiP)":
            canvas = self._screen_canvas(screen_frame)
            if cam_frame is not None:
                canvas = self._overlay_pip(canvas, cam_frame)
        elif self.mode == "Webcam + écran (PiP)":
            canvas = self._camera_canvas(cam_frame) if cam_frame is not None else self._screen_canvas(screen_frame)
            if screen_frame is not None and cam_frame is not None:
                canvas = self._overlay_pip(canvas, screen_frame)
        else:
            canvas = self._screen_canvas(screen_frame)

        if self.show_rec_indicator and is_recording:
            self._draw_rec_indicator(canvas)
        if self.show_timestamp:
            self._draw_timestamp(canvas, elapsed)
        if self.overlay_text:
            self._draw_overlay_text(canvas)
        if self.show_watermark:
            self._draw_watermark(canvas)
        return canvas

    def _screen_canvas(self, frame):
        if frame is None:
            return self.bg_fallback.copy()
        return frame.copy()

    def _camera_canvas(self, frame):
        if frame is None:
            canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(canvas, "CAMERA OFFLINE", (300, 380),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            return canvas
        return frame.copy()

    def _overlay_pip(self, base, overlay):
        h, w = base.shape[:2]
        oh, ow = overlay.shape[:2]
        new_w = max(120, int(w * self.pip_scale))
        new_h = int(new_w * oh / ow)
        new_h = max(90, new_h)
        resized = cv2.resize(overlay, (new_w, new_h))

        if self.webcam_shape == "circle":
            resized = self._make_circle(resized)
        elif self.webcam_shape == "rounded":
            resized = self._make_rounded(resized, 30)

        positions = {
            "top-left": (20, 20),
            "top-right": (w - new_w - 20, 20),
            "bottom-left": (20, h - new_h - 20),
            "bottom-right": (w - new_w - 20, h - new_h - 20),
        }
        x, y = positions.get(self.pip_position, positions["bottom-right"])
        x = max(0, min(x, w - new_w))
        y = max(0, min(y, h - new_h))

        try:
            roi = base[y:y + new_h, x:x + new_w]
            if resized.shape[2] == 4:
                mask = resized[:, :, 3]
                mask_inv = cv2.bitwise_not(mask)
                bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
                fg = cv2.bitwise_and(resized[:, :, :3], resized[:, :, :3], mask=mask)
                dst = cv2.add(bg, fg)
            else:
                dst = resized
            base[y:y + new_h, x:x + new_w] = dst
            cv2.rectangle(base, (x, y), (x + new_w, y + new_h),
                          hex_to_rgb(self.border_color), 2)
        except Exception as exc:
            LOGGER.error(f"PiP overlay : {exc}")
        return base

    def _make_circle(self, img):
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        radius = min(w, h) // 2
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, center, radius, 255, -1)
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mask
        return rgba

    def _make_rounded(self, img, radius):
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask, (radius, 0), (w - radius, h), 255, -1)
        cv2.rectangle(mask, (0, radius), (w, h - radius), 255, -1)
        cv2.circle(mask, (radius, radius), radius, 255, -1)
        cv2.circle(mask, (w - radius, radius), radius, 255, -1)
        cv2.circle(mask, (radius, h - radius), radius, 255, -1)
        cv2.circle(mask, (w - radius, h - radius), radius, 255, -1)
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mask
        return rgba

    def _draw_rec_indicator(self, canvas):
        h, w = canvas.shape[:2]
        radius = max(10, int(min(h, w) * 0.012))
        cx, cy = w - radius - 40, radius + 40
        blink = int(time.time() * 2) % 2 == 0
        color = (0, 0, 255) if blink else (80, 0, 0)
        cv2.circle(canvas, (cx, cy), radius, color, -1)
        cv2.putText(canvas, "REC", (cx - 70, cy + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    def _draw_timestamp(self, canvas, elapsed):
        h, w = canvas.shape[:2]
        text = format_duration(elapsed)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full = f"{text}  |  {now}"
        scale = max(0.5, min(h, w) / 2200)
        thick = max(1, int(scale * 2))
        cv2.putText(canvas, full, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 0), thick)

    def _draw_overlay_text(self, canvas):
        h, w = canvas.shape[:2]
        y = h - 30
        cv2.putText(canvas, self.overlay_text, (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

    def _draw_watermark(self, canvas):
        h, w = canvas.shape[:2]
        text = f"{APP_NAME} v{VERSION} — {AUTHOR}"
        scale = max(0.4, min(h, w) / 2800)
        thick = max(1, int(scale))
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(canvas, text, (w - tw - 20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 100, 0), thick)


# ═══════════════════════════════════════════════════════════════════════════════
# MOTEUR D'ENREGISTREMENT VIDÉO
# ═══════════════════════════════════════════════════════════════════════════════
class VideoRecorderEngine:
    """Gère la file de frames, l'encodage et l'audio."""

    def __init__(self, app):
        self.app = app
        self.recording = False
        self.paused = False
        self.start_time = None
        self.pause_start = None
        self.total_pause = 0.0
        self.out = None
        self.fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.fps = 30
        self.writer_thread = None
        self.frame_queue = queue.Queue(maxsize=120)
        self.lock = threading.Lock()
        self.output_path = None
        self.audio_path = None
        self.audio_recorder = AudioRecorder()
        self.audio_enabled = True
        self.frames_written = 0
        self.frames_dropped = 0
        self.session_start = None

    def configure(self, source_mode, fps, quality, output_dir, filename, resolution, audio_enabled):
        self.source_mode = source_mode
        self.fps = max(1, min(60, int(fps)))
        self.output_dir = output_dir
        self.filename = filename
        self.resolution = resolution
        self.audio_enabled = audio_enabled
        quality_map = {
            "Basse": ("XVID", 0.5),
            "Moyenne": ("XVID", 0.75),
            "Haute": ("mp4v", 0.95),
            "Ultra": ("H264", 1.0),
        }
        codec, _ = quality_map.get(quality, ("XVID", 0.75))
        if codec == "H264" and not self._has_h264():
            codec = "mp4v"
            LOGGER.warn("Codec H264 indisponible — fallback mp4v")
        self.fourcc = cv2.VideoWriter_fourcc(*codec)

    def _has_h264(self):
        try:
            t = cv2.VideoWriter_fourcc(*"H264")
            return t > 0
        except Exception:
            return False

    def start(self):
        with self.lock:
            if self.recording:
                return False
            ensure_dir(self.output_dir)
            ts = now_str()
            base = safe_filename(self.filename)
            ext = ".avi"
            self.output_path = os.path.join(self.output_dir, f"{base}_{ts}{ext}")
            self.audio_path = os.path.join(self.output_dir, f"{base}_{ts}.wav")

            size = self.app.get_active_resolution()
            self.out = cv2.VideoWriter(self.output_path, self.fourcc, self.fps, size)
            if not self.out.isOpened():
                LOGGER.error("Impossible d'ouvrir VideoWriter")
                self.out = None
                return False

            self.recording = True
            self.paused = False
            self.start_time = time.time()
            self.total_pause = 0.0
            self.frames_written = 0
            self.frames_dropped = 0
            self.session_start = datetime.datetime.now().isoformat()

            if self.audio_enabled:
                self.audio_recorder.start()

            self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
            self.writer_thread.start()
            LOGGER.info(f"Enregistrement démarré : {self.output_path}")
            return True

    def stop(self):
        with self.lock:
            if not self.recording:
                return None
            self.recording = False
            self.paused = False

        if self.writer_thread:
            self.writer_thread.join(timeout=3)

        try:
            if self.out:
                self.out.release()
                self.out = None
        except Exception as exc:
            LOGGER.error(f"VideoWriter release : {exc}")

        if self.audio_enabled:
            self.audio_recorder.stop(self.audio_path)

        elapsed = time.time() - self.start_time - self.total_pause if self.start_time else 0
        self.start_time = None
        self.session_start = None

        LOGGER.info(f"Enregistrement terminé : {self.output_path}")
        self.app.on_recording_finished(self.output_path)
        self.app.update_stats_after_stop(elapsed)
        return self.output_path

    def toggle_pause(self):
        if not self.recording:
            return
        if self.paused:
            self.paused = False
            if self.pause_start:
                self.total_pause += time.time() - self.pause_start
            self.pause_start = None
            LOGGER.info("Enregistrement repris")
        else:
            self.paused = True
            self.pause_start = time.time()
            LOGGER.info("Enregistrement en pause")

    def get_elapsed(self):
        if not self.recording or self.start_time is None:
            return 0
        elapsed = time.time() - self.start_time - self.total_pause
        if self.paused and self.pause_start:
            elapsed -= (time.time() - self.pause_start)
        return max(0, elapsed)

    def push_frame(self, frame):
        if not self.recording or self.paused:
            return
        try:
            self.frame_queue.put(frame, timeout=0.05)
        except queue.Full:
            self.frames_dropped += 1

    def _writer_loop(self):
        while self.recording:
            try:
                frame = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if frame is None:
                continue
            try:
                if self.out:
                    self.out.write(frame)
                    self.frames_written += 1
            except Exception as exc:
                LOGGER.error(f"Write frame : {exc}")
                self.frames_dropped += 1


# ═══════════════════════════════════════════════════════════════════════════════
# PANNEAU D'APERÇU TKINTER
# ═══════════════════════════════════════════════════════════════════════════════
class PreviewPanel(tk.Canvas):
    """Canvas dédié à l'affichage du flux vidéo."""

    def __init__(self, parent, width=720, height=405, **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self.width = width
        self.height = height
        self.image_id = None
        self.photo = None

    def update_frame(self, pil_image):
        if pil_image is None:
            return
        try:
            pil_image = pil_image.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(pil_image)
            if self.image_id is None:
                self.image_id = self.create_image(0, 0, anchor=tk.NW, image=self.photo)
            else:
                self.itemconfig(self.image_id, image=self.photo)
        except Exception as exc:
            LOGGER.error(f"Preview update : {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════
class RecorderApp:
    """Interface principale RECORDER."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION} — {AUTHOR}")
        self.config = Config()
        self.history = []
        self.last_frame = None
        self.preview_running = False
        self.preview_thread = None
        self.stats_update_id = None

        self.screen_source = ScreenSource()
        self.camera_source = CameraSource()
        self.composite = CompositeRenderer()
        self.engine = VideoRecorderEngine(self)

        self._build_styles()
        self._build_ui()
        self._apply_config()
        self._bind_hotkeys()
        self._start_clock()
        self._start_preview()

        LOGGER.add_listener(self._on_log_line)
        LOGGER.info(f"{APP_NAME} v{VERSION} démarré")

    def _build_styles(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=DEFAULT_BG)
        self.style.configure("TLabel", background=DEFAULT_BG, foreground=DEFAULT_FG)
        self.style.configure("TButton", background=ACCENT_DIM, foreground=DEFAULT_FG,
                             font=(FONT_FAMILY, 9, "bold"))
        self.style.configure("TNotebook", background=DEFAULT_BG, tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", background=ACCENT_DIM, foreground=DEFAULT_FG,
                             font=(FONT_FAMILY, 9, "bold"), padding=[12, 4])
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#005500")],
                       foreground=[("selected", "#AAFFAA")])
        self.style.configure("TCombobox", fieldbackground=DEFAULT_BG, foreground=DEFAULT_FG,
                             selectbackground="#005500", selectforeground=DEFAULT_FG)
        self.style.configure("TSpinbox", fieldbackground=DEFAULT_BG, foreground=DEFAULT_FG)
        self.style.configure("Horizontal.TScale", background=DEFAULT_BG, troughcolor=ACCENT_DIM)

    def _build_ui(self):
        self.root.configure(bg=DEFAULT_BG)
        geo = self.config.get("window_geometry", "1280x800+100+50")
        self.root.geometry(geo)

        # En-tête
        header = tk.Frame(self.root, bg=DEFAULT_BG, height=60)
        header.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(header, text=f"◄ {APP_NAME} v{VERSION} ►",
                 bg=DEFAULT_BG, fg=DEFAULT_FG,
                 font=(FONT_FAMILY, 24, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=f"by {AUTHOR}",
                 bg=DEFAULT_BG, fg=ACCENT_RED,
                 font=(FONT_FAMILY, 12, "italic")).pack(side=tk.LEFT, padx=15)
        self.clock_label = tk.Label(header, text="", bg=DEFAULT_BG, fg=DEFAULT_FG,
                                    font=(MONO_FONT, 12))
        self.clock_label.pack(side=tk.RIGHT)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_record = tk.Frame(self.notebook, bg=DEFAULT_BG)
        self.tab_settings = tk.Frame(self.notebook, bg=DEFAULT_BG)
        self.tab_history = tk.Frame(self.notebook, bg=DEFAULT_BG)
        self.tab_logs = tk.Frame(self.notebook, bg=DEFAULT_BG)
        self.tab_about = tk.Frame(self.notebook, bg=DEFAULT_BG)

        self.notebook.add(self.tab_record, text=" ENREGISTREMENT ")
        self.notebook.add(self.tab_settings, text=" PARAMÈTRES ")
        self.notebook.add(self.tab_history, text=" HISTORIQUE ")
        self.notebook.add(self.tab_logs, text=" JOURNAUX ")
        self.notebook.add(self.tab_about, text=" À PROPOS ")

        self._build_record_tab()
        self._build_settings_tab()
        self._build_history_tab()
        self._build_logs_tab()
        self._build_about_tab()

        # Barre d'état
        self.status = tk.Label(self.root, text="Prêt", bg=ACCENT_DIM, fg=DEFAULT_FG,
                               font=(FONT_FAMILY, 10), anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM, ipady=4)

    def _build_record_tab(self):
        left = tk.Frame(self.tab_record, bg=DEFAULT_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_header = tk.Frame(left, bg=DEFAULT_BG)
        preview_header.pack(fill=tk.X)
        tk.Label(preview_header, text="APERÇU EN DIRECT", bg=DEFAULT_BG,
                 fg=DEFAULT_FG, font=(FONT_FAMILY, 12, "bold")).pack(side=tk.LEFT)
        self.preview_size_label = tk.Label(preview_header, text="", bg=DEFAULT_BG,
                                           fg=ACCENT_RED, font=(FONT_FAMILY, 9))
        self.preview_size_label.pack(side=tk.RIGHT)

        self.preview = PreviewPanel(left, width=720, height=405, bg="black",
                                    highlightbackground=DEFAULT_FG, highlightthickness=2)
        self.preview.pack(pady=10, fill=tk.BOTH, expand=True)

        self.timer_display = tk.Label(left, text="00:00:00", bg=DEFAULT_BG,
                                      fg=DEFAULT_FG, font=(MONO_FONT, 48, "bold"))
        self.timer_display.pack(pady=5)

        btn_frame = tk.Frame(left, bg=DEFAULT_BG)
        btn_frame.pack(pady=10)

        self.btn_record = tk.Button(btn_frame, text="▶ ENREGISTRER", bg="#004400",
                                    fg="white", activebackground="#006600",
                                    font=(FONT_FAMILY, 12, "bold"), width=16,
                                    command=self.start_recording)
        self.btn_record.pack(side=tk.LEFT, padx=5)

        self.btn_pause = tk.Button(btn_frame, text="⏸ PAUSE", bg="#444400",
                                   fg="white", activebackground="#666600",
                                   font=(FONT_FAMILY, 12, "bold"), width=12,
                                   command=self.pause_recording)
        self.btn_pause.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(btn_frame, text="■ ARRÊTER", bg="#550000",
                                  fg="white", activebackground="#770000",
                                  font=(FONT_FAMILY, 12, "bold"), width=12,
                                  command=self.stop_recording)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_screenshot = tk.Button(btn_frame, text="📷 CAPTURE", bg="#003333",
                                        fg="white", activebackground="#005555",
                                        font=(FONT_FAMILY, 12, "bold"), width=12,
                                        command=self.take_screenshot)
        self.btn_screenshot.pack(side=tk.LEFT, padx=5)

        right = tk.Frame(self.tab_record, bg=DEFAULT_BG)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        mode_box = tk.LabelFrame(right, text=" MODE SOURCE ", bg=DEFAULT_BG,
                                 fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        mode_box.pack(fill=tk.X, pady=5)
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(mode_box, textvariable=self.mode_var,
                                       values=CompositeRenderer.MODES, state="readonly", width=28)
        self.mode_combo.pack(padx=8, pady=8, fill=tk.X)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        cam_box = tk.LabelFrame(right, text=" CAMÉRA ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        cam_box.pack(fill=tk.X, pady=5)
        self.btn_cam_toggle = tk.Button(cam_box, text="OUVRIR CAMÉRA", bg="#003300",
                                        fg="white", command=self.toggle_camera)
        self.btn_cam_toggle.pack(padx=8, pady=8, fill=tk.X)
        self.cam_status = tk.Label(cam_box, text="Caméra fermée", bg=DEFAULT_BG,
                                   fg=ACCENT_RED, font=(FONT_FAMILY, 9))
        self.cam_status.pack()

        qual_box = tk.LabelFrame(right, text=" QUALITÉ & FPS ", bg=DEFAULT_BG,
                                 fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        qual_box.pack(fill=tk.X, pady=5)
        tk.Label(qual_box, text="FPS:", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.fps_var = tk.IntVar(value=30)
        tk.Spinbox(qual_box, from_=1, to=60, textvariable=self.fps_var, width=10,
                   bg=DEFAULT_BG, fg=DEFAULT_FG, buttonbackground=ACCENT_DIM).pack(padx=8, pady=2)
        tk.Label(qual_box, text="Qualité:", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.quality_var = tk.StringVar(value="Haute")
        ttk.Combobox(qual_box, textvariable=self.quality_var,
                     values=["Basse", "Moyenne", "Haute", "Ultra"], state="readonly").pack(padx=8, pady=2)

        timer_box = tk.LabelFrame(right, text=" MINUTERIE ", bg=DEFAULT_BG,
                                  fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        timer_box.pack(fill=tk.X, pady=5)
        self.timer_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(timer_box, text="Activer", variable=self.timer_enabled,
                       bg=DEFAULT_BG, fg=DEFAULT_FG, selectcolor=ACCENT_DIM).pack(anchor=tk.W, padx=8)
        tk.Label(timer_box, text="Durée (min):", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.timer_min_var = tk.IntVar(value=5)
        tk.Spinbox(timer_box, from_=1, to=180, textvariable=self.timer_min_var, width=10,
                   bg=DEFAULT_BG, fg=DEFAULT_FG, buttonbackground=ACCENT_DIM).pack(padx=8, pady=2)

        overlay_box = tk.LabelFrame(right, text=" OVERLAY ", bg=DEFAULT_BG,
                                    fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        overlay_box.pack(fill=tk.X, pady=5)
        self.overlay_var = tk.StringVar(value="HACKERS TCHAD")
        tk.Entry(overlay_box, textvariable=self.overlay_var, bg=DEFAULT_BG, fg=DEFAULT_FG,
                 insertbackground=DEFAULT_FG, font=(FONT_FAMILY, 9)).pack(padx=8, pady=8, fill=tk.X)

        stats_box = tk.LabelFrame(right, text=" STATISTIQUES ", bg=DEFAULT_BG,
                                  fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        stats_box.pack(fill=tk.X, pady=5)
        self.stats_label = tk.Label(stats_box, text="Aucune session", bg=DEFAULT_BG,
                                    fg=DEFAULT_FG, font=(MONO_FONT, 9), justify=tk.LEFT)
        self.stats_label.pack(padx=8, pady=8, anchor=tk.W)

    def _build_settings_tab(self):
        container = tk.Frame(self.tab_settings, bg=DEFAULT_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        left = tk.Frame(container, bg=DEFAULT_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = tk.Frame(container, bg=DEFAULT_BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        out_box = tk.LabelFrame(left, text=" DOSSIER DE SORTIE ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        out_box.pack(fill=tk.X, pady=5)
        self.output_dir_var = tk.StringVar(value=get_desktop_path())
        tk.Entry(out_box, textvariable=self.output_dir_var, bg=DEFAULT_BG, fg=DEFAULT_FG,
                 insertbackground=DEFAULT_FG).pack(padx=8, pady=5, fill=tk.X)
        tk.Button(out_box, text="Parcourir...", bg=ACCENT_DIM, fg=DEFAULT_FG,
                  command=self._browse_output_dir).pack(padx=8, pady=5, anchor=tk.E)

        name_box = tk.LabelFrame(left, text=" NOM DE FICHIER ", bg=DEFAULT_BG,
                                 fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        name_box.pack(fill=tk.X, pady=5)
        self.filename_var = tk.StringVar(value="RECORDER_capture")
        tk.Entry(name_box, textvariable=self.filename_var, bg=DEFAULT_BG, fg=DEFAULT_FG,
                 insertbackground=DEFAULT_FG).pack(padx=8, pady=8, fill=tk.X)

        res_box = tk.LabelFrame(left, text=" RÉSOLUTION ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        res_box.pack(fill=tk.X, pady=5)
        self.resolution_var = tk.StringVar(value="1920x1080")
        ttk.Combobox(res_box, textvariable=self.resolution_var,
                     values=["1280x720", "1920x1080", "2560x1440", "3840x2160",
                             "Caméra native", "Écran native"], state="readonly").pack(padx=8, pady=8, fill=tk.X)

        mon_box = tk.LabelFrame(left, text=" MONITEUR ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        mon_box.pack(fill=tk.X, pady=5)
        self.monitor_var = tk.StringVar(value="0")
        self.monitor_combo = ttk.Combobox(mon_box, textvariable=self.monitor_var,
                                          values=self.screen_source.list_monitors(), state="readonly")
        self.monitor_combo.pack(padx=8, pady=8, fill=tk.X)

        theme_box = tk.LabelFrame(left, text=" THÈME ", bg=DEFAULT_BG,
                                  fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        theme_box.pack(fill=tk.X, pady=5)
        self.theme_var = tk.StringVar(value="green")
        ttk.Combobox(theme_box, textvariable=self.theme_var,
                     values=["green", "red", "blue", "amber"], state="readonly").pack(padx=8, pady=8, fill=tk.X)

        pip_box = tk.LabelFrame(right, text=" PARAMÈTRES PIP ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        pip_box.pack(fill=tk.X, pady=5)
        tk.Label(pip_box, text="Position:", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.pip_pos_var = tk.StringVar(value="bottom-right")
        ttk.Combobox(pip_box, textvariable=self.pip_pos_var,
                     values=["top-left", "top-right", "bottom-left", "bottom-right"],
                     state="readonly").pack(padx=8, pady=2, fill=tk.X)
        tk.Label(pip_box, text="Échelle:", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.pip_scale_var = tk.DoubleVar(value=0.25)
        tk.Scale(pip_box, from_=0.1, to=0.6, resolution=0.05, orient=tk.HORIZONTAL,
                 variable=self.pip_scale_var, bg=DEFAULT_BG, fg=DEFAULT_FG,
                 highlightthickness=0, troughcolor=ACCENT_DIM).pack(padx=8, pady=2, fill=tk.X)
        tk.Label(pip_box, text="Forme:", bg=DEFAULT_BG, fg=DEFAULT_FG).pack(anchor=tk.W, padx=8)
        self.webcam_shape_var = tk.StringVar(value="rectangle")
        ttk.Combobox(pip_box, textvariable=self.webcam_shape_var,
                     values=["rectangle", "rounded", "circle"], state="readonly").pack(padx=8, pady=2, fill=tk.X)

        disp_box = tk.LabelFrame(right, text=" OPTIONS D'AFFICHAGE ", bg=DEFAULT_BG,
                                 fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        disp_box.pack(fill=tk.X, pady=5)
        self.watermark_var = tk.BooleanVar(value=True)
        self.timestamp_var = tk.BooleanVar(value=True)
        self.rec_indicator_var = tk.BooleanVar(value=True)
        self.audio_var = tk.BooleanVar(value=True)
        tk.Checkbutton(disp_box, text="Watermark", variable=self.watermark_var,
                       bg=DEFAULT_BG, fg=DEFAULT_FG, selectcolor=ACCENT_DIM).pack(anchor=tk.W, padx=8)
        tk.Checkbutton(disp_box, text="Horodatage", variable=self.timestamp_var,
                       bg=DEFAULT_BG, fg=DEFAULT_FG, selectcolor=ACCENT_DIM).pack(anchor=tk.W, padx=8)
        tk.Checkbutton(disp_box, text="Indicateur REC", variable=self.rec_indicator_var,
                       bg=DEFAULT_BG, fg=DEFAULT_FG, selectcolor=ACCENT_DIM).pack(anchor=tk.W, padx=8)
        tk.Checkbutton(disp_box, text="Audio micro", variable=self.audio_var,
                       bg=DEFAULT_BG, fg=DEFAULT_FG, selectcolor=ACCENT_DIM).pack(anchor=tk.W, padx=8)

        hot_box = tk.LabelFrame(right, text=" RACCOURCIS CLAVIER ", bg=DEFAULT_BG,
                                fg=DEFAULT_FG, font=(FONT_FAMILY, 10, "bold"))
        hot_box.pack(fill=tk.X, pady=5)
        tk.Label(hot_box,
                 text="F9 = Enregistrer\nF10 = Arrêter\nF11 = Pause\nF12 = Capture",
                 bg=DEFAULT_BG, fg=DEFAULT_FG, font=(MONO_FONT, 9), justify=tk.LEFT).pack(padx=8, pady=8, anchor=tk.W)

        tk.Button(container, text="💾 SAUVEGARDER LES PARAMÈTRES", bg="#004400",
                  fg="white", font=(FONT_FAMILY, 12, "bold"),
                  command=self._save_settings).pack(side=tk.BOTTOM, fill=tk.X, pady=10)

    def _build_history_tab(self):
        top = tk.Frame(self.tab_history, bg=DEFAULT_BG)
        top.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(top, text="FICHIERS ENREGISTRÉS", bg=DEFAULT_BG, fg=DEFAULT_FG,
                 font=(FONT_FAMILY, 12, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Rafraîchir", bg=ACCENT_DIM, fg=DEFAULT_FG,
                  command=self._refresh_history).pack(side=tk.RIGHT)
        tk.Button(top, text="Ouvrir dossier", bg=ACCENT_DIM, fg=DEFAULT_FG,
                  command=self._open_output_dir).pack(side=tk.RIGHT, padx=5)

        self.history_list = tk.Listbox(self.tab_history, bg=DEFAULT_BG, fg=DEFAULT_FG,
                                       selectbackground="#005500", font=(MONO_FONT, 10))
        self.history_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.history_list.bind("<Double-Button-1>", self._on_history_double)

    def _build_logs_tab(self):
        top = tk.Frame(self.tab_logs, bg=DEFAULT_BG)
        top.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(top, text="JOURNAUX SYSTÈME", bg=DEFAULT_BG, fg=DEFAULT_FG,
                 font=(FONT_FAMILY, 12, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Effacer", bg=ACCENT_DIM, fg=DEFAULT_FG,
                  command=self._clear_logs).pack(side=tk.RIGHT)
        self.log_text = tk.Text(self.tab_logs, bg=DEFAULT_BG, fg=DEFAULT_FG,
                                insertbackground=DEFAULT_FG, font=(MONO_FONT, 9),
                                state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _build_about_tab(self):
        frame = tk.Frame(self.tab_about, bg=DEFAULT_BG)
        frame.pack(expand=True)
        tk.Label(frame, text=APP_NAME, bg=DEFAULT_BG, fg=DEFAULT_FG,
                 font=(FONT_FAMILY, 36, "bold")).pack(pady=10)
        tk.Label(frame, text=f"Version {VERSION}", bg=DEFAULT_BG, fg=DEFAULT_FG,
                 font=(FONT_FAMILY, 14)).pack()
        tk.Label(frame, text=f"Développé par {AUTHOR}", bg=DEFAULT_BG, fg=ACCENT_RED,
                 font=(FONT_FAMILY, 14, "bold")).pack(pady=10)
        info = (
            "RECORDER est un outil avancé de capture d'écran et de webcam.\n"
            "Interface cyberpunk green/red, minuterie, overlays, rendu PiP,\n"
            "raccourcis clavier, historique et encodage haute qualité.\n"
            "Les vidéos sont enregistrées directement sur le Bureau par défaut."
        )
        tk.Label(frame, text=info, bg=DEFAULT_BG, fg="#AAAAAA",
                 font=(FONT_FAMILY, 11), justify=tk.CENTER).pack(pady=20)

    def _apply_config(self):
        cfg = self.config
        self.output_dir_var.set(cfg.get("output_dir", get_desktop_path()))
        self.filename_var.set(cfg.get("filename", "RECORDER_capture"))
        self.fps_var.set(cfg.get("fps", 30))
        self.quality_var.set(cfg.get("quality", "Haute"))
        self.mode_var.set(cfg.get("mode", "Écran seul"))
        self.resolution_var.set(cfg.get("resolution", "1920x1080"))
        self.monitor_var.set(str(cfg.get("monitor", 0)))
        self.pip_pos_var.set(cfg.get("pip_position", "bottom-right"))
        self.pip_scale_var.set(cfg.get("pip_scale", 0.25))
        self.webcam_shape_var.set(cfg.get("webcam_shape", "rectangle"))
        self.watermark_var.set(cfg.get("show_watermark", True))
        self.timestamp_var.set(cfg.get("show_timestamp", True))
        self.rec_indicator_var.set(cfg.get("show_rec_indicator", True))
        self.audio_var.set(cfg.get("audio_enabled", True))
        self.overlay_var.set(cfg.get("overlay_text", "HACKERS TCHAD"))
        self.theme_var.set(cfg.get("theme", "green"))
        self.timer_enabled.set(cfg.get("timer_enabled", False))
        self.timer_min_var.set(cfg.get("timer_minutes", 5))
        self._apply_theme()
        self._on_mode_changed(None)

    def _apply_theme(self):
        theme = self.theme_var.get()
        themes = {
            "green": ("#00FF41", "#003B00"),
            "red": ("#FF1A1A", "#3B0000"),
            "blue": ("#00CCFF", "#001A3B"),
            "amber": ("#FFBF00", "#3B2800"),
        }
        fg, dim = themes.get(theme, (DEFAULT_FG, ACCENT_DIM))
        self.root.configure(bg=DEFAULT_BG)
        self.style.configure("TLabel", background=DEFAULT_BG, foreground=fg)
        self.style.configure("TButton", background=dim, foreground=fg)
        self.style.configure("TNotebook.Tab", background=dim, foreground=fg)
        self.style.map("TNotebook.Tab",
                       background=[("selected", "#005500")],
                       foreground=[("selected", "#AAFFAA")])
        self.status.configure(bg=dim, fg=fg)

    def _save_settings(self):
        self.config.set("output_dir", self.output_dir_var.get())
        self.config.set("filename", self.filename_var.get())
        self.config.set("fps", self.fps_var.get())
        self.config.set("quality", self.quality_var.get())
        self.config.set("mode", self.mode_var.get())
        self.config.set("resolution", self.resolution_var.get())
        try:
            self.config.set("monitor", int(self.monitor_var.get().split(":")[0]))
        except Exception:
            self.config.set("monitor", 0)
        self.config.set("pip_position", self.pip_pos_var.get())
        self.config.set("pip_scale", self.pip_scale_var.get())
        self.config.set("webcam_shape", self.webcam_shape_var.get())
        self.config.set("show_watermark", self.watermark_var.get())
        self.config.set("show_timestamp", self.timestamp_var.get())
        self.config.set("show_rec_indicator", self.rec_indicator_var.get())
        self.config.set("audio_enabled", self.audio_var.get())
        self.config.set("overlay_text", self.overlay_var.get())
        self.config.set("theme", self.theme_var.get())
        self.config.set("timer_enabled", self.timer_enabled.get())
        self.config.set("timer_minutes", self.timer_min_var.get())
        self.config.set("window_geometry", self.root.geometry())
        self.config.save()
        self._apply_theme()
        self._update_screen_source()
        self.status.config(text="Paramètres sauvegardés")
        LOGGER.info("Paramètres sauvegardés")

    def _browse_output_dir(self):
        path = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if path:
            self.output_dir_var.set(path)

    def _bind_hotkeys(self):
        self.root.bind("<F9>", lambda e: self.start_recording())
        self.root.bind("<F10>", lambda e: self.stop_recording())
        self.root.bind("<F11>", lambda e: self.pause_recording())
        self.root.bind("<F12>", lambda e: self.take_screenshot())

    def _start_clock(self):
        self.clock_label.config(text=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._start_clock)

    def _on_log_line(self, line):
        def update():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, line + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, update)

    def _clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _on_mode_changed(self, event):
        mode = self.mode_var.get()
        self.composite.set_mode(mode)
        if mode in ("Caméra seule", "Écran + webcam (PiP)", "Webcam + écran (PiP)"):
            if not self.camera_source.active:
                self.toggle_camera()
        LOGGER.info(f"Mode source : {mode}")

    def _update_screen_source(self):
        try:
            idx = int(self.monitor_var.get().split(":")[0])
        except Exception:
            idx = 0
        self.screen_source = ScreenSource(monitor_index=idx)

    def toggle_camera(self):
        if self.camera_source.active:
            self.camera_source.stop()
            self.btn_cam_toggle.config(text="OUVRIR CAMÉRA", bg="#003300")
            self.cam_status.config(text="Caméra fermée", fg=ACCENT_RED)
        else:
            if self.camera_source.start():
                self.btn_cam_toggle.config(text="FERMER CAMÉRA", bg="#550000")
                self.cam_status.config(text="Caméra active", fg=DEFAULT_FG)
            else:
                messagebox.showerror("Caméra", "Impossible d'ouvrir la caméra.")

    def get_active_resolution(self):
        res = self.resolution_var.get()
        if res == "Caméra native":
            return self.camera_source.get_size()
        if res == "Écran native":
            return self.screen_source.get_size()
        return parse_resolution(res)

    def _start_preview(self):
        self.preview_running = True
        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

    def _preview_loop(self):
        interval = 1.0 / 30.0
        while self.preview_running:
            t0 = time.time()
            screen = self.screen_source.read()
            cam = self.camera_source.read() if self.camera_source.active else None
            elapsed = self.engine.get_elapsed() if self.engine.recording else 0
            composite = self.composite.render(screen, cam, self.engine.recording, elapsed)
            self.last_frame = composite
            if composite is not None:
                try:
                    resized = cv2.resize(composite, (720, 405))
                    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb)
                    self.root.after(0, self.preview.update_frame, pil_img)
                    self.root.after(0, self.preview_size_label.config,
                                    {"text": f"{composite.shape[1]}x{composite.shape[0]} @ {self.fps_var.get()}fps"})
                except Exception as exc:
                    LOGGER.error(f"Preview render : {exc}")

            if self.engine.recording:
                self.root.after(0, self.timer_display.config,
                                {"text": format_duration(self.engine.get_elapsed())})
                self.engine.push_frame(composite)
                self._update_live_stats()
            else:
                self.root.after(0, self.timer_display.config, {"text": "00:00:00"})

            if self.engine.recording and self.timer_enabled.get():
                limit = self.timer_min_var.get() * 60
                if self.engine.get_elapsed() >= limit:
                    self.root.after(0, self.stop_recording)

            elapsed_loop = time.time() - t0
            time.sleep(max(0.001, interval - elapsed_loop))

    def _update_live_stats(self):
        txt = (
            f"Frames écrits : {self.engine.frames_written}\n"
            f"Frames perdus : {self.engine.frames_dropped}\n"
            f"Durée         : {format_duration(self.engine.get_elapsed())}\n"
            f"État          : {'PAUSE' if self.engine.paused else 'REC'}"
        )
        self.stats_label.config(text=txt)

    def update_stats_after_stop(self, elapsed):
        txt = (
            f"Dernière session\n"
            f"Durée : {format_duration(elapsed)}\n"
            f"Frames écrits : {self.engine.frames_written}\n"
            f"Frames perdus : {self.engine.frames_dropped}"
        )
        self.stats_label.config(text=txt)

    def start_recording(self):
        if self.engine.recording:
            return
        self._update_screen_source()
        self.composite.overlay_text = self.overlay_var.get()
        self.composite.pip_position = self.pip_pos_var.get()
        self.composite.pip_scale = self.pip_scale_var.get()
        self.composite.webcam_shape = self.webcam_shape_var.get()
        self.composite.show_watermark = self.watermark_var.get()
        self.composite.show_timestamp = self.timestamp_var.get()
        self.composite.show_rec_indicator = self.rec_indicator_var.get()
        self.composite.border_color = DEFAULT_FG if self.theme_var.get() == "green" else ACCENT_RED

        self.engine.configure(
            self.mode_var.get(),
            self.fps_var.get(),
            self.quality_var.get(),
            self.output_dir_var.get(),
            self.filename_var.get(),
            self.get_active_resolution(),
            self.audio_var.get(),
        )
        if self.engine.start():
            self.status.config(text="● ENREGISTREMENT EN COURS", fg=ACCENT_RED)
            self.btn_record.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            LOGGER.info("Enregistrement démarré")

    def stop_recording(self):
        if not self.engine.recording:
            return
        self.engine.stop()
        self.status.config(text="Prêt", fg=DEFAULT_FG)
        self.btn_record.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_pause.config(text="⏸ PAUSE", bg="#444400")
        self.timer_display.config(text="00:00:00")

    def pause_recording(self):
        if not self.engine.recording:
            return
        self.engine.toggle_pause()
        if self.engine.paused:
            self.btn_pause.config(text="▶ REPRENDRE", bg="#004400")
            self.status.config(text="⏸ PAUSE", fg="#FFBF00")
        else:
            self.btn_pause.config(text="⏸ PAUSE", bg="#444400")
            self.status.config(text="● ENREGISTREMENT EN COURS", fg=ACCENT_RED)

    def take_screenshot(self):
        if self.last_frame is None:
            return
        ensure_dir(self.output_dir_var.get())
        path = os.path.join(self.output_dir_var.get(), f"screenshot_{now_str()}.png")
        try:
            cv2.imwrite(path, self.last_frame)
            self.history.append((path, "Screenshot", os.path.getsize(path)))
            self._refresh_history()
            self.status.config(text=f"Capture : {path}")
            LOGGER.info(f"Screenshot : {path}")
        except Exception as exc:
            LOGGER.error(f"Screenshot : {exc}")

    def on_recording_finished(self, path):
        if path and os.path.exists(path):
            size = os.path.getsize(path)
            self.history.append((path, "Vidéo", size))
            self._refresh_history()
            self.status.config(text=f"Vidéo sauvegardée ({format_size(size)})")

    def _refresh_history(self):
        self.history_list.delete(0, tk.END)
        for item, kind, size in reversed(self.history):
            display = f"[{kind}] {os.path.basename(item)} — {format_size(size)}"
            self.history_list.insert(tk.END, display)

    def _on_history_double(self, event):
        selection = self.history_list.curselection()
        if not selection:
            return
        idx = selection[0]
        real_idx = len(self.history) - 1 - idx
        path = self.history[real_idx][0]
        self._open_path(path)

    def _open_output_dir(self):
        self._open_path(self.output_dir_var.get())

    def _open_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            LOGGER.error(f"Ouverture : {exc}")

    def on_close(self):
        self.preview_running = False
        if self.preview_thread:
            self.preview_thread.join(timeout=2)
        self.camera_source.stop()
        if self.engine.recording:
            self.engine.stop()
        self.config.set("window_geometry", self.root.geometry())
        self.config.save()
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    app = RecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
