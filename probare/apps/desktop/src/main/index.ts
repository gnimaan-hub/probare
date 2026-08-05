import { app, BrowserWindow, shell, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import {
  startSidecar, stopSidecar, getSidecarPort, getSidecarToken, waitForSidecar,
  getSidecarErrorLog,
} from './sidecar'

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

  // La fenêtre s'ouvre AVANT que le moteur soit prêt : elle affiche l'écran de
  // démarrage pendant que le sidecar se lance. Attendre ici laisserait
  // l'utilisateur devant un bureau vide jusqu'à une demi-minute quand le
  // démarrage échoue — c'est le renderer qui sonde /health et sait patienter.
  try {
    await startSidecar()
  } catch (err) {
    // Échec du lancement : la fenêtre doit s'ouvrir quand même pour porter le
    // diagnostic, sinon l'application ne montre rien du tout.
    console.error('[main] Démarrage du sidecar impossible:', err)
  }
  createWindow()

  waitForSidecar(45)
    .then(() => console.log(`[main] Sidecar Python démarré sur le port ${getSidecarPort()}`))
    .catch((err) => console.error('[main] Impossible de démarrer le sidecar:', err))

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// IPC : port et jeton du sidecar
ipcMain.handle('get-api-port', () => getSidecarPort())
ipcMain.handle('get-api-token', () => getSidecarToken())
// Diagnostic affiché sur l'écran d'erreur quand le moteur n'a pas démarré.
ipcMain.handle('get-sidecar-error', () => getSidecarErrorLog())

app.on('window-all-closed', async () => {
  await stopSidecar()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', async () => {
  await stopSidecar()
})
