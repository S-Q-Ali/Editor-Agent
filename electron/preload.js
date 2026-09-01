const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('backend:url'),
  openFolderDialog: () => ipcRenderer.invoke('dialog:openFolder'),
  openFileDialog: (filters) => ipcRenderer.invoke('dialog:openFile', filters),
  saveFileDialog: (defaultName, filters) =>
    ipcRenderer.invoke('dialog:saveFile', defaultName, filters),
  getSystemInfo: () => ipcRenderer.invoke('system:info'),
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  getAppVersion: () => ipcRenderer.invoke('app:version'),
  onUpdateAvailable: (callback) =>
    ipcRenderer.on('update:available', (_, version) => callback(version)),
  onUpdateProgress: (callback) =>
    ipcRenderer.on('update:progress', (_, percent) => callback(percent)),
  onUpdateDownloaded: (callback) =>
    ipcRenderer.on('update:downloaded', () => callback()),
  installUpdate: () => ipcRenderer.invoke('update:install'),
})
