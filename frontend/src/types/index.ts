export interface Project {
  id: string
  name: string
  path: string
  created_at: string
  updated_at: string
  status: string
  music_file: string | null
  lyrics_file: string | null
  clips: ClipInfo[]
  clip_order_file: string | null
  timeline_mode: string
  analysis_complete: boolean
  timeline_ready: boolean
  preview_ready: boolean
  approved: boolean
}

export interface ClipInfo {
  clip_id: string
  filename: string
  duration: number
}

export interface MusicAnalysis {
  duration: number
  bpm: number
  beats: number[]
  downbeats: number[]
  sections: Section[]
  energy_curve: number[]
}

export interface Section {
  start: number
  end: number
  label: string
}

export interface LyricLine {
  text: string
  start: number
  end: number
  importance: number
}

export interface LyricsAlignment {
  lines: LyricLine[]
}

export interface ClipAnalysis {
  clip_id: string
  duration: number
  actions: string[]
  objects: string[]
  emotion: string
  motion_score: number
  quality_score: number
  description: string
  semantic_embedding?: number[]
}

export interface TimelineEvent {
  clip_id: string
  source_start: number
  source_end: number
  timeline_start: number
  timeline_end: number
  transition: string
  reason: string
  confidence: number
  lyric_text: string
  selection_method: string
  clip_caption: string
}

export interface ClipOrderItem {
  index: number
  filename: string
}

export interface ClipOrder {
  mode: string
  clips: ClipOrderItem[]
}

export interface CaptionTemplate {
  id: string
  label: string
  description: string
}

export interface Timeline {
  version: number
  duration: number
  tracks: {
    video: TimelineEvent[]
    audio: unknown[]
  }
}

export interface QCResult {
  score: number
  warnings: string[]
  errors: string[]
}
