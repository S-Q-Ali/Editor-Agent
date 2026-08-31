import re
from typing import Dict, List, Optional


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
        "font": "C\\:/Windows/Fonts/calibri.ttf",
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
        "font": "C\\:/Windows/Fonts/arialbd.ttf",
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
        "font": "C\\:/Windows/Fonts/calibri.ttf",
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
        "font": "C\\:/Windows/Fonts/calibri.ttf",
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
        "font": "C\\:/Windows/Fonts/arialbd.ttf",
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
        "font": "C\\:/Windows/Fonts/arialbd.ttf",
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
    "verse": "white",
    "chorus": "yellow",
    "bridge": "cyan",
    "intro": "lightgreen",
    "outro": "lightgreen",
    "default": "white",
}


def get_template(template_id: str) -> Optional[Dict]:
    return CAPTION_TEMPLATES.get(template_id)


def get_available_templates() -> List[Dict]:
    return [
        {"id": t["id"], "label": t["label"], "description": t["description"]}
        for t in CAPTION_TEMPLATES.values()
    ]


def escape_ffmpeg_text(text: str) -> str:
    text = text.replace("\\", "\\\\\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace(";", "\\;")
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
    section_label: str = "",
    fontsize_override: Optional[int] = None,
    fontcolor_override: Optional[str] = None,
) -> str:
    template = CAPTION_TEMPLATES.get(template_id)
    if not template or not template.get("enabled", False):
        return ""

    if not lyric_text or lyric_text.strip() == "":
        return ""

    escaped_text = escape_ffmpeg_text(lyric_text)

    font = template.get("font", "C\\:/Windows/Fonts/calibri.ttf")
    fontsize = fontsize_override or template.get("fontsize", 28)

    if fontcolor_override:
        fontcolor = fontcolor_override
    elif template_id == "colorful" and section_label:
        fontcolor = get_section_color(section_label)
    else:
        fontcolor = template.get("fontcolor", "white")

    borderw = template.get("borderw", 0)
    bordercolor = template.get("bordercolor", "black")
    x = template.get("x", "(w-text_w)/2")
    y = template.get("y", "h-60")

    parts = [
        f"drawtext=fontfile='{font}'",
        f"text='{escaped_text}'",
        f"fontsize={fontsize}",
        f"fontcolor={fontcolor}",
    ]

    if borderw > 0:
        parts.append(f"borderw={borderw}")
        parts.append(f"bordercolor={bordercolor}")

    if template.get("box", False):
        boxcolor = template.get("boxcolor", "black@0.5")
        boxborderw = template.get("boxborderw", 5)
        parts.append(f"box=1")
        parts.append(f"boxcolor={boxcolor}")
        parts.append(f"boxborderw={boxborderw}")

    parts.append(f"x={x}")
    parts.append(f"y={y}")
    parts.append(f"enable='between(t\\,{start_time:.3f}\\,{end_time:.3f})'")

    return ",".join(parts)


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
        lyric = event.get("lyric_text", "")
        if not lyric or lyric.strip() == "":
            continue

        start = event.get("timeline_start", 0)
        end = event.get("timeline_end", 0)
        section = event.get("section", "")

        dt = build_drawtext_filter(
            lyric, template_id, start, end, section,
            fontsize_override, fontcolor_override,
        )
        if dt:
            filters.append(dt)

    return ",".join(filters)
