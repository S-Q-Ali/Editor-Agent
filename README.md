# Editor-Agent

Local-first AI video editing desktop application with AI-powered music-video synchronization, CLIP+BLIP visual matching, Whisper auto-transcription, beat-aligned timeline generation, lyrics caption rendering, and export options.

## Features

- **AI Music-Video Sync** — CLIP visual matching pairs video clips to music beats
- **Auto Transcription** — Whisper (small model) with 18 language support
- **Beat Detection** — Librosa-powered beat analysis for timeline alignment
- **Caption Rendering** — FFmpeg-based lyrics captions with 7 template styles
- **Visual Search** — CLIP + BLIP for semantic video clip discovery
- **Export Settings** — Lossless/lossy video (H.264/H.265/VP9) and audio (FLAC/AAC) options
- **Desktop App** — Standalone Electron shell, no Python install required

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | Python + FastAPI + uvicorn |
| AI Models | CLIP (ViT-B-32), BLIP, Whisper (small) |
| Video Processing | FFmpeg, OpenCV, PyAV, Librosa |
| Desktop Shell | Electron 30 + electron-builder |
| Python Bundling | PyInstaller (single .exe) |

## Quick Start

### Development Mode

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173` | Backend: `http://127.0.0.1:8000`

### Desktop App

```bash
# Build everything (frontend + Python bundle + Electron)
scripts\build-all.bat

# Run
release\win-unpacked\Editor Agent.exe
```

### Dev Mode with Electron

```bash
scripts\build-dev.bat
```

## Project Structure

```
Editor-Agent/
├── backend/
│   └── app/
│       ├── api/              # 13 FastAPI routers
│       │   ├── analysis.py   # Audio/visual analysis
│       │   ├── clips.py      # Video clip management
│       │   ├── files.py      # File browser
│       │   ├── health.py     # Health check
│       │   ├── jobs.py       # Background jobs
│       │   ├── lyrics.py     # Whisper transcription
│       │   ├── projects.py   # Project CRUD
│       │   ├── qc.py         # Quality control
│       │   ├── render.py     # FFmpeg rendering
│       │   ├── revision.py   # Revision tracking
│       │   ├── search.py     # CLIP visual search
│       │   ├── timeline.py   # Timeline generation
│       │   └── upload.py     # File uploads
│       ├── agents/
│       │   └── editor_brain.py  # AI timeline generator
│       ├── lyrics/
│       │   └── engine.py     # Whisper transcription engine
│       ├── rendering/
│       │   ├── caption_templates.py  # 7 caption styles
│       │   └── ffmpeg_renderer.py    # Parametric renderer
│       ├── search/
│       │   └── clip_engine.py  # CLIP+BLIP matching
│       ├── utils/
│       │   └── config.py     # Config loader, path resolution
│       └── main.py           # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── components/       # React components
│       │   ├── FolderPicker.tsx      # Directory browser
│       │   ├── UpdateNotification.tsx # Auto-update toast
│       │   └── EventDetail.tsx       # Timeline event details
│       ├── pages/            # Page components
│       │   ├── HomePage.tsx
│       │   ├── ProjectPage.tsx
│       │   └── ReviewPage.tsx
│       ├── services/
│       │   └── api.ts        # API client
│       ├── stores/
│       │   └── index.ts      # Zustand state
│       └── types/
│           └── index.ts      # TypeScript types
├── electron/
│   ├── main.js              # Electron entry point
│   ├── preload.js           # Secure context bridge
│   ├── python-manager.js    # Backend lifecycle
│   ├── ipc-handlers.js      # IPC dialog handlers
│   ├── menu.js              # Native menu bar
│   └── updater.js           # Auto-updater
├── config/
│   └── settings.yaml        # App configuration
├── scripts/
│   ├── build-all.bat        # Full build pipeline
│   ├── build-python.bat     # Python backend build
│   ├── build-python.spec    # PyInstaller config
│   └── build-dev.bat        # Dev mode launcher
├── package.json             # Electron config
└── backend/
    └── requirements.txt     # Python dependencies
```

## Configuration

Edit `config/settings.yaml`:

```yaml
whisper:
  model_size: "small"    # tiny, base, small, medium, large-v3
  device: "cpu"          # cpu or cuda
  compute_type: "int8"   # int8, float16, float32

beats:
  bpm_range: [60, 200]
  beat_weight: 0.6
  onset_weight: 0.4
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/projects/create` | Create project |
| POST | `/api/upload/{path}` | Upload files |
| POST | `/api/analysis/detect-beats` | Beat detection |
| POST | `/api/analysis/extract-frames` | Frame extraction |
| POST | `/api/lyrics/auto` | Whisper transcription |
| POST | `/api/clips/match` | CLIP visual matching |
| POST | `/api/timeline/generate` | Generate timeline |
| POST | `/api/render/{path}` | Render video |
| POST | `/api/render/{path}/estimate` | File size estimate |
| GET | `/api/files/browse` | Browse directories |

## Export Options

### Video
- **Format**: MP4, WebM, MKV
- **Resolution**: 480p to 4K (or custom)
- **Codec**: H.264, H.265, VP9
- **Quality**: Lossless (CRF 0), Visually Lossless (CRF 18), Balanced (CRF 23), Compact (CRF 28)

### Audio
- **Codec**: AAC, FLAC, Copy
- **Bitrate**: 128k to 320k (AAC), Lossless (FLAC)

## Building

### Full Build
```bash
scripts\build-all.bat
```

This will:
1. Build frontend (Vite)
2. Bundle Python with PyInstaller (~1.2GB)
3. Build Electron app

### Output
- `release\win-unpacked\Editor Agent.exe` — Standalone app
- `release\Editor Agent Setup *.exe` — NSIS installer (when configured)

## Platform Support

| Platform | Status |
|----------|--------|
| Windows x64 | ✅ Supported |
| macOS | Not yet |
| Linux | Not yet |

## License

MIT

## Author

S-Q-Ali
