import axios from 'axios'
import type { Project } from '../types'

const api = axios.create({
  baseURL: '/api',
})

export const projectApi = {
  list: () => api.get<Project[]>('/projects/'),
  get: (path: string) => api.get<Project>(`/projects/${path}`),
  create: (name: string) => api.post<Project>('/projects/', { name }),
  update: (path: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${path}`, data),
}

export const healthApi = {
  check: () => api.get<{ status: string; ffmpeg: boolean; ffprobe: boolean }>('/health'),
}
