# PROJECT DOCUMENTATION

## 1. Project Overview

Local AI Video Editor Agent — a local-first, AI-assisted video editing application that accepts a master music/audio file, lyrics, and pre-generated AI video clips, then automatically produces a publish-ready 16:9 video through an intelligent pipeline with human review.

## 2. Product Vision

Build a local-first AI video editing agent that:
- Accepts a master music/audio file, lyrics, and pre-generated AI video clips
- Automatically analyzes the music and clips
- Aligns lyrics with the audio
- Selects relevant visuals
- Intelligently trims and sequences clips
- Removes original clip audio
- Synchronizes edits with lyrics and music
- Creates a publish-ready 16:9 video
- Renders a preview for human review
- Accepts natural-language corrections
- Produces a final render after approval

## 3. Functional Requirements

- Project creation and management
- Music/audio file upload and analysis
- Lyrics paste and alignment
- AI video clip upload and analysis
- Semantic search for clip selection
- Timeline generation by editing agent
- Intelligent clip trimming
- Audio removal from source clips
- Beat and lyric synchronization
- Preview rendering
- Quality control checks
- Human review interface
- Natural-language revision support
- Final render in H.264/AAC MP4

## 4. Non-Functional Requirements

- Local-first: no cloud dependencies
- Model-agnostic AI layer
- Hardware abstraction (CPU/GPU detection)
- Deterministic rendering via FFmpeg
- Immutable source media
- Version history via Git

## 5. Architecture

```
                    ┌─────────────────────┐
                    │      React UI       │
                    │   Local Web App     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Server   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Music Engine      Clip Engine      Agent Engine
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                       Timeline Engine
                               │
                               ▼
                           FFmpeg
                               │
                               ▼
                        Preview / Final
```

## 6. Technology Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI + Pydantic
- **Video processing:** FFmpeg, FFprobe, OpenCV, PyAV
- **Audio analysis:** FFmpeg + librosa
- **Lyrics/transcription alignment:** Whisper or faster-whisper
- **AI layer:** Model-agnostic interfaces for LLM, vision, embeddings, transcription
- **Vector search:** Chroma or Qdrant
- **Desktop packaging:** Tauri (future)

## 7. Directory Structure

```
local-ai-video-editor/
├── AGENTS.md
├── PROJECT_DOCUMENTATION.md
├── SESSION_STATE.md
├── README.md
├── .env.example
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   ├── audio/
│   │   ├── lyrics/
│   │   ├── video/
│   │   ├── vision/
│   │   ├── embeddings/
│   │   ├── timeline/
│   │   ├── rendering/
│   │   ├── qc/
│   │   ├── storage/
│   │   └── utils/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/
│   │   ├── services/
│   │   └── types/
│   └── tests/
├── models/
├── projects/
├── scripts/
└── config/
```

## 8. AI Models

The AI layer must be model-agnostic. The Model Manager detects available hardware and selects appropriate local models:
- Hardware detector
- Model registry
- Model manager
- CPU fallback
- GPU acceleration where available
- Configurable model paths

## 9. Music Analysis Pipeline

Analyzes the actual audio:
- Duration, BPM, beat timestamps
- Downbeats, tempo, energy curve
- Silence detection
- Intro/outro detection
- Musical section segmentation

Output:
```json
{
  "duration": 161.4,
  "bpm": 112,
  "beats": [],
  "downbeats": [],
  "sections": [],
  "energy_curve": []
}
```

## 10. Lyrics Alignment Pipeline

Aligns supplied lyrics to actual song audio. Preserves section labels (Intro, Verse, Chorus, Bridge, Outro).

Output:
```json
{
  "lines": [
    {
      "text": "Good morning, little sunshine",
      "start": 4.21,
      "end": 6.83,
      "importance": 0.92
    }
  ]
}
```

## 11. Clip Analysis Pipeline

Analyzes each supplied AI-generated clip once and caches results:
- Duration, scene description, actions, objects, characters
- Emotion, motion score, visual quality
- Best usable segments, semantic embedding

Output:
```json
{
  "clip_id": "clip_017",
  "duration": 8.4,
  "actions": ["waking", "opening eyes", "stretching"],
  "objects": ["bed", "pillow"],
  "emotion": "happy",
  "motion_score": 0.78,
  "quality_score": 0.91
}
```

## 12. Embedding/Search System

