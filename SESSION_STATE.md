# SESSION STATE

## Current Phase
Phase 12 — Auto Captions, Export Settings & Production Polish (complete)

## Current Objective
Full pipeline with auto-generated captions from audio (Whisper), export options menu with video/audio sections, and lossless compression support.

## Overall Progress
99%

## Completed
- Phases 0-11 complete (see git history: ab669a8..0b664c2)
- Phase 12: Auto captions + Export menu (2026-09-01, details below)

## Phase 12 Work Completed (2026-09-01)

### Auto-Generated Captions from Audio
- Upgraded Whisper model from `base` to `small` for better transcription accuracy
- Added language parameter to `/auto` endpoint — supports 18 tier-one languages
- Language selector dropdown in ProjectPage (auto-detect by default)
- Commented out manual lyrics textarea — system now auto-extracts lyrics from audio only
- Improved line grouping: max 6 words per line, min 1.5s duration, max 4s duration
- Whisper config added to settings.yaml and config.py (model_size, device, compute_type)

### Bug Fixes
- Added `section` field to TimelineEvent dataclass — fixes `colorful` template section coloring
- Fixed `escape_ffmpeg_text()` — now escapes `\`, `:`, `;`, `[`, `]`, `%` for FFmpeg drawtext filter
- Added `auto_generated` field to TimelineEvent — tracks Whisper-generated lyrics
- Section propagation: lyrics → phrases → slots → events (both auto and sequential modes)

### Export Settings Menu
- Full export settings modal with VIDEO and AUDIO sections
- **Video options:** format (MP4/WebM/MKV), resolution (4K/1080p/720p/480p), codec (H.264/H.265/AV1), FPS (24/25/30/60)
- **Video quality presets:** Lossless (CRF 0), Visually Lossless (CRF 18), Balanced (CRF 23), Compact (CRF 28)
- **Audio options:** codec (AAC/MP3/FLAC/Copy), bitrate, sample rate, channels
- **Audio quality presets:** Lossless (FLAC), High (AAC 320k), Standard (AAC 192k)
- File size estimate before export (video + audio breakdown)
- Custom export directory option
- New `/api/render/{path}/estimate` endpoint for file size estimation

### UI Improvements
- Font size slider (16-72px) and font color dropdown in caption settings
- "Whisper" badge on auto-generated lyrics in EventDetail
- Section display in EventDetail panel
- ReviewPage redesigned with "Open Export Settings" button → modal with full options

## In Progress
None

## Blocked
None

## Decisions Made
- Local-first architecture; React frontend; Python/FastAPI backend; FFmpeg deterministic renderer
- Timeline as structured JSON (schema v2); human approval before final render; model-agnostic AI layer
- Whisper `small` model chosen for best accuracy/speed balance on CPU
- Auto-only lyrics system (no manual text input) — Whisper handles all transcription
- Lossless compression = zero quality loss but still compressed (CRF 0 for video, FLAC for audio)
- Export settings as modal overlay, not inline — keeps ReviewPage clean
- File size estimation uses CRF-to-bitrate mapping for quick preview before export

## Files Modified (Phase 12)
- backend/app/api/lyrics.py (Whisper small, language param, improved line grouping)
- backend/app/lyrics/engine.py (Whisper small, config-based settings)
- backend/app/agents/editor_brain.py (section + auto_generated fields, propagation)
- backend/app/rendering/caption_templates.py (escape_ffmpeg_text fix)
- backend/app/rendering/ffmpeg_renderer.py (full param support, resolution/codec/crf/preset/fps, estimate function)
- backend/app/api/render.py (expanded RenderRequest, estimate endpoint, custom export path)
- backend/app/utils/config.py (whisper defaults)
- config/settings.yaml (whisper config section)
- frontend/src/pages/ProjectPage.tsx (language dropdown, comment out manual lyrics)
- frontend/src/pages/ReviewPage.tsx (export settings modal, font controls)
- frontend/src/components/EventDetail.tsx (Whisper badge, section display)
- frontend/src/services/api.ts (estimate API call)
- frontend/src/types/index.ts (ExportSettings, FileEstimate, section, auto_generated)

## Git Commits
- ab669a8..480421f: Phases 0-10
- 0b664c2: Phase 11 — pipeline correctness, lyric-anchored auto mode, QC hardening
- 755f37e: Phase 12a — auto-only captions with Whisper small + language selector + bug fixes
- 217943b: Phase 12b — export settings menu with video/audio sections + lossless compression

## Next Steps
1. Test full pipeline with new Whisper small model on a sample project
2. Verify export settings render correctly with different codec/resolution combos
3. Implement xfade crossfade/dissolve rendering (transitions currently cut/fade metadata only)
4. Recalibrate CLIP confidence display in Review UI (scores ~0.2 are normal, not failures)
5. Desktop packaging (Phase 14)

## Last Updated
2026-09-01
