#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   HACKERS TCHAD - ADVANCED SCREEN & CAMERA RECORDER v9.9.9                   ║
║                                                                              ║
║   Auteur  : HACKERS TCHAD                                                    ║
║   Version : 9.9.9 (ULTIMATE EDITION)                                         ║
║   Date    : 2026                                                             ║
║   Style   : Cyberpunk Hacker - Vert/Rouge/Noir                               ║
║                                                                              ║
║   Fonctionnalités principales :                                              ║
║   - Enregistrement d'écran haute qualité (jusqu'à 4K/60 FPS)                 ║
║   - Enregistrement de la webcam intégrée ou externe                          ║
║   - Choix du moniteur à capturer (multi-écrans)                              ║
║   - Choix entre mode ÉCRAN, CAMÉRA ou LES DEUX                               ║
║   - Interface Tkinter avancée et stylisée                                    ║
║   - Sauvegarde automatique sur le Bureau                                     ║
║   - Compteur de minutes en temps réel                                        ║
║   - Prévisualisation en direct                                               ║
║   - Raccourcis clavier globaux                                               ║
║   - Détection des résolutions, codecs, périphériques                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTATIONS GLOBALES
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import cv2
import numpy as np
import mss
import threading
import time
import datetime
import json
import platform
import subprocess
import shutil
import ctypes
import logging
import queue
import random
import string
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from PIL import Image, ImageTk, ImageDraw, ImageFont
from pathlib import Path
from collections import deque

# Gestion optionnelle du son
RECORD_AUDIO = False
try:
    import sounddevice as sd
    import soundfile as sf
    RECORD_AUDIO = True
except ImportError:
    RECORD_AUDIO = False

# Gestion optionnelle des raccourcis globaux
try:
    import keyboard
    GLOBAL_HOTKEYS = True
except ImportError:
    GLOBAL_HOTKEYS = False

# Gestion optionnelle des infos système
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION GLOBALE ET CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "HACKERS TCHAD RECORDER"
APP_VERSION = "9.9.9 ULTIMATE"
APP_AUTHOR = "HACKERS TCHAD"
APP_SIGNATURE = "[HT]"

# Palette cyberpunk / hacker
color = {
    "bg": "#050505",
    "bg2": "#0a0a0a",
    "bg3": "#111111",
    "fg": "#00ff41",
    "fg2": "#00cc33",
    "accent": "#ff0033",
    "accent2": "#cc0022",
    "warn": "#ffcc00",
    "info": "#00ffff",
    "text": "#e0e0e0",
    "disabled": "#555555",
    "border": "#004411",
    "red_border": "#550000",
    "green_glow": "#00ff41",
    "red_glow": "#ff0033",
}

# Polices
font = {
    "mono": ("Consolas", 10),
    "mono_bold": ("Consolas", 10, "bold"),
    "title": ("Consolas", 16, "bold"),
    "big": ("Consolas", 24, "bold"),
    "huge": ("Consolas", 36, "bold"),
    "small": ("Consolas", 8),
}

# Configuration par défaut
DEFAULT_CONFIG = {
    "fps": 30,
    "quality": "high",
    "codec": "mp4v",
    "resolution": "auto",
    "output_dir": "",
    "prefix": "HT_REC_",
    "hotkey_record": "f9",
    "hotkey_stop": "f10",
    "hotkey_screenshot": "f11",
    "theme": "hacker_green",
    "show_preview": True,
    "record_audio": False,
    "cursor": True,
    "monitor": 0,
    "camera_id": 0,
    "mode": "screen",
    "watermark": True,
    "watermark_text": "HACKERS TCHAD",
    "split_screen": False,
    "auto_stop": 0,
}

# Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("HTR")


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_desktop_path():
    """Récupère le chemin du Bureau de l'utilisateur."""
    system = platform.system()
    try:
        if system == "Windows":
            return os.path.join(os.path.expanduser("~"), "Desktop")
        elif system == "Darwin":
            return os.path.join(os.path.expanduser("~"), "Desktop")
        else:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.isdir(desktop):
                return desktop
            return os.path.expanduser("~")
    except Exception as e:
        logger.error(f"Erreur desktop path: {e}")
        return os.path.expanduser("~")


def ensure_dir(path):
    """Crée un répertoire s'il n'existe pas."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Erreur création dossier {path}: {e}")
        return False


def generate_filename(prefix, suffix, ext):
    """Génère un nom de fichier unique avec timestamp."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{timestamp}_{random_id}{suffix}.{ext}"


def format_duration(seconds):
    """Formate une durée en secondes en HH:MM:SS."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_size(size_bytes):
    """Formate une taille en bytes en unités lisibles."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_system_info():
    """Récupère les informations système de base."""
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }
    if HAS_PSUTIL:
        info["cpu_count"] = psutil.cpu_count(logical=True)
        info["ram_total"] = format_size(psutil.virtual_memory().total)
        info["ram_used"] = format_size(psutil.virtual_memory().used)
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    else:
        info["cpu_count"] = "N/A"
        info["ram_total"] = "N/A"
        info["ram_used"] = "N/A"
        info["cpu_percent"] = "N/A"
    return info


def list_available_cameras(max_id=10):
    """Liste les caméras disponibles."""
    cameras = []
    for i in range(max_id):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cameras.append({"id": i, "name": f"Caméra {i} ({width}x{height})", "res": (width, height)})
            cap.release()
    return cameras


def list_available_monitors():
    """Liste les moniteurs disponibles via mss."""
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            result = []
            for idx, mon in enumerate(monitors):
                result.append({
                    "id": idx,
                    "name": f"Moniteur {idx}: {mon['width']}x{mon['height']} @ ({mon['left']},{mon['top']})",
                    "rect": mon,
                })
            return result
    except Exception as e:
        logger.error(f"Erreur liste moniteurs: {e}")
        return [{"id": 0, "name": "Tous les écrans", "rect": {"left": 0, "top": 0, "width": 1920, "height": 1080}}]


def get_cv2_codecs():
    """Retourne les codecs compatibles OpenCV courants."""
    return {
        "mp4v": {"ext": "mp4", "desc": "MPEG-4 (compatible)"},
        "XVID": {"ext": "avi", "desc": "XviD AVI"},
        "MJPG": {"ext": "avi", "desc": "Motion JPEG"},
        "DIV3": {"ext": "avi", "desc": "DivX 3"},
        "H264": {"ext": "mp4", "desc": "H.264 (si installé)"},
        "X264": {"ext": "mp4", "desc": "x264 (si installé)"},
        "avc1": {"ext": "mp4", "desc": "AVC1 (si installé)"},
    }


def draw_hacker_watermark(frame, text="HACKERS TCHAD", color=(0, 255, 65), alpha=0.7):
    """Ajoute un watermark style hacker sur une frame."""
    if frame is None:
        return None
    overlay = frame.copy()
    h, w = frame.shape[:2]
    font_scale = max(w / 1920, 0.5)
    thickness = max(int(font_scale * 2), 1)
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
    x = w - text_size[0] - 20
    y = h - 20
    cv2.putText(overlay, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
    cv2.rectangle(overlay, (x - 10, y - text_size[1] - 10), (w - 10, y + 10), color, 2)
    return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)


