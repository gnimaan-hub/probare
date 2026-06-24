import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Activity, RefreshCw, ArrowUpRight, Bot, User, ChevronDown } from 'lucide-react'
import { Header } from '../components/layout/Header'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { formatDate } from '../lib/utils'

const TYPE_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  transition_etat: { label: 'Transition',    color: 'bg-primary-100 text-primary-700 border-primary-200', icon: ArrowUpRight },
  appel_llm:       { label: 'IA',            color: 'bg-violet-100 text-violet-700 border-violet-200',   icon: Bot },
  action_humaine:  { label: 'Auditeur',      color: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: User },
}

function describePayload(type: string, payload: any): string {
  if (!payload) return ''
  try {
    const p = typeof payload === 'string' ? JSON.parse(payload) : payload
    if (type === 'transition_etat') {
      if (p.de && p.vers) return `${p.de} → ${p.vers}`
      if (p.vers) return `Passage à « ${p.vers} »`
    }
    if (type === 'appel_llm') {
      const model = p.modele || p.model || ''
      const action = p.action || p.type || ''
      const tokens = p.tokens_utilises || p.tokens || ''
      const parts = [action, model, tokens ? `${tokens} tokens` : ''].filter(Boolean)
      return parts.join(' · ')
    }
    if (type === 'action_humaine') {
      return p.action || p.description || p.type || ''
    }
    const str = typeof p === 'object' ? JSON.stringify(p) : String(p)
    return str.length > 120 ? str.slice(0, 120) + '…' : str
  } catch {
    const str = String(payload)
    return str.length > 120 ? str.slice(0, 120) + '…' : str
  }
}

function JournalEntry({ entry, index }: { entry: any; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = TYPE_CONFIG[entry.type] || { label: entry.type, color: 'bg-slate-100 text-slate-600 border-slate-200', icon: Activity }
  const Icon = cfg.icon
  const description = describePayload(entry.type, entry.payload)
  const hasDetail = !!entry.payload

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.02, 0.3) }}
      className="flex items-start gap-3 p-3 bg-white border border-border rounded-xl hover:border-border-strong transition-colors"
    >
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${cfg.color}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge border text-[10px] font-semibold ${cfg.color}`}>
            {cfg.label}
          </span>
          {description && (
            <span className="text-xs text-slate-700 font-medium">{description}</span>
          )}
          <span className="text-xs text-slate-400 ml-auto">{formatDate(entry.horodatage)}</span>
        </div>
        {hasDetail && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="mt-1.5 flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
          >
            <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            {expanded ? 'Masquer le détail' : 'Voir le détail technique'}
          </button>
        )}
        {expanded && hasDetail && (
          <pre className="mt-2 text-xs text-slate-500 font-mono overflow-x-auto whitespace-pre-wrap break-words leading-relaxed bg-slate-50 rounded p-2 border border-border">
            {typeof entry.payload === 'object'
              ? JSON.stringify(entry.payload, null, 2)
              : String(entry.payload)}
          </pre>
        )}
      </div>
    </motion.div>
  )
}

export function Journal() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get } = useApi()
  const toast = useToast()
  const { projetActif } = useProjetStore()
  const [journal, setJournal] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    if (!projetId) return
    setLoading(true)
    try {
      const data = await get(`/projets/${projetId}/journal?limit=200`)
      setJournal(data.journal || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [projetId])

  const nbTransitions = journal.filter(e => e.type === 'transition_etat').length
  const nbLlm = journal.filter(e => e.type === 'appel_llm').length
  const nbHumain = journal.filter(e => e.type === 'action_humaine').length

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Journal d'audit"
        subtitle="Piste d'audit complète — NEP 230"
        actions={
          <button onClick={load} disabled={loading} className="btn-ghost">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {journal.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white border border-border rounded-xl p-3 text-center">
                <div className="text-lg font-bold text-primary-700">{nbTransitions}</div>
                <div className="text-xs text-slate-500">Transitions</div>
              </div>
              <div className="bg-white border border-border rounded-xl p-3 text-center">
                <div className="text-lg font-bold text-violet-700">{nbLlm}</div>
                <div className="text-xs text-slate-500">Appels IA</div>
              </div>
              <div className="bg-white border border-border rounded-xl p-3 text-center">
                <div className="text-lg font-bold text-emerald-700">{nbHumain}</div>
                <div className="text-xs text-slate-500">Actions auditeur</div>
              </div>
            </div>
          )}

          {journal.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="Journal vide"
              description="Les actions seront enregistrées ici au fur et à mesure de la mission."
            />
          ) : (
            <div className="space-y-2">
              {journal.map((entry, i) => (
                <JournalEntry key={entry.id} entry={entry} index={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
