const { app, BrowserWindow, Menu, ipcMain, dialog, shell } = require('electron')
const path = require('path')
const PythonManager = require('./python-manager')
const { setupIPC } = require('./ipc-handlers')
const { createMenu } = require('./menu')
const { setupAutoUpdater } = require('./updater')

let mainWindow
let pythonManager

const isDev = !app.isPackaged

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 600,
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
    icon: path.join(__dirname, '..', 'build', 'icon.ico'),
    title: 'Editor Agent',
    show: false,
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    const indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }

  mainWindow.on('close', (e) => {
    if (pythonManager && pythonManager.isRunning) {
      e.preventDefault()
      pythonManager.stop().then(() => {
        mainWindow.destroy()
      })
    }
  })

  Menu.setApplicationMenu(Menu.buildFromTemplate(createMenu(shell)))
  setupIPC(mainWindow)

  if (!isDev) {
    setupAutoUpdater(mainWindow)
  }
}

async function startBackend() {
  pythonManager = new PythonManager()

  const backendPath = isDev
    ? null
    : path.join(process.resourcesPath, 'backend', 'main.exe')

  try {
    await pythonManager.start(backendPath)
    await pythonManager.waitForReady()
    console.log('Python backend ready on port', pythonManager.port)
  } catch (err) {
    console.error('Failed to start Python backend:', err)
    dialog.showErrorBox(
      'Backend Error',
      'Failed to start the Python backend. Please check your installation.'
    )
  }
}

app.whenReady().then(async () => {
  await startBackend()
  await createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (pythonManager && pythonManager.isRunning) {
    pythonManager.stop()
  }
  app.quit()
})

app.on('before-quit', () => {
  if (pythonManager && pythonManager.isRunning) {
    pythonManager.stop()
  }
})
