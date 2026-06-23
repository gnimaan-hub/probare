import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle, CheckCircle, Wand2, Send, ArrowRight, X,
  ChevronDown, ChevronRight, RefreshCw, Lightbulb, ClipboardList,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type Exception } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'

const severiteLabel: Record<string, string> = {
  mineure: 'Mineure',
  significative: 'Significative',
  critique: 'Critique',
}

const urgenceColor: Record<string, string> = {
  faible: 'bg-slate-100 text-slate-600',
  moyenne: 'bg-amber-100 text-amber-700',
  elevee: 'bg-red-100 text-red-700',
}

const urgenceLabel: Record<string, string> = {
  faible: 'Urgence faible',
  moyenne: 'Urgence moyenne',
  elevee: 'Urgence élevée',
}

function IAPanel({
  exc,
  onRelancer,
  relancing,
}: {
  exc: Exception
  onRelancer: () => void
  relancing: boolean
}) {
  const [expanded, setExpanded] = useState(true)
  const hasIA = !!exc.interpretation_llm

  if (!hasIA && !relancing) {
    return (
      <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-dashed border-slate-200">
        <Wand2 className="w-4 h-4 text-slate-400" />
        <span className="text-xs text-slate-500 flex-1">Analyse IA non disponible (clé API non configurée).</span>
        <button onClick={onRelancer} className="btn-secondary text-xs py-1 px-2">
          <RefreshCw className="w-3 h-3" />
          Analyser
        </button>
      </div>
    )
  }

  if (relancing) {
    return (
      <div className="flex items-center gap-2 p-3 bg-primary-50 rounded-lg border border-primary-100">
        <Spinner size="sm" />
        <span className="text-xs text-primary-700">L'IA analyse cette exception…</span>
      </div>
    )
  }

  return (
    <div className="bg-primary-50 border border-primary-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-primary-100/50 transition-colors"
      >
        <Wand2 className="w-3.5 h-3.5 text-primary-600 flex-shrink-0" />
        <span className="text-xs font-semibold text-primary-700 flex-1">Analyse IA</span>
        {exc.urgence && (
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${urgenceColor[exc.urgence] || ''}`}>
            {urgenceLabel[exc.urgence] || exc.urgence}
          </span>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onRelancer() }}
          className="p-1 rounded hover:bg-primary-200/50 text-primary-500 hover:text-primary-700 transition-colors"
          title="Relancer l'analyse IA"
        >
          <RefreshCw className="w-3 h-3" />
        </button>
        {expanded
          ? <ChevronDown className="w-3.5 h-3.5 text-primary-500" />
          : <ChevronRight className="w-3.5 h-3.5 text-primary-500" />
        }
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-3 pb-3 space-y-3"
          >
            {/* Explication */}
            {exc.interpretation_llm && (
              <p className="text-xs text-primary-900 leading-relaxed border-t border-primary-100 pt-3">
                {exc.interpretation_llm}
              </p>
            )}

            {/* Hypothèses */}
            {exc.hypotheses && exc.hypotheses.length > 0 && (
              <div>
                <div className="flex items-center gap-1 text-[10px] font-semibold text-primary-600 uppercase tracking-wider mb-1.5">
                  <Lightbulb className="w-3 h-3" />
                  Hypothèses de cause
                </div>
                <ul className="space-y-1">
                  {exc.hypotheses.map((h, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-primary-800">
                      <span className="text-primary-400 mt-0.5 flex-shrink-0">▸</span>
                      {h}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Diligences */}
            {exc.diligences && exc.diligences.length > 0 && (
              <div>
                <div className="flex items-center gap-1 text-[10px] font-semibold text-primary-600 uppercase tracking-wider mb-1.5">
                  <ClipboardList className="w-3 h-3" />
                  Diligences à effectuer
                </div>
                <ul className="space-y-1">
                  {exc.diligences.map((d, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-primary-800">
                      <span className="text-primary-400 mt-0.5 flex-shrink-0">□</span>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ExceptionCard({
  exc,
  onTrancher,
  onValiderDecisionIA,
  onRelancerIA,
  relancing,
}: {
  exc: Exception
  onTrancher: (exc: Exception) => void
  onValiderDecisionIA: (exc: Exception) => void
  onRelancerIA: (exc: Exception) => void
  relancing: boolean
}) {
  const isTranchee = exc.statut === 'tranchee'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className={`card p-5 border-l-4 transition-all ${
        isTranchee
          ? 'border-l-emerald-400 opacity-80'
          : exc.severite === 'critique'
          ? 'border-l-red-500'
          : exc.severite === 'significative'
          ? 'border-l-orange-400'
          : 'border-l-slate-300'
      }`}
    >
      {/* En-tête */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-slate-800">{exc.controle_ref}</span>
            <span className={`badge badge-${exc.statut}`}>
              {isTranchee ? '✓ Tranchée' : '● Ouverte'}
            </span>
            <span className={`badge badge-${exc.severite}`}>
              {severiteLabel[exc.severite || ''] || exc.severite}
            </span>
            <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
              {exc.nep_ref}
            </code>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">{exc.description}</p>
        </div>
        {isTranchee && <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />}
      </div>

      {/* Panneau IA (toujours visible) */}
      {!isTranchee && (
        <div className="mb-3">
          <IAPanel exc={exc} onRelancer={() => onRelancerIA(exc)} relancing={relancing} />
        </div>
      )}

      {/* Décision IA proposée (si disponible) */}
      {!isTranchee && exc.decision_proposee && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 mb-3">
          <div className="text-[10px] font-semibold text-indigo-600 uppercase tracking-wider mb-1.5">
            Décision proposée par l'IA
          </div>
          <p className="text-xs text-indigo-900 leading-relaxed italic">
            {exc.decision_proposee}
          </p>
        </div>
      )}

      {/* Décision humaine (tranchée) */}
      {isTranchee && (
        <div className="space-y-2">
          {exc.interpretation_llm && (
            <div className="bg-primary-50 border border-primary-100 rounded-lg p-3">
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-primary-600 uppercase tracking-wider mb-1">
                <Wand2 className="w-3 h-3" />
                Analyse IA
              </div>
              <p className="text-xs text-primary-800 leading-relaxed">{exc.interpretation_llm}</p>
            </div>
          )}
          {exc.decision_humaine && (
            <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
              <div className="text-xs font-semibold text-emerald-700 mb-1">Décision de l'auditeur</div>
              <p className="text-xs text-emerald-800">{exc.decision_humaine}</p>
              <p className="text-xs text-emerald-600 mt-1">
                Par {exc.decideur} · {formatDate(exc.horodatage)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {!isTranchee && (
        <div className="flex gap-2 mt-3">
          {exc.decision_proposee ? (
            <>
              <button
                onClick={() => onValiderDecisionIA(exc)}
                className="btn-primary text-xs py-1.5 flex-1"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Valider la décision IA
              </button>
              <button
                onClick={() => onTrancher(exc)}
                className="btn-secondary text-xs py-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                Modifier
              </button>
            </>
          ) : (
            <button
              onClick={() => onTrancher(exc)}
              className="btn-primary text-xs py-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              Trancher cette exception
            </button>
          )}
        </div>
      )}
    </motion.div>
  )
}

interface TrancherModalProps {
  exc: Exception
  onClose: () => void
  onConfirmed: (decision: string, decideur: string) => void
}

function TrancherModal({ exc, onClose, onConfirmed }: TrancherModalProps) {
  const [decision, setDecision] = useState(exc.decision_proposee || '')
  const [decideur, setDecideur] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmationCritique, setConfirmationCritique] = useState('')

  const isCritique = exc.severite === 'critique'
  const CONFIRMATION_REQUISE = 'VALIDER'

  const peutSoumettre = (
    decision.trim().length >= 20 &&
    decideur.trim().length >= 2 &&
    (!isCritique || confirmationCritique === CONFIRMATION_REQUISE)
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!peutSoumettre) return
    setLoading(true)
    onConfirmed(decision, decideur)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 12 }}
        className="bg-white rounded-2xl shadow-modal w-full max-w-lg"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-slate-900">Trancher l'exception</h2>
            {isCritique && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                Critique
              </span>
            )}
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600">
            <strong>{exc.controle_ref}</strong> — {exc.nep_ref}<br />
            <span className="text-slate-500 mt-1 block">{exc.description}</span>
          </div>

          {isCritique && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">
                <strong>Exception critique.</strong> Votre décision sera inscrite définitivement dans le dossier d'audit et engage votre responsabilité professionnelle. Relisez attentivement avant de valider.
              </p>
            </div>
          )}

          {exc.decision_proposee && (
            <div className="flex items-start gap-2 p-2.5 bg-indigo-50 border border-indigo-100 rounded-lg">
              <Wand2 className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-indigo-700">
                La décision ci-dessous est pré-rédigée par l'IA. Modifiez-la si nécessaire avant de valider.
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Décision de l'auditeur <span className="text-red-500">*</span>
            </label>
            <textarea
              className="input-field min-h-28 resize-none"
              placeholder="Ex : Écart justifié par une régularisation de fin d'exercice. Pièce n° 2025/12/045 reçue et vérifiée."
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              required
              autoFocus
            />
            {decision.trim().length > 0 && decision.trim().length < 20 && (
              <p className="text-xs text-amber-600 mt-1">La décision doit être suffisamment argumentée (20 caractères minimum).</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Nom de l'auditeur <span className="text-red-500">*</span>
            </label>
            <input
              className="input-field"
              placeholder="Prénom Nom"
              value={decideur}
              onChange={(e) => setDecideur(e.target.value)}
              required
            />
          </div>

          {isCritique && (
            <div>
              <label className="block text-sm font-medium text-red-700 mb-1.5">
                Confirmation requise — saisissez <code className="bg-red-100 px-1 rounded">{CONFIRMATION_REQUISE}</code> pour valider <span className="text-red-500">*</span>
              </label>
              <input
                className="input-field border-red-200 focus:border-red-400"
                placeholder={CONFIRMATION_REQUISE}
                value={confirmationCritique}
                onChange={(e) => setConfirmationCritique(e.target.value.toUpperCase())}
              />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Annuler</button>
            <button
              type="submit"
              disabled={!peutSoumettre || loading}
              className={`flex-1 ${isCritique ? 'btn-danger' : 'btn-primary'}`}
            >
              {loading ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
              Confirmer la décision
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

export function Exceptions() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif, exceptions, setExceptions } = useProjetStore()
  useSyncProjet()

  const [pendingTrancher, setPendingTrancher] = useState<Exception | null>(null)
  const [relancingId, setRelancingId] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState(false)
  const [filtre, setFiltre] = useState<'toutes' | 'ouverte' | 'tranchee'>('toutes')

  useEffect(() => {
    if (!projetId) return
    get(`/projets/${projetId}/exceptions`)
      .then((d) => setExceptions(d.exceptions || []))
      .catch((e) => toast.error(e.message))
  }, [projetId])

  const handleRelancerIA = async (exc: Exception) => {
    if (!projetId) return
    setRelancingId(exc.id)
    try {
      const result = await post(`/projets/${projetId}/exceptions/${exc.id}/interpreter`)
      if (result.exception) {
        setExceptions(exceptions.map((e) => e.id === exc.id ? result.exception : e))
      }
      toast.success('Analyse IA mise à jour.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setRelancingId(null)
    }
  }

  const handleValiderDecisionIA = (exc: Exception) => {
    // Ouvre le modal pré-rempli avec la décision proposée par l'IA
    setPendingTrancher(exc)
  }

  const handleTrancher = async (decision: string, decideur: string) => {
    if (!projetId || !pendingTrancher) return
    try {
      const updated = await post(
        `/projets/${projetId}/exceptions/${pendingTrancher.id}/trancher`,
        { decision_humaine: decision, decideur }
      )
      setExceptions(exceptions.map((e) => (e.id === updated.id ? updated : e)))
      toast.success('Exception tranchée et archivée.')
      setPendingTrancher(null)
    } catch (e: any) {
      toast.error(e.message)
      setPendingTrancher(null)
    }
  }

  const handlePasserGeneration = async () => {
    if (!projetId) return
    setTransitioning(true)
    try {
      const etat = projetActif?.etat_courant
      if (etat === 'controles') {
        await post(`/projets/${projetId}/transition`, { vers: 'revue', acteur: 'utilisateur' })
      }
      const updated = await post(`/projets/${projetId}/transition`, { vers: 'generation', acteur: 'utilisateur' })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/rapport`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const ouvertes = exceptions.filter((e) => e.statut === 'ouverte')
  const tranchees = exceptions.filter((e) => e.statut === 'tranchee')
  const filtrees = filtre === 'toutes' ? exceptions : exceptions.filter((e) => e.statut === filtre)
  const toutesTranschees = ouvertes.length === 0 && exceptions.length > 0

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Revue des exceptions"
        subtitle={`${ouvertes.length} ouverte${ouvertes.length !== 1 ? 's' : ''} · ${tranchees.length} tranchée${tranchees.length !== 1 ? 's' : ''}`}
        actions={
          toutesTranschees && (
            <button onClick={handlePasserGeneration} disabled={transitioning} className="btn-primary">
              {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
              Générer le dossier
            </button>
          )
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Banner toutes tranchées */}
          {toutesTranschees && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl"
            >
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <div>
                <div className="text-sm font-semibold text-emerald-800">
                  Toutes les exceptions ont été tranchées
                </div>
                <div className="text-xs text-emerald-700 mt-0.5">
                  Vous pouvez générer le dossier de travail.
                </div>
              </div>
            </motion.div>
          )}

          {/* Filtre */}
          {exceptions.length > 0 && (
            <div className="flex gap-2">
              {(['toutes', 'ouverte', 'tranchee'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFiltre(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    filtre === f
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-white text-slate-600 border border-border hover:bg-slate-50'
                  }`}
                >
                  {f === 'toutes' ? `Toutes (${exceptions.length})`
                   : f === 'ouverte' ? `Ouvertes (${ouvertes.length})`
                   : `Tranchées (${tranchees.length})`}
                </button>
              ))}
            </div>
          )}

          {/* Liste */}
          {filtrees.length === 0 ? (
            <EmptyState
              icon={AlertTriangle}
              title="Aucune exception"
              description="Tous les contrôles ont passé sans anomalie, ou aucun contrôle n'a encore été exécuté."
            />
          ) : (
            <AnimatePresence>
              {filtrees.map((exc) => (
                <ExceptionCard
                  key={exc.id}
                  exc={exc}
                  onTrancher={setPendingTrancher}
                  onValiderDecisionIA={handleValiderDecisionIA}
                  onRelancerIA={handleRelancerIA}
                  relancing={relancingId === exc.id}
                />
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>

      <AnimatePresence>
        {pendingTrancher && (
          <TrancherModal
            exc={pendingTrancher}
            onClose={() => setPendingTrancher(null)}
            onConfirmed={handleTrancher}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
