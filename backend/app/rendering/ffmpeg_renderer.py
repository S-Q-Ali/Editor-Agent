import json
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.rendering.caption_templates import build_caption_filter_chain


class FFmpegRenderer:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)

    def render(
        self,
        timeline: Dict,
        clips_dir: str,
        audio_path: str,
        output_path: str,
        preview: bool = False,
        caption_template: str = "none",
        caption_fontsize: Optional[int] = None,
        caption_fontcolor: Optional[str] = None,
    ) -> Dict[str, Any]:
        events = timeline.get("tracks", {}).get("video", [])
        if not events:
            return {"error": "No video events in timeline"}

        clip_files = self._resolve_clip_files(events, clips_dir)
        missing = [e["clip_id"] for e in events if e["clip_id"] not in clip_files]
        if missing:
            return {"error": f"Missing clip files: {missing}"}

        segment_files = []
        for i, event in enumerate(events):
            clip_path = clip_files[event["clip_id"]]
            segment_path = str(self.temp_dir / f"segment_{i:04d}.mp4")

            result = self._trim_clip(
                clip_path,
                event["source_start"],
                event["source_end"],
                segment_path,
                preview,
            )
            if result.get("error"):
                return {"error": f"Failed to trim segment {i}: {result['error']}"}

            segment_files.append(segment_path)

        concat_list = str(self.temp_dir / "concat_list.txt")
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        concat_output = str(self.temp_dir / "concat_raw.mp4")
        concat_result = self._concat_segments(concat_list, concat_output)
        if concat_result.get("error"):
            return concat_result

        video_with_captions = concat_output
        if caption_template != "none":
            caption_result = self._apply_captions(
                concat_output, events, output_path,
                caption_template, caption_fontsize, caption_fontcolor,
            )
            if caption_result.get("error"):
                return caption_result
            video_with_captions = output_path

        audio_result = self._replace_audio(video_with_captions, audio_path, output_path)
        if audio_result.get("error"):
            return audio_result

        self._cleanup_segments(segment_files)
        if os.path.exists(concat_list):
            os.remove(concat_list)
        if os.path.exists(concat_output) and video_with_captions != concat_output:
            os.remove(concat_output)

        return {
            "output": output_path,
            "duration": timeline.get("duration", 0),
            "events_rendered": len(events),
            "preview": preview,
            "caption_template": caption_template,
        }

    def _trim_clip(
        self,
        input_path: str,
        start: float,
        end: float,
        output_path: str,
        preview: bool = False,
    ) -> Dict:
        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(end - start),
            "-c:v", "libx264",
            "-preset", "ultrafast" if preview else "medium",
            "-crf", "28" if preview else "23",
            "-an",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            output_path,
        ]
        return self._run_command(cmd)

    def _concat_segments(self, concat_list: str, output_path: str) -> Dict:
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path,
        ]
        return self._run_command(cmd)

    def _apply_captions(
        self,
        input_path: str,
        events: List[Dict],
        output_path: str,
        template_id: str,
        fontsize_override: Optional[int] = None,
        fontcolor_override: Optional[str] = None,
    ) -> Dict:
        caption_chain = build_caption_filter_chain(
            events, template_id, fontsize_override, fontcolor_override,
        )

        if not caption_chain:
            return {"success": True}

        vf = f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{caption_chain}"

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-an",
            "-vf", vf,
            "-r", "30",
            output_path,
        ]
        return self._run_command(cmd)

    def _replace_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> Dict:
        temp_output = video_path + ".temp.mp4"
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            temp_output,
        ]
        result = self._run_command(cmd)
        if not result.get("error"):
            os.replace(temp_output, output_path)
        return result

    def _resolve_clip_files(self, events: List[Dict], clips_dir: str) -> Dict[str, str]:
        clips_path = Path(clips_dir)
        clip_files = {}

        for event in events:
            clip_id = event["clip_id"]
            if clip_id in clip_files:
                continue

            for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                candidates = list(clips_path.glob(f"*{ext}"))
                for candidate in candidates:
                    if candidate.stem == clip_id or clip_id in candidate.stem:
                        clip_files[clip_id] = str(candidate)
                        break
                if clip_id in clip_files:
                    break

        return clip_files

    def _run_command(self, cmd: List[str]) -> Dict:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                return {"error": result.stderr[-500:] if result.stderr else "Unknown error"}
            return {"success": True}
        except subprocess.TimeoutExpired:
            return {"error": "FFmpeg command timed out"}
        except Exception as e:
            return {"error": str(e)}

    def _cleanup_segments(self, segment_files: List[str]):
        for seg in segment_files:
            if os.path.exists(seg):
                os.remove(seg)

    def get_video_info(self, video_path: str) -> Dict:
        cmd = [
            self.ffprobe_path, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return {}
