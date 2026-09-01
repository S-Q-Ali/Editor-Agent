import re
import platform
from typing import Dict, List, Optional


def _get_font_path(font_name: str = "calibri.ttf") -> str:
    system = platform.system()
    if system == "Windows":
        return f"C\\:/Windows/Fonts/{font_name}"
    elif system == "Darwin":
        return f"/System/Library/Fonts/{font_name}"
    else:
        return f"/usr/share/fonts/{font_name}"


def _get_font_path_plain(font_name: str = "calibri.ttf") -> str:
    system = platform.system()
    if system == "Windows":
        return f"C:/Windows/Fonts/{font_name}"
    elif system == "Darwin":
        return f"/System/Library/Fonts/{font_name}"
    else:
        return f"/usr/share/fonts/{font_name}"


CAPTION_TEMPLATES: Dict[str, Dict] = {
    "none": {
        "id": "none",
        "label": "No Captions",
        "description": "No on-screen text",
        "enabled": False,
    },
    "subtitle": {
        "id": "subtitle",
        "label": "Subtitle",
        "description": "Clean white text at the bottom",
        "enabled": True,
        "font": _get_font_path("calibri.ttf"),
        "fontsize": 28,
        "fontcolor": "white",
        "borderw": 2,
        "bordercolor": "black",
        "x": "(w-text_w)/2",
        "y": "h-60",
        "box": False,
    },
    "karaoke": {
        "id": "karaoke",
        "label": "Karaoke",
        "description": "Large yellow text in the center",
        "enabled": True,
        "font": _get_font_path("arialbd.ttf"),
        "fontsize": 48,
        "fontcolor": "yellow",
        "borderw": 3,
        "bordercolor": "black",
        "x": "(w-text_w)/2",
        "y": "(h-text_h)/2",
        "box": False,
    },
    "kids_bubble": {
        "id": "kids_bubble",
        "label": "Kids Bubble",
        "description": "White text on a semi-transparent background",
        "enabled": True,
        "font": _get_font_path("calibri.ttf"),
        "fontsize": 32,
        "fontcolor": "white",
        "borderw": 0,
        "bordercolor": "black",
        "x": "(w-text_w)/2",
        "y": "h-80",
        "box": True,
        "boxcolor": "black@0.5",
        "boxborderw": 8,
    },
    "minimal": {
        "id": "minimal",
        "label": "Minimal",
        "description": "Small subtle text in the corner",
        "enabled": True,
        "font": _get_font_path("calibri.ttf"),
        "fontsize": 20,
        "fontcolor": "white@0.8",
        "borderw": 0,
        "bordercolor": "black",
        "x": "w-text_w-20",
        "y": "20",
        "box": False,
    },
    "bold_center": {
        "id": "bold_center",
        "label": "Bold Center",
        "description": "Very large bold text in the center",
        "enabled": True,
        "font": _get_font_path("arialbd.ttf"),
        "fontsize": 64,
        "fontcolor": "white",
        "borderw": 4,
        "bordercolor": "black",
        "x": "(w-text_w)/2",
        "y": "(h-text_h)/2",
        "box": False,
    },
    "colorful": {
        "id": "colorful",
        "label": "Colorful",
        "description": "Color changes based on song section",
        "enabled": True,
        "font": _get_font_path("arialbd.ttf"),
        "fontsize": 36,
        "fontcolor": "white",
        "borderw": 3,
        "bordercolor": "black",
        "x": "(w-text_w)/2",
        "y": "h-70",
        "box": False,
    },
}

SECTION_COLORS = {
    "chorus": "yellow",
    "verse": "white",
    "bridge": "cyan",
    "intro": "lightgreen",
    "outro": "lightgreen",
    "default": "white",
}


def get_available_templates() -> List[Dict[str, str]]:
    return [
        {"id": t["id"], "label": t["label"], "description": t["description"]}
        for t in CAPTION_TEMPLATES.values()
    ]


def escape_ffmpeg_text(text: str) -> str:
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(";", "\\;")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("%", "%%")
    return text


def get_section_color(section_label: str) -> str:
    label = section_label.lower()
    for key, color in SECTION_COLORS.items():
        if key in label:
            return color
    return SECTION_COLORS["default"]


def build_drawtext_filter(
    lyric_text: str,
    template_id: str,
    start_time: float,
    end_time: float,
    fontsize_override: Optional[int] = None,
    fontcolor_override: Optional[str] = None,
) -> str:
    template = CAPTION_TEMPLATES.get(template_id, CAPTION_TEMPLATES["subtitle"])
    if not template.get("enabled", True):
        return ""

    text = escape_ffmpeg_text(lyric_text)
    font = template["font"]
    fontsize = fontsize_override or template["fontsize"]
    fontcolor = fontcolor_override or template["fontcolor"]
    borderw = template.get("borderw", 0)
    bordercolor = template.get("bordercolor", "black")
    x = template.get("x", "(w-text_w)/2")
    y = template.get("y", "h-60")
    box = template.get("box", False)

    escaped_text = text.replace("'", "\\'")

    opts = (
        f"fontfile='{font}'"
        f":fontsize={fontsize}"
        f":fontcolor={fontcolor}"
        f":text='{escaped_text}'"
        f":x={x}"
        f":y={y}"
        f":borderw={borderw}"
        f":bordercolor={bordercolor}"
        f":enable='between(t,{start_time:.3f},{end_time:.3f})'"
    )

    if box:
        boxcolor = template.get("boxcolor", "black@0.5")
        boxborderw = template.get("boxborderw", 8)
        opts += f":box=1:boxcolor={boxcolor}:boxborderw={boxborderw}"

    return f"drawtext={opts}"


def build_caption_filter_chain(
    events: List[Dict],
    template_id: str,
    fontsize_override: Optional[int] = None,
    fontcolor_override: Optional[str] = None,
) -> str:
    if template_id == "none":
        return ""

    filters = []
    for event in events:
        lyric = event.get("lyric_text", "").strip()
        if not lyric or lyric.startswith("["):
            continue

        start = event.get("timeline_start", 0)
        end = event.get("timeline_end", 0)
        if end - start < 0.1:
            continue

        section = event.get("section", "")
        color = get_section_color(section) if template_id == "colorful" else None

        f = build_drawtext_filter(
            lyric, template_id, start, end,
            fontsize_override,
            color or fontcolor_override,
        )
        if f:
            filters.append(f)

    return ",".join(filters)
