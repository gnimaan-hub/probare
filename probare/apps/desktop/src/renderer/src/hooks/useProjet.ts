import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useApi } from './useApi'
import { useProjetStore } from '../stores/projetStore'

/**
 * Synchronise automatiquement le projet actif depuis l'API au montage
 * de chaque page. Garantit que l'état du pipeline est toujours à jour.
 */
export function useSyncProjet() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get } = useApi()
  const { setProjetActif } = useProjetStore()

  useEffect(() => {
    if (!projetId) return
    get(`/projets/${projetId}`)
      .then(setProjetActif)
      .catch(() => {}) // silencieux — les erreurs critiques sont gérées par les pages
  }, [projetId])
}