Converts lyric lines into visual intent and searches the clip index for relevant candidates. Uses vector search (Chroma or Qdrant) for semantic matching.

## 13. Editing Agent

The editing agent combines music analysis, lyric alignment, clip metadata and editing rules to generate a timeline. The LLM reasons about WHAT should happen; deterministic services handle HOW it is rendered.

Decisions include:
- Clip selection, source start/end
- Timeline start/end, cut points
- Visual repetition handling
- Transition selection
- Visual intensity
- Beat alignment
- Confidence and reason for every decision

## 14. Timeline Schema

```json
{
  "version": 2,
  "mode": "auto",
  "duration": 161.4,
  "total_events": 46,
  "tracks": {
    "video": [],
    "audio": []
  },
  "metadata": {}
}
```

Each video event:
- clip_id, source_start, source_end
- timeline_start, timeline_end
- transition, reason, confidence
- lyric_text, selection_method, clip_caption

Invariants (enforced by editing brain + QC):
- Events cover the full song with no gaps or overlaps
- `source_end - source_start == timeline_end - timeline_start` (exact A/V sync)
- Source ranges never exceed the actual clip duration
- Event boundaries anchored at lyric timestamps (lyric events)

## 15. FFmpeg Rendering

Converts validated timeline into deterministic FFmpeg processing:
- Trim, scale, crop
- FPS normalization
- Concatenation, transitions
- Audio replacement
- Encoding

## 16. Review System

- Video preview player
- Timeline overview
- Selected clip details
- Reason for clip selection
- Confidence display
- Replace clip capability
- Trim adjustment
- Section-level regeneration
- Natural-language correction input

## 17. Revision System

Natural-language revision agent:
- Understands corrections in multiple languages
- Modifies only affected timeline sections
- Does not regenerate entire project

## 18. Quality Control

Automated QC checks:
- Duration validation, audio presence
- Rendered file duration vs music/timeline duration (catches silent truncation)
- Per-event source duration vs timeline duration match (catches A/V drift)
- Timeline gaps/overlaps
- Invalid timestamps
- Minimum event duration policy (2.0s guideline, 1.0s hard floor)
- Resolution/FPS/encoding validation
- Excessive repetition detection
- Low-confidence selection warnings

## 19. API Specification

REST API endpoints for:
- Project CRUD
- File upload (music, lyrics, clips)
- Analysis triggers
- Timeline generation
- Preview/final rendering
- Review/approval
- Revision requests

## 20. Database Schema

Project state stored as JSON:
- project.json
- music_analysis.json
- lyrics_alignment.json
- clip_index.json
- timeline.json
- review.json
- render_manifest.json

## 21. Configuration

```yaml
video:
  default_width: 1920
  default_height: 1080
  fps: 30

editing:
  default_style: adaptive
  beat_sync: true
  lyric_sync: true
  repetition_penalty: true

render:
  codec: h264
  audio_codec: aac
```

## 22. Error Handling

- Graceful degradation
- Detailed error logging
- User-friendly error messages
- Automatic retry for transient failures

## 23. Testing Strategy

- Unit tests for every core service
- Music analysis tests
- Lyrics alignment tests
- Clip analysis tests
- Embedding/search tests
- Timeline validation tests
- Renderer tests
- QC tests
- Project-state tests
- Short synthetic media for automated tests
- Representative full songs/clips for integration tests

## 24. Performance Optimization

- Parallel analysis where possible
- Caching of analysis results
- Incremental processing
- Efficient memory usage

## 25. Security / Local Privacy

- All processing local
- No cloud uploads
- Source media immutability
- No secrets in code

## 26. Future Features

- 9:16 automatic adaptation
- Desktop packaging via Tauri
- Multi-language support
- Advanced transitions
- Template system

## 27. Known Limitations

- Requires pre-generated AI video clips
- Dependent on local hardware for AI model performance
- FFmpeg processing time scales with project complexity
- Transitions: cuts render natively; "fade" is metadata for intro/outro (no xfade blending yet)
- Crossfade/dissolve transitions are stored in the schema but not rendered
- Caption apostrophes are rendered as typographic apostrophes (U+2019)
- CLIP whole-clip match scores typically land in the 0.15-0.3 range; low-confidence QC warnings are informational, not failures
- Events may drop below the 2.0s guideline (floor 1.0s) when lyric phrase anchors collide — sync always wins

