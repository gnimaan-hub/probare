import { useProjetStore } from '../stores/projetStore'

function useBaseUrl() {
  const port = useProjetStore((s) => s.apiPort)
  return `http://127.0.0.1:${port}/api`
}

/**
 * En-têtes d'authentification pour l'API locale. Lit le jeton depuis le store
 * (utilisable hors composant React via getState), et le combine avec des
 * en-têtes supplémentaires éventuels. Retourne un objet vide si aucun jeton
 * n'est configuré (mode dev/browser sans Electron).
 */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = useProjetStore.getState().apiToken
  return token ? { ...extra, 'X-Probare-Token': token } : { ...extra }
}

export function useApi() {
  const base = useBaseUrl()

  async function get<T = any>(path: string): Promise<T> {
    const res = await fetch(`${base}${path}`, { headers: authHeaders() })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function post<T = any>(path: string, body?: any): Promise<T> {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function patch<T = any>(path: string, body: any): Promise<T> {
    const res = await fetch(`${base}${path}`, {
      method: 'PATCH',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function put<T = any>(path: string, body: any): Promise<T> {
    const res = await fetch(`${base}${path}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function uploadFile(path: string, formData: FormData): Promise<any> {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function del<T = any>(path: string): Promise<T> {
    const res = await fetch(`${base}${path}`, { method: 'DELETE', headers: authHeaders() })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function downloadBlob(
    path: string,
    method: 'GET' | 'POST' = 'POST',
    body?: any,
  ): Promise<{ blob: Blob; filename: string }> {
    const hasBody = body !== undefined && method !== 'GET'
    const res = await fetch(`${base}${path}`, {
      method,
      headers: hasBody
        ? authHeaders({ 'Content-Type': 'application/json' })
        : authHeaders(),
      body: hasBody ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    const blob = await res.blob()
    const disposition = res.headers.get('content-disposition') || ''
    const match = disposition.match(/filename="?([^";\n]+)"?/)
    const filename = match ? match[1] : 'export'
    return { blob, filename }
  }

  return { get, post, patch, put, del, uploadFile, downloadBlob, baseUrl: base }
}
