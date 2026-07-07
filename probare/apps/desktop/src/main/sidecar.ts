import { ChildProcess, spawn } from 'child_process'
import { join } from 'path'
import { app } from 'electron'
import { is } from '@electron-toolkit/utils'
import * as http from 'http'
import * as net from 'net'
import { randomBytes } from 'crypto'

let sidecarProcess: ChildProcess | null = null
let sidecarPort: number = 8765
// Jeton partagé entre le renderer et le sidecar, régénéré à chaque démarrage.
const sidecarToken: string = randomBytes(32).toString('hex')

async function findFreePort(start = 8765): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(start, '127.0.0.1', () => {
      const port = (server.address() as net.AddressInfo).port
      server.close(() => resolve(port))
    })
    server.on('error', () => findFreePort(start + 1).then(resolve).catch(reject))
  })
}

export async function startSidecar(): Promise<void> {
  if (sidecarProcess) return

  sidecarPort = await findFreePort(8765)

  let pythonExe: string
  let args: string[]

  if (is.dev) {
    // Développement : utiliser Python du venv ou du système
    const engineDir = join(app.getAppPath(), '../../apps/engine')
    pythonExe = process.platform === 'win32' ? 'python' : 'python3'
    args = [
      '-m', 'uvicorn',
      'probare_engine.main:app',
      '--host', '127.0.0.1',
      '--port', String(sidecarPort),
      '--no-access-log',
    ]
    const sep = process.platform === 'win32' ? ';' : ':'
    const existingPythonPath = process.env.PYTHONPATH || ''
    const pythonPath = [engineDir, existingPythonPath].filter(Boolean).join(sep)

    sidecarProcess = spawn(pythonExe, args, {
      cwd: engineDir,
      env: { ...process.env, PYTHONPATH: pythonPath, PROBARE_API_TOKEN: sidecarToken },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
  } else {
    // Production : binaire PyInstaller embarqué
    const sidecarBin = join(
      process.resourcesPath,
      'engine',
      process.platform === 'win32' ? 'probare_engine.exe' : 'probare_engine'
    )
    args = ['--host', '127.0.0.1', '--port', String(sidecarPort)]
    sidecarProcess = spawn(sidecarBin, args, {
      env: { ...process.env, PROBARE_API_TOKEN: sidecarToken },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
  }

  sidecarProcess.stdout?.on('data', (d: Buffer) =>
    console.log('[sidecar]', d.toString().trim())
  )
  sidecarProcess.stderr?.on('data', (d: Buffer) =>
    console.error('[sidecar:err]', d.toString().trim())
  )
  sidecarProcess.on('exit', (code) => {
    console.log('[sidecar] Processus terminé avec le code', code)
    sidecarProcess = null
  })
}

export async function stopSidecar(): Promise<void> {
  if (!sidecarProcess) return
  sidecarProcess.kill('SIGTERM')
  await new Promise<void>((resolve) => {
    const timeout = setTimeout(() => {
      sidecarProcess?.kill('SIGKILL')
      resolve()
    }, 3000)
    sidecarProcess?.on('exit', () => {
      clearTimeout(timeout)
      resolve()
    })
  })
  sidecarProcess = null
}

export function getSidecarPort(): number {
  return sidecarPort
}

export function getSidecarToken(): string {
  return sidecarToken
}

export async function waitForSidecar(timeoutSec = 30): Promise<void> {
  const deadline = Date.now() + timeoutSec * 1000
  while (Date.now() < deadline) {
    try {
      await ping(sidecarPort)
      return
    } catch {
      await new Promise((r) => setTimeout(r, 300))
    }
  }
  throw new Error(`Sidecar non disponible après ${timeoutSec}s`)
}

function ping(port: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const req = http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
      if (res.statusCode === 200) resolve()
      else reject(new Error(`HTTP ${res.statusCode}`))
    })
    req.on('error', reject)
    req.setTimeout(1000, () => { req.destroy(); reject(new Error('timeout')) })
  })
}
