import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, CheckCircle, Lock, LayoutDashboard } from 'lucide-react'
import { Spinner } from '../ui/Spinner'
import { useApi } from '../../hooks/useApi'
import { useToast } from '../../hooks/useToast'
import { useProjetStore } from '../../stores/projetStore'
import { LINEAR_STEPS, normaliserEtat, type LinearStep } from '../../lib/mission'
import type { Progression } from '../../hooks/useMissionProgress'

/**
 * Bandeau de guidage « prochaine étape », commun à toutes les pages linéaires.
 * Il répond en permanence à deux questions : « où en suis-je ? » et « que
 * dois-je faire pour avancer ? ». La disponibilité et la raison d'un blocage
 * viennent du backend (progression) — jamais devinées.
 */
export function StepFooter({
  projetId,
  step,
  progression,
  onAdvance,
  advancing,
  blockedReason,
}: {
  projetId: string
  step: LinearStep
  progression: Progression | null
  /** Handler d'avance spécifique à la page (sauvegarde, confirmations…).
   *  Si absent, StepFooter effectue la transition générique + navigation. */
  onAdvance?: () => void
  advancing?: boolean
  /** Précondition purement frontend (ex : documents requis manquants) qui bloque
   *  l'avance même quand le backend l'autoriserait. Prioritaire sur la garde backend. */
  blockedReason?: string
}) {
  const navigate = useNavigate()
  const { post } = useApi()
  const toast = useToast()
  const { setProjetActif } = useProjetStore()
  const [busy, setBusy] = useState(false)

  const etatCourant = progression?.etat_courant ?? step.etat
  const estEtapeCourante = normaliserEtat(etatCourant) === step.etat
  const prochaine = progression?.prochaine ?? null
  const nextStep = prochaine
    ? LINEAR_STEPS.find((s) => s.etat === prochaine.vers)
    : LINEAR_STEPS[step.num] // num est 1-based → l'élément d'index num est la suivante

  const running = busy || !!advancing

  const handleGenericAdvance = async () => {
    if (!prochaine || !nextStep) return
    setBusy(true)
    try {
      const updated = await post(`/projets/${projetId}/transition`, { vers: prochaine.vers, acteur: 'utilisateur' })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/${nextStep.route}`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setBusy(false)
    }
  }

  const advance = onAdvance ?? handleGenericAdvance

  // Étape déjà dépassée : on propose juste de revenir au cockpit.
  if (!estEtapeCourante) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="card p-4 flex items-center justify-between gap-4 border-emerald-200 bg-emerald-50/40"
      >
        <div className="flex items-center gap-2.5 text-sm text-emerald-800">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          Étape déjà franchie — vous pouvez la revoir ou la corriger librement.
        </div>
        <button onClick={() => navigate(`/projet/${projetId}`)} className="btn-secondary text-sm flex-shrink-0">
          <LayoutDashboard className="w-4 h-4" />
          Plan de mission
        </button>
      </motion.div>
    )
  }

  // Si la progression backend est indisponible (endpoint absent / hors ligne),
  // on autorise l'avance de façon optimiste : la garde backend s'applique de toute
  // façon à la transition réelle. Une précondition frontend (blockedReason) prime toujours.
  const peut = (progression ? prochaine?.peut ?? false : true) && !blockedReason
  const raison = blockedReason || prochaine?.raison || ''

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="card p-5 flex items-center justify-between gap-4"
    >
      <div className="min-w-0">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Étape {step.num} / {LINEAR_STEPS.length}
        </p>
        {nextStep ? (
          peut ? (
            <p className="text-sm text-slate-700 mt-0.5">
              Prêt à passer à <span className="font-semibold text-slate-900">{nextStep.label}</span>.
            </p>
          ) : (
            <p className="text-sm text-amber-700 mt-0.5 flex items-start gap-1.5">
              <Lock className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{raison || `Complétez cette étape avant de passer à ${nextStep.label}.`}</span>
            </p>
          )
        ) : (
          <p className="text-sm text-slate-700 mt-0.5">Dernière étape de la mission.</p>
        )}
      </div>

      {nextStep && (
        <button
          onClick={advance}
          disabled={!peut || running}
          title={!peut ? raison : ''}
          className="btn-primary flex-shrink-0"
        >
          {running ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
          Passer à {nextStep.short}
        </button>
      )}
    </motion.div>
  )
}
