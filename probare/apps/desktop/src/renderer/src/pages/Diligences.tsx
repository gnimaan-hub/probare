import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldAlert, Users, CalendarClock, HeartPulse, FileSignature, Landmark,
  Handshake, CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronRight,
  Sparkles, Loader2, Info, PenLine, Mail, Copy, Wand2,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatMontant, formatDate } from '../lib/utils'

// ─── Types (miroir de GET /peripherie) ───────────────────────────────────────

interface QuestionDiligence {
  id: string
  question: string
  risque_si_non: string
  reponse?: 'oui' | 'non' | 'na' | null
  commentaire?: string
}

interface IndicateursContinuite {
  capitaux_propres: number
  capital_social: number
  resultat_exercice: number
  fonds_roulement: number
  tresorerie_nette: number
  alertes: string[]
  nb_alertes: number
}

interface EvaluationDiligence {
  score?: number
  niveau?: string
  synthese_ia?: string
  points_attention?: string[]
  diligences_complementaires?: string[]
  conclusion_proposee?: string
  indicateurs_json?: IndicateursContinuite | null
  conclusion?: string
  conclu_par?: string
  conclu_le?: string
  lettre_ia?: string
  lettre_generee_le?: string
  evalue_le?: string
}

interface Diligence {
  code: string
  libelle: string
  nep_ref: string
  ordre: number
  phase: string
  description: string
  conclusion_requise: boolean
  lettre: 'affirmation' | 'gouvernance' | null
  questions: QuestionDiligence[]
  nb_repondues: number
  nb_total: number
  score_info?: { score: number; niveau: string; nb_oui: number; nb_non: number; nb_na: number; label: string }
  evaluation?: EvaluationDiligence | null
  statut: 'non_commencee' | 'en_cours' | 'evaluee' | 'conclue'
}

// ─── Constantes d'affichage ───────────────────────────────────────────────────

const DILIGENCE_ICONS: Record<string, any> = {
  acceptation: Handshake,
  fraude: ShieldAlert,
  parties_liees: Users,
  evenements_posterieurs: CalendarClock,
  continuite: HeartPulse,
  declarations_ecrites: FileSignature,
  gouvernance: Landmark,
}

const PHASES: Record<string, string> = {
  cadrage: 'Dès le cadrage',
  planification: 'Planification',
  travaux: 'Travaux substantifs',
  revue: 'Revue',
  generation: 'Avant le rapport',
}

const STATUTS: Record<string, { label: string; cls: string }> = {
  non_commencee: { label: 'Non commencée', cls: 'bg-slate-100 text-slate-500' },
  en_cours:      { label: 'En cours',      cls: 'bg-blue-100 text-blue-700' },
  evaluee:       { label: 'Évaluée — à conclure', cls: 'bg-amber-100 text-amber-700' },
  conclue:       { label: 'Conclue ✓',     cls: 'bg-emerald-100 text-emerald-700' },
}

const NIVEAUX: Record<string, { label: string; cls: string; icon: any }> = {
  favorable:   { label: 'Favorable',          cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: CheckCircle },
  attention:   { label: 'Point d\'attention', cls: 'bg-amber-50 text-amber-700 border-amber-200',       icon: AlertTriangle },
  defavorable: { label: 'Défavorable',        cls: 'bg-red-50 text-red-700 border-red-200',             icon: XCircle },
}

// ─── Ligne de question (même patron que le QCI) ───────────────────────────────

