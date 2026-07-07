import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle, XCircle, Play, ArrowRight, ChevronDown, ChevronRight,
  Shield, Wand2, ShoppingCart, TrendingUp, Landmark, Package, Users, Receipt, PieChart,
  Mail, Send, Plus, Trash2, AlertTriangle, FileText, Eye, RefreshCw,
  BarChart3, CheckSquare, Square,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type ResultatControle } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate, normeLabel } from '../lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

type Cycle = 'tresorerie' | 'achats' | 'ventes' | 'immobilisations' | 'stocks' | 'paie' | 'impots' | 'capitaux_propres'

const CYCLES: { id: Cycle; label: string; icon: any; nep: string; accounts: string }[] = [
  {
    id: 'tresorerie',
    label: 'Trésorerie',
    icon: Shield,
    nep: '500, 330, 520',
    accounts: 'Comptes 5xx',
  },
  {
    id: 'achats',
    label: 'Achats-Fournisseurs',
    icon: ShoppingCart,
    nep: '500, 330, 520',
    accounts: 'Comptes 40x + 60x-63x',
  },
  {
    id: 'ventes',
    label: 'Ventes-Clients',
    icon: TrendingUp,
    nep: '500, 330, 520',
    accounts: 'Comptes 41x + 70x-73x',
  },
  {
    id: 'immobilisations',
    label: 'Immobilisations',
    icon: Landmark,
    nep: '500, 330, 520',
    accounts: 'Comptes 2xx',
  },
  {
    id: 'stocks',
    label: 'Stocks',
    icon: Package,
    nep: '500, 330, 520',
    accounts: 'Comptes 3xx',
  },
  {
    id: 'paie',
    label: 'Paie / Personnel',
    icon: Users,
    nep: '500, 330, 520',
    accounts: 'Comptes 42x + 64x',
  },
  {
    id: 'impots',
    label: 'Impôts & Taxes',
    icon: Receipt,
    nep: '500, 330, 520',
    accounts: 'Comptes 44x + 63x',
  },
  {
    id: 'capitaux_propres',
    label: 'Capitaux propres',
    icon: PieChart,
    nep: '500, 330, 520',
    accounts: 'Comptes 10x-15x',
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
  externallyLaunching,
}: {
  cycle: typeof CYCLES[0]
  projetId: string
  etatCourant: string
  externallyLaunching?: boolean
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
    // Si des résultats existent déjà, demander confirmation pour éviter la duplication
    if (resultats.length > 0) {
      const ok = window.confirm(
        `Des résultats existent déjà pour le cycle ${cycle.label}.\nRelancer les contrôles peut créer des doublons dans les exceptions.\n\nContinuer quand même ?`
      )
      if (!ok) return
    }
    setRunning(true)
    setIaAnalysees(0)
    try {
      const result = await post(`/projets/${projetId}/controles/${cycle.id.replace(/_/g, '-')}`, {})
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
  const canRun = ['travaux_substantifs', 'controles', 'extraction', 'revue'].includes(etatCourant)
  const isBlocked = running || !!externallyLaunching

  return (
    <div className="space-y-4">
      {/* En-tête du cycle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500">{cycle.accounts} — {normeLabel(cycle.nep)}</p>
        </div>
        {canRun && (
          <button onClick={handleLancer} disabled={isBlocked} className="btn-secondary text-sm">
            {isBlocked ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
            {running ? 'Calcul + analyse IA…' : externallyLaunching ? 'En cours…' : resultats.length > 0 ? 'Relancer les contrôles' : 'Lancer les contrôles'}
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

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const STATUT_CIRC_LABEL: Record<string, string> = {
  propose: 'Proposé',
  envoye: 'Envoyé',
  reponse_recue: 'Réponse reçue',
  sans_reponse: 'Sans réponse',
  clos: 'Clos',
}

const STATUT_CIRC_CLASS: Record<string, string> = {
  propose: 'bg-slate-100 text-slate-600',
  envoye: 'bg-blue-100 text-blue-700',
  reponse_recue: 'bg-amber-100 text-amber-700',
  sans_reponse: 'bg-red-100 text-red-700',
  clos: 'bg-emerald-100 text-emerald-700',
}

// ─── Circularisation (NEP 505) ───────────────────────────────────────────────

type Circ = {
  id: string; projet_id: string; cycle: string; compte: string; libelle: string
  solde_comptable: number | null; statut: string; lettre_ia: any
  solde_confirme: number | null; ecart: number | null; ecart_pct: number | null
  est_significatif: boolean; reponse_brute: string; analyse_ia: any
  date_envoi: string | null; date_reponse: string | null; sources: string[]
}

function CircularisationPanel({
  projetId, cycles, etatCourant,
}: { projetId: string; cycles: typeof CYCLES; etatCourant: string }) {
  const { get, post, patch, del } = useApi()
  const toast = useToast()

  const [activeCycle, setActiveCycle] = useState(cycles[0]?.id ?? '')
  const [circs, setCircs] = useState<Circ[]>([])
  const [loading, setLoading] = useState(false)
  const [proposing, setProposing] = useState(false)
  const [tiersProposed, setTiersProposed] = useState<any[]>([])
  const [selectedTiers, setSelectedTiers] = useState<Set<string>>(new Set())
  const [showPropose, setShowPropose] = useState(false)
  const [expandedCirc, setExpandedCirc] = useState<string | null>(null)
  const [reponseForm, setReponseForm] = useState<{ id: string; solde: string; texte: string } | null>(null)
  const [showLettre, setShowLettre] = useState<string | null>(null)
  const [generatingLetter, setGeneratingLetter] = useState<string | null>(null)
  const [analysingCirc, setAnalysingCirc] = useState<string | null>(null)
  const [creatingCircs, setCreatingCircs] = useState(false)

  const canAct = ['travaux_substantifs', 'controles', 'revue'].includes(etatCourant)

  const load = () => {
    setLoading(true)
    get(`/projets/${projetId}/circularisation?cycle=${activeCycle}`)
      .then((d) => setCircs(d.circularisations || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [activeCycle])

  const handleProposer = async () => {
    setProposing(true)
    try {
      const d = await post(`/projets/${projetId}/circularisation/proposer`, { cycle: activeCycle, n: 10 })
      setTiersProposed(d.tiers || [])
      setSelectedTiers(new Set((d.tiers || []).map((t: any) => t.compte)))
      setShowPropose(true)
    } catch (e: any) { toast.error(e.message) }
    finally { setProposing(false) }
  }

  const handleCreerCircs = async () => {
    setCreatingCircs(true)
    try {
      const toCreate = tiersProposed.filter((t) => selectedTiers.has(t.compte))
      for (const t of toCreate) {
        await post(`/projets/${projetId}/circularisation`, {
          cycle: activeCycle, compte: t.compte, libelle: t.libelle,
          solde_comptable: t.solde, sources: t.sources,
          type_circularisation: activeCycle === 'tresorerie' ? 'banque'
            : activeCycle === 'ventes' ? 'client' : 'fournisseur',
        })
      }
      toast.success(`${toCreate.length} circularisation(s) créée(s).`)
      setShowPropose(false)
      load()
    } catch (e: any) { toast.error(e.message) }
    finally { setCreatingCircs(false) }
  }

  const handleGenererLettre = async (circ: Circ) => {
    setGeneratingLetter(circ.id)
    try {
      const d = await post(`/projets/${projetId}/circularisation/${circ.id}/generer-lettre`, {})
      setCircs((prev) => prev.map((c) => c.id === circ.id ? d.circularisation : c))
      setShowLettre(circ.id)
      toast.success('Lettre générée par l\'IA.')
    } catch (e: any) { toast.error(e.message) }
    finally { setGeneratingLetter(null) }
  }

  const handleEnregistrerReponse = async () => {
    if (!reponseForm) return
    try {
      const d = await post(`/projets/${projetId}/circularisation/${reponseForm.id}/enregistrer-reponse`, {
        solde_confirme: parseFloat(reponseForm.solde) || 0,
        reponse_brute: reponseForm.texte,
      })
      setCircs((prev) => prev.map((c) => c.id === reponseForm.id ? d.circularisation : c))
      setReponseForm(null)
      toast.success(`Réponse enregistrée. Écart : ${fmt(d.ecart?.ecart)} Fdj.`)
    } catch (e: any) { toast.error(e.message) }
  }

  const handleAnalyser = async (circ: Circ) => {
    setAnalysingCirc(circ.id)
    try {
      const d = await post(`/projets/${projetId}/circularisation/${circ.id}/analyser`, {})
      setCircs((prev) => prev.map((c) => c.id === circ.id ? d.circularisation : c))
      toast.success('Analyse IA terminée.')
    } catch (e: any) { toast.error(e.message) }
    finally { setAnalysingCirc(null) }
  }

  const handleMarquerSansReponse = async (circ: Circ) => {
    const d = await patch(`/projets/${projetId}/circularisation/${circ.id}`, { statut: 'sans_reponse' })
    setCircs((prev) => prev.map((c) => c.id === circ.id ? d.circularisation : c))
  }

  const handleSupprimer = async (circ: Circ) => {
    if (!confirm(`Supprimer la circularisation ${circ.compte} ?`)) return
    await del(`/projets/${projetId}/circularisation/${circ.id}`)
    setCircs((prev) => prev.filter((c) => c.id !== circ.id))
    toast.success('Supprimée.')
  }

  const cycleCirc = circs.filter((c) => c.cycle === activeCycle)

  return (
    <div className="flex flex-col h-full">
      {/* Onglets cycles */}
      <div className="border-b border-border bg-white sticky top-[41px] z-10">
        <div className="flex overflow-x-auto">
          {cycles.map((c) => {
            const Icon = c.icon
            return (
              <button key={c.id} onClick={() => setActiveCycle(c.id)}
                className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
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

      <div className="p-6 max-w-3xl mx-auto w-full space-y-4">
        {/* En-tête */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-800 flex items-center gap-2">
              <Mail className="w-4 h-4 text-primary-500" />
              Circularisation — {normeLabel('505')}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Confirmation externe des soldes auprès des tiers ({cycleCirc.length} tiers suivi{cycleCirc.length !== 1 ? 's' : ''})
            </p>
          </div>
          {canAct && (
            <button onClick={handleProposer} disabled={proposing} className="btn-secondary text-sm">
              {proposing ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
              Proposer des tiers
            </button>
          )}
        </div>

        {/* Modal proposition tiers */}
        <AnimatePresence>
          {showPropose && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="card border-primary-100 bg-primary-50/30 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-700">
                  Tiers proposés ({tiersProposed.length}) — sélectionnez ceux à circulariser
                </p>
                <button onClick={() => setShowPropose(false)} className="text-slate-400 hover:text-slate-600 text-xs">Annuler</button>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {tiersProposed.map((t) => (
                  <label key={t.compte} className="flex items-center gap-3 p-2 rounded-lg bg-white border border-border cursor-pointer hover:bg-slate-50">
                    <input type="checkbox" className="rounded"
                      checked={selectedTiers.has(t.compte)}
                      onChange={(e) => {
                        const s = new Set(selectedTiers)
                        e.target.checked ? s.add(t.compte) : s.delete(t.compte)
                        setSelectedTiers(s)
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 truncate">{t.libelle || t.compte}</div>
                      <div className="text-xs text-slate-500 font-mono">{t.compte}</div>
                    </div>
                    <div className="text-sm font-semibold text-slate-700 flex-shrink-0">
                      {fmt(t.solde)} Fdj
                    </div>
                  </label>
                ))}
                {tiersProposed.length === 0 && (
                  <p className="text-sm text-slate-500 text-center py-4">Aucune donnée disponible pour ce cycle.</p>
                )}
              </div>
              {tiersProposed.length > 0 && (
                <div className="flex justify-end gap-2">
                  <button onClick={() => setShowPropose(false)} className="btn-ghost text-sm">Annuler</button>
                  <button onClick={handleCreerCircs} disabled={creatingCircs || selectedTiers.size === 0} className="btn-primary text-sm">
                    {creatingCircs ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
                    Créer {selectedTiers.size} circularisation{selectedTiers.size !== 1 ? 's' : ''}
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Liste */}
        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : cycleCirc.length === 0 ? (
          <div className="flex flex-col items-center py-16 gap-3 text-center">
            <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
              <Mail className="w-6 h-6 text-slate-300" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600">Aucune circularisation créée</p>
              <p className="text-xs text-slate-400 mt-1">
                Cliquez sur « Proposer des tiers » pour sélectionner les comptes à confirmer.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {cycleCirc.map((circ) => {
              const lettre = circ.lettre_ia
                ? (typeof circ.lettre_ia === 'string' ? JSON.parse(circ.lettre_ia) : circ.lettre_ia)
                : null
              const analyse = circ.analyse_ia
                ? (typeof circ.analyse_ia === 'string' ? JSON.parse(circ.analyse_ia) : circ.analyse_ia)
                : null
              const isExpanded = expandedCirc === circ.id
              return (
                <motion.div key={circ.id} layout
                  className={`card overflow-hidden transition-all ${
                    circ.est_significatif ? 'border-red-200' : ''
                  }`}
                >
                  {/* Header */}
                  <button className="w-full flex items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
                    onClick={() => setExpandedCirc(isExpanded ? null : circ.id)}>
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      circ.statut === 'clos' ? 'bg-emerald-400' :
                      circ.statut === 'reponse_recue' ? 'bg-amber-400' :
                      circ.statut === 'sans_reponse' ? 'bg-red-400' :
                      circ.statut === 'envoye' ? 'bg-blue-400' : 'bg-slate-300'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-800">{circ.libelle || circ.compte}</span>
                        <code className="text-xs text-slate-500 font-mono">{circ.compte}</code>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUT_CIRC_CLASS[circ.statut] || 'bg-slate-100 text-slate-600'}`}>
                          {STATUT_CIRC_LABEL[circ.statut] || circ.statut}
                        </span>
                        {circ.est_significatif && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />Écart significatif
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                        <span>Solde comptable : <span className="font-semibold">{fmt(circ.solde_comptable)} Fdj</span></span>
                        {circ.solde_confirme != null && (
                          <span>Confirmé : <span className="font-semibold">{fmt(circ.solde_confirme)} Fdj</span></span>
                        )}
                        {circ.ecart != null && (
                          <span className={circ.est_significatif ? 'text-red-600 font-semibold' : ''}>
                            Écart : {fmt(circ.ecart)} Fdj ({((circ.ecart_pct || 0)).toFixed(1)} %)
                          </span>
                        )}
                      </div>
                    </div>
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    }
                  </button>

                  {/* Contenu expandé */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} className="border-t border-border">
                        <div className="p-4 space-y-3">
                          {/* Actions */}
                          {canAct && (
                            <div className="flex flex-wrap gap-2">
                              {!lettre && (
                                <button onClick={() => handleGenererLettre(circ)}
                                  disabled={generatingLetter === circ.id}
                                  className="btn-ghost text-xs">
                                  {generatingLetter === circ.id ? <Spinner size="sm" /> : <Mail className="w-3.5 h-3.5" />}
                                  Générer la lettre IA
                                </button>
                              )}
                              {lettre && (
                                <button onClick={() => setShowLettre(showLettre === circ.id ? null : circ.id)}
                                  className="btn-ghost text-xs">
                                  <Eye className="w-3.5 h-3.5" />
                                  {showLettre === circ.id ? 'Masquer' : 'Voir la lettre'}
                                </button>
                              )}
                              {circ.statut === 'envoye' && (
                                <>
                                  <button onClick={() => setReponseForm({ id: circ.id, solde: '', texte: '' })}
                                    className="btn-ghost text-xs">
                                    <Send className="w-3.5 h-3.5" />
                                    Saisir la réponse
                                  </button>
                                  <button onClick={() => handleMarquerSansReponse(circ)}
                                    className="btn-ghost text-xs">
                                    <AlertTriangle className="w-3.5 h-3.5" />
                                    Sans réponse
                                  </button>
                                </>
                              )}
                              {circ.statut === 'reponse_recue' && !analyse && (
                                <button onClick={() => handleAnalyser(circ)}
                                  disabled={analysingCirc === circ.id}
                                  className="btn-ghost text-xs">
                                  {analysingCirc === circ.id ? <Spinner size="sm" /> : <Wand2 className="w-3.5 h-3.5" />}
                                  Analyse IA
                                </button>
                              )}
                              <button onClick={() => handleSupprimer(circ)} className="btn-ghost text-xs text-red-500 hover:text-red-700 ml-auto">
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}

                          {/* Lettre */}
                          {showLettre === circ.id && lettre && (
                            <div className="bg-slate-50 rounded-lg p-4 text-xs space-y-2 border border-border">
                              <p className="font-semibold text-slate-600 text-xs uppercase tracking-wider">Lettre de confirmation</p>
                              <p><span className="font-medium">Objet : </span>{lettre.objet}</p>
                              <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed">{lettre.corps}</pre>
                              {lettre.formule_confirmation && (
                                <div className="border-t border-dashed border-slate-200 pt-2">
                                  <p className="font-medium text-slate-600">Formule de confirmation :</p>
                                  <p className="italic text-slate-700 mt-1">{lettre.formule_confirmation}</p>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Formulaire réponse */}
                          {reponseForm?.id === circ.id && (
                            <div className="bg-amber-50 rounded-lg p-4 border border-amber-200 space-y-3">
                              <p className="text-xs font-semibold text-amber-800">Enregistrer la réponse du tiers</p>
                              <div className="flex gap-3">
                                <div className="flex-1">
                                  <label className="text-xs text-slate-600 mb-1 block">Solde confirmé (Fdj)</label>
                                  <input type="number" className="input text-sm" placeholder="0"
                                    value={reponseForm.solde}
                                    onChange={(e) => setReponseForm({ ...reponseForm, solde: e.target.value })}
                                  />
                                </div>
                              </div>
                              <div>
                                <label className="text-xs text-slate-600 mb-1 block">Réponse brute / commentaire</label>
                                <textarea className="input text-sm w-full h-20 resize-none"
                                  placeholder="Texte de la réponse reçue du tiers..."
                                  value={reponseForm.texte}
                                  onChange={(e) => setReponseForm({ ...reponseForm, texte: e.target.value })}
                                />
                              </div>
                              <div className="flex gap-2 justify-end">
                                <button onClick={() => setReponseForm(null)} className="btn-ghost text-xs">Annuler</button>
                                <button onClick={handleEnregistrerReponse} className="btn-primary text-xs">
                                  <CheckCircle className="w-3.5 h-3.5" />
                                  Enregistrer
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Analyse IA */}
                          {analyse && (
                            <div className="bg-primary-50 rounded-lg p-4 border border-primary-100 space-y-2 text-xs">
                              <div className="flex items-center gap-2">
                                <Wand2 className="w-3.5 h-3.5 text-primary-600" />
                                <span className="font-semibold text-primary-800">Analyse IA</span>
                                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                                  analyse.conclusion === 'sans_anomalie' ? 'bg-emerald-100 text-emerald-700' :
                                  analyse.conclusion === 'anomalie_expliquee' ? 'bg-amber-100 text-amber-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                  {analyse.conclusion?.replace(/_/g, ' ')}
                                </span>
                              </div>
                              <p className="text-slate-700 leading-relaxed">{analyse.synthese}</p>
                              {analyse.causes_probables?.length > 0 && (
                                <div>
                                  <p className="font-medium text-slate-600 mt-2">Causes probables :</p>
                                  <ul className="list-disc list-inside space-y-1 text-slate-600">
                                    {analyse.causes_probables.map((c: string, i: number) => <li key={i}>{c}</li>)}
                                  </ul>
                                </div>
                              )}
                              {analyse.diligences?.length > 0 && (
                                <div>
                                  <p className="font-medium text-slate-600 mt-2">Diligences recommandées :</p>
                                  <ul className="list-disc list-inside space-y-1 text-slate-600">
                                    {analyse.diligences.map((d: string, i: number) => <li key={i}>{d}</li>)}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Réponse brute */}
                          {circ.reponse_brute && !analyse && (
                            <div className="bg-slate-50 rounded-lg p-3 border border-border text-xs text-slate-600">
                              <span className="font-medium">Réponse reçue : </span>
                              {circ.reponse_brute}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        )}

        {/* Récap */}
        {cycleCirc.length > 0 && (
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Total', val: cycleCirc.length, cls: 'border-slate-400' },
              { label: 'Réponses', val: cycleCirc.filter((c) => ['reponse_recue', 'clos'].includes(c.statut)).length, cls: 'border-emerald-400' },
              { label: 'Sans réponse', val: cycleCirc.filter((c) => c.statut === 'sans_reponse').length, cls: 'border-red-400' },
              { label: 'Écarts sign.', val: cycleCirc.filter((c) => c.est_significatif).length, cls: 'border-amber-400' },
            ].map((s) => (
              <div key={s.label} className={`card p-3 border-l-4 ${s.cls} text-center`}>
                <div className="text-xl font-bold text-slate-900">{s.val}</div>
                <div className="text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Sondages sur pièces (NEP 530) ───────────────────────────────────────────

type SondageElement = {
  id: string; sondage_id: string; projet_id: string; index_original: number
  compte: string; libelle: string; montant: number; numero_piece: string
  date_piece: string; sources: string[]; est_anomalie: boolean; montant_anomalie: number
  commentaire: string
}

type Sondage = {
  id: string; projet_id: string; cycle: string; libelle: string; prefixes: string[]
  population: number; taille_echantillon: number; taux_erreur_tolere: number
  niveau_confiance: number; montant_population: number; seed: number
  nb_anomalies: number; montant_anomalies: number; taux_anomalie: number | null
  montant_projete: number | null; conclusion_ia: any; statut: string; cree_le: string
  elements?: SondageElement[]
}

const CYCLE_PREFIXES: Record<string, string[]> = {
  tresorerie: ['51', '52', '53', '54'],
  achats: ['40', '60', '61', '62'],
  ventes: ['41', '70', '71', '72'],
  immobilisations: ['20', '21', '22', '23'],
  stocks: ['31', '32', '33', '34', '35', '37'],
  paie: ['42', '43', '64'],
  impots: ['44', '63'],
  capitaux_propres: ['10', '11', '12', '13', '14', '15'],
}

function SondagesPanel({
  projetId, cycles, etatCourant,
}: { projetId: string; cycles: typeof CYCLES; etatCourant: string }) {
  const { get, post, patch, del } = useApi()
  const toast = useToast()

  const [sondages, setSondages] = useState<Sondage[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selecting, setSelecting] = useState<string | null>(null)
  const [concluding, setConcluding] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({
    cycle: cycles[0]?.id ?? '',
    libelle: '',
    taux_erreur_tolere: 0.05,
    niveau_confiance: 95,
  })
  const [creating, setCreating] = useState(false)

  const canAct = ['travaux_substantifs', 'controles', 'revue'].includes(etatCourant)

  const load = () => {
    setLoading(true)
    get(`/projets/${projetId}/sondages`)
      .then((d) => setSondages(d.sondages || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreer = async () => {
    if (!createForm.libelle.trim()) { toast.error('Donnez un libellé au sondage.'); return }
    setCreating(true)
    try {
      const d = await post(`/projets/${projetId}/sondages`, {
        ...createForm,
        prefixes: CYCLE_PREFIXES[createForm.cycle] || [],
      })
      setSondages((prev) => [...prev, { ...d.sondage, elements: [] }])
      setExpandedId(d.sondage.id)
      setShowCreate(false)
      setCreateForm({ cycle: cycles[0]?.id ?? '', libelle: '', taux_erreur_tolere: 0.05, niveau_confiance: 95 })
      toast.success(`Sondage créé — taille recommandée : ${d.sondage.taille_echantillon} éléments.`)
    } catch (e: any) { toast.error(e.message) }
    finally { setCreating(false) }
  }

  const handleSelectionner = async (sondage: Sondage) => {
    setSelecting(sondage.id)
    try {
      const d = await post(`/projets/${projetId}/sondages/${sondage.id}/selectionner`, {})
      setSondages((prev) => prev.map((s) =>
        s.id === sondage.id ? { ...d.sondage, elements: d.elements } : s
      ))
      toast.success(`${d.elements.length} élément(s) sélectionné(s) aléatoirement.`)
    } catch (e: any) { toast.error(e.message) }
    finally { setSelecting(null) }
  }

  const handleToggleAnomalie = async (sondage: Sondage, elt: SondageElement) => {
    const est = !elt.est_anomalie
    try {
      const d = await patch(
        `/projets/${projetId}/sondages/${sondage.id}/elements/${elt.id}`,
        { est_anomalie: est, montant_anomalie: est ? Math.abs(elt.montant) : 0 }
      )
      setSondages((prev) => prev.map((s) => {
        if (s.id !== sondage.id) return s
        return {
          ...d.sondage,
          elements: (s.elements || []).map((e) => e.id === elt.id ? d.element : e),
        }
      }))
    } catch (e: any) { toast.error(e.message) }
  }

  const handleConclure = async (sondage: Sondage) => {
    setConcluding(sondage.id)
    try {
      const d = await post(`/projets/${projetId}/sondages/${sondage.id}/conclure`, {})
      setSondages((prev) => prev.map((s) =>
        s.id === sondage.id ? { ...d.sondage, elements: s.elements } : s
      ))
      toast.success('Conclusion IA générée.')
    } catch (e: any) { toast.error(e.message) }
    finally { setConcluding(null) }
  }

  const handleSupprimer = async (sondage: Sondage) => {
    if (!confirm(`Supprimer le sondage « ${sondage.libelle} » ?`)) return
    await del(`/projets/${projetId}/sondages/${sondage.id}`)
    setSondages((prev) => prev.filter((s) => s.id !== sondage.id))
    toast.success('Sondage supprimé.')
  }

  return (
    <div className="p-6 max-w-4xl mx-auto w-full space-y-4">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-800 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary-500" />
            Sondages sur pièces — {normeLabel('530')}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Sélection statistique + projection d'erreur ({sondages.length} sondage{sondages.length !== 1 ? 's' : ''})
          </p>
        </div>
        {canAct && (
          <button onClick={() => setShowCreate(!showCreate)} className="btn-secondary text-sm">
            <Plus className="w-4 h-4" />
            Nouveau sondage
          </button>
        )}
      </div>

      {/* Formulaire création */}
      <AnimatePresence>
        {showCreate && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="card border-primary-100 bg-primary-50/30 p-4 space-y-3">
            <p className="text-sm font-semibold text-slate-700">Nouveau sondage sur pièces</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-600 mb-1 block">Cycle</label>
                <select className="input text-sm w-full"
                  value={createForm.cycle}
                  onChange={(e) => setCreateForm({ ...createForm, cycle: e.target.value })}>
                  {cycles.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-600 mb-1 block">Libellé du sondage</label>
                <input className="input text-sm w-full" placeholder="ex : Sondage factures achats N"
                  value={createForm.libelle}
                  onChange={(e) => setCreateForm({ ...createForm, libelle: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs text-slate-600 mb-1 block">Taux d'erreur toléré</label>
                <select className="input text-sm w-full"
                  value={createForm.taux_erreur_tolere}
                  onChange={(e) => setCreateForm({ ...createForm, taux_erreur_tolere: parseFloat(e.target.value) })}>
                  <option value={0.02}>2 % — Élevé</option>
                  <option value={0.05}>5 % — Standard</option>
                  <option value={0.10}>10 % — Faible risque</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-600 mb-1 block">Niveau de confiance</label>
                <select className="input text-sm w-full"
                  value={createForm.niveau_confiance}
                  onChange={(e) => setCreateForm({ ...createForm, niveau_confiance: parseInt(e.target.value) })}>
                  <option value={90}>90 %</option>
                  <option value={95}>95 % — Standard</option>
                  <option value={99}>99 % — Élevé</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="btn-ghost text-sm">Annuler</button>
              <button onClick={handleCreer} disabled={creating} className="btn-primary text-sm">
                {creating ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
                Créer
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Liste sondages */}
      {loading ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : sondages.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-3 text-center">
          <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-slate-300" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-600">Aucun sondage créé</p>
            <p className="text-xs text-slate-400 mt-1">
              Créez un sondage pour sélectionner statistiquement des éléments à vérifier.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {sondages.map((sondage) => {
            const isExpanded = expandedId === sondage.id
            const elements = sondage.elements || []
            const nbAno = sondage.nb_anomalies || 0
            const conclusion = sondage.conclusion_ia
              ? (typeof sondage.conclusion_ia === 'string' ? JSON.parse(sondage.conclusion_ia) : sondage.conclusion_ia)
              : null
            const cycleMeta = cycles.find((c) => c.id === sondage.cycle)

            return (
              <motion.div key={sondage.id} layout className="card overflow-hidden">
                {/* Header */}
                <button className="w-full flex items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : sondage.id)}>
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    sondage.statut === 'conclu' ? 'bg-emerald-400' : 'bg-blue-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-slate-800">{sondage.libelle}</span>
                      {cycleMeta && (
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                          {cycleMeta.label}
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        sondage.statut === 'conclu' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                        {sondage.statut === 'conclu' ? 'Conclu' : 'En cours'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                      <span>Population : <span className="font-semibold">{sondage.population}</span></span>
                      <span>Échantillon : <span className="font-semibold">{elements.length || sondage.taille_echantillon}</span></span>
                      {nbAno > 0 && <span className="text-amber-600 font-medium">{nbAno} anomalie{nbAno !== 1 ? 's' : ''}</span>}
                      {sondage.montant_projete != null && (
                        <span>Projeté : <span className="font-semibold">{fmt(sondage.montant_projete)} Fdj</span></span>
                      )}
                    </div>
                  </div>
                  {isExpanded
                    ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  }
                </button>

                {/* Contenu expandé */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }} className="border-t border-border">
                      <div className="p-4 space-y-4">
                        {/* Infos */}
                        <div className="grid grid-cols-4 gap-3">
                          {[
                            { label: 'Population', val: `${sondage.population}` },
                            { label: 'Taille échantillon', val: `${elements.length || sondage.taille_echantillon}` },
                            { label: 'Montant population', val: `${fmt(sondage.montant_population)} Fdj` },
                            { label: 'Taux erreur toléré', val: `${(sondage.taux_erreur_tolere * 100).toFixed(0)} %` },
                          ].map((s) => (
                            <div key={s.label} className="card p-3 text-center">
                              <div className="text-sm font-bold text-slate-800">{s.val}</div>
                              <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
                            </div>
                          ))}
                        </div>

                        {/* Actions */}
                        {canAct && (
                          <div className="flex flex-wrap gap-2">
                            <button onClick={() => handleSelectionner(sondage)} disabled={selecting === sondage.id}
                              className="btn-ghost text-xs">
                              {selecting === sondage.id ? <Spinner size="sm" /> : <RefreshCw className="w-3.5 h-3.5" />}
                              {elements.length > 0 ? 'Renouveler l\'échantillon' : 'Sélectionner l\'échantillon'}
                            </button>
                            {elements.length > 0 && sondage.statut !== 'conclu' && (
                              <button onClick={() => handleConclure(sondage)} disabled={concluding === sondage.id}
                                className="btn-ghost text-xs">
                                {concluding === sondage.id ? <Spinner size="sm" /> : <Wand2 className="w-3.5 h-3.5" />}
                                Conclure (IA)
                              </button>
                            )}
                            <button onClick={() => handleSupprimer(sondage)} className="btn-ghost text-xs text-red-500 hover:text-red-700 ml-auto">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}

                        {/* Tableau éléments */}
                        {elements.length > 0 && (
                          <div className="overflow-x-auto rounded-lg border border-border">
                            <table className="w-full text-xs">
                              <thead className="bg-slate-50">
                                <tr>
                                  <th className="px-3 py-2 text-left font-medium text-slate-600 w-8">Ano.</th>
                                  <th className="px-3 py-2 text-left font-medium text-slate-600">Compte</th>
                                  <th className="px-3 py-2 text-left font-medium text-slate-600">Libellé</th>
                                  <th className="px-3 py-2 text-left font-medium text-slate-600">Pièce</th>
                                  <th className="px-3 py-2 text-right font-medium text-slate-600">Montant</th>
                                  <th className="px-3 py-2 text-right font-medium text-slate-600">Anomalie</th>
                                </tr>
                              </thead>
                              <tbody>
                                {elements.map((elt, i) => (
                                  <tr key={elt.id} className={`border-t border-border ${elt.est_anomalie ? 'bg-red-50' : i % 2 === 0 ? '' : 'bg-slate-50/50'}`}>
                                    <td className="px-3 py-2">
                                      {canAct ? (
                                        <button onClick={() => handleToggleAnomalie(sondage, elt)}
                                          className="text-slate-400 hover:text-red-500 transition-colors">
                                          {elt.est_anomalie
                                            ? <CheckSquare className="w-4 h-4 text-red-500" />
                                            : <Square className="w-4 h-4" />
                                          }
                                        </button>
                                      ) : (
                                        elt.est_anomalie
                                          ? <CheckSquare className="w-4 h-4 text-red-500" />
                                          : <Square className="w-4 h-4 text-slate-300" />
                                      )}
                                    </td>
                                    <td className="px-3 py-2 font-mono text-slate-600">{elt.compte}</td>
                                    <td className="px-3 py-2 text-slate-700 max-w-[180px] truncate">{elt.libelle || '—'}</td>
                                    <td className="px-3 py-2 text-slate-500">{elt.numero_piece || '—'}</td>
                                    <td className="px-3 py-2 text-right font-semibold text-slate-800">{fmt(elt.montant)}</td>
                                    <td className="px-3 py-2 text-right">
                                      {elt.est_anomalie && (
                                        <span className="text-red-600 font-semibold">{fmt(elt.montant_anomalie)}</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                              <tfoot className="bg-slate-50 border-t-2 border-border">
                                <tr>
                                  <td colSpan={4} className="px-3 py-2 text-xs font-medium text-slate-600">
                                    {nbAno} anomalie{nbAno !== 1 ? 's' : ''} sur {elements.length} éléments
                                    {sondage.taux_anomalie != null && ` — taux : ${(sondage.taux_anomalie * 100).toFixed(1)} %`}
                                  </td>
                                  <td className="px-3 py-2 text-right text-xs font-semibold text-slate-600">
                                    {fmt(elements.reduce((a, e) => a + (e.montant || 0), 0))}
                                  </td>
                                  <td className="px-3 py-2 text-right text-xs font-semibold text-red-600">
                                    {fmt(sondage.montant_anomalies)}
                                  </td>
                                </tr>
                              </tfoot>
                            </table>
                          </div>
                        )}

                        {/* Conclusion IA */}
                        {conclusion && (
                          <div className="bg-primary-50 rounded-lg p-4 border border-primary-100 space-y-2 text-xs">
                            <div className="flex items-center gap-2">
                              <Wand2 className="w-3.5 h-3.5 text-primary-600" />
                              <span className="font-semibold text-primary-800">Conclusion IA — {normeLabel('530')}</span>
                              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
                                conclusion.conclusion === 'acceptable' ? 'bg-emerald-100 text-emerald-700' :
                                conclusion.conclusion === 'exige_diligences' ? 'bg-amber-100 text-amber-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {conclusion.conclusion === 'acceptable' ? 'Acceptable'
                                  : conclusion.conclusion === 'exige_diligences' ? 'Diligences requises'
                                  : 'Significatif'}
                              </span>
                            </div>
                            <p className="text-slate-700 leading-relaxed">{conclusion.synthese}</p>
                            {conclusion.diligences?.length > 0 && (
                              <div>
                                <p className="font-medium text-slate-600 mt-2">Diligences :</p>
                                <ul className="list-disc list-inside space-y-1 text-slate-600">
                                  {conclusion.diligences.map((d: string, i: number) => <li key={i}>{d}</li>)}
                                </ul>
                              </div>
                            )}
                            {conclusion.impact_opinion && (
                              <p className="text-slate-600 border-t border-primary-100 pt-2 mt-2">
                                <span className="font-medium">Impact opinion : </span>{conclusion.impact_opinion}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Projection */}
                        {sondage.montant_projete != null && (
                          <div className="grid grid-cols-2 gap-3">
                            <div className="card p-3 border-l-4 border-amber-400 text-center">
                              <div className="text-lg font-bold text-amber-700">{(sondage.nb_anomalies || 0)}</div>
                              <div className="text-xs text-slate-500">Anomalies constatées</div>
                            </div>
                            <div className="card p-3 border-l-4 border-red-400 text-center">
                              <div className="text-lg font-bold text-red-700">{fmt(sondage.montant_projete)} Fdj</div>
                              <div className="text-xs text-slate-500">Montant projeté (population)</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
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
    // Vérifier si des résultats existent déjà dans le store
    if (resultats.length > 0) {
      const ok = window.confirm(
        `Des résultats existent déjà pour cette mission.\nRelancer les procédures analytiques remplacera les résultats précédents et les exceptions non tranchées (les décisions déjà signées sont conservées).\n\nContinuer quand même ?`
      )
      if (!ok) return
    }
    setLaunchingAll(true)
    try {
      let totalControles = 0
      let totalExceptions = 0
      for (const c of cyclesMission) {
        const result = await post(`/projets/${projetId}/controles/${c.id.replace(/_/g, '-')}`, {})
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

  const canRun = ['travaux_substantifs', 'controles', 'extraction', 'revue'].includes(etatCourant)
  const canPasser = resultats.length > 0 && ['travaux_substantifs', 'controles'].includes(etatCourant)
  const nbCycles = cyclesMission.length

  // Sous-onglet principal : analytiques vs contrôles de détail
  const [sousOnglet, setSousOnglet] = useState<'analytiques' | 'detail'>('analytiques')
  // Sous-onglet dans "Contrôles de détail" : circularisation vs sondages
  const [detailOnglet, setDetailOnglet] = useState<'circularisation' | 'sondages'>('circularisation')

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Travaux substantifs"
        subtitle={`${nbCycles} cycle${nbCycles !== 1 ? 's' : ''} · Procédures analytiques & contrôles de détail`}
        actions={
          <div className="flex gap-2">
            {canRun && sousOnglet === 'analytiques' && (
              <button onClick={handleLancerTous} disabled={launchingAll} className="btn-secondary">
                {launchingAll ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
                Lancer les procédures analytiques
              </button>
            )}
            {canPasser && (
              <button onClick={handlePasserRevue} disabled={transitioning} className="btn-primary">
                {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                Passer à la revue
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        {/* Sous-onglets familles de travaux */}
        <div className="border-b border-border bg-white sticky top-0 z-20">
          <div className="flex px-6 pt-1">
            <button
              onClick={() => setSousOnglet('analytiques')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                sousOnglet === 'analytiques'
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Play className="w-3.5 h-3.5" />
              Procédures analytiques
            </button>
            <button
              onClick={() => setSousOnglet('detail')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                sousOnglet === 'detail'
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Contrôles de détail
            </button>
          </div>
        </div>

        {sousOnglet === 'analytiques' ? (
          <>
            {/* Onglets cycles */}
            <div className="border-b border-border bg-white sticky top-[41px] z-10">
              <div className="flex">
                {cyclesMission.map((c) => {
                  const Icon = c.icon
                  return (
                    <button
                      key={c.id}
                      onClick={() => setActiveCycle(c.id)}
                      className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
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

            {/* Contenu cycle actif */}
            <div className="p-6 max-w-3xl mx-auto">
              {projetId && cyclesMission.map((c) => (
                <div key={c.id} className={activeCycle === c.id ? '' : 'hidden'}>
                  <CyclePanel
                    cycle={c}
                    projetId={projetId}
                    etatCourant={etatCourant}
                    externallyLaunching={launchingAll}
                  />
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="flex flex-col">
            {/* Sous-onglets Circularisation / Sondages */}
            <div className="border-b border-border bg-white sticky top-[41px] z-10">
              <div className="flex px-6">
                <button onClick={() => setDetailOnglet('circularisation')}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    detailOnglet === 'circularisation'
                      ? 'border-primary-600 text-primary-700'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}>
                  <Mail className="w-3.5 h-3.5" />
                  Circularisation
                  <span className="text-xs text-slate-400">{normeLabel('505')}</span>
                </button>
                <button onClick={() => setDetailOnglet('sondages')}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    detailOnglet === 'sondages'
                      ? 'border-primary-600 text-primary-700'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}>
                  <BarChart3 className="w-3.5 h-3.5" />
                  Sondages sur pièces
                  <span className="text-xs text-slate-400">{normeLabel('530')}</span>
                </button>
              </div>
            </div>

            {detailOnglet === 'circularisation' && projetId && (
              <CircularisationPanel
                projetId={projetId}
                cycles={cyclesMission}
                etatCourant={etatCourant}
              />
            )}
            {detailOnglet === 'sondages' && projetId && (
              <SondagesPanel
                projetId={projetId}
                cycles={cyclesMission}
                etatCourant={etatCourant}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
