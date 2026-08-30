import { create } from 'zustand'
import type { Project } from '../types'

interface AppState {
  projects: Project[]
  currentProject: Project | null
  currentProjectPath: string | null
  loading: boolean
  error: string | null
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setCurrentProjectPath: (path: string | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  projects: [],
  currentProject: null,
  currentProjectPath: null,
  loading: false,
  error: null,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (project) => set({ currentProject: project, currentProjectPath: project?.path ?? null }),
  setCurrentProjectPath: (path) => set({ currentProjectPath: path }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))