function QuestionRow({
  question, onChange, disabled,
}: {
  question: QuestionDiligence
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
          {question.reponse === 'non' && question.risque_si_non && (
            <p className="text-xs text-red-600 mt-1">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              {question.risque_si_non}
            </p>
          )}
        </div>
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
              onClick={() => setShowComment((v) => !v)}
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
              placeholder="Commentaire de l'auditeur (constat, entretien mené, renvoi à pièce…)"
              rows={2}
              className="w-full text-xs rounded-lg border border-slate-200 p-2 resize-none focus:outline-none focus:ring-1 focus:ring-primary-400 text-slate-700 placeholder:text-slate-300"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Indicateurs de continuité (ISA 570) — calculés par le moteur ─────────────

function IndicateursBlock({ ind }: { ind: IndicateursContinuite }) {
  const items = [
    { label: 'Capitaux propres',   val: ind.capitaux_propres },
    { label: 'Capital social',     val: ind.capital_social },
    { label: 'Résultat exercice',  val: ind.resultat_exercice },
    { label: 'Fonds de roulement', val: ind.fonds_roulement },
    { label: 'Trésorerie nette',   val: ind.tresorerie_nette },
  ]
  return (
    <div className="bg-slate-50 border border-border rounded-xl p-4 space-y-3">
      <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
        Indicateurs financiers calculés depuis la balance
      </p>
      <div className="grid grid-cols-5 gap-2">
        {items.map((it) => (
          <div key={it.label} className="text-center">
            <p className="text-[10px] text-slate-400 leading-tight">{it.label}</p>
            <p className={`text-sm font-bold ${it.val < 0 ? 'text-red-600' : 'text-slate-800'}`}>
              {formatMontant(it.val, '')}
            </p>
          </div>
        ))}
      </div>
      {ind.alertes?.length > 0 && (
        <div className="space-y-1 pt-1 border-t border-slate-200">
          {ind.alertes.map((a, i) => (
            <p key={i} className="text-xs text-red-700 flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              {a}
            </p>
          ))}
        </div>
      )}
      {ind.alertes?.length === 0 && (
        <p className="text-xs text-emerald-700 flex items-center gap-1.5 pt-1 border-t border-slate-200">
          <CheckCircle className="w-3.5 h-3.5" />
          Aucune alerte levée par le moteur sur ces indicateurs.
        </p>
      )}
    </div>
  )
}

// ─── Bloc lettre (ISA 580 / 260-265) ──────────────────────────────────────────

function LettreBlock({
  diligence, projetId, onUpdated,
}: {
  diligence: Diligence
  projetId: string
  onUpdated: () => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [generating, setGenerating] = useState(false)

  let lettre: { objet?: string; corps?: string } | null = null
  if (diligence.evaluation?.lettre_ia) {
    try { lettre = JSON.parse(diligence.evaluation.lettre_ia) } catch { /* brut */ }
    if (!lettre) lettre = { corps: diligence.evaluation.lettre_ia }
  }

  const label = diligence.lettre === 'affirmation'
    ? 'lettre d\'affirmation de la direction'
    : 'lettre de communication à la gouvernance'

  const handleGenerer = async () => {
    setGenerating(true)
    try {
      await post(`/projets/${projetId}/peripherie/${diligence.code}/generer-lettre`)
      toast.success('Projet de lettre généré — relisez-le avant tout envoi.')
      onUpdated()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopier = () => {
    const txt = lettre ? `${lettre.objet ? `Objet : ${lettre.objet}\n\n` : ''}${lettre.corps || ''}` : ''
    navigator.clipboard.writeText(txt)
      .then(() => toast.success('Lettre copiée dans le presse-papiers.'))
      .catch(() => toast.error('Copie impossible.'))
  }

  return (
    <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold text-indigo-700 flex items-center gap-1.5">
          <Mail className="w-3.5 h-3.5" />
          Projet de {label}
        </p>
        <div className="flex items-center gap-2">
          {lettre && (
            <button onClick={handleCopier} className="btn-secondary text-xs py-1 px-2">
              <Copy className="w-3 h-3" />
              Copier
            </button>
          )}
          <button onClick={handleGenerer} disabled={generating} className="btn-secondary text-xs py-1 px-2">
            {generating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
            {lettre ? 'Régénérer' : 'Générer par IA'}
          </button>
        </div>
      </div>
      {lettre ? (
        <div className="bg-white border border-indigo-100 rounded-lg p-4 max-h-80 overflow-y-auto">
          {lettre.objet && (
            <p className="text-sm font-semibold text-slate-800 mb-2">Objet : {lettre.objet}</p>
          )}
          <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{lettre.corps}</p>
          {diligence.evaluation?.lettre_generee_le && (
            <p className="text-[10px] text-slate-400 mt-3">
              Générée le {formatDate(diligence.evaluation.lettre_generee_le)} — projet à relire et
              adapter par l'auditeur avant envoi. Générer n'est pas envoyer.
            </p>
          )}
        </div>
      ) : (
        <p className="text-xs text-indigo-600/80">
          L'IA rédige un projet de lettre à partir du contenu réel du dossier (anomalies tranchées,
          faiblesses du contrôle interne, seuil). Chaque montant cité provient du moteur de calcul.
        </p>
      )}
    </div>
  )
}

// ─── Bloc conclusion signée ───────────────────────────────────────────────────

function ConclusionBlock({
  diligence, projetId, onUpdated,
}: {
  diligence: Diligence
  projetId: string
  onUpdated: () => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const ev = diligence.evaluation
  const [conclusion, setConclusion] = useState(ev?.conclusion || ev?.conclusion_proposee || '')
  const [signataire, setSignataire] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setConclusion(ev?.conclusion || ev?.conclusion_proposee || '')
  }, [ev?.conclusion, ev?.conclusion_proposee])

  if (!ev?.evalue_le) return null

  if (ev.conclusion) {
    return (
      <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
        <p className="text-xs font-semibold text-emerald-700 mb-1.5 flex items-center gap-1.5">
          <CheckCircle className="w-3.5 h-3.5" />
          Conclusion signée
        </p>
        <p className="text-sm text-emerald-900 leading-relaxed">{ev.conclusion}</p>
        <p className="text-xs text-emerald-600 mt-2">
          Par {ev.conclu_par} · {formatDate(ev.conclu_le)}
        </p>
      </div>
    )
  }

  const handleSigner = async () => {
    setSaving(true)
    try {
      await post(`/projets/${projetId}/peripherie/${diligence.code}/conclure`, {
        conclusion, conclu_par: signataire,
      })
      toast.success('Conclusion signée et versée au dossier.')
      onUpdated()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white border border-border rounded-xl p-4 space-y-3">
      <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
        <PenLine className="w-3.5 h-3.5" />
        Conclusion de l'auditeur
        {diligence.conclusion_requise && (
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-700">
            Requise avant génération
          </span>
        )}
      </p>
      {ev.conclusion_proposee && (
        <p className="text-xs text-indigo-600 flex items-start gap-1">
          <Wand2 className="w-3 h-3 flex-shrink-0 mt-0.5" />
          Projet rédigé par l'IA au conditionnel — réalisez les diligences puis validez ou modifiez.
        </p>
      )}
      <textarea
        className="input-field min-h-24 resize-none text-sm"
        value={conclusion}
        onChange={(e) => setConclusion(e.target.value)}
        placeholder="Conclusion motivée de l'auditeur (20 caractères minimum)…"
      />
      <div className="flex items-center gap-2">
        <input
          className="input-field flex-1"
          placeholder="Prénom Nom du signataire"
          value={signataire}
          onChange={(e) => setSignataire(e.target.value)}
        />
        <button
          onClick={handleSigner}
          disabled={saving || conclusion.trim().length < 20 || signataire.trim().length < 2}
          className="btn-primary"
        >
          {saving ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
          Signer la conclusion
        </button>
      </div>
    </div>
  )
}

// ─── Carte diligence (accordéon) ──────────────────────────────────────────────

function DiligenceCard({
  d, projetId, expanded, onToggle, onReponse, onEvaluer, evaluating, onUpdated,
}: {
  d: Diligence
  projetId: string
  expanded: boolean
  onToggle: () => void
  onReponse: (code: string, id: string, reponse: 'oui' | 'non' | 'na', commentaire: string) => void
  onEvaluer: (code: string) => Promise<void>
  evaluating: string | null
  onUpdated: () => void
}) {
  const Icon = DILIGENCE_ICONS[d.code] || ShieldAlert
  const statut = STATUTS[d.statut] || STATUTS.non_commencee
  const niveau = d.evaluation?.niveau || d.score_info?.niveau
  const nivCfg = niveau ? NIVEAUX[niveau] : null
  const progression = d.nb_total > 0 ? (d.nb_repondues / d.nb_total) * 100 : 0

  return (
    <div className={`card overflow-hidden border-l-4 ${
      d.statut === 'conclue' ? 'border-l-emerald-400'
        : niveau === 'defavorable' ? 'border-l-red-400'
        : niveau === 'attention' ? 'border-l-amber-400'
        : 'border-l-slate-200'
    }`}>
      <button onClick={onToggle} className="w-full p-4 flex items-center gap-3 text-left hover:bg-slate-50/50 transition-colors">
        <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-slate-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-slate-900 text-sm">{d.libelle}</p>
            <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{d.nep_ref}</code>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${statut.cls}`}>{statut.label}</span>
            {d.conclusion_requise && d.statut !== 'conclue' && (
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                Bloque la génération
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {PHASES[d.phase] || d.phase} · {d.nb_repondues}/{d.nb_total} questions répondues
          </p>
        </div>
        {nivCfg && (
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${nivCfg.cls}`}>
            <nivCfg.icon className="w-3 h-3" />
            {nivCfg.label}
          </span>
        )}
        {expanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
      </button>

      <div className="px-4 pb-1">
        <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${progression === 100 ? 'bg-emerald-500' : 'bg-primary-400'}`}
            style={{ width: `${progression}%` }}
          />
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 pt-3 space-y-4">
              <p className="text-xs text-slate-500 leading-relaxed">{d.description}</p>

              {/* Questionnaire */}
              <div className="space-y-2">
                {d.questions.map((q) => (
                  <QuestionRow
                    key={q.id}
                    question={q}
                    onChange={(id, rep, c) => onReponse(d.code, id, rep, c)}
                    disabled={false}
                  />
                ))}
              </div>

              {/* Évaluer */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onEvaluer(d.code)}
                  disabled={evaluating === d.code || d.nb_repondues < 3}
                  className="btn-secondary text-xs py-1.5"
                  title={d.nb_repondues < 3 ? 'Répondez à au moins 3 questions' : ''}
                >
                  {evaluating === d.code
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Analyse…</>
                    : <><Sparkles className="w-3.5 h-3.5" />{d.evaluation?.evalue_le ? 'Réévaluer' : 'Évaluer'}</>
                  }
                </button>
                {d.nb_repondues < 3 && (
                  <span className="text-xs text-slate-400 italic">
                    Répondez à au moins 3 questions pour évaluer.
                  </span>
                )}
                {d.code === 'fraude' && (
                  <span className="text-xs text-slate-400">
                    Les risques de fraude identifiés alimenteront la cartographie des risques
                    (à valider en Planification).
                  </span>
                )}
              </div>

              {/* Résultat d'évaluation */}
              {d.evaluation?.evalue_le && (
                <div className="space-y-3">
                  {d.evaluation.synthese_ia && (
                    <div className="bg-violet-50 border border-violet-100 rounded-xl p-4 flex items-start gap-2">
                      <Sparkles className="w-4 h-4 text-violet-500 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-violet-900 leading-relaxed">{d.evaluation.synthese_ia}</p>
                    </div>
                  )}
                  {d.evaluation.indicateurs_json && (
                    <IndicateursBlock ind={d.evaluation.indicateurs_json} />
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    {(d.evaluation.points_attention?.length || 0) > 0 && (
                      <div className="bg-amber-50 border border-amber-100 rounded-xl p-3">
                        <p className="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Points d'attention
                        </p>
                        <ul className="space-y-1">
                          {d.evaluation.points_attention!.map((p, i) => (
                            <li key={i} className="text-xs text-amber-800 leading-relaxed flex gap-1.5">
                              <span className="flex-shrink-0 mt-0.5">·</span>{p}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {(d.evaluation.diligences_complementaires?.length || 0) > 0 && (
                      <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
                        <p className="text-xs font-semibold text-blue-700 mb-2 flex items-center gap-1.5">
                          <Info className="w-3.5 h-3.5" />
                          Diligences à mener avant de conclure
                        </p>
                        <ul className="space-y-1">
                          {d.evaluation.diligences_complementaires!.map((p, i) => (
                            <li key={i} className="text-xs text-blue-800 leading-relaxed flex gap-1.5">
                              <span className="flex-shrink-0 font-bold mt-0.5">{i + 1}.</span>{p}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Lettre (580 / 260-265) */}
              {d.lettre && (
                <LettreBlock diligence={d} projetId={projetId} onUpdated={onUpdated} />
              )}

              {/* Conclusion signée */}
              <ConclusionBlock diligence={d} projetId={projetId} onUpdated={onUpdated} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function Diligences() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get, post } = useApi()
  const toast = useToast()
  const { projetActif } = useProjetStore()
  useSyncProjet()

  const [diligences, setDiligences] = useState<Diligence[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [evaluating, setEvaluating] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!projetId) return
    try {
      const res = await get(`/projets/${projetId}/peripherie`)
      setDiligences(res.diligences || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetId])

  useEffect(() => { load() }, [load])

  // Sauvegarde groupée des réponses (même patron anti-télescopage que le QCI)
  const pendingRef = useRef(new Map<string, Map<string, { reponse: string; commentaire: string }>>())
  const timersRef = useRef(new Map<string, ReturnType<typeof setTimeout>>())

  const flush = useCallback(async (code: string) => {
    if (!projetId) return
    const pending = pendingRef.current.get(code)
    if (!pending || pending.size === 0) return
    const reponses = Array.from(pending.entries()).map(([question_id, v]) => ({
      question_id, reponse: v.reponse, commentaire: v.commentaire,
    }))
    pendingRef.current.set(code, new Map())
    try {
      await post(`/projets/${projetId}/peripherie/${code}/reponses`, { reponses })
    } catch (e: any) {
      const again = pendingRef.current.get(code) ?? new Map()
      reponses.forEach((r) => {
        if (!again.has(r.question_id)) again.set(r.question_id, { reponse: r.reponse, commentaire: r.commentaire })
      })
      pendingRef.current.set(code, again)
      toast.error(`Sauvegarde échouée : ${e.message}`)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetId])

  const handleReponse = (code: string, id: string, reponse: 'oui' | 'non' | 'na', commentaire: string) => {
    // Mise à jour optimiste de l'état local
    setDiligences((ds) => ds.map((d) => {
      if (d.code !== code) return d
      const questions = d.questions.map((q) => q.id === id ? { ...q, reponse, commentaire } : q)
      return { ...d, questions, nb_repondues: questions.filter((q) => q.reponse).length }
    }))
    const pending = pendingRef.current.get(code) ?? new Map()
    pending.set(id, { reponse, commentaire })
    pendingRef.current.set(code, pending)
    const t = timersRef.current.get(code)
    if (t) clearTimeout(t)
    timersRef.current.set(code, setTimeout(() => flush(code), 800))
  }

  const handleEvaluer = async (code: string) => {
    if (!projetId) return
    const t = timersRef.current.get(code)
    if (t) clearTimeout(t)
    await flush(code)
    setEvaluating(code)
    try {
      const res = await post(`/projets/${projetId}/peripherie/${code}/evaluer`)
      if (res.risques_fraude_crees > 0) {
        toast.success(`${res.risques_fraude_crees} risque(s) de fraude proposé(s) — validez-les dans la cartographie des risques (Planification).`)
      } else {
        toast.success('Diligence évaluée.')
      }
      await load()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setEvaluating(null)
    }
  }

  const nbConclues = diligences.filter((d) => d.statut === 'conclue').length
  const continuite = diligences.find((d) => d.code === 'continuite')

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Diligences de périphérie de mission"
        subtitle={`Acceptation, fraude, parties liées, continuité… · ${nbConclues}/${diligences.length || 7} conclue${nbConclues !== 1 ? 's' : ''}`}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-blue-800">
              Ces diligences couvrent la <strong>périphérie de la mission</strong> : acceptation,
              fraude, parties liées, événements postérieurs, continuité d'exploitation,
              déclarations écrites et communication à la gouvernance. Pour chacune : répondez au
              questionnaire, l'IA synthétise et propose un projet de conclusion, vous signez.
              L'état de chaque diligence est versé au dossier de travail.
            </p>
          </div>

          {continuite && continuite.statut !== 'conclue' && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200">
              <HeartPulse className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">
                La conclusion signée sur la <strong>continuité d'exploitation</strong> ({continuite.nep_ref})
                est obligatoire avant le passage en génération du dossier.
              </p>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : (
            diligences.map((d) => (
              <DiligenceCard
                key={d.code}
                d={d}
                projetId={projetId!}
                expanded={expanded === d.code}
                onToggle={() => setExpanded(expanded === d.code ? null : d.code)}
                onReponse={handleReponse}
                onEvaluer={handleEvaluer}
                evaluating={evaluating}
                onUpdated={load}
              />
            ))
          )}

          {projetActif?.consentement_client === false && (
            <p className="text-xs text-slate-400 text-center">
              Sans consentement client, les synthèses et lettres IA sont indisponibles —
              scores et questionnaires restent fonctionnels (mode dégradé).
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