def draw_recording_indicator(frame, elapsed_seconds, fps=0):
    """Dessine un indicateur rouge d'enregistrement + timer."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    radius = max(w // 80, 12)
    center = (radius + 20, radius + 20)
    color_red = (0, 0, 255)
    if int(elapsed_seconds * 2) % 2 == 0:
        cv2.circle(frame, center, radius, color_red, -1)
    timer_text = format_duration(elapsed_seconds)
    fps_text = f"{fps:.1f} FPS"
    cv2.putText(frame, f"REC {timer_text} | {fps_text}", (center[0] + radius + 15, center[1] + 8),
                cv2.FONT_HERSHEY_SIMPLEX, max(w / 1600, 0.5), color_red, 1, cv2.LINE_AA)
    return frame


def resize_keep_aspect(frame, max_width, max_height):
    """Redimensionne une frame en conservant le ratio."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)


def apply_matrix_effect(frame, intensity=0.1):
    """Applique un effet matrice léger sur une frame pour la prévisualisation."""
    if frame is None or intensity <= 0:
        return frame
    mask = np.zeros_like(frame)
    h, w = frame.shape[:2]
    num_lines = int(w * intensity / 5)
    for _ in range(num_lines):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        cv2.line(mask, (x, 0), (x, h), (0, int(random.uniform(50, 150)), 0), 1)
    return cv2.addWeighted(frame, 1.0, mask, 0.3, 0)


