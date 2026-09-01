function createMenu(shell) {
  const isMac = process.platform === 'darwin'

  const template = [
    ...(isMac
      ? [
          {
            label: 'Editor Agent',
            submenu: [
              { role: 'about' },
              { type: 'separator' },
              { role: 'hide' },
              { role: 'hideOthers' },
              { role: 'unhide' },
              { type: 'separator' },
              { role: 'quit' },
            ],
          },
        ]
      : []),
    {
      label: 'File',
      submenu: [
        { label: 'New Project', accelerator: 'CmdOrCtrl+N', enabled: false },
        { label: 'Open Project', accelerator: 'CmdOrCtrl+O', enabled: false },
        { type: 'separator' },
        { label: 'Export', accelerator: 'CmdOrCtrl+E', enabled: false },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: () => shell.openExternal('https://github.com/S-Q-Ali/Editor-Agent'),
        },
        {
          label: 'Report Issue',
          click: () =>
            shell.openExternal('https://github.com/S-Q-Ali/Editor-Agent/issues'),
        },
        { type: 'separator' },
        {
          label: 'About Editor Agent',
          click: (menuItem, browserWindow) => {
            const { dialog } = require('electron')
            dialog.showMessageBox(browserWindow, {
              type: 'info',
              title: 'About Editor Agent',
              message: 'Editor Agent',
              detail:
                'Local AI Video Editor\nVersion 1.0.0\n\nAI-powered video editing with beat-synced timelines, lyrics extraction, and visual matching.',
            })
          },
        },
      ],
    },
  ]

  return template
}

module.exports = { createMenu }
