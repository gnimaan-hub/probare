import { app, BrowserWindow, shell, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { startSidecar, stopSidecar, getSidecarPort, getSidecarToken, waitForSidecar } from './sidecar'

let mainWindow: BrowserWindow | null = null

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    autoHideMenuBar: true,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    backgroundColor: '#f8fafc',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(async () => {
  electronApp.setAppUserModelId('com.probare.audit')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // Démarrer le sidecar Python
  try {
    await startSidecar()
    await waitForSidecar(30)
    console.log(`[main] Sidecar Python démarré sur le port ${getSidecarPort()}`)
  } catch (err) {
    console.error('[main] Impossible de démarrer le sidecar:', err)
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// IPC : port et jeton du sidecar
ipcMain.handle('get-api-port', () => getSidecarPort())
ipcMain.handle('get-api-token', () => getSidecarToken())

app.on('window-all-closed', async () => {
  await stopSidecar()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', async () => {
  await stopSidecar()
})