def overlay_camera_on_screen(screen_frame, cam_frame, position="bottom-right", size_ratio=0.25):
    """Superpose la caméra sur l'écran en mode picture-in-picture."""
    if screen_frame is None or cam_frame is None:
        return screen_frame
    h, w = screen_frame.shape[:2]
    cam_h, cam_w = cam_frame.shape[:2]
    target_w = int(w * size_ratio)
    target_h = int(target_w * cam_h / cam_w)
    cam_resized = cv2.resize(cam_frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
    margin = 20
    if position == "bottom-right":
        x1, y1 = w - target_w - margin, h - target_h - margin
    elif position == "bottom-left":
        x1, y1 = margin, h - target_h - margin
    elif position == "top-right":
        x1, y1 = w - target_w - margin, margin
    elif position == "top-left":
        x1, y1 = margin, margin
    else:
        x1, y1 = w - target_w - margin, h - target_h - margin
    x2, y2 = x1 + target_w, y1 + target_h
    screen_frame[y1:y2, x1:x2] = cam_resized
    cv2.rectangle(screen_frame, (x1, y1), (x2, y2), (0, 255, 65), 2)
    return screen_frame


def make_split_screen(screen_frame, cam_frame):
    """Crée un écran partagé 50/50 entre écran et caméra."""
    if screen_frame is None or cam_frame is None:
        return screen_frame
    h, w = screen_frame.shape[:2]
    cam_resized = cv2.resize(cam_frame, (w // 2, h), interpolation=cv2.INTER_AREA)
    combined = np.zeros((h, w, 3), dtype=np.uint8)
    screen_half = cv2.resize(screen_frame, (w // 2, h), interpolation=cv2.INTER_AREA)
    combined[:, :w // 2] = screen_half
    combined[:, w // 2:] = cam_resized
    cv2.line(combined, (w // 2, 0), (w // 2, h), (0, 255, 65), 2)
    return combined


def add_timestamp_overlay(frame):
    """Ajoute un horodatage sur la frame."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, max(w / 1800, 0.5),
                (0, 255, 65), 1, cv2.LINE_AA)
    return frame


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE DE GESTION DE LA CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class ConfigManager:
    """Gère la sauvegarde et le chargement de la configuration utilisateur."""

    def __init__(self):
        self.config_dir = Path.home() / ".hackers_tchad_recorder"
        self.config_file = self.config_dir / "config.json"
        ensure_dir(self.config_dir)
        self.config = self.load()

    def load(self):
        """Charge la configuration depuis le fichier JSON."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    config = DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except Exception as e:
                logger.error(f"Erreur chargement config: {e}")
        return DEFAULT_CONFIG.copy()

    def save(self):
        """Sauvegarde la configuration dans le fichier JSON."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE D'ENREGISTREMENT AUDIO (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════════

class AudioRecorder:
    """Enregistre l'audio du microphone ou du système si disponible."""

    def __init__(self, output_path, sample_rate=44100, channels=2):
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.thread = None
        self.device = None

    def start(self):
        if not RECORD_AUDIO:
            logger.warning("Module sounddevice/soundfile non installé. Audio désactivé.")
            return False
        try:
            self.recording = True
            self.frames = []
            self.thread = threading.Thread(target=self._record_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            logger.error(f"Erreur démarrage audio: {e}")
            return False

    def _record_loop(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='float32') as stream:
                while self.recording:
                    data, _ = stream.read(1024)
                    self.frames.append(data.copy())
        except Exception as e:
            logger.error(f"Erreur capture audio: {e}")

    def stop(self):
        if not self.recording:
            return False
        self.recording = False
        if self.thread:
            self.thread.join(timeout=2.0)
        try:
            if self.frames:
                audio = np.concatenate(self.frames, axis=0)
                sf.write(self.output_path, audio, self.sample_rate)
                return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde audio: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE D'ENREGISTREMENT VIDÉO
# ═══════════════════════════════════════════════════════════════════════════════

class VideoRecorder:
    """
    Moteur d'enregistrement vidéo avancé.
    Prend en charge l'écran, la caméra, ou les deux en mode picture-in-picture ou split-screen.
    """

    def __init__(self, config_manager, status_callback=None, frame_callback=None):
        self.cfg = config_manager
        self.status_callback = status_callback
        self.frame_callback = frame_callback
        self.recording = False
        self.paused = False
        self.start_time = None
        self.pause_time = 0
        self.frames_recorded = 0
        self.output_path = ""
        self.audio_path = ""
        self.video_writer = None
        self.thread = None
        self.lock = threading.Lock()
        self.frame_queue = queue.Queue(maxsize=5)
        self.actual_fps = 0.0
        self.last_fps_time = time.time()
        self.fps_counter = 0
        self.audio_recorder = None
        self.camera_capture = None
        self.camera_opened = False
        self.sct = None
        self.monitors = list_available_monitors()
        self.cameras = list_available_cameras()
        self._stop_event = threading.Event()

    def set_status(self, message):
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)

    def open_camera(self, camera_id=None):
        """Ouvre la caméra sélectionnée."""
        if camera_id is None:
            camera_id = self.cfg.get("camera_id", 0)
        try:
            if self.camera_capture is not None:
                self.camera_capture.release()
            backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
            self.camera_capture = cv2.VideoCapture(camera_id, backend)
            if not self.camera_capture.isOpened():
                self.set_status(f"[ERREUR] Impossible d'ouvrir la caméra {camera_id}")
                self.camera_opened = False
                return False
            self.camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera_opened = True
            self.set_status(f"[OK] Caméra {camera_id} ouverte")
            return True
        except Exception as e:
            self.set_status(f"[ERREUR] Caméra {camera_id}: {e}")
            self.camera_opened = False
            return False

    def close_camera(self):
        """Ferme la caméra."""
        if self.camera_capture is not None:
            self.camera_capture.release()
            self.camera_capture = None
        self.camera_opened = False
        self.set_status("[OK] Caméra fermée")

    def read_camera_frame(self):
        """Lit une frame depuis la caméra."""
        if not self.camera_opened or self.camera_capture is None:
            return None
        ret, frame = self.camera_capture.read()
        if ret:
            return frame
        return None

    def get_screen_resolution(self):
        """Retourne la résolution de capture selon la configuration."""
        monitor_id = self.cfg.get("monitor", 0)
        if monitor_id >= len(self.monitors):
            monitor_id = 0
        mon = self.monitors[monitor_id]["rect"]
        return mon["width"], mon["height"], mon["left"], mon["top"]

    def setup_video_writer(self, width, height):
        """Initialise l'objet VideoWriter d'OpenCV."""
        codec = self.cfg.get("codec", "mp4v")
        codecs = get_cv2_codecs()
        ext = codecs.get(codec, {}).get("ext", "mp4")
        output_dir = self.cfg.get("output_dir") or get_desktop_path()
        ensure_dir(output_dir)
        filename = generate_filename(self.cfg.get("prefix", "HT_REC_"), "", ext)
        self.output_path = os.path.join(output_dir, filename)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        fps = float(self.cfg.get("fps", 30))
        quality_map = {"low": 0.5, "medium": 1.0, "high": 1.5, "ultra": 2.0}
        scale = quality_map.get(self.cfg.get("quality", "high"), 1.0)
        out_w = int(width * scale)
        out_h = int(height * scale)
        if out_w % 2 != 0:
            out_w += 1
        if out_h % 2 != 0:
            out_h += 1
        try:
            self.video_writer = cv2.VideoWriter(self.output_path, fourcc, fps, (out_w, out_h))
            if not self.video_writer.isOpened():
                self.set_status(f"[ERREUR] Codec {codec} non supporté, fallback vers mp4v")
                fallback_fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self.output_path = self.output_path.replace(f".{ext}", ".mp4")
                self.video_writer = cv2.VideoWriter(self.output_path, fallback_fourcc, fps, (out_w, out_h))
            self.set_status(f"[OK] Fichier vidéo: {self.output_path} ({out_w}x{out_h} @ {fps}fps)")
            return out_w, out_h
        except Exception as e:
            self.set_status(f"[ERREUR] VideoWriter: {e}")
            return None, None

    def capture_screen(self):
        """Capture une frame de l'écran avec mss."""
        try:
            if self.sct is None:
                self.sct = mss.mss()
            monitor_id = self.cfg.get("monitor", 0)
            if monitor_id >= len(self.monitors):
                monitor_id = 0
            monitor = self.monitors[monitor_id]["rect"]
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            if len(img.shape) == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except Exception as e:
            logger.error(f"Erreur capture écran: {e}")
            return None

    def take_screenshot(self):
        """Prend une capture d'écran et la sauvegarde."""
        try:
            output_dir = self.cfg.get("output_dir") or get_desktop_path()
            ensure_dir(output_dir)
            filename = generate_filename(self.cfg.get("prefix", "HT_REC_"), "_SCREENSHOT", "png")
            path = os.path.join(output_dir, filename)
            frame = self.capture_screen()
            if frame is not None:
                if self.cfg.get("watermark", True):
                    frame = draw_hacker_watermark(frame, self.cfg.get("watermark_text", "HACKERS TCHAD"))
                cv2.imwrite(path, frame)
                self.set_status(f"[OK] Screenshot sauvegardé: {path}")
                return path
        except Exception as e:
            self.set_status(f"[ERREUR] Screenshot: {e}")
        return None

    def get_duration(self):
        """Retourne la durée d'enregistrement en secondes."""
        if self.start_time is None:
            return 0
        if self.paused:
            return self.pause_time - self.start_time
        return time.time() - self.start_time - self.total_pause_duration()

    def total_pause_duration(self):
        """Calcule le temps total passé en pause."""
        total = 0.0
        if hasattr(self, '_pause_start') and self._pause_start is not None:
            total += time.time() - self._pause_start
        return getattr(self, '_total_pause', 0.0) + total

    def get_file_size(self):
        """Retourne la taille actuelle du fichier vidéo."""
        try:
            if self.output_path and os.path.exists(self.output_path):
                return os.path.getsize(self.output_path)
        except Exception:
            pass
        return 0

    def start_recording(self):
        """Démarre l'enregistrement selon le mode sélectionné."""
        if self.recording:
            return False
        mode = self.cfg.get("mode", "screen")
        self.frames_recorded = 0
        self.actual_fps = 0.0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.pause_time = 0
        self._pause_start = None
        self._total_pause = 0.0
        self._stop_event.clear()

        if mode == "camera":
            if not self.open_camera(self.cfg.get("camera_id", 0)):
                self.set_status("[ERREUR] Impossible d'ouvrir la caméra pour l'enregistrement")
                return False
            width = int(self.camera_capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
            height = int(self.camera_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        elif mode == "both":
            if not self.open_camera(self.cfg.get("camera_id", 0)):
                self.set_status("[ERREUR] Impossible d'ouvrir la caméra pour le mode combiné")
                return False
            sw, sh, _, _ = self.get_screen_resolution()
            width, height = sw, sh
        else:
            sw, sh, _, _ = self.get_screen_resolution()
            width, height = sw, sh

        out_w, out_h = self.setup_video_writer(width, height)
        if out_w is None or out_h is None:
            return False

        self.recording = True
        self.paused = False
        self.start_time = time.time()
        self.audio_path = self.output_path.replace(os.path.splitext(self.output_path)[1], "_audio.wav")

        if self.cfg.get("record_audio", False):
            self.audio_recorder = AudioRecorder(self.audio_path)
            self.audio_recorder.start()

        self.thread = threading.Thread(target=self._record_loop, args=(mode, out_w, out_h), daemon=True)
        self.thread.start()
        self.set_status(f"[REC] Enregistrement démarré en mode {mode.upper()}")
        return True

    def _record_loop(self, mode, out_w, out_h):
        """Boucle principale d'enregistrement vidéo."""
        fps = float(self.cfg.get("fps", 30))
        target_frame_time = 1.0 / fps if fps > 0 else 0.033
        while self.recording and not self._stop_event.is_set():
            loop_start = time.time()
            if self.paused:
                time.sleep(0.1)
                continue

            frame = None
            try:
                if mode == "screen":
                    frame = self.capture_screen()
                    if frame is not None:
                        frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                elif mode == "camera":
                    frame = self.read_camera_frame()
                    if frame is not None:
                        frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                elif mode == "both":
                    screen_frame = self.capture_screen()
                    cam_frame = self.read_camera_frame()
                    if screen_frame is not None:
                        screen_frame = cv2.resize(screen_frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                        if cam_frame is not None:
                            if self.cfg.get("split_screen", False):
                                frame = make_split_screen(screen_frame, cam_frame)
                            else:
                                frame = overlay_camera_on_screen(screen_frame, cam_frame)
                        else:
                            frame = screen_frame

                if frame is not None:
                    elapsed = self.get_duration()
                    if self.cfg.get("watermark", True):
                        frame = draw_hacker_watermark(frame, self.cfg.get("watermark_text", "HACKERS TCHAD"))
                    frame = draw_recording_indicator(frame, elapsed, self.actual_fps)
                    frame = add_timestamp_overlay(frame)
                    with self.lock:
                        if self.video_writer is not None:
                            self.video_writer.write(frame)
                    self.frames_recorded += 1
                    self.fps_counter += 1
                    if time.time() - self.last_fps_time >= 1.0:
                        self.actual_fps = self.fps_counter / (time.time() - self.last_fps_time)
                        self.fps_counter = 0
                        self.last_fps_time = time.time()
                    if self.frame_callback:
                        self.frame_callback(frame, elapsed)

                    auto_stop = self.cfg.get("auto_stop", 0)
                    if auto_stop > 0 and elapsed >= auto_stop * 60:
                        self.set_status("[AUTO-STOP] Durée maximale atteinte")
                        self.stop_recording()
                        break
            except Exception as e:
                logger.error(f"Erreur boucle enregistrement: {e}")

            elapsed_loop = time.time() - loop_start
            sleep_time = target_frame_time - elapsed_loop
            if sleep_time > 0:
                time.sleep(sleep_time)

    def pause_recording(self):
        """Met l'enregistrement en pause."""
        if not self.recording or self.paused:
            return
        self.paused = True
        self._pause_start = time.time()
        self.set_status("[PAUSE] Enregistrement en pause")

    def resume_recording(self):
        """Reprend l'enregistrement après une pause."""
        if not self.recording or not self.paused:
            return
        if self._pause_start is not None:
            self._total_pause += time.time() - self._pause_start
            self._pause_start = None
        self.paused = False
        self.set_status("[REC] Enregistrement repris")

    def stop_recording(self):
        """Arrête l'enregistrement et libère les ressources."""
        if not self.recording:
            return
        self.recording = False
        self._stop_event.set()
        self.set_status("[STOP] Arrêt de l'enregistrement...")
        if self.thread:
            self.thread.join(timeout=3.0)
        with self.lock:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
        if self.audio_recorder:
            self.audio_recorder.stop()
            self.audio_recorder = None
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None
        self.set_status(f"[OK] Fichier sauvegardé: {self.output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE DE PRÉVISUALISATION CAMÉRA
# ═══════════════════════════════════════════════════════════════════════════════

class CameraPreview:
    """Gère l'aperçu en direct de la caméra dans un canvas Tkinter."""

    def __init__(self, recorder, canvas):
        self.recorder = recorder
        self.canvas = canvas
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.thread = None

    def _loop(self):
        while self.running:
            try:
                frame = self.recorder.read_camera_frame()
                if frame is not None:
                    canvas_w = self.canvas.winfo_width()
                    canvas_h = self.canvas.winfo_height()
                    if canvas_w > 10 and canvas_h > 10:
                        resized = resize_keep_aspect(frame, canvas_w, canvas_h)
                        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(rgb)
                        imgtk = ImageTk.PhotoImage(image=img)
                        self.canvas.imgtk = imgtk
                        self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=imgtk, anchor=tk.CENTER)
            except Exception as e:
                logger.error(f"Erreur aperçu caméra: {e}")
            time.sleep(0.03)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE INTERFACE TKINTER HACKER
# ═══════════════════════════════════════════════════════════════════════════════

class HackerRecorderApp:
    """Interface graphique principale de l'application."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION} - {APP_AUTHOR}")
        self.root.configure(bg=color["bg"])
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background=color["bg2"], foreground=color["fg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=color["bg3"], foreground=color["fg"], font=font["mono_bold"], padding=10)
        self.style.map("TNotebook.Tab", background=[("selected", color["accent2"])], foreground=[("selected", "white")])
        self.style.configure("TCombobox", fieldbackground=color["bg3"], background=color["bg3"], foreground=color["fg"])
        self.style.configure("Horizontal.TProgressbar", background=color["fg"], troughcolor=color["bg3"])

        self.config_manager = ConfigManager()
        if not self.config_manager.get("output_dir"):
            self.config_manager.set("output_dir", get_desktop_path())
            self.config_manager.save()

        self.recorder = VideoRecorder(
            self.config_manager,
            status_callback=self.log_status,
            frame_callback=self.on_frame_recorded
        )
        self.camera_preview = None
        self.preview_active = False
        self.elapsed_seconds = 0
        self.status_history = deque(maxlen=100)

        self.build_ui()
        self.refresh_devices()
        self.setup_hotkeys()
        self.update_clock()
        self.update_timer()
        self.update_system_stats()
        self.log_status("[OK] Application HACKERS TCHAD RECORDER démarrée")

    def build_ui(self):
        """Construit l'interface utilisateur complète."""
        self.main_frame = tk.Frame(self.root, bg=color["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.build_header()

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        self.tab_record = tk.Frame(self.notebook, bg=color["bg2"])
        self.tab_camera = tk.Frame(self.notebook, bg=color["bg2"])
        self.tab_settings = tk.Frame(self.notebook, bg=color["bg2"])
        self.tab_logs = tk.Frame(self.notebook, bg=color["bg2"])
        self.tab_about = tk.Frame(self.notebook, bg=color["bg2"])

        self.notebook.add(self.tab_record, text=" ⏺ ENREGISTRER ")
        self.notebook.add(self.tab_camera, text=" 📷 CAMÉRA ")
        self.notebook.add(self.tab_settings, text=" ⚙ PARAMÈTRES ")
        self.notebook.add(self.tab_logs, text=" 🖥 LOGS ")
        self.notebook.add(self.tab_about, text=" ℹ À PROPOS ")

        self.build_record_tab()
        self.build_camera_tab()
        self.build_settings_tab()
        self.build_logs_tab()
        self.build_about_tab()
        self.build_footer()

    def build_header(self):
        """Crée l'en-tête avec le titre et l'horloge."""
        header = tk.Frame(self.main_frame, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        header.pack(fill=tk.X, pady=(0, 10))

        title = tk.Label(header, text=f"◄ {APP_NAME} ►", bg=color["bg2"], fg=color["fg"], font=font["title"])
        title.pack(side=tk.LEFT, padx=20, pady=10)

        subtitle = tk.Label(header, text=f"by {APP_AUTHOR} | v{APP_VERSION}", bg=color["bg2"], fg=color["accent"], font=font["mono"])
        subtitle.pack(side=tk.LEFT, padx=10, pady=10)

        self.clock_label = tk.Label(header, text="00:00:00", bg=color["bg2"], fg=color["info"], font=font["big"])
        self.clock_label.pack(side=tk.RIGHT, padx=20, pady=10)

    def build_record_tab(self):
        """Construit l'onglet principal d'enregistrement."""
        top = tk.Frame(self.tab_record, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="[ CONTRÔLES D'ENREGISTREMENT ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(pady=10)

        controls = tk.Frame(top, bg=color["bg2"])
        controls.pack(pady=10)

        self.btn_record = tk.Button(controls, text="⏺ ENREGISTRER", bg=color["accent2"], fg="white",
                                    font=font["mono_bold"], width=18, height=2, command=self.start_recording)
        self.btn_record.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(controls, text="⏹ ARRÊTER", bg=color["bg3"], fg=color["fg"],
                                  font=font["mono_bold"], width=18, height=2, command=self.stop_recording)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.btn_pause = tk.Button(controls, text="⏸ PAUSE", bg=color["bg3"], fg=color["fg"],
                                   font=font["mono_bold"], width=18, height=2, command=self.toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=10)

        self.btn_screenshot = tk.Button(controls, text="📸 SCREENSHOT", bg=color["bg3"], fg=color["info"],
                                        font=font["mono_bold"], width=18, height=2, command=self.take_screenshot)
        self.btn_screenshot.pack(side=tk.LEFT, padx=10)

        # Mode d'enregistrement
        mode_frame = tk.Frame(top, bg=color["bg2"])
        mode_frame.pack(pady=10)

        tk.Label(mode_frame, text="MODE:", bg=color["bg2"], fg=color["fg"], font=font["mono_bold"]).pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value=self.config_manager.get("mode", "screen"))
        for m, label in [("screen", "📺 ÉCRAN"), ("camera", "📷 CAMÉRA"), ("both", "📺+📷 LES DEUX")]:
            tk.Radiobutton(mode_frame, text=label, variable=self.mode_var, value=m,
                           bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                           command=self.on_mode_changed).pack(side=tk.LEFT, padx=10)

        self.split_var = tk.BooleanVar(value=self.config_manager.get("split_screen", False))
        tk.Checkbutton(mode_frame, text="Split-screen", variable=self.split_var,
                       bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                       command=self.save_settings).pack(side=tk.LEFT, padx=20)

        self.preview_var = tk.BooleanVar(value=self.config_manager.get("show_preview", True))
        tk.Checkbutton(mode_frame, text="Prévisualisation", variable=self.preview_var,
                       bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                       command=self.save_settings).pack(side=tk.LEFT, padx=10)

        # Timer et stats
        timer_frame = tk.Frame(top, bg=color["bg2"])
        timer_frame.pack(pady=10)

        tk.Label(timer_frame, text="DURÉE:", bg=color["bg2"], fg=color["fg"], font=font["mono_bold"]).pack(side=tk.LEFT, padx=5)
        self.timer_label = tk.Label(timer_frame, text="00:00:00", bg=color["bg2"], fg=color["accent"], font=font["huge"])
        self.timer_label.pack(side=tk.LEFT, padx=20)

        self.stats_label = tk.Label(timer_frame, text="FPS: 0.0\nFrames: 0\nTaille: 0 B",
                                    bg=color["bg2"], fg=color["info"], font=font["mono"], justify=tk.LEFT)
        self.stats_label.pack(side=tk.LEFT, padx=30)

        # Zone de prévisualisation
        bottom = tk.Frame(self.tab_record, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        bottom.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom, text="[ APERÇU EN DIRECT ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(pady=5)

        self.preview_canvas = tk.Canvas(bottom, bg="black", highlightbackground=color["border"], highlightthickness=2)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def build_camera_tab(self):
        """Construit l'onglet de gestion de la caméra."""
        top = tk.Frame(self.tab_camera, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="[ CONTRÔLES CAMÉRA ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(pady=10)

        controls = tk.Frame(top, bg=color["bg2"])
        controls.pack(pady=10)

        tk.Label(controls, text="CAMÉRA:", bg=color["bg2"], fg=color["fg"], font=font["mono_bold"]).pack(side=tk.LEFT, padx=5)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(controls, textvariable=self.camera_var, state="readonly", width=45, font=font["mono"])
        self.camera_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(controls, text="🔄 RAFRAÎCHIR", bg=color["bg3"], fg=color["fg"], font=font["mono_bold"],
                  command=self.refresh_cameras).pack(side=tk.LEFT, padx=10)
        tk.Button(controls, text="▶ OUVRIR", bg=color["accent2"], fg="white", font=font["mono_bold"],
                  command=self.open_selected_camera).pack(side=tk.LEFT, padx=10)
        tk.Button(controls, text="⏹ FERMER", bg=color["bg3"], fg=color["warn"], font=font["mono_bold"],
                  command=self.close_camera).pack(side=tk.LEFT, padx=10)

        bottom = tk.Frame(self.tab_camera, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        bottom.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom, text="[ APERÇU CAMÉRA ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(pady=10)

        self.camera_canvas = tk.Canvas(bottom, bg="black", highlightbackground=color["border"], highlightthickness=2)
        self.camera_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.camera_preview = CameraPreview(self.recorder, self.camera_canvas)

    def build_settings_tab(self):
        """Construit l'onglet des paramètres."""
        container = tk.Frame(self.tab_settings, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(container, text="[ PARAMÈTRES AVANCÉS ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(pady=10)

        grid = tk.Frame(container, bg=color["bg2"])
        grid.pack(padx=20, pady=10, fill=tk.X)

        tk.Label(grid, text="FPS:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.fps_var = tk.StringVar(value=str(self.config_manager.get("fps", 30)))
        fps_combo = ttk.Combobox(grid, textvariable=self.fps_var, values=["15", "24", "30", "60", "120"], width=10, font=font["mono"])
        fps_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        fps_combo.bind("<<ComboboxSelected>>", self.save_settings)

        tk.Label(grid, text="QUALITÉ:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.StringVar(value=self.config_manager.get("quality", "high"))
        quality_combo = ttk.Combobox(grid, textvariable=self.quality_var, values=["low", "medium", "high", "ultra"], width=10, font=font["mono"])
        quality_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        quality_combo.bind("<<ComboboxSelected>>", self.save_settings)

        tk.Label(grid, text="CODEC:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.codec_var = tk.StringVar(value=self.config_manager.get("codec", "mp4v"))
        codec_combo = ttk.Combobox(grid, textvariable=self.codec_var, values=list(get_cv2_codecs().keys()), width=10, font=font["mono"])
        codec_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        codec_combo.bind("<<ComboboxSelected>>", self.save_settings)

        tk.Label(grid, text="MONITEUR:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.monitor_var = tk.StringVar()
        self.monitor_combo = ttk.Combobox(grid, textvariable=self.monitor_var, state="readonly", width=45, font=font["mono"])
        self.monitor_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        self.monitor_combo.bind("<<ComboboxSelected>>", self.on_monitor_changed)

        tk.Label(grid, text="DOSSIER:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=4, column=0, sticky=tk.W, pady=5)
        out_frame = tk.Frame(grid, bg=color["bg2"])
        out_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        self.output_entry = tk.Entry(out_frame, width=40, bg=color["bg3"], fg=color["fg"], insertbackground=color["fg"], font=font["mono"])
        self.output_entry.pack(side=tk.LEFT)
        self.output_entry.insert(0, self.config_manager.get("output_dir", get_desktop_path()))
        tk.Button(out_frame, text="PARCOURIR", bg=color["bg3"], fg=color["fg"], font=font["mono_bold"],
                  command=self.choose_output_dir).pack(side=tk.LEFT, padx=5)

        tk.Label(grid, text="PRÉFIXE:", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.prefix_var = tk.StringVar(value=self.config_manager.get("prefix", "HT_REC_"))
        prefix_entry = tk.Entry(grid, textvariable=self.prefix_var, width=20, bg=color["bg3"], fg=color["fg"],
                                insertbackground=color["fg"], font=font["mono"])
        prefix_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        prefix_entry.bind("<KeyRelease>", self.save_settings)

        self.watermark_var = tk.BooleanVar(value=self.config_manager.get("watermark", True))
        tk.Checkbutton(grid, text="Watermark", variable=self.watermark_var,
                       bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                       command=self.save_settings).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.watermark_text_var = tk.StringVar(value=self.config_manager.get("watermark_text", "HACKERS TCHAD"))
        wm_entry = tk.Entry(grid, textvariable=self.watermark_text_var, width=30, bg=color["bg3"], fg=color["fg"],
                            insertbackground=color["fg"], font=font["mono"])
        wm_entry.grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        wm_entry.bind("<KeyRelease>", self.save_settings)

        self.cursor_var = tk.BooleanVar(value=self.config_manager.get("cursor", True))
        tk.Checkbutton(grid, text="Capturer le curseur", variable=self.cursor_var,
                       bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                       command=self.save_settings).grid(row=7, column=0, sticky=tk.W, pady=5)

        self.audio_var = tk.BooleanVar(value=self.config_manager.get("record_audio", False))
        tk.Checkbutton(grid, text="Enregistrer l'audio (micro)", variable=self.audio_var,
                       bg=color["bg2"], fg=color["fg"], selectcolor=color["bg3"], font=font["mono"],
                       command=self.save_settings).grid(row=7, column=1, sticky=tk.W, padx=5, pady=5)

        tk.Label(grid, text="ARRÊT AUTO (min):", bg=color["bg2"], fg=color["fg"], font=font["mono"]).grid(row=8, column=0, sticky=tk.W, pady=5)
        self.auto_stop_var = tk.StringVar(value=str(self.config_manager.get("auto_stop", 0)))
        auto_stop_combo = ttk.Combobox(grid, textvariable=self.auto_stop_var, values=["0", "5", "10", "15", "30", "60"], width=10, font=font["mono"])
        auto_stop_combo.grid(row=8, column=1, sticky=tk.W, padx=5, pady=5)
        auto_stop_combo.bind("<<ComboboxSelected>>", self.save_settings)

        action_frame = tk.Frame(container, bg=color["bg2"])
        action_frame.pack(pady=20)

        tk.Button(action_frame, text="SAUVEGARDER", bg=color["bg3"], fg=color["fg"], font=font["mono_bold"],
                  command=self.save_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="RÉINITIALISER", bg=color["accent2"], fg="white", font=font["mono_bold"],
                  command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="OUVRIR DOSSIER", bg=color["bg3"], fg=color["info"], font=font["mono_bold"],
                  command=self.open_output_folder).pack(side=tk.LEFT, padx=5)

        info_text = "[CODECS] mp4v = compatible partout | XVID/MJPG = AVI | H264/X264 = nécessite codec installé"
        tk.Label(container, text=info_text, bg=color["bg2"], fg=color["warn"], font=font["small"]).pack(pady=5)

    def build_logs_tab(self):
        """Construit l'onglet des logs."""
        top = tk.Frame(self.tab_logs, bg=color["bg2"])
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="[ CONSOLE HACKERS TCHAD ]", bg=color["bg2"], fg=color["accent"],
                 font=font["mono_bold"]).pack(side=tk.LEFT, padx=10, pady=10)

        tk.Button(top, text="EFFACER", bg=color["bg3"], fg=color["fg"], font=font["mono_bold"],
                  command=self.clear_logs).pack(side=tk.RIGHT, padx=10)
        tk.Button(top, text="COPIER", bg=color["bg3"], fg=color["info"], font=font["mono_bold"],
                  command=self.copy_logs).pack(side=tk.RIGHT, padx=10)

        self.log_text = scrolledtext.ScrolledText(self.tab_logs, bg=color["bg3"], fg=color["fg"],
                                                  insertbackground=color["fg"], font=font["mono"],
                                                  state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def build_about_tab(self):
        """Construit l'onglet À propos."""
        frame = tk.Frame(self.tab_about, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ascii_art = """
        ██╗  ██╗ █████╗  ██████╗██╗  ██╗███████╗██████╗ ███████╗
        ██║  ██║██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗██╔════╝
        ███████║███████║██║     █████╔╝ █████╗  ██████╔╝███████╗
        ██╔══██║██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗╚════██║
        ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║███████║
        ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝
                              TCHAD
        """
        tk.Label(frame, text=ascii_art, bg=color["bg2"], fg=color["fg"], font=("Consolas", 8)).pack(pady=10)

        about_text = (
            f"Application : {APP_NAME}\n"
            f"Version     : {APP_VERSION}\n"
            f"Auteur      : {APP_AUTHOR}\n"
            f"License     : Open Source - Éducation\n\n"
            "Cet outil avancé permet d'enregistrer l'écran, la caméra,\n"
            "ou les deux simultanément avec un style cyberpunk hacker.\n\n"
            "Utilisez-le de manière responsable et légale.\n\n"
            "Fonctionnalités:\n"
            "- Capture écran haute qualité\n"
            "- Capture webcam\n"
            "- Mode écran partagé / incrustation\n"
            "- Sélection du moniteur\n"
            "- Watermark personnalisable\n"
            "- Prévisualisation en direct\n"
            "- Screenshot instantané\n"
            "- Audio micro (optionnel)\n"
        )
        tk.Label(frame, text=about_text, bg=color["bg2"], fg=color["text"], font=font["mono"], justify=tk.LEFT).pack(pady=10)

        sys_info = get_system_info()
        sys_text = (
            f"Système : {sys_info.get('os')} {sys_info.get('release')}\n"
            f"Machine : {sys_info.get('machine')}\n"
            f"Python  : {sys_info.get('python')}\n"
            f"RAM     : {sys_info.get('ram_total', 'N/A')}"
        )
        tk.Label(frame, text=sys_text, bg=color["bg2"], fg=color["info"], font=font["mono"], justify=tk.LEFT).pack(pady=10)

        self.sys_info_label = tk.Label(frame, text="", bg=color["bg2"], fg=color["warn"], font=font["mono"])
        self.sys_info_label.pack(pady=5)

    def build_footer(self):
        """Crée le pied de page avec barre de statut."""
        footer = tk.Frame(self.main_frame, bg=color["bg2"], highlightbackground=color["border"], highlightthickness=1)
        footer.pack(fill=tk.X, pady=(10, 0))

        self.status_label = tk.Label(footer, text="Prêt", bg=color["bg2"], fg=color["fg"], font=font["mono"], anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)

        self.rec_indicator = tk.Label(footer, text="●", bg=color["bg2"], fg=color["disabled"], font=("Consolas", 14))
        self.rec_indicator.pack(side=tk.RIGHT, padx=10)

    def refresh_devices(self):
        """Rafraîchit la liste des caméras et moniteurs."""
        self.refresh_monitors()
        self.refresh_cameras()

    def refresh_monitors(self):
        """Met à jour le combobox des moniteurs."""
        monitors = self.recorder.monitors
        names = [m["name"] for m in monitors]
        self.monitor_combo["values"] = names
        current = self.config_manager.get("monitor", 0)
        if current < len(names):
            self.monitor_combo.current(current)
        else:
            self.monitor_combo.current(0)

    def refresh_cameras(self):
        """Met à jour le combobox des caméras."""
        cameras = self.recorder.cameras
        if not cameras:
            cameras = [{"id": 0, "name": "Caméra 0 (défaut)"}]
        names = [c["name"] for c in cameras]
        self.camera_combo["values"] = names
        current = self.config_manager.get("camera_id", 0)
        if current < len(names):
            self.camera_combo.current(current)
        else:
            self.camera_combo.current(0)

    def on_monitor_changed(self, event=None):
        """Callback changement de moniteur."""
        idx = self.monitor_combo.current()
        self.config_manager.set("monitor", idx)
        self.config_manager.save()

    def on_mode_changed(self):
        """Callback changement de mode d'enregistrement."""
        mode = self.mode_var.get()
        self.config_manager.set("mode", mode)
        self.config_manager.save()
        self.log_status(f"[MODE] Mode sélectionné: {mode.upper()}")

    def choose_output_dir(self):
        """Ouvre un dialogue pour choisir le dossier de sortie."""
        path = filedialog.askdirectory(initialdir=self.config_manager.get("output_dir", get_desktop_path()))
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)
            self.save_settings()

    def open_output_folder(self):
        """Ouvre le dossier de sortie dans l'explorateur."""
        path = self.config_manager.get("output_dir", get_desktop_path())
        if not os.path.isdir(path):
            ensure_dir(path)
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log_status(f"[ERREUR] Impossible d'ouvrir le dossier: {e}")

    def save_settings(self, event=None):
        """Sauvegarde tous les paramètres."""
        try:
            self.config_manager.set("fps", int(self.fps_var.get()))
        except ValueError:
            self.config_manager.set("fps", 30)
        self.config_manager.set("quality", self.quality_var.get())
        self.config_manager.set("codec", self.codec_var.get())
        self.config_manager.set("monitor", self.monitor_combo.current())
        self.config_manager.set("output_dir", self.output_entry.get())
        self.config_manager.set("prefix", self.prefix_var.get())
        self.config_manager.set("watermark", self.watermark_var.get())
        self.config_manager.set("watermark_text", self.watermark_text_var.get())
        self.config_manager.set("cursor", self.cursor_var.get())
        self.config_manager.set("record_audio", self.audio_var.get())
        self.config_manager.set("split_screen", self.split_var.get())
        self.config_manager.set("show_preview", self.preview_var.get())
        self.config_manager.set("mode", self.mode_var.get())
        try:
            self.config_manager.set("auto_stop", int(self.auto_stop_var.get()))
        except ValueError:
            self.config_manager.set("auto_stop", 0)
        try:
            self.config_manager.set("camera_id", self.camera_combo.current())
        except Exception:
            pass
        self.config_manager.save()

    def reset_settings(self):
        """Réinitialise les paramètres par défaut."""
        if messagebox.askyesno("Réinitialiser", "Voulez-vous vraiment réinitialiser les paramètres ?"):
            self.config_manager.config = DEFAULT_CONFIG.copy()
            self.config_manager.set("output_dir", get_desktop_path())
            self.config_manager.save()
            self.root.destroy()
            main()

    def setup_hotkeys(self):
        """Configure les raccourcis clavier globaux si disponibles."""
        if GLOBAL_HOTKEYS:
            try:
                keyboard.add_hotkey(self.config_manager.get("hotkey_record", "f9"), self.start_recording)
                keyboard.add_hotkey(self.config_manager.get("hotkey_stop", "f10"), self.stop_recording)
                keyboard.add_hotkey(self.config_manager.get("hotkey_screenshot", "f11"), self.take_screenshot)
                self.log_status("[HOTKEYS] Raccourcis globaux activés (F9/F10/F11)")
            except Exception as e:
                self.log_status(f"[WARN] Raccourcis globaux indisponibles: {e}")
        else:
            self.log_status("[WARN] Module 'keyboard' non installé. Raccourcis globaux désactivés.")

    def start_recording(self):
        """Démarre l'enregistrement."""
        if self.recorder.recording:
            return
        self.save_settings()
        success = self.recorder.start_recording()
        if success:
            self.btn_record.config(state=tk.DISABLED, bg=color["disabled"])
            self.btn_stop.config(state=tk.NORMAL, bg=color["accent"])
            self.rec_indicator.config(fg=color["accent"])
            if self.preview_var.get():
                self.preview_active = True

    def stop_recording(self):
        """Arrête l'enregistrement."""
        if not self.recorder.recording:
            return
        self.recorder.stop_recording()
        self.btn_record.config(state=tk.NORMAL, bg=color["accent2"])
        self.btn_stop.config(state=tk.NORMAL, bg=color["bg3"])
        self.btn_pause.config(text="⏸ PAUSE")
        self.rec_indicator.config(fg=color["disabled"])
        self.preview_active = False
        self.preview_canvas.delete("all")
        messagebox.showinfo("Enregistrement terminé", f"Fichier sauvegardé:\n{self.recorder.output_path}")

    def toggle_pause(self):
        """Bascule pause/reprise."""
        if not self.recorder.recording:
            return
        if self.recorder.paused:
            self.recorder.resume_recording()
            self.btn_pause.config(text="⏸ PAUSE")
        else:
            self.recorder.pause_recording()
            self.btn_pause.config(text="▶ REPRENDRE")

    def take_screenshot(self):
        """Prend un screenshot."""
        path = self.recorder.take_screenshot()
        if path:
            self.log_status(f"[OK] Screenshot: {path}")

    def open_selected_camera(self):
        """Ouvre la caméra sélectionnée dans l'onglet caméra."""
        idx = self.camera_combo.current()
        self.config_manager.set("camera_id", idx)
        self.config_manager.save()
        if self.recorder.open_camera(idx):
            self.camera_preview.start()
            self.log_status(f"[CAM] Aperçu caméra {idx} démarré")
        else:
            messagebox.showerror("Caméra", f"Impossible d'ouvrir la caméra {idx}")

    def close_camera(self):
        """Ferme la caméra."""
        self.camera_preview.stop()
        self.recorder.close_camera()
        self.camera_canvas.delete("all")

    def on_frame_recorded(self, frame, elapsed):
        """Callback appelé à chaque frame enregistrée."""
        self.elapsed_seconds = elapsed
        if self.preview_var.get() and self.preview_active:
            self.update_preview(frame)

    def update_preview(self, frame):
        """Met à jour la prévisualisation en direct."""
        try:
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            if canvas_w < 10 or canvas_h < 10:
                return
            resized = resize_keep_aspect(frame, canvas_w, canvas_h)
            if resized is None:
                return
            resized = apply_matrix_effect(resized, intensity=0.05)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.preview_canvas.imgtk = imgtk
            self.preview_canvas.create_image(canvas_w // 2, canvas_h // 2, image=imgtk, anchor=tk.CENTER)
        except Exception as e:
            logger.error(f"Erreur update preview: {e}")

    def update_clock(self):
        """Met à jour l'horloge."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def update_timer(self):
        """Met à jour le timer d'enregistrement et les stats."""
        if self.recorder.recording:
            elapsed = self.recorder.get_duration()
            self.timer_label.config(text=format_duration(elapsed))
            size = self.recorder.get_file_size()
            stats = (
                f"FPS: {self.recorder.actual_fps:.1f}\n"
                f"Frames: {self.recorder.frames_recorded}\n"
                f"Taille: {format_size(size)}"
            )
            self.stats_label.config(text=stats)
            if int(elapsed * 2) % 2 == 0:
                self.rec_indicator.config(fg=color["accent"])
            else:
                self.rec_indicator.config(fg=color["accent2"])
        else:
            self.timer_label.config(text="00:00:00")
            self.stats_label.config(text="FPS: 0.0\nFrames: 0\nTaille: 0 B")
            self.rec_indicator.config(fg=color["disabled"])
        self.root.after(200, self.update_timer)

    def update_system_stats(self):
        """Met à jour les statistiques système."""
        if HAS_PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                text = f"CPU: {cpu}% | RAM: {ram}%"
                if hasattr(self, 'sys_info_label'):
                    self.sys_info_label.config(text=text)
                self.status_label.config(text=f"{self.status_history[-1] if self.status_history else 'Prêt'} | {text}")
            except Exception:
                pass
        self.root.after(2000, self.update_system_stats)

    def log_status(self, message):
        """Ajoute un message dans les logs et la barre de statut."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full = f"[{timestamp}] {message}"
        self.status_history.append(full)
        self.status_label.config(text=full)
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, full + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def clear_logs(self):
        """Efface les logs."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def copy_logs(self):
        """Copie les logs dans le presse-papiers."""
        try:
            text = self.log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_status("[OK] Logs copiés dans le presse-papiers")
        except Exception as e:
            self.log_status(f"[ERREUR] Copie logs: {e}")

    def on_closing(self):
        """Gestion de la fermeture de l'application."""
        if self.recorder.recording:
            if not messagebox.askyesno("Quitter", "Un enregistrement est en cours. Voulez-vous l'arrêter et quitter ?"):
                return
            self.recorder.stop_recording()
        if self.camera_preview:
            self.camera_preview.stop()
        self.close_camera()
        self.save_settings()
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS SUPPLÉMENTAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def check_dependencies():
    """Vérifie que les dépendances principales sont installées."""
    required = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "PIL": "Pillow",
        "mss": "mss",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def print_banner():
    """Affiche la bannière dans la console."""
    banner = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                  {APP_NAME} v{APP_VERSION}              ║
    ║                      by {APP_AUTHOR}                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def handle_cli_args():
    """Gère les arguments en ligne de commande."""
    args = sys.argv[1:]
    config = {}
    if "--screen" in args:
        config["mode"] = "screen"
    if "--camera" in args:
        config["mode"] = "camera"
    if "--both" in args:
        config["mode"] = "both"
    if "--no-gui" in args:
        config["no_gui"] = True
    return config


def console_mode(config):
    """Mode console sans interface graphique."""
    print_banner()
    print("Mode console activé. Appuyez sur Ctrl+C pour arrêter.")
    cfg = ConfigManager()
    for key, value in config.items():
        if key != "no_gui":
            cfg.set(key, value)
    recorder = VideoRecorder(cfg, status_callback=print)
    try:
        recorder.start_recording()
        while recorder.recording:
            time.sleep(1)
            print(f"Durée: {format_duration(recorder.get_duration())}")
    except KeyboardInterrupt:
        print("Arrêt demandé...")
        recorder.stop_recording()


def create_shortcut_windows():
    """Crée un raccourci sur le Bureau Windows (optionnel)."""
    if platform.system() != "Windows":
        return False
    try:
        import winshell
        from win32com.client import Dispatch
        desktop = winshell.desktop()
        path = os.path.join(desktop, "HACKERS TCHAD RECORDER.lnk")
        target = os.path.abspath(sys.argv[0])
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = os.path.dirname(target)
        shortcut.IconLocation = target
        shortcut.save()
        return True
    except Exception as e:
        logger.error(f"Erreur création raccourci: {e}")
        return False


def show_splash(root):
    """Affiche un écran de démarrage temporaire."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg=color["bg"])
    width, height = 500, 300
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(splash, text=APP_NAME, bg=color["bg"], fg=color["fg"], font=font["title"]).pack(pady=20)
    tk.Label(splash, text=f"v{APP_VERSION}", bg=color["bg"], fg=color["accent"], font=font["mono_bold"]).pack()
    tk.Label(splash, text=f"by {APP_AUTHOR}", bg=color["bg"], fg=color["info"], font=font["mono"]).pack(pady=10)

    progress = ttk.Progressbar(splash, mode="indeterminate", length=400)
    progress.pack(pady=30)
    progress.start()

    splash.after(2500, splash.destroy)
    root.wait_window(splash)


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Fonction principale de l'application."""
    print_banner()
    missing = check_dependencies()
    if missing:
        print("[ERREUR] Dépendances manquantes:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("Installez-les avec: pip install " + " ".join(missing))
        sys.exit(1)

    cli_config = handle_cli_args()
    if cli_config.get("no_gui", False):
        console_mode(cli_config)
        return

    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    show_splash(root)
    app = HackerRecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
