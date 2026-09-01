import json
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.rendering.caption_templates import build_caption_filter_chain

RESOLUTIONS = {
    "4k": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "480p": (854, 480),
}

CODECS = {
    "h264": "libx264",
    "h265": "libx265",
    "hevc": "libx265",
    "av1": "libsvtav1",
}

CRF_PRESETS = {
    "lossless": 0,
    "visually_lossless": 18,
    "balanced": 23,
    "compact": 28,
}

AUDIO_CODECS = {
    "aac": "aac",
    "mp3": "libmp3lame",
    "flac": "flac",
    "copy": "copy",
}


class FFmpegRenderer:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.temp_dir = Path(tempfile.gettempdir()) / "editor_agent_temp"
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
        resolution: str = "1080p",
        crf: int = 23,
        preset: str = "medium",
        codec: str = "h264",
        fps: int = 30,
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        audio_sample_rate: int = 48000,
        audio_channels: int = 2,
        container: str = "mp4",
    ) -> Dict[str, Any]:
        events = timeline.get("tracks", {}).get("video", [])
        if not events:
            return {"error": "No video events in timeline"}

        clip_files = self._resolve_clip_files(events, clips_dir)
        missing = [e["clip_id"] for e in events if e["clip_id"] not in clip_files]
        if missing:
            return {"error": f"Missing clip files: {missing}"}

        width, height = RESOLUTIONS.get(resolution, (1920, 1080))
        ffmpeg_codec = CODECS.get(codec, "libx264")

        if preview:
            crf = 28
            preset = "ultrafast"

        clip_durations: Dict[str, float] = {}
        for clip_id, clip_path in clip_files.items():
            info = self.get_video_info(clip_path)
            dur = 0.0
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    try:
                        dur = float(stream.get("duration") or 0)
                    except (TypeError, ValueError):
                        dur = 0.0
                    break
            if dur <= 0:
                try:
                    dur = float(info.get("format", {}).get("duration", 0) or 0)
                except (TypeError, ValueError):
                    dur = 0.0
            clip_durations[clip_id] = dur

        command_timeout = max(300, 20 * len(events))
        warnings: List[str] = []

        segment_files = []
        for i, event in enumerate(events):
            clip_path = clip_files[event["clip_id"]]
            clip_dur = clip_durations.get(event["clip_id"], 0.0)
            expected_dur = event["timeline_end"] - event["timeline_start"]

            source_start = float(event["source_start"])
            source_end = float(event["source_end"])
            if clip_dur > 0:
                if source_start >= clip_dur - 0.01:
                    return {"error": (
                        f"Segment {i}: source_start {source_start:.2f}s beyond clip "
                        f"duration {clip_dur:.2f}s (clip {event['clip_id']})"
                    )}
                if source_end > clip_dur:
                    warnings.append(
                        f"Segment {i}: source_end clamped {source_end:.2f}s -> {clip_dur:.2f}s "
                        f"(clip {event['clip_id']})"
                    )
                    source_end = clip_dur

            segment_path = str(self.temp_dir / f"segment_{i:04d}.mp4")

            result = self._trim_clip(
                clip_path,
                source_start,
                source_end,
                segment_path,
                preview,
                expected_duration=expected_dur,
                clip_duration=clip_dur if clip_dur > 0 else None,
                timeout=command_timeout,
                width=width,
                height=height,
                crf=crf,
                preset=preset,
                codec=ffmpeg_codec,
                fps=fps,
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
                width, height, crf, preset, ffmpeg_codec, fps,
            )
            if caption_result.get("error"):
                return caption_result
            video_with_captions = output_path

        audio_result = self._replace_audio(
            video_with_captions, audio_path, output_path,
            audio_codec, audio_bitrate, audio_sample_rate, audio_channels,
        )
        if audio_result.get("error"):
            return audio_result

        self._cleanup_segments(segment_files)
        if os.path.exists(concat_list):
            os.remove(concat_list)
        if os.path.exists(concat_output) and video_with_captions != concat_output:
            os.remove(concat_output)

        final_duration = 0.0
        output_info = self.get_video_info(output_path)
        try:
            final_duration = float(output_info.get("format", {}).get("duration", 0) or 0)
        except (TypeError, ValueError):
            final_duration = 0.0
        expected_total = timeline.get("duration", 0)
        duration_ok = True
        if expected_total > 0 and final_duration > 0:
            duration_ok = abs(final_duration - expected_total) <= 1.0
            if not duration_ok:
                warnings.append(
                    f"Final render duration {final_duration:.2f}s differs from "
                    f"timeline duration {expected_total:.2f}s"
                )

        file_size = 0
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)

        return {
            "output": output_path,
            "duration": final_duration or timeline.get("duration", 0),
            "events_rendered": len(events),
            "preview": preview,
            "caption_template": caption_template,
            "duration_ok": duration_ok,
            "warnings": warnings,
            "file_size": file_size,
            "resolution": f"{width}x{height}",
            "codec": codec,
            "crf": crf,
        }

    def _trim_clip(
        self,
        input_path: str,
        start: float,
        end: float,
        output_path: str,
        preview: bool = False,
        expected_duration: Optional[float] = None,
        clip_duration: Optional[float] = None,
        timeout: int = 300,
        width: int = 1920,
        height: int = 1080,
        crf: int = 23,
        preset: str = "medium",
        codec: str = "libx264",
        fps: int = 30,
    ) -> Dict:
        duration = end - start
        if expected_duration is not None and expected_duration > 0:
            duration = expected_duration

        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        )

        if clip_duration is not None and (start + duration) > clip_duration + 0.01:
            available = max(0.05, clip_duration - start)
            vf += (
                f",tpad=stop_mode=clone:stop_duration=30,"
                f"trim=duration={duration},setpts=PTS-STARTPTS"
            )
            read_duration = available
        else:
            read_duration = duration

        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(read_duration),
            "-c:v", codec,
            "-preset", preset,
            "-crf", str(crf),
            "-an",
            "-vf", vf,
            "-r", str(fps),
            output_path,
        ]
        result = self._run_command(cmd, timeout=timeout)
        if result.get("error"):
            return result

        seg_dur = 0.0
        info = self.get_video_info(output_path)
        try:
            seg_dur = float(info.get("format", {}).get("duration", 0) or 0)
        except (TypeError, ValueError):
            seg_dur = 0.0
        if seg_dur > 0 and abs(seg_dur - duration) > 0.3:
            return {"error": (
                f"Segment duration verification failed: expected {duration:.2f}s, "
                f"got {seg_dur:.2f}s"
            )}
        return {"success": True}

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
        width: int = 1920,
        height: int = 1080,
        crf: int = 23,
        preset: str = "medium",
        codec: str = "libx264",
        fps: int = 30,
    ) -> Dict:
        caption_chain = build_caption_filter_chain(
            events, template_id, fontsize_override, fontcolor_override,
        )

        if not caption_chain:
            return {"success": True}

        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,{caption_chain}"
        )

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-c:v", codec,
            "-preset", preset,
            "-crf", str(crf),
            "-an",
            "-vf", vf,
            "-r", str(fps),
            output_path,
        ]
        return self._run_command(cmd)

    def _replace_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        audio_sample_rate: int = 48000,
        audio_channels: int = 2,
    ) -> Dict:
        temp_output = video_path + ".temp.mp4"
        ffmpeg_audio_codec = AUDIO_CODECS.get(audio_codec, "aac")

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", ffmpeg_audio_codec,
        ]

        if ffmpeg_audio_codec != "copy":
            cmd.extend(["-b:a", audio_bitrate])
            cmd.extend(["-ar", str(audio_sample_rate)])
            cmd.extend(["-ac", str(audio_channels)])

        cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            temp_output,
        ])

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

            exact = None
            substring_candidates = []
            for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
                for candidate in sorted(clips_path.glob(f"*{ext}")):
                    if candidate.stem == clip_id:
                        exact = str(candidate)
                        break
                    if clip_id in candidate.stem:
                        substring_candidates.append(str(candidate))
                if exact:
                    break

            if exact:
                clip_files[clip_id] = exact
            elif len(substring_candidates) == 1:
                clip_files[clip_id] = substring_candidates[0]

        return clip_files

    def _run_command(self, cmd: List[str], timeout: int = 300) -> Dict:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
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

    @staticmethod
    def estimate_file_size(
        duration: float,
        crf: int = 23,
        resolution: str = "1080p",
        audio_bitrate: str = "192k",
        audio_codec: str = "aac",
    ) -> Dict[str, float]:
        width, height = RESOLUTIONS.get(resolution, (1920, 1080))
        pixels = width * height

        crf_bitrates = {
            0: max(80000, pixels * 0.3),
            18: max(8000, pixels * 0.03),
            23: max(4000, pixels * 0.015),
            28: max(1500, pixels * 0.005),
        }
        video_kbps = crf_bitrates.get(crf, 4000)

        if audio_codec == "flac":
            audio_kbps = 1000
        elif audio_codec == "copy":
            audio_kbps = 320
        else:
            audio_kbps = int(audio_bitrate.replace("k", ""))

        total_kbps = video_kbps + audio_kbps
        video_bytes = (video_kbps * 1000 / 8) * duration
        audio_bytes = (audio_kbps * 1000 / 8) * duration
        total_bytes = video_bytes + audio_bytes

        return {
            "video_mb": round(video_bytes / (1024 * 1024), 1),
            "audio_mb": round(audio_bytes / (1024 * 1024), 1),
            "total_mb": round(total_bytes / (1024 * 1024), 1),
            "video_kbps": round(video_kbps),
            "audio_kbps": audio_kbps,
        }
