import axios from 'axios'
import type { Project, ClipOrder, FileEstimate } from '../types'

const API_BASE = import.meta.env.DEV ? '' : 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api`,
})

export const fileApi = {
  browse: (path: string) =>
    axios.get<{ current: string; parent: string | null; directories: { name: string; path: string }[] }>(
      `${API_BASE}/api/files/browse`,
      { params: { path } }
    ),
}

export const projectApi = {
  list: () => api.get<Project[]>('/projects/'),
  get: (path: string) => api.get<Project>(`/projects/${path}`),
  create: (name: string) => api.post<Project>('/projects/', { name }),
  update: (path: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${path}`, data),
  delete: (path: string) => api.delete(`/projects/${path}`),
}

export const clipApi = {
  saveOrder: (path: string, order: ClipOrder) =>
    api.post(`/upload/clips/${path}/order`, order),
}

export const timelineApi = {
  generate: (path: string, mode: string = 'auto') =>
    api.post(`/timeline/${path}/generate`, { mode }),
  get: (path: string) => api.get(`/timeline/${path}`),
  patchEvent: (path: string, eventIndex: number, patch: { source_start?: number; source_end?: number; clip_id?: string }) =>
    api.patch(`/timeline/${path}/events/${eventIndex}`, patch),
}

export const renderApi = {
  downloadUrl: (path: string) => `${API_BASE}/api/render/${encodeURIComponent(path)}/download`,
  getCaptionTemplates: () => api.get('/render/captions/templates'),
  estimate: (path: string, params: { crf: number; resolution: string; audio_bitrate: string; audio_codec: string }) =>
    api.post<FileEstimate>(`/render/${path}/estimate`, params),
}

export const healthApi = {
  check: () => api.get<{ status: string; ffmpeg: boolean; ffprobe: boolean }>('/health'),
}
