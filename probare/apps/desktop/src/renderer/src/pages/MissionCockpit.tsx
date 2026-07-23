import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight, CheckCircle, Lock, PlayCircle, AlertTriangle, Building2,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { useMissionProgress } from '../hooks/useMissionProgress'
import {
  LINEAR_STEPS, TRANSVERSAL_ITEMS, accesEtape, accesTransversal, statutEtape,
} from '../lib/mission'
import { normeLabel } from '../lib/utils'

// ─── Étape linéaire ───────────────────────────────────────────────────────────

function EtapeCard({
  projetId, step, etatCourant, onOpen,
}: {
  projetId: string
  step: typeof LINEAR_STEPS[number]
  etatCourant: string
  onOpen: () => void
}) {
  const statut = statutEtape(step.etat, etatCourant)
  const { accessible, raison } = accesEtape(step.etat, etatCourant)
  const Icon = step.icon

  const ring =
    statut === 'en_cours' ? 'border-primary-300 bg-primary-50/40 ring-1 ring-primary-200'
    : statut === 'fait'   ? 'border-emerald-200 bg-white'
    : 'border-border bg-white'

  return (
    <button
      onClick={accessible ? onOpen : undefined}
      disabled={!accessible}
      title={!accessible ? raison : ''}
      className={`w-full text-left flex items-start gap-3.5 p-4 rounded-2xl border transition-all ${ring} ${
        accessible ? 'hover:border-primary-300 hover:shadow-sm cursor-pointer' : 'opacity-55 cursor-not-allowed'
      }`}
    >
      {/* Pastille numéro / statut */}
      <div className="relative flex-shrink-0">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
          statut === 'fait' ? 'bg-emerald-100'
          : statut === 'en_cours' ? 'bg-primary-600'
          : 'bg-slate-100'
        }`}>
          {statut === 'fait'
            ? <CheckCircle className="w-5 h-5 text-emerald-600" />
            : statut === 'en_cours'
              ? <Icon className="w-5 h-5 text-white" />
              : accessible
                ? <Icon className="w-5 h-5 text-slate-400" />
                : <Lock className="w-4 h-4 text-slate-400" />}
        </div>
        <span className="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-white border border-border text-[10px] font-bold text-slate-500 flex items-center justify-center">
          {step.num}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-slate-900">{step.label}</span>
          {step.norme && (
            <span className="text-[10px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
              {normeLabel(step.norme)}
            </span>
          )}
          {statut === 'en_cours' && (
            <span className="text-[10px] font-semibold text-primary-700 bg-primary-100 px-1.5 py-0.5 rounded-full">
              En cours
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{step.but}</p>
      </div>

      {accessible && <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0 mt-1" />}
    </button>
  )
}

// ─── Travail transversal ──────────────────────────────────────────────────────

function TransversalCard({
  item, etatCourant, statut, onOpen,
}: {
  item: typeof TRANSVERSAL_ITEMS[number]
  etatCourant: string
  statut?: { fait: boolean; detail?: string }
  onOpen: () => void
}) {
  const { accessible, raison } = accesTransversal(item, etatCourant)
  const Icon = item.icon

  return (
    <button
      onClick={accessible ? onOpen : undefined}
      disabled={!accessible}
      title={!accessible ? raison : ''}
      className={`w-full text-left flex items-start gap-3 p-4 rounded-2xl border transition-all bg-white ${
        accessible ? 'border-border hover:border-primary-300 hover:shadow-sm cursor-pointer' : 'opacity-55 cursor-not-allowed'
      }`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        statut?.fait ? 'bg-emerald-100' : 'bg-slate-100'
      }`}>
        {accessible
          ? <Icon className={`w-4 h-4 ${statut?.fait ? 'text-emerald-600' : 'text-slate-500'}`} />
          : <Lock className="w-4 h-4 text-slate-400" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-slate-900">{item.label}</span>
          {item.norme && (
            <span className="text-[10px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
              {normeLabel(item.norme)}
            </span>
          )}
          {item.obligatoire && (
            statut?.fait
              ? <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">Fait</span>
              : <span className="text-[10px] font-semibold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full">Obligatoire</span>
          )}
        </div>
        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{item.but}</p>
        {statut?.detail && <p className="text-[11px] text-slate-400 mt-1">{statut.detail}</p>}
      </div>
    </button>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function MissionCockpit() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { projetActif } = useProjetStore()
  useSyncProjet()
  const { progression, loading } = useMissionProgress(projetId)

  const etatCourant = progression?.etat_courant ?? projetActif?.etat_courant ?? 'cadrage'
  const etapeCourante = LINEAR_STEPS.find((s) => s.etat === progression?.etape_courante)
    ?? LINEAR_STEPS[0]
  const pct = progression ? Math.round(((progression.index) / (progression.total - 1)) * 100) : 0

  const go = (route: string) => navigate(`/projet/${projetId}/${route}`)

  const transStatut: Record<string, { fait: boolean; detail?: string }> = {
    'journal-entries': {
      fait: !!progression?.transversal.journal_entries.fait,
      detail: progression?.transversal.journal_entries.fait
        ? `${progression.transversal.journal_entries.nb_signalees} écriture(s) signalée(s)`
        : undefined,
    },
    diligences: {
      fait: !!progression?.transversal.continuite.conclue,
      detail: progression?.transversal.continuite.conclue
        ? 'Continuité d\'exploitation conclue'
        : 'Continuité d\'exploitation à conclure',
    },
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title={projetActif?.nom || 'Plan de mission'}
        subtitle={
          projetActif
            ? `${projetActif.client || 'Client'} · Exercice ${projetActif.exercice || 'N/A'}`
            : 'Chargement…'
        }
        actions={
          etapeCourante && (
            <button onClick={() => go(etapeCourante.route)} className="btn-primary">
              <PlayCircle className="w-4 h-4" />
              Continuer la mission
            </button>
          )
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">

          {/* Barre d'avancement */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avancement</p>
                <p className="text-sm text-slate-700 mt-0.5">
                  Étape {(progression?.index ?? 0) + 1} sur {progression?.total ?? LINEAR_STEPS.length} —{' '}
                  <span className="font-semibold text-slate-900">{etapeCourante?.label}</span>
                </p>
              </div>
              <span className="text-2xl font-bold text-primary-700 tabular-nums">{pct}%</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                className="h-full bg-primary-500 rounded-full"
              />
            </div>
            {progression?.prochaine && !progression.prochaine.peut && (
              <div className="mt-3 flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-2.5">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>{progression.prochaine.raison}</span>
              </div>
            )}
          </motion.div>

          {loading && !progression ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : (
            <div className="grid lg:grid-cols-[1fr_20rem] gap-6 items-start">
              {/* Parcours linéaire */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-sm font-semibold text-slate-900">Parcours de la mission</h2>
                  <span className="text-xs text-slate-400">— séquentiel</span>
                </div>
                <div className="space-y-2.5">
                  {LINEAR_STEPS.map((step) => (
                    <EtapeCard
                      key={step.etat}
                      projetId={projetId!}
                      step={step}
                      etatCourant={etatCourant}
                      onOpen={() => go(step.route)}
                    />
                  ))}
                </div>
              </div>

              {/* Travaux transversaux */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-sm font-semibold text-slate-900">Travaux transversaux</h2>
                </div>
                <p className="text-xs text-slate-500 mb-3 leading-relaxed">
                  Diligences qui s'exercent sur toute la mission, hors séquence.
                  Deux d'entre elles sont obligatoires pour boucler le dossier.
                </p>
                <div className="space-y-2.5">
                  {TRANSVERSAL_ITEMS.map((item) => (
                    <TransversalCard
                      key={item.id}
                      item={item}
                      etatCourant={etatCourant}
                      statut={transStatut[item.id]}
                      onOpen={() => go(item.route)}
                    />
                  ))}
                </div>

                <button
                  onClick={() => navigate('/dashboard')}
                  className="btn-ghost text-xs gap-1.5 text-slate-500 mt-4 w-full justify-center"
                >
                  <Building2 className="w-3.5 h-3.5" />
                  Toutes les missions
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
