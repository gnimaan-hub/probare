/// <reference types="vite/client" />

/**
 * API exposée par le préchargement Electron (`src/preload/index.ts`).
 *
 * La déclaration y figure déjà, mais `tsconfig.web.json` ne compile que le
 * renderer : sans ce miroir, `window.electron` n'existe pas pour le typage du
 * renderer. Les deux doivent rester alignés.
 *
 * `electron` est optionnel : le renderer tourne aussi dans un navigateur
 * simple (`npm run preview:renderer`), où le pont n'existe pas.
 */
export interface ElectronAPI {
  getApiPort: () => Promise<number>
  getApiToken: () => Promise<string>
  getSidecarError: () => Promise<string>
  platform: string
}

declare global {
  interface Window {
    electron?: ElectronAPI
  }
}
