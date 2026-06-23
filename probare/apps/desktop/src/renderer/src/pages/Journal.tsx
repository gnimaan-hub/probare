import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Activity, RefreshCw, ArrowUpRight, Bot, User } from 'lucide-react'
import { Header } from '../components/layout/Header'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { formatDate } from '../lib/utils'

const typeColors: Record<string, string> = {
  transition_etat: 'bg-primary-100 text-primary-700',
  appel_llm: 'bg-violet-100 text-violet-700',
  action_humaine: 'bg-emerald-100 text-emerald-700',
}

const typeIcons: Record<string, React.ElementType> = {
  transition_etat: ArrowUpRight,
  appel_llm: Bot,
  action_humaine: User,
}

export function Journal() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get } = useApi()
  const toast = useToast()
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

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Journal d'audit"
        subtitle="Traçabilité complète de toutes les actions"
        actions={
          <button onClick={load} disabled={loading} className="btn-ghost">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          {journal.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="Journal vide"
              description="Les actions seront enregistrées ici au fur et à mesure de la mission."
            />
          ) : (
            <div className="space-y-2">
              {journal.map((entry, i) => {
                const Icon = typeIcons[entry.type] || Activity
                const colorClass = typeColors[entry.type] || 'bg-slate-100 text-slate-600'
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: Math.min(i * 0.02, 0.3) }}
                    className="flex items-start gap-3 p-3 bg-white border border-border rounded-xl hover:border-border-strong transition-colors"
                  >
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`badge border ${colorClass}`}>
                          {entry.type.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-slate-400">{formatDate(entry.horodatage)}</span>
                      </div>
                      <pre className="mt-1 text-xs text-slate-600 font-mono overflow-x-auto whitespace-pre-wrap break-words leading-relaxed">
                        {typeof entry.payload === 'object'
                          ? JSON.stringify(entry.payload, null, 2)
                          : String(entry.payload)}
                      </pre>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
