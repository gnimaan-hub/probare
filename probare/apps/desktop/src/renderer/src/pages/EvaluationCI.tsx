import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheck, ArrowRight, CheckCircle, XCircle, MinusCircle,
  Sparkles, AlertTriangle, ChevronDown, ChevronRight, Info,
  Shield, ShoppingCart, TrendingUp, Loader2,
  Landmark, Package, Users, Receipt, PieChart
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Question {
  id: string
  question: string
  assertion: string
  risque_si_non: string
  reponse?: 'oui' | 'non' | 'na' | null
  commentaire?: string
}

interface CycleQCI {
  cycle: string
  questions: Question[]
  nb_repondues: number
  nb_total: number
  score_info?: {
    score: number
    niveau: 'faible' | 'moyen' | 'eleve'
    nb_oui: number
    nb_non: number
    nb_na: number
    label: string
    couleur: string
  }
  evaluation?: {
    synthese: string
    forces: string[]
    faiblesses: string[]
    recommandations: string[]
    niveau_risque: string
    score: number
    evalue_le: string
  }
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const CYCLE_META: Record<string, { label: string; icon: any; color: string }> = {
  tresorerie:      { label: 'Trésorerie',         icon: Shield,       color: 'blue' },
  achats:          { label: 'Achats-Fournisseurs', icon: ShoppingCart, color: 'orange' },
  ventes:          { label: 'Ventes-Clients',      icon: TrendingUp,   color: 'emerald' },
  immobilisations: { label: 'Immobilisations',     icon: Landmark,     color: 'slate' },
  stocks:          { label: 'Stocks',              icon: Package,      color: 'amber' },
  paie:            { label: 'Paie / Personnel',    icon: Users,        color: 'violet' },
  impots:          { label: 'Impôts & Taxes',      icon: Receipt,      color: 'rose' },
  capitaux_propres:{ label: 'Capitaux propres',    icon: PieChart,     color: 'indigo' },
}

const NIVEAU_CONFIG: Record<string, { bg: string; text: string; border: string; label: string }> = {
  faible: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Faible' },
  moyen:  { bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   label: 'Moyen' },
  eleve:  { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200',     label: 'Élevé' },
}

// ─── Composant question ───────────────────────────────────────────────────────

function QuestionRow({
  question,
  onChange,
  disabled,
}: {
  question: Question
  onChange: (id: string, reponse: 'oui' | 'non' | 'na', commentaire: string) => void
  disabled: boolean
}) {
  const [showComment, setShowComment] = useState(!!question.commentaire)
  const [comment, setComment] = useState(question.commentaire || '')

  const handleReponse = (rep: 'oui' | 'non' | 'na') => {
    if (disabled) return
    onChange(question.id, rep, comment)
    if (rep === 'non') setShowComment(true)
  }

  const handleComment = (val: string) => {
    setComment(val)
    if (question.reponse) onChange(question.id, question.reponse, val)
  }

  return (
    <div className={`rounded-xl border p-4 transition-all ${
      question.reponse === 'non'
        ? 'border-red-200 bg-red-50/30'
        : question.reponse === 'oui'
          ? 'border-emerald-100 bg-emerald-50/20'
          : 'border-border bg-white'
    }`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-800 leading-relaxed">{question.question}</p>
          <p className="text-xs text-slate-400 mt-0.5">
            <span className="font-medium">Assertion :</span> {question.assertion}
          </p>
          {question.reponse === 'non' && question.risque_si_non && (
            <p className="text-xs text-red-600 mt-1">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              {question.risque_si_non}
            </p>
          )}
        </div>

        {/* Boutons réponse */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {(['oui', 'non', 'na'] as const).map((rep) => (
            <button
              key={rep}
              onClick={() => handleReponse(rep)}
              disabled={disabled}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border ${
                question.reponse === rep
                  ? rep === 'oui'
                    ? 'bg-emerald-500 text-white border-emerald-500'
                    : rep === 'non'
                      ? 'bg-red-500 text-white border-red-500'
                      : 'bg-slate-400 text-white border-slate-400'
                  : 'bg-white text-slate-400 border-slate-200 hover:border-slate-300 hover:text-slate-600'
              } ${disabled ? 'cursor-default' : 'cursor-pointer'}`}
            >
              {rep === 'na' ? 'N/A' : rep.toUpperCase()}
            </button>
          ))}
          {question.reponse && (
            <button
              onClick={() => setShowComment(v => !v)}
              className="p-1 text-slate-400 hover:text-slate-600 transition-colors"
              title="Ajouter un commentaire"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <AnimatePresence>
        {(showComment || question.commentaire) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-3"
          >
            <textarea
              value={comment}
              onChange={(e) => handleComment(e.target.value)}
              disabled={disabled}
              placeholder="Commentaire de l'auditeur (constat, justification, renvoi à pièce justificative…)"
              rows={2}
              className="w-full text-xs rounded-lg border border-slate-200 p-2 resize-none focus:outline-none focus:ring-1 focus:ring-primary-400 text-slate-700 placeholder:text-slate-300"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Badge niveau CI ──────────────────────────────────────────────────────────

function NiveauBadge({ niveau }: { niveau: string }) {
  const cfg = NIVEAU_CONFIG[niveau] || NIVEAU_CONFIG.eleve
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      {niveau === 'faible'
        ? <CheckCircle className="w-3.5 h-3.5" />
        : niveau === 'moyen'
          ? <AlertTriangle className="w-3.5 h-3.5" />
          : <XCircle className="w-3.5 h-3.5" />
      }
      Risque {cfg.label}
    </span>
  )
}

// ─── Bloc évaluation IA ───────────────────────────────────────────────────────

function EvaluationBlock({ evaluation }: { evaluation: NonNullable<CycleQCI['evaluation']> }) {
  return (
    <div className="space-y-3">
      {/* Synthèse */}
      <div className="bg-violet-50 border border-violet-100 rounded-xl p-4">
        <div className="flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-violet-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-violet-900 leading-relaxed">{evaluation.synthese}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Forces */}
        {evaluation.forces?.length > 0 && (
          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3">
            <p className="text-xs font-semibold text-emerald-700 mb-2 flex items-center gap-1.5">
              <CheckCircle className="w-3.5 h-3.5" />
              Forces ({evaluation.forces.length})
            </p>
            <ul className="space-y-1">
              {evaluation.forces.map((f, i) => (
                <li key={i} className="text-xs text-emerald-800 leading-relaxed flex gap-1.5">
                  <span className="flex-shrink-0 mt-0.5">·</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Faiblesses */}
        {evaluation.faiblesses?.length > 0 && (
          <div className="bg-red-50 border border-red-100 rounded-xl p-3">
            <p className="text-xs font-semibold text-red-700 mb-2 flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5" />
              Faiblesses ({evaluation.faiblesses.length})
            </p>
            <ul className="space-y-1">
              {evaluation.faiblesses.map((f, i) => (
                <li key={i} className="text-xs text-red-800 leading-relaxed flex gap-1.5">
                  <span className="flex-shrink-0 mt-0.5">·</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recommandations */}
      {evaluation.recommandations?.length > 0 && (
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-3">
          <p className="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Implications pour les travaux substantifs
          </p>
          <ul className="space-y-1">
            {evaluation.recommandations.map((r, i) => (
              <li key={i} className="text-xs text-amber-800 leading-relaxed flex gap-1.5">
                <span className="flex-shrink-0 font-bold mt-0.5">{i + 1}.</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ─── Panel par cycle ──────────────────────────────────────────────────────────

function CyclePanel({
  cycleKey,
  data,
  projetId,
  onReponse,
  onEvaluer,
  evaluating,
  locked,
}: {
  cycleKey: string
  data: CycleQCI
  projetId: string
  onReponse: (cycle: string, id: string, reponse: 'oui' | 'non' | 'na', commentaire: string) => void
  onEvaluer: (cycle: string) => Promise<void>
  evaluating: string | null
  locked: boolean
}) {
  const [showQuestions, setShowQuestions] = useState(true)
  const meta = CYCLE_META[cycleKey] || { label: cycleKey, icon: ShieldCheck, color: 'slate' }
  const Icon = meta.icon
  const progression = data.nb_total > 0 ? (data.nb_repondues / data.nb_total) * 100 : 0
  const niveau = data.evaluation?.niveau_risque || data.score_info?.niveau

  return (
    <div className="space-y-4">
      {/* Header cycle */}
      <div className={`card p-4 border-l-4 ${
        niveau === 'faible' ? 'border-l-emerald-400' :
        niveau === 'moyen'  ? 'border-l-amber-400' :
        niveau === 'eleve'  ? 'border-l-red-400' :
        'border-l-slate-200'
      }`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center">
              <Icon className="w-5 h-5 text-slate-500" />
            </div>
            <div>
              <p className="font-semibold text-slate-900 text-sm">{meta.label}</p>
              <p className="text-xs text-slate-400">
                {data.nb_repondues}/{data.nb_total} questions répondues
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {niveau && <NiveauBadge niveau={niveau} />}
            {!locked && data.nb_repondues >= 3 && (
              <button
                onClick={() => onEvaluer(cycleKey)}
                disabled={evaluating === cycleKey}
                className="btn-secondary text-xs py-1.5"
              >
                {evaluating === cycleKey
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Analyse…</>
                  : <><Sparkles className="w-3.5 h-3.5" />{data.evaluation ? 'Réévaluer' : 'Évaluer par IA'}</>
                }
              </button>
            )}
          </div>
        </div>

        {/* Barre de progression */}
        <div className="mt-3">
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                progression === 100 ? 'bg-emerald-500' : 'bg-primary-400'
              }`}
              style={{ width: `${progression}%` }}
            />
          </div>
        </div>
      </div>

      {/* Évaluation IA */}
      {data.evaluation && (
        <div>
          <button
            onClick={() => setShowQuestions(v => !v)}
            className="flex items-center gap-1.5 text-xs text-slate-500 mb-3 hover:text-slate-700 transition-colors"
          >
            {showQuestions ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            {showQuestions ? 'Masquer le questionnaire' : 'Afficher le questionnaire'}
          </button>
          <EvaluationBlock evaluation={data.evaluation} />
        </div>
      )}

      {/* Questions */}
      <AnimatePresence initial={false}>
        {showQuestions && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-2"
          >
            {data.questions.map((q) => (
              <QuestionRow
                key={q.id}
                question={q}
                onChange={(id, rep, comment) => onReponse(cycleKey, id, rep, comment)}
                disabled={locked}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function EvaluationCI() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()
  useSyncProjet()

  const [qciData, setQciData] = useState<Record<string, CycleQCI>>({})
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState(false)

  // Cycle actif
  const cycles = Object.keys(qciData)
  const [activeCycle, setActiveCycle] = useState<string | null>(null)
  useEffect(() => {
    if (cycles.length > 0 && !activeCycle) setActiveCycle(cycles[0])
  }, [cycles.length])

  const loadQci = useCallback(async () => {
    if (!projetId) return
    try {
      const res = await get(`/projets/${projetId}/qci`)
      setQciData(res.cycles || {})
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }, [projetId])

  useEffect(() => { loadQci() }, [loadQci])

  // ── Gestion réponses (debounce save) ──────────────────────────────────────

  const pendingRef = { current: new Map<string, ReturnType<typeof setTimeout>>() }

  const handleReponse = (cycle: string, questionId: string, reponse: 'oui' | 'non' | 'na', commentaire: string) => {
    // Mise à jour locale immédiate
    setQciData(prev => {
      const cycleData = prev[cycle]
      if (!cycleData) return prev
      return {
        ...prev,
        [cycle]: {
          ...cycleData,
          questions: cycleData.questions.map(q =>
            q.id === questionId ? { ...q, reponse, commentaire } : q
          ),
          nb_repondues: cycleData.questions.filter(q =>
            q.id === questionId ? !!reponse : !!q.reponse
          ).length,
        },
      }
    })

    // Sauvegarde groupée après 600ms d'inactivité
    const key = `${cycle}-${questionId}`
    const existing = pendingRef.current.get(key)
    if (existing) clearTimeout(existing)
    const timer = setTimeout(async () => {
      if (!projetId) return
      setSaving(cycle)
      try {
        await post(`/projets/${projetId}/qci/${cycle}/reponses`, {
          reponses: [{ question_id: questionId, reponse, commentaire }],
        })
      } catch (e: any) {
        toast.error(`Sauvegarde échouée : ${e.message}`)
      } finally {
        setSaving(null)
      }
    }, 600)
    pendingRef.current.set(key, timer)
  }

  // ── Évaluation IA ─────────────────────────────────────────────────────────

  const handleEvaluer = async (cycle: string) => {
    if (!projetId) return
    setEvaluating(cycle)
    try {
      const result = await post(`/projets/${projetId}/qci/${cycle}/evaluer`, {})
      setQciData(prev => ({
        ...prev,
        [cycle]: {
          ...prev[cycle],
          evaluation: { ...result, evalue_le: new Date().toISOString() },
        },
      }))
      toast.success(`Évaluation CI ${cycle} terminée.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setEvaluating(null)
    }
  }

  // ── Transition vers travaux substantifs ───────────────────────────────────

  const anyRepondu = cycles.some(c => (qciData[c]?.nb_repondues ?? 0) > 0)
  const allEvalues = cycles.length > 0 && cycles.every(c => qciData[c]?.evaluation)

  const handlePasserTravaux = async () => {
    if (!projetId) return
    setTransitioning(true)
    try {
      const updated = await post(`/projets/${projetId}/transition`, {
        vers: 'ingestion',
        acteur: 'utilisateur',
      })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/ingestion`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const etatCourant = projetActif?.etat_courant || ''
  // Verrouillé seulement une fois les contrôles lancés (le QCI peut être mis à jour en cours de planification)
  const locked = ['travaux_substantifs', 'controles', 'revue', 'generation', 'opinion'].includes(etatCourant)

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Évaluation du contrôle interne" subtitle={projetActif?.nom} />
        <div className="flex-1 flex items-center justify-center">
          <Spinner />
        </div>
      </div>
    )
  }

  const activeCycleData = activeCycle ? qciData[activeCycle] : null

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Évaluation du contrôle interne"
        subtitle={`NEP 315 · ${cycles.length} cycle${cycles.length !== 1 ? 's' : ''}`}
        actions={
          <div className="flex items-center gap-2">
            {saving && (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Sauvegarde…
              </span>
            )}
            {etatCourant === 'evaluation_ci' && (
              <button
                onClick={handlePasserTravaux}
                disabled={transitioning || !allEvalues}
                title={!allEvalues ? 'Évaluez tous les cycles avant de continuer' : ''}
                className="btn-primary"
              >
                {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                Passer à l'ingestion
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        {/* Bandeau informatif */}
        <div className="bg-blue-50 border-b border-blue-100 px-6 py-3">
          <div className="flex items-start gap-2 max-w-3xl mx-auto">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700 leading-relaxed">
              <strong>NEP 315 — Connaissance de l'entité et de son environnement.</strong>{' '}
              Ce questionnaire évalue le dispositif de contrôle interne par cycle.
              Les résultats alimentent directement le programme de travail : un risque CI élevé
              implique d'étendre les procédures analytiques et de prévoir des contrôles de détail renforcés.
            </p>
          </div>
        </div>

        {/* Onglets cycles */}
        {cycles.length > 1 && (
          <div className="border-b border-border bg-white sticky top-0 z-10">
            <div className="flex">
              {cycles.map(c => {
                const meta = CYCLE_META[c] || { label: c, icon: ShieldCheck }
                const Icon = meta.icon
                const niveau = qciData[c]?.evaluation?.niveau_risque || qciData[c]?.score_info?.niveau
                return (
                  <button
                    key={c}
                    onClick={() => setActiveCycle(c)}
                    className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors ${
                      activeCycle === c
                        ? 'border-primary-600 text-primary-700 bg-primary-50/50'
                        : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {meta.label}
                    {niveau && (
                      <span className={`w-2 h-2 rounded-full ml-0.5 ${
                        niveau === 'faible' ? 'bg-emerald-400' :
                        niveau === 'moyen'  ? 'bg-amber-400' :
                        'bg-red-400'
                      }`} />
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Contenu */}
        <div className="p-6 max-w-3xl mx-auto">
          {cycles.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <ShieldCheck className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucun cycle sélectionné dans le cadrage.</p>
              <p className="text-xs mt-1">Retournez au cadrage pour sélectionner les cycles à auditer.</p>
            </div>
          ) : activeCycle && activeCycleData ? (
            <CyclePanel
              key={activeCycle}
              cycleKey={activeCycle}
              data={activeCycleData}
              projetId={projetId!}
              onReponse={handleReponse}
              onEvaluer={handleEvaluer}
              evaluating={evaluating}
              locked={locked}
            />
          ) : null}

          {/* Récapitulatif si tous évalués */}
          {allEvalues && (
            <div className="mt-6 p-4 bg-slate-50 rounded-xl border border-border">
              <p className="text-xs font-semibold text-slate-600 mb-3">Récapitulatif — Niveaux de risque CI</p>
              <div className="space-y-2">
                {cycles.map(c => {
                  const meta = CYCLE_META[c] || { label: c }
                  const niveau = qciData[c]?.evaluation?.niveau_risque || 'eleve'
                  const cfg = NIVEAU_CONFIG[niveau] || NIVEAU_CONFIG.eleve
                  const score = qciData[c]?.evaluation?.score ?? 0
                  return (
                    <div key={c} className="flex items-center gap-3">
                      <span className="text-xs text-slate-600 w-36 font-medium">{meta.label}</span>
                      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            niveau === 'faible' ? 'bg-emerald-400' :
                            niveau === 'moyen'  ? 'bg-amber-400' :
                            'bg-red-400'
                          }`}
                          style={{ width: `${score * 100}%` }}
                        />
                      </div>
                      <NiveauBadge niveau={niveau} />
                    </div>
                  )
                })}
              </div>
              {!locked && (
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={handlePasserTravaux}
                    disabled={transitioning}
                    className="btn-primary"
                  >
                    {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                    Passer à l'ingestion
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
