import { useCallback, useEffect, useState } from 'react'
import { useApi } from './useApi'

export interface EtapeProgression {
  id: string
  statut: 'fait' | 'en_cours' | 'a_venir'
}

export interface ProchaineTransition {
  vers: string
  peut: boolean
  raison: string
}

export interface TransversalProgression {
  journal_entries: { obligatoire: boolean; fait: boolean; nb_signalees: number; disponible_des: string }
  continuite: { obligatoire: boolean; conclue: boolean; disponible_des: string }
}

export interface Progression {
  etat_courant: string
  etape_courante: string
  index: number
  total: number
  etapes: EtapeProgression[]
  prochaine: ProchaineTransition | null
  transversal: TransversalProgression
}

/**
 * Lit l'avancement de la mission depuis le backend (source de vérité des gardes).
 * Alimente le cockpit et le guidage « prochaine étape ». Se recharge sur demande
 * (après une transition ou une action qui change l'état).
 */
export function useMissionProgress(projetId?: string) {
  const { get } = useApi()
  const [progression, setProgression] = useState<Progression | null>(null)
  const [loading, setLoading] = useState(false)

  const recharger = useCallback(async () => {
    if (!projetId) return
    setLoading(true)
    try {
      const data = await get(`/projets/${projetId}/progression`)
      setProgression(data)
    } catch {
      /* silencieux — le guidage est un confort, pas un bloqueur */
    } finally {
      setLoading(false)
    }
  }, [projetId])

  useEffect(() => { recharger() }, [recharger])

  return { progression, loading, recharger }
}
