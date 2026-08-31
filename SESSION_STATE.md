# SESSION STATE

## Current Phase
Phase 11 — Pipeline Correctness & Production Hardening (complete)

## Current Objective
Full pipeline verified end-to-end on project TT_8f1cd796: lyric-synced, full-length, QC-clean preview render.

## Overall Progress
97%

## Completed
- Phases 0-10 complete (see git history: ab669a8..480421f)
- Phase 11: Pipeline correctness overhaul (2026-08-31, details below)

## Phase 11 Work Completed (2026-08-31)
### Root-cause analysis of TT_8f1cd796 preview (old preview was 117.57s vs 156.12s song)
- Tail-fill bug: last event claimed 53.94s from a 15.09s clip → renderer silently dropped 38.55s
- Lyric desync: AUTO mode stacked events back-to-back from 0s, ignoring lyric timestamps (drift up to ~45s)
- Strobe cutting: 88/97 events under 2s (min 0.14s); min-duration/grouping only existed in sequential mode
- QC blind spots: never compared render duration vs music, nor per-event source vs timeline duration
- Caption bug: drawtext options joined with ',' (filter separator) instead of ':' — captions never actually rendered
- Stale project state: upload/analysis/timeline/render endpoints never updated project.json

### Fixes implemented
- editor_brain.py: complete AUTO mode rewrite — lyric-anchored slots (real timestamps), intro/music-fill/outro
  slots, gap holding, max-event chunking (8s), overlap prevention, repetition groups (normalized text) with
  primary+alternate clips, two-stage matching with source-window pool (trim-from-anywhere: freshness +
  motion/quality + beat snapping), repetition tracked per (clip, window), deterministic transitions (random
  removed), confidence_threshold 0.15
- ffmpeg_renderer.py: deterministic exact-stem clip resolution, clip duration probing + source clamping,
  last-frame tpad padding for short source ranges, per-segment duration verification, scaled timeouts,
  final duration verification, warnings in result
- caption_templates.py: fixed drawtext option separator (':'), safe text escaping (apostrophes → U+2019)
- checker.py: new checks — render duration vs expected, per-event source/timeline match, min event duration
- API state updates: upload (music/lyrics), analysis (analysis_complete), timeline (timeline_ready/mode),
  render (preview_ready/status) now persist to project.json
- tests/test_timeline_sync.py: 11 regression tests (coverage, min duration, source/timeline match, clip
  bounds, lyric anchoring, intro/outro, overlaps, clip overuse, determinism, validation, renderer e2e)
- tests/test_main.py: fixed /health → /api/health route mismatch

### Verification results (TT_8f1cd796)
- New timeline: 46 events, 0 gaps, 0 overlaps, 0 source overruns, 0 src/tl mismatches, deterministic
- 37/43 lyric phrases CLIP-matched (clip_match), 6 best_available, 3 filler (intro/music/outro)
- New preview.mp4: 156.117s == music duration (was 117.57s), 1920x1080/30fps H.264+AAC, karaoke captions
- QC score 94, zero errors (only informational warnings: low CLIP confidence ~0.22 avg, expected repetition)

## In Progress
None

## Blocked
None

## Decisions Made
- Local-first architecture; React frontend; Python/FastAPI backend; FFmpeg deterministic renderer
- Timeline as structured JSON (schema v2); human approval before final render; model-agnostic AI layer
- Lyric sync anchor wins over minimum event duration: 2.0s guideline, 1.0s hard floor
- Repetition unit is (clip_id, source_window), not clip; max_clip_usage safety cap = 8
- Deterministic pipeline: no randomness anywhere in timeline generation
- CLIP confidence_threshold 0.15 (whole-clip scores typically 0.15-0.3)
- Renderer never silently truncates: clamps source ranges, pads with held last frame, verifies durations

## Files Modified (Phase 11)
- backend/app/agents/editor_brain.py (AUTO mode rewrite)
- backend/app/rendering/ffmpeg_renderer.py (robustness)
- backend/app/rendering/caption_templates.py (drawtext fix)
- backend/app/qc/checker.py (3 new checks)
- backend/app/api/upload.py, analysis.py, clips.py, timeline.py, render.py (state persistence)
- backend/tests/test_timeline_sync.py (NEW, 11 tests), backend/tests/test_main.py (route fix)
- PROJECT_DOCUMENTATION.md, SESSION_STATE.md

## Git Commits
- ab669a8..480421f: Phases 0-10
- (this session) Phase 11 — pipeline correctness, lyric-anchored auto mode, QC hardening

## Next Steps
1. Review new preview.mp4 visually; adjust clip-to-lyric groups via PATCH overrides if needed
2. Implement xfade crossfade/dissolve rendering (transitions currently cut/fade metadata only)
3. Recalibrate CLIP confidence display in Review UI (scores ~0.2 are normal, not failures)
4. Regenerate low-quality clip captions (e.g., "the secret in") to improve matching
5. Consider 720p output option (source clips are 720p; upscaling adds no detail)
6. Frontend: surface renderer "warnings" and QC "checks" detail in QCDisplay
7. Desktop packaging (Phase 14)

## Last Updated
2026-08-31
