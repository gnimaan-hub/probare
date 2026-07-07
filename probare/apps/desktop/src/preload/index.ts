import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  getApiPort: () => ipcRenderer.invoke('get-api-port'),
  getApiToken: () => ipcRenderer.invoke('get-api-token'),
  platform: process.platform,
})

export type ElectronAPI = {
  getApiPort: () => Promise<number>
  getApiToken: () => Promise<string>
  platform: string
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}
