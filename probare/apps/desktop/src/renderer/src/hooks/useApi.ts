import { useProjetStore } from '../stores/projetStore'
import { acteurCourant } from '../lib/cabinet'

function useBaseUrl() {
  const port = useProjetStore((s) => s.apiPort)
  return `http://127.0.0.1:${port}/api`
}

/**
 * En-têtes de chaque appel à l'API locale. Deux choses distinctes y voyagent :
 *
 * - « X-Probare-Token » : le jeton partagé avec le sidecar (contrôle d'accès).
 *   Absent en mode dev/browser sans Electron — le moteur désactive alors la garde.
 * - « X-Probare-Acteur » : le responsable signataire de la fiche Cabinet, écrit
 *   comme auteur dans la piste d'audit (ISA 230). Ce n'est pas une
 *   authentification, c'est une attribution — voir `acteur.py` côté moteur.
 *
 * Les caractères non-ASCII sont retirés du nom : un en-tête HTTP ne transporte
 * que du latin-1 et `fetch` lève sur un accent, ce qui casserait l'appel entier
 * pour un signataire nommé « Awalé ». Le moteur ne se sert de ce nom que pour
 * le journal ; les livrables signés portent, eux, le nom complet non dégradé.
 */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  const token = useProjetStore.getState().apiToken
  if (token) headers['X-Probare-Token'] = token
  const acteur = acteurCourant()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // accents retires, pas les lettres
    .replace(/[^\x20-\x7e]/g, '')
    .trim()
  if (acteur) headers['X-Probare-Acteur'] = acteur
  return headers
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
