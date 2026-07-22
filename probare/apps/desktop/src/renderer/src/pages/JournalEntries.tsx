import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ScanSearch, Play, AlertTriangle, CheckCircle, XCircle, Loader2, Info,
  ArrowRight, ChevronDown, ChevronRight, FileWarning,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatMontant, formatDate, normeLabel } from '../lib/utils'

// ─── Types (miroir de /journal-entries) ───────────────────────────────────────

interface JetEcriture {
  id: string
  numero_piece: string
  date_piece: string
  libelle: string
  montant: number
  comptes: string[]
  nb_lignes: number
  signaux: string[]
  score: number
  est_anomalie: number
  commentaire?: string | null
}

interface JetData {
  ecritures: JetEcriture[]
  nb_signalees: number
  nb_pointees: number
  nb_anomalies: number
  signaux_libelles: Record<string, string>
}

// Poids indicatifs (miroir du backend) pour colorer les signaux forts.
const SIGNAUX_FORTS = new Set(['desequilibre', 'sous_seuil', 'contrepartie', 'weekend', 'cutoff_tardif'])

const SIGNAL_SHORT: Record<string, string> = {
  desequilibre: 'Déséquilibrée',
  sous_seuil: 'Sous le seuil',
  contrepartie: 'Contrepartie inhabituelle',
  weekend: 'Week-end',
  cutoff_tardif: 'Clôture tardive',
  sans_piece: 'Sans pièce',
  libelle_suspect: 'Libellé générique',
  montant_rond: 'Montant rond',
}

