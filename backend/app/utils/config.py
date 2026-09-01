import os
import sys
import yaml
import platform
from pathlib import Path
from typing import Any, Dict


if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent.parent.parent

CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.yaml"


def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)
    return get_default_config()


def get_default_config() -> Dict[str, Any]:
    return {
        "video": {
            "default_width": int(os.getenv("DEFAULT_WIDTH", "1920")),
            "default_height": int(os.getenv("DEFAULT_HEIGHT", "1080")),
            "fps": int(os.getenv("DEFAULT_FPS", "30")),
            "aspect_ratio": "16:9",
        },
        "whisper": {
            "model_size": os.getenv("WHISPER_MODEL", "small"),
            "device": "cpu",
            "compute_type": "int8",
        },
        "editing": {
            "default_style": "adaptive",
            "beat_sync": True,
            "lyric_sync": True,
            "repetition_penalty": True,
        },
        "render": {
            "codec": os.getenv("VIDEO_CODEC", "h264"),
            "audio_codec": os.getenv("AUDIO_CODEC", "aac"),
            "preset": "medium",
            "crf": 23,
        },
        "ai": {
            "model_agnostic": True,
            "hardware_detection": True,
            "cpu_fallback": True,
        },
        "quality_control": {
            "max_black_frame_duration": 0.5,
            "min_audio_level": -60,
            "max_repetition_score": 0.8,
            "min_confidence_threshold": 0.5,
        },
        "captions": {
            "default_template": "subtitle",
            "font_path": get_system_font_path("calibri.ttf"),
            "available_templates": [
                "none", "subtitle", "karaoke", "kids_bubble",
                "minimal", "bold_center", "colorful",
            ],
        },
    }


def get_system_font_path(font_name: str = "calibri.ttf") -> str:
    system = platform.system()
    if system == "Windows":
        return f"C:/Windows/Fonts/{font_name}"
    elif system == "Darwin":
        return f"/System/Library/Fonts/{font_name}"
    else:
        return f"/usr/share/fonts/{font_name}"


def get_project_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path.home() / "EditorAgent" / "projects"
    return Path(os.getenv("PROJECTS_DIR", "./projects")).resolve()


def get_models_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path.home() / "EditorAgent" / "models"
    return Path(os.getenv("MODELS_DIR", "./models")).resolve()