## 28. Timeline Modes

### AUTO Mode (lyric-anchored, two-stage matching)
Events are anchored at the REAL sung timestamp of every lyric phrase — visuals land on the words as they are sung.

**Stage 1 — clip selection per repetition group:**
Lyrics are normalized and grouped (`"good morning"` ×16 = one group). Each group gets a primary clip plus alternates from whole-clip CLIP matching (85% CLIP visual, 10% semantic, 5% text). Repeated lyrics reuse the same clip family → consistent visual motif per hook.

**Stage 2 — source-window selection ("trim from anywhere"):**
Within the chosen clip, the best window for the exact needed duration is selected by scoring: window freshness (no overlap with already-used windows of that clip), motion/quality of covered `best_segments`, and beat snapping. Repetition is tracked per `(clip_id, source_window)`, not per clip — a 15s clip yields ~4-5 distinct windows. Window reuse is allowed only after a group's pool is exhausted (with a confidence penalty).

**Coverage slots:**
- Intro slot covers instrumental before the first lyric.
- Pauses between phrases extend (hold) the previous shot; longer pauses get a music-fill slot with a different clip.
- Outro slot covers the tail after the last lyric.
- Slots longer than `max_event_duration` (8s) are split into equal chunks with fresh windows.
- Overlapping phrase anchors never produce overlapping events (sync wins over duration).

Fallback chain: clip_match → clip_match_low → best_available → window reuse → hard_fallback.

### SEQUENTIAL Mode
User uploads clips in numbered order (e.g., `01_wake_up.mp4`, `02_brush.mp4`). Agent uses clips in that exact sequence. Features:
- **Lyric grouping**: Consecutive short lyrics merged into 2-4s phrases
- **Source range tracking**: Different source ranges used per clip reuse (e.g., 0-3s, 3-6s, 6-9s)
- **Full song coverage**: Tail-filling covers entire song duration
- **Manual overrides**: User can edit source ranges per event after generation

### Manual Overrides (Both Modes)
After timeline generation, user can adjust `source_start`/`source_end` per event via PATCH endpoint or EventDetail panel. The renderer clamps source ranges to actual clip bounds and pads short trims by holding the last frame, so A/V sync can never silently drift.

## 29. Lyric Grouping Algorithm

Groups consecutive short lyrics into phrases (both modes):
- Merge if gap between lyrics ≤ 0.5s
- Merge if combined duration ≤ 4.0s
- Merge if either lyric is shorter than min duration (2.0s)
- Stop merging at section boundaries (verse → chorus)
- AUTO mode: each phrase is anchored at its real timestamp (never stretched to fill the song); gaps are held on the previous shot or filled with a music slot
- SEQUENTIAL mode: phrase durations are scaled proportionally to fill total song duration

## Development Phases

| Phase | Description |
|-------|-------------|
| 0 | Project setup + documentation |
| 1 | Backend + frontend foundation |
| 2 | Music analysis |
| 3 | Lyrics alignment |
| 4 | Clip analysis |
| 5 | Semantic search |
| 6 | Editing agent |
| 7 | Timeline engine |
| 8 | FFmpeg renderer |
| 9 | Preview + QC |
| 10 | Review UI |
| 11 | Natural-language revisions |
| 12 | Sequential mode (clip ordering, lyric grouping) |
| 13 | Optimization |
| 14 | Desktop packaging |

## Final Product Workflow

```
CREATE PROJECT
       ↓
Upload Song → Paste Lyrics → Upload AI Clips
       ↓
SELECT MODE (Auto / Sequential)
       ↓
[Sequential] → Order Clips (auto-detect numeric prefixes)
       ↓
GENERATE
       ↓
Music Analysis → Lyrics Alignment → Clip Analysis
       ↓
[Auto] CLIP Matching → Timeline Planning
[Sequential] Ordered Clips → Lyric Grouping → Source Range Selection
       ↓
Smart Trimming → Audio Removal → Beat/Lyric Sync
       ↓
Preview Render → QC → USER REVIEW
       ↓
Manual Range Overrides (optional)
       ↓
Natural-Language Revision if needed
       ↓
APPROVE → FINAL MP4
```

## Default Output

- Resolution: 1920x1080
- Aspect ratio: 16:9
- Video codec: H.264
- Audio codec: AAC
- Master music only
- Publish-ready MP4
