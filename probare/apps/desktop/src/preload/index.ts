import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  getApiPort: () => ipcRenderer.invoke('get-api-port'),
  platform: process.platform,
})

export type ElectronAPI = {
  getApiPort: () => Promise<number>
  platform: string
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}
