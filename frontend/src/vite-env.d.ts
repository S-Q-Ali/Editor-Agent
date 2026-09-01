/// <reference types="vite/client" />

interface ElectronAPI {
  getBackendUrl: () => Promise<string>
  openFolderDialog: () => Promise<string | null>
  openFileDialog: (filters?: { name: string; extensions: string[] }[]) => Promise<string[] | null>
  saveFileDialog: (defaultName: string, filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  getSystemInfo: () => Promise<{
    platform: string
    arch: string
    release: string
    totalMemory: number
    freeMemory: number
    cpus: number
  }>
  openExternal: (url: string) => Promise<void>
  getAppVersion: () => Promise<string>
  onUpdateAvailable: (callback: (version: string) => void) => void
  onUpdateProgress: (callback: (percent: number) => void) => void
  onUpdateDownloaded: (callback: () => void) => void
  installUpdate: () => Promise<void>
}

interface Window {
  electronAPI?: ElectronAPI
}
