import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle, XCircle, Play, ArrowRight, ChevronDown, ChevronRight,
  Shield, Wand2, ShoppingCart, TrendingUp
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type ResultatControle } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

type Cycle = 'tresorerie' | 'achats' | 'ventes'

const CYCLES: { id: Cycle; label: string; icon: any; nep: string; accounts: string }[] = [
  {
    id: 'tresorerie',
    label: 'Trésorerie',
    icon: Shield,
    nep: 'NEP 500, 330, 520',
    accounts: 'Comptes 5xx',
  },
  {
    id: 'achats',
    label: 'Achats-Fournisseurs',
    icon: ShoppingCart,
    nep: 'NEP 500, 330, 520',
    accounts: 'Comptes 40x + 60x-63x',
  },
  {
    id: 'ventes',
    label: 'Ventes-Clients',
    icon: TrendingUp,
    nep: 'NEP 500, 330, 520',
    accounts: 'Comptes 41x + 70x-73x',
  },
]

// ─── Composant résultat ───────────────────────────────────────────────────────

function ResultatRow({ resultat, index }: { resultat: ResultatControle; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const isOk = resultat.statut === 'ok'

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.025 }}
      className={`border rounded-xl overflow-hidden transition-all ${
        isOk ? 'border-border' : 'border-red-200'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center gap-3 p-3.5 text-left hover:bg-slate-50 transition-colors ${
          !isOk ? 'bg-red-50/50' : ''
        }`}
      >
        {isOk
          ? <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
          : <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
        }
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-800">{resultat.controle_ref}</span>
            <span className={`badge ${isOk ? 'badge-ok' : 'badge-exception'}`}>
              {isOk ? 'OK' : 'Exception'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{resultat.details}</p>
        </div>
        <div className="text-xs text-slate-400 mr-2 flex-shrink-0">
          {formatDate(resultat.calcule_le)}
        </div>
        {expanded
          ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
          : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
        }
      </button>

      {expanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="border-t border-border px-4 pb-4 pt-3 bg-slate-50/50"
        >
          <div className="text-xs space-y-2">
            <div>
              <span className="font-semibold text-slate-600">Détails : </span>
              <span className="text-slate-700">{resultat.details}</span>
            </div>
            {resultat.valeur !== undefined && resultat.valeur !== null && (
              <div>
                <span className="font-semibold text-slate-600">Valeur : </span>
                <span className="font-mono text-slate-700">{resultat.valeur}</span>
              </div>
            )}
            {resultat.sources && resultat.sources.length > 0 && (
              <div>
                <span className="font-semibold text-slate-600">Sources ({resultat.sources.length}) : </span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {resultat.sources.slice(0, 6).map((src) => (
                    <code key={src} className="bg-white border border-border px-1.5 py-0.5 rounded text-[10px] text-slate-600">
                      {src.slice(0, 8)}…
                    </code>
                  ))}
                  {resultat.sources.length > 6 && (
                    <span className="text-slate-400 text-xs">+{resultat.sources.length - 6}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

// ─── Onglet d'un cycle ────────────────────────────────────────────────────────

function CyclePanel({
  cycle,
  projetId,
  etatCourant,
}: {
  cycle: typeof CYCLES[0]
  projetId: string
  etatCourant: string
}) {
  const { post, get } = useApi()
  const toast = useToast()
  const { setExceptions } = useProjetStore()

  const [running, setRunning] = useState(false)
  const [resultats, setResultats] = useState<ResultatControle[]>([])
  const [iaAnalysees, setIaAnalysees] = useState(0)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!projetId) return
    get(`/projets/${projetId}/controles?cycle=${cycle.id}`)
      .then((d) => { setResultats(d.resultats || []); setLoaded(true) })
      .catch(() => setLoaded(true))
  }, [projetId, cycle.id])

  const handleLancer = async () => {
    setRunning(true)
    setIaAnalysees(0)
    try {
      const result = await post(`/projets/${projetId}/controles/${cycle.id}`, {})
      setResultats(result.resultats || [])
      setExceptions(result.exceptions || [])
      const nbIA = (result.exceptions || []).filter((e: any) => e.ia_analysee).length
      setIaAnalysees(nbIA)
      const msg = result.nb_exceptions > 0
        ? `${result.nb_controles} contrôle(s). ${result.nb_exceptions} exception(s)${nbIA > 0 ? `, ${nbIA} analysée(s) par l'IA` : ''}.`
        : `${result.nb_controles} contrôle(s) — aucune exception.`
      toast.success(msg)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setRunning(false)
    }
  }

  const nbOk = resultats.filter((r) => r.statut === 'ok').length
  const nbExc = resultats.filter((r) => r.statut === 'exception').length
  const canRun = ['controles', 'extraction', 'revue'].includes(etatCourant)

  return (
    <div className="space-y-4">
      {/* En-tête du cycle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500">{cycle.accounts} — {cycle.nep}</p>
        </div>
        {canRun && (
          <button onClick={handleLancer} disabled={running} className="btn-secondary text-sm">
            {running ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
            {running ? 'Calcul + analyse IA…' : `Lancer les contrôles`}
          </button>
        )}
      </div>

      {/* Bannière IA */}
      {iaAnalysees > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-3.5 bg-primary-50 border border-primary-100 rounded-xl"
        >
          <Wand2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
          <p className="text-sm text-primary-800">
            <span className="font-semibold">{iaAnalysees} exception{iaAnalysees !== 1 ? 's' : ''}</span>
            {' '}analysée{iaAnalysees !== 1 ? 's' : ''} et interprétée{iaAnalysees !== 1 ? 's' : ''} par l'IA.
            Consultez la page <span className="font-semibold">Exceptions</span> pour valider.
          </p>
        </motion.div>
      )}

      {/* Statistiques */}
      {resultats.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="card p-3 border-l-4 border-primary-400 text-center">
            <div className="text-xl font-bold text-slate-900">{resultats.length}</div>
            <div className="text-xs text-slate-500">Contrôles</div>
          </div>
          <div className="card p-3 border-l-4 border-emerald-400 text-center">
            <div className="text-xl font-bold text-emerald-700">{nbOk}</div>
            <div className="text-xs text-emerald-600">OK</div>
          </div>
          <div className="card p-3 border-l-4 border-red-400 text-center">
            <div className="text-xl font-bold text-red-700">{nbExc}</div>
            <div className="text-xs text-red-600">Exceptions</div>
          </div>
        </div>
      )}

      {/* Résultats */}
      {!loaded ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : resultats.length === 0 ? (
        <EmptyState
          icon={cycle.icon}
          title={`Contrôles ${cycle.label} non exécutés`}
          description={`Lancez les contrôles pour analyser les données ${cycle.accounts}.`}
          action={
            canRun ? (
              <button onClick={handleLancer} disabled={running} className="btn-primary">
                {running ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
                Lancer les contrôles
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
            {resultats.length} résultat{resultats.length !== 1 ? 's' : ''} — code Python, aucun calcul LLM
          </div>
          {resultats.map((r, i) => (
            <ResultatRow key={r.id} resultat={r} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function Controles() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { post } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif, resultats } = useProjetStore()
  useSyncProjet()

  const [transitioning, setTransitioning] = useState(false)
  const [launchingAll, setLaunchingAll] = useState(false)

  const etatCourant = projetActif?.etat_courant || ''

  // Filtre les cycles selon la mission
  const cyclesMission = CYCLES.filter((c) =>
    (projetActif?.cycles_couverts ?? []).includes(c.id)
  )
  const [activeCycle, setActiveCycle] = useState<Cycle | null>(null)

  // Quand les cycles de la mission sont connus, sélectionner le premier
  useEffect(() => {
    if (cyclesMission.length > 0 && !activeCycle) {
      setActiveCycle(cyclesMission[0].id)
    }
  }, [cyclesMission.length])

  const handlePasserRevue = async () => {
    if (!projetId) return
    setTransitioning(true)
    try {
      const updated = await post(`/projets/${projetId}/transition`, { vers: 'revue', acteur: 'utilisateur' })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/exceptions`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const handleLancerTous = async () => {
    if (!projetId) return
    setLaunchingAll(true)
    try {
      let totalControles = 0
      let totalExceptions = 0
      for (const c of cyclesMission) {
        const result = await post(`/projets/${projetId}/controles/${c.id}`, {})
        totalControles += result.nb_controles || 0
        totalExceptions += result.nb_exceptions || 0
      }
      toast.success(`${totalControles} contrôle(s) sur ${cyclesMission.length} cycle(s). ${totalExceptions} exception(s).`)
      // Forcer rechargement des panels en changeant d'onglet
      if (cyclesMission.length > 0) {
        setActiveCycle(null)
        setTimeout(() => setActiveCycle(cyclesMission[0].id), 50)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLaunchingAll(false)
    }
  }

  const canRun = ['controles', 'extraction', 'revue'].includes(etatCourant)
  const nbCycles = cyclesMission.length

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Contrôles déterministes"
        subtitle={`Calcul Python — ${nbCycles} cycle${nbCycles !== 1 ? 's' : ''} dans la mission`}
        actions={
          <div className="flex gap-2">
            {canRun && (
              <button onClick={handleLancerTous} disabled={launchingAll} className="btn-secondary">
                {launchingAll ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
                Lancer tous les contrôles
              </button>
            )}
            {resultats.length > 0 && etatCourant === 'controles' && (
              <button onClick={handlePasserRevue} disabled={transitioning} className="btn-primary">
                {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                Passer à la revue
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        {/* Onglets cycles — uniquement ceux de la mission */}
        <div className="border-b border-border bg-white sticky top-0 z-10">
          <div className="flex">
            {cyclesMission.map((c) => {
              const Icon = c.icon
              return (
                <button
                  key={c.id}
                  onClick={() => setActiveCycle(c.id)}
                  className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${
                    activeCycle === c.id
                      ? 'border-primary-600 text-primary-700 bg-primary-50/50'
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {c.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Contenu du cycle actif */}
        <div className="p-6 max-w-3xl mx-auto">
          {projetId && cyclesMission.map((c) => (
            <div key={c.id} className={activeCycle === c.id ? '' : 'hidden'}>
              <CyclePanel
                cycle={c}
                projetId={projetId}
                etatCourant={etatCourant}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
