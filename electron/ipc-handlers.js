const { ipcMain, dialog, shell } = require('electron')

function setupIPC(mainWindow) {
  ipcMain.handle('dialog:openFolder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      title: 'Select Folder',
    })
    return result.canceled ? null : result.filePaths[0]
  })

  ipcMain.handle('dialog:openFile', async (_, filters) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile', 'multiSelections'],
      filters: filters || [
        { name: 'All Files', extensions: ['*'] },
        { name: 'Video', extensions: ['mp4', 'avi', 'mov', 'mkv', 'webm'] },
        { name: 'Audio', extensions: ['mp3', 'wav', 'flac', 'ogg', 'm4a'] },
      ],
    })
    return result.canceled ? null : result.filePaths
  })

  ipcMain.handle('dialog:saveFile', async (_, defaultName, filters) => {
    const result = await dialog.showSaveDialog(mainWindow, {
      defaultPath: defaultName,
      filters: filters || [
        { name: 'Video', extensions: ['mp4'] },
        { name: 'All Files', extensions: ['*'] },
      ],
    })
    return result.canceled ? null : result.filePath
  })

  ipcMain.handle('system:info', () => {
    return {
      platform: process.platform,
      arch: process.arch,
      release: require('os').release(),
      totalMemory: require('os').totalmem(),
      freeMemory: require('os').freemem(),
      cpus: require('os').cpus().length,
    }
  })

  ipcMain.handle('shell:openExternal', (_, url) => {
    shell.openExternal(url)
  })

  ipcMain.handle('app:version', () => {
    return require('electron').app.getVersion()
  })
}

module.exports = { setupIPC }
