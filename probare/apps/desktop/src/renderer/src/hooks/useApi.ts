import { useProjetStore } from '../stores/projetStore'

function useBaseUrl() {
  const port = useProjetStore((s) => s.apiPort)
  return `http://127.0.0.1:${port}/api`
}

export function useApi() {
  const base = useBaseUrl()

  async function get<T = any>(path: string): Promise<T> {
    const res = await fetch(`${base}${path}`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function post<T = any>(path: string, body?: any): Promise<T> {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' },
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
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function del<T = any>(path: string): Promise<T> {
    const res = await fetch(`${base}${path}`, { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || res.statusText)
    }
    return res.json()
  }

  async function downloadBlob(path: string, method: 'GET' | 'POST' = 'POST'): Promise<{ blob: Blob; filename: string }> {
    const res = await fetch(`${base}${path}`, { method })
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

  return { get, post, patch, del, uploadFile, downloadBlob, baseUrl: base }
}
