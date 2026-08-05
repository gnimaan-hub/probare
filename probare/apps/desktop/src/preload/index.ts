import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  getApiPort: () => ipcRenderer.invoke('get-api-port'),
  getApiToken: () => ipcRenderer.invoke('get-api-token'),
  getSidecarError: () => ipcRenderer.invoke('get-sidecar-error'),
  platform: process.platform,
})

// Miroir typé dans src/renderer/src/env.d.ts — garder les deux alignés.
export type ElectronAPI = {
  getApiPort: () => Promise<number>
  getApiToken: () => Promise<string>
  getSidecarError: () => Promise<string>
  platform: string
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}