function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 5 ? 'bg-red-100 text-red-700'
    : score >= 3 ? 'bg-amber-100 text-amber-700'
    : 'bg-slate-100 text-slate-600'
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cls}`} title="Score de risque">
      {score}
    </span>
  )
}

// ─── Carte écriture signalée ──────────────────────────────────────────────────

function EcritureCard({
  e, libelles, projetId, onPointed,
}: {
  e: JetEcriture
  libelles: Record<string, string>
  projetId: string
  onPointed: () => void
}) {
  const { patch } = useApi()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [comment, setComment] = useState(e.commentaire || '')
  const [saving, setSaving] = useState(false)
  const pointee = !!e.commentaire || e.est_anomalie === 1

  const pointer = async (est_anomalie: boolean) => {
    setSaving(true)
    try {
      await patch(`/projets/${projetId}/journal-entries/${e.id}`, {
        est_anomalie, commentaire: comment || null,
      })
      toast.success(est_anomalie ? 'Écriture pointée comme anomalie.' : 'Écriture pointée conforme.')
      onPointed()
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.div layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className={`card p-4 border-l-4 ${
        e.est_anomalie === 1 ? 'border-l-red-500'
          : pointee ? 'border-l-emerald-400'
          : e.score >= 5 ? 'border-l-red-300'
          : 'border-l-amber-300'
      }`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-start gap-3 text-left">
        <div className="flex-shrink-0 pt-0.5">
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <ScoreBadge score={e.score} />
            <span className="text-sm font-semibold text-slate-800">
              Pièce {e.numero_piece || '(sans numéro)'}
            </span>
            <span className="text-xs text-slate-500">{formatMontant(e.montant)}</span>
            {e.date_piece && <span className="text-xs text-slate-400">{e.date_piece}</span>}
            {e.est_anomalie === 1 && (
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-700">Anomalie</span>
            )}
            {pointee && e.est_anomalie !== 1 && (
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">Conforme</span>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {e.signaux.map((s) => (
              <span key={s} className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                SIGNAUX_FORTS.has(s) ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-500'
              }`} title={libelles[s] || s}>
                {SIGNAL_SHORT[s] || s}
              </span>
            ))}
          </div>
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="pl-7 pt-3 space-y-3">
              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600">
                <p><strong>Comptes mouvementés :</strong> {e.comptes.join(', ') || '—'}</p>
                <p><strong>Libellé :</strong> {e.libelle || <em className="text-slate-400">absent</em>}</p>
                <p><strong>Signaux ({e.signaux.length}) :</strong>{' '}
                  {e.signaux.map((s) => libelles[s] || s).join(' · ')}</p>
              </div>
              <textarea
                className="input-field text-sm min-h-16 resize-none"
                placeholder="Constat de l'auditeur après investigation (justification obtenue, pièce examinée…)"
                value={comment}
                onChange={(ev) => setComment(ev.target.value)}
              />
              <div className="flex items-center gap-2">
                <button onClick={() => pointer(false)} disabled={saving} className="btn-secondary text-xs py-1.5">
                  {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                  Conforme
                </button>
                <button onClick={() => pointer(true)} disabled={saving} className="btn-secondary text-xs py-1.5 text-red-600">
                  <XCircle className="w-3.5 h-3.5" />
                  Anomalie
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function JournalEntries() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post } = useApi()
  const toast = useToast()
  const { projetActif } = useProjetStore()
  useSyncProjet()

  const [data, setData] = useState<JetData | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [derniereAnalyse, setDerniereAnalyse] = useState<any>(null)

  const load = useCallback(async () => {
    if (!projetId) return
    try {
      setData(await get(`/projets/${projetId}/journal-entries`))
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetId])

  useEffect(() => { load() }, [load])

  const handleRun = async () => {
    setRunning(true)
    try {
      const res = await post(`/projets/${projetId}/controles/journal-entries`, {})
      setDerniereAnalyse(res.analyse)
      toast.success(`${res.nb_signalees} écriture(s) signalée(s) sur ${res.analyse.nb_ecritures} analysée(s).`)
      await load()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setRunning(false)
    }
  }

  const locked = ['generation', 'opinion'].includes(projetActif?.etat_courant || '')
  const analyse = derniereAnalyse
  const parSignal = analyse?.par_signal || {}

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Tests des écritures de journal"
        subtitle={`Journal Entry Testing — détection du contournement des contrôles (${normeLabel('240')})`}
        actions={
          !locked && (
            <button onClick={handleRun} disabled={running} className="btn-primary">
              {running ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
              {data && data.nb_signalees > 0 ? 'Relancer l\'analyse' : 'Lancer l\'analyse'}
            </button>
          )
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-blue-800">
              Le test des écritures de journal ({normeLabel('240')}) parcourt <strong>l'intégralité du grand
              livre</strong> et attribue à chaque écriture un <strong>score de risque</strong> calculé par le
              moteur (déséquilibre, montant juste sous le seuil, contrepartie inhabituelle, week-end, clôture
              tardive, libellé générique…). Les écritures les plus risquées sont retenues pour revue ciblée :
              investiguez-les puis pointez-les conformes ou en anomalie.
            </p>
          </div>

          {/* Synthèse de la dernière analyse */}
          {analyse && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center gap-4 flex-wrap">
                <div>
                  <p className="text-xs text-slate-400">Écritures analysées</p>
                  <p className="text-xl font-bold text-slate-800">{analyse.nb_ecritures}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400">Retenues pour revue</p>
                  <p className={`text-xl font-bold ${analyse.nb_signalees > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                    {analyse.nb_signalees}
                  </p>
                </div>
                <div className="text-xs text-slate-400">
                  Seuil de signalement : score ≥ {analyse.seuil_signalement}
                </div>
              </div>
              {Object.keys(parSignal).length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border">
                  {Object.entries(parSignal).map(([s, n]) => (
                    <span key={s} className={`text-xs px-2 py-0.5 rounded-full ${
                      SIGNAUX_FORTS.has(s) ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {SIGNAL_SHORT[s] || s} : <strong>{n as number}</strong>
                    </span>
                  ))}
                </div>
              )}
              {analyse.sans_piece_desactive && (
                <p className="text-xs text-slate-400 flex items-center gap-1">
                  <FileWarning className="w-3.5 h-3.5" />
                  Le grand livre ne porte pas de numéros de pièce : le signal « sans pièce » a été neutralisé.
                </p>
              )}
            </div>
          )}

          {/* Barre de progression du pointage */}
          {data && data.nb_signalees > 0 && (
            <div className="flex items-center justify-between text-sm text-slate-600">
              <span>
                {data.nb_pointees}/{data.nb_signalees} écriture(s) revue(s)
                {data.nb_anomalies > 0 && <span className="text-red-600"> · {data.nb_anomalies} anomalie(s)</span>}
              </span>
              <button onClick={() => navigate(`/projet/${projetId}/exceptions`)}
                className="text-primary-600 hover:text-primary-800 flex items-center gap-1 text-xs">
                Voir les exceptions générées <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Liste des écritures signalées */}
          {loading ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : !data || data.nb_signalees === 0 ? (
            <EmptyState
              icon={ScanSearch}
              title={data && data.ecritures.length === 0 && analyse ? 'Aucune écriture à risque' : 'Analyse non lancée'}
              description={data && analyse
                ? 'Aucune écriture n\'a atteint le seuil de signalement — le grand livre ne présente pas de signaux de risque marqués.'
                : 'Lancez l\'analyse pour parcourir le grand livre et détecter les écritures à risque.'}
            />
          ) : (
            <AnimatePresence>
              {data.ecritures.map((e) => (
                <EcritureCard key={e.id} e={e} libelles={data.signaux_libelles}
                  projetId={projetId!} onPointed={load} />
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  )
}
