# RECORDER — HACKERS TCHAD EDITION

**RECORDER** est une application Python avancée de capture d'écran et de webcam, avec une interface graphique **tkinter** stylisée en vert/rouge cyberpunk. Elle a été développée par **HACKERS TCHAD**.

## Fonctionnalités

- Enregistrement de l'écran (full screen ou moniteur sélectionné)
- Enregistrement de la webcam avec ouverture/fermeture manuelle
- Modes composites : écran seul, caméra seule, écran + webcam (PiP), webcam + écran (PiP)
- Minuterie programmable (arrêt automatique après N minutes)
- Pause / reprise de l'enregistrement
- Capture d'écran instantanée
- Audio microphone optionnel (si PyAudio est disponible)
- Overlay texte personnalisable, watermark, horodatage, indicateur REC clignotant
- Choix de la résolution, du FPS, du codec et de la qualité
- Historique des fichiers avec ouverture directe
- Journal système en temps réel
- Raccourcis clavier : F9, F10, F11, F12
- Thèmes green / red / blue / amber
- Interface single-page avec onglets

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python RECORDER.py
```

## Fichier de configuration

Les paramètres sont sauvegardés dans `recorder_config.json`.

## Auteur

Développé avec passion par **HACKERS TCHAD**.
