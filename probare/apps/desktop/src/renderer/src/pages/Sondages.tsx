import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database, Plus, ChevronDown, ChevronRight, Play, CheckSquare, Square,
  RefreshCw, Wand2, Trash2, AlertTriangle, CheckCircle,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { OriginBadge } from '../components/ui/OriginBadge'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useSyncProjet } from '../hooks/useProjet'

const CYCLES = [
  { id: 'tresorerie', label: 'Trésorerie' },
  { id: 'achats', label: 'Achats-Fournisseurs' },
  { id: 'ventes', label: 'Ventes-Clients' },
  { id: 'immobilisations', label: 'Immobilisations' },
  { id: 'stocks', label: 'Stocks' },
  { id: 'paie', label: 'Paie / Personnel' },
  { id: 'impots', label: 'Impôts & Taxes' },
  { id: 'capitaux_propres', label: 'Capitaux propres' },
]

function CreateModal({ onClose, onCreate }: { onClose: () => void; onCreate: (data: any) => Promise<void> }) {
  const [cycle, setCycle] = useState('tresorerie')
  const [libelle, setLibelle] = useState('')
  const [taux, setTaux] = useState(5)
  const [confiance, setConfiance] = useState(95)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    await onCreate({ cycle, libelle, taux_erreur_tolere: taux / 100, niveau_confiance: confiance })
    setLoading(false)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Nouveau sondage</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 leading-relaxed">
            <strong>NEP 530 — Sondages statistiques.</strong> Probare calcule la taille d'échantillon
            selon la formule de Neyman, puis sélectionne aléatoirement les éléments à vérifier.
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Cycle</label>
            <select className="input-field" value={cycle} onChange={(e) => setCycle(e.target.value)}>
              {CYCLES.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Libellé</label>
            <input className="input-field" value={libelle} onChange={(e) => setLibelle(e.target.value)}
              placeholder="Ex : Vérification factures fournisseurs N" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Taux d'erreur toléré (%)
                <span className="ml-1 text-slate-400 font-normal" title="Pourcentage maximal d'anomalies acceptable dans la population. 5 % est la norme en audit.">?</span>
              </label>
              <input type="number" className="input-field" min={1} max={20} value={taux}
                onChange={(e) => setTaux(Number(e.target.value))} />
              <p className="text-xs text-slate-400 mt-1">5 % recommandé (norme audit)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Niveau de confiance
                <span className="ml-1 text-slate-400 font-normal" title="Probabilité que l'échantillon soit représentatif. 95 % est le standard en audit légal.">?</span>
              </label>
              <select className="input-field" value={confiance} onChange={(e) => setConfiance(Number(e.target.value))}>
                <option value={90}>90 % — risque modéré</option>
                <option value={95}>95 % — standard audit</option>
                <option value={99}>99 % — risque très faible</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Annuler</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
              Créer
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

function SondageDetail({ sondage, projetId, onRefresh }: { sondage: any; projetId: string; onRefresh: () => void }) {
  const { post, patch } = useApi()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [concluding, setConcluding] = useState(false)
  const [tailleOverride, setTailleOverride] = useState<number | ''>('')

  const elements: any[] = sondage.elements || []
  const nb_anomalies = elements.filter((e) => e.est_anomalie).length
  const conclusion_ia = sondage.conclusion_ia
    ? (typeof sondage.conclusion_ia === 'string' ? JSON.parse(sondage.conclusion_ia) : sondage.conclusion_ia)
    : null

  const handleSelectionner = async () => {
    setLoading(true)
    try {
      const body = tailleOverride ? { taille_echantillon: tailleOverride } : {}
      await post(`/projets/${projetId}/sondages/${sondage.id}/selectionner`, body)
      toast.success('Échantillon sélectionné.')
      onRefresh()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAnomalie = async (elt: any) => {
    try {
      await patch(`/projets/${projetId}/sondages/${sondage.id}/elements/${elt.id}`, {
        est_anomalie: elt.est_anomalie ? 0 : 1,
        montant_anomalie: elt.est_anomalie ? 0 : Math.abs(elt.montant || 0),
      })
      onRefresh()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleConclure = async () => {
    setConcluding(true)
    try {
      await post(`/projets/${projetId}/sondages/${sondage.id}/conclure`, {})
      toast.success('Conclusion IA rédigée.')
      onRefresh()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setConcluding(false)
    }
  }

  return (
    <div className="mt-3 space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="bg-slate-50 rounded-lg p-2">
          <div className="text-base font-bold text-slate-900">{sondage.population ?? '—'}</div>
          <div className="text-[10px] text-slate-500">Population</div>
          <OriginBadge source="calcule" />
        </div>
        <div className="bg-blue-50 rounded-lg p-2">
          <div className="text-base font-bold text-blue-700">{sondage.taille_echantillon ?? '—'}</div>
          <div className="text-[10px] text-blue-500">Taille recommandée</div>
          <OriginBadge source="calcule" />
        </div>
        <div className={`rounded-lg p-2 ${nb_anomalies > 0 ? 'bg-red-50' : 'bg-emerald-50'}`}>
          <div className={`text-base font-bold ${nb_anomalies > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
            {nb_anomalies}
          </div>
          <div className={`text-[10px] ${nb_anomalies > 0 ? 'text-red-500' : 'text-emerald-500'}`}>Anomalies</div>
        </div>
        <div className="bg-amber-50 rounded-lg p-2">
          <div className="text-base font-bold text-amber-700">
            {sondage.taux_anomalie != null ? `${(sondage.taux_anomalie * 100).toFixed(1)} %` : '—'}
          </div>
          <div className="text-[10px] text-amber-500">Taux anomalie</div>
          <OriginBadge source="calcule" />
        </div>
      </div>

      {/* Sélection de l'échantillon */}
      <div className="flex items-center gap-3">
        <input
          type="number"
          className="input w-32"
          placeholder={`Taille (déf: ${sondage.taille_echantillon ?? '?'})`}
          value={tailleOverride}
          onChange={(e) => setTailleOverride(e.target.value ? Number(e.target.value) : '')}
        />
        <button onClick={handleSelectionner} disabled={loading} className="btn-secondary">
          {loading ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
          {elements.length > 0 ? 'Resélectionner' : 'Sélectionner l\'échantillon'}
        </button>
      </div>

      {/* Éléments */}
      {elements.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-700">
              Éléments sélectionnés ({elements.length})
            </span>
            <span className="text-xs text-slate-400">Cochez les anomalies constatées</span>
          </div>
          <div className="border border-border rounded-xl overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Anomalie</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Compte</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Libellé</th>
                  <th className="px-3 py-2 text-right font-semibold text-slate-600">Montant</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Pièce</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600">Date</th>
                </tr>
              </thead>
              <tbody>
                {elements.map((elt) => (
                  <tr
                    key={elt.id}
                    className={`border-t border-border hover:bg-slate-50 cursor-pointer ${elt.est_anomalie ? 'bg-red-50/50' : ''}`}
                    onClick={() => handleToggleAnomalie(elt)}
                  >
                    <td className="px-3 py-2">
                      {elt.est_anomalie
                        ? <CheckSquare className="w-4 h-4 text-red-500" />
                        : <Square className="w-4 h-4 text-slate-300" />}
                    </td>
                    <td className="px-3 py-2 font-mono">{elt.compte}</td>
                    <td className="px-3 py-2 text-slate-700 max-w-[180px] truncate">{elt.libelle}</td>
                    <td className="px-3 py-2 text-right font-mono">
                      {elt.montant != null ? elt.montant.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) : '—'}
                    </td>
                    <td className="px-3 py-2 text-slate-500">{elt.numero_piece || '—'}</td>
                    <td className="px-3 py-2 text-slate-500">{elt.date_piece || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Projection */}
          {sondage.montant_projete != null && (
            <div className="mt-2 flex items-center gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg">
              <div className="text-xs text-blue-700">
                <span className="font-semibold">Projection Python (NEP 530) :</span>{' '}
                Montant projeté sur la population ={' '}
                <span className="font-bold">
                  {sondage.montant_projete.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} FDJ
                </span>
              </div>
              <OriginBadge source="calcule" />
            </div>
          )}

          {/* Bouton conclure */}
          <div className="mt-3">
            <button
              onClick={handleConclure}
              disabled={concluding}
              className="btn-secondary w-full"
            >
              {concluding ? <Spinner size="sm" /> : <Wand2 className="w-4 h-4" />}
              Conclure avec l'IA
            </button>
          </div>
        </div>
      )}

      {/* Conclusion IA */}
      {conclusion_ia && (
        <div className="bg-amber-50 border border-amber-100 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Wand2 className="w-3.5 h-3.5 text-amber-600" />
            <span className="text-xs font-semibold text-amber-700">Conclusion IA</span>
            <OriginBadge source="ia" />
          </div>
          <p className="text-xs text-amber-800 leading-relaxed">{conclusion_ia.synthese}</p>
          {conclusion_ia.diligences?.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {conclusion_ia.diligences.map((d: string, i: number) => (
                <li key={i} className="text-xs text-amber-700 flex gap-1.5">
                  <span className="text-amber-400">•</span> {d}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-2">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              conclusion_ia.conclusion === 'acceptable' ? 'bg-emerald-100 text-emerald-700'
              : conclusion_ia.conclusion === 'materiel' ? 'bg-red-100 text-red-700'
              : 'bg-amber-100 text-amber-700'
            }`}>
              {conclusion_ia.conclusion === 'acceptable' ? 'Acceptable'
                : conclusion_ia.conclusion === 'materiel' ? 'Matériel — diligences requises'
                : 'Exige des diligences complémentaires'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export function Sondages() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get, post, del } = useApi()
  const toast = useToast()
  useSyncProjet()

  const [sondages, setSondages] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  const loadSondages = async () => {
    if (!projetId) return
    try {
      const data = await get(`/projets/${projetId}/sondages`)
      setSondages(data.sondages || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSondages() }, [projetId])

  const handleCreate = async (body: any) => {
    try {
      await post(`/projets/${projetId}/sondages`, body)
      toast.success('Sondage créé.')
      setShowModal(false)
      await loadSondages()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await del(`/projets/${projetId}/sondages/${id}`)
      toast.success('Sondage supprimé.')
      await loadSondages()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const CYCLE_LABELS: Record<string, string> = Object.fromEntries(
    [
      ['tresorerie', 'Trésorerie'],
      ['achats', 'Achats'],
      ['ventes', 'Ventes'],
      ['immobilisations', 'Immobilisations'],
      ['stocks', 'Stocks'],
      ['paie', 'Paie'],
      ['impots', 'Impôts'],
      ['capitaux_propres', 'Capitaux propres'],
    ]
  )

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Sondages sur pièces"
        subtitle="NEP 530 — Échantillonnage statistique (formule Neyman)"
        actions={
          <div className="flex gap-2">
            <button onClick={loadSondages} className="btn-ghost">
              <RefreshCw className="w-4 h-4" />
            </button>
            <button onClick={() => setShowModal(true)} className="btn-primary">
              <Plus className="w-4 h-4" />
              Nouveau sondage
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          {loading ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : sondages.length === 0 ? (
            <EmptyState
              icon={Database}
              title="Aucun sondage"
              description="Créez un sondage statistique pour sélectionner un échantillon à partir des données importées."
            />
          ) : (
            <div className="space-y-3">
              {sondages.map((s) => {
                const isExpanded = expanded === s.id
                const isConclu = s.statut === 'conclu'
                const elements: any[] = s.elements || []
                return (
                  <motion.div
                    key={s.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card overflow-hidden"
                  >
                    <button
                      onClick={() => setExpanded(isExpanded ? null : s.id)}
                      className="w-full flex items-center gap-3 p-4 text-left hover:bg-slate-50 transition-colors"
                    >
                      {isExpanded
                        ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-slate-900 truncate">
                            {s.libelle || 'Sondage sans titre'}
                          </span>
                          {isConclu && <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />}
                        </div>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-slate-500">{CYCLE_LABELS[s.cycle] || s.cycle}</span>
                          <span className="text-xs text-slate-400">Population : {s.population ?? '—'}</span>
                          <span className="text-xs text-slate-400">Taille : {s.taille_echantillon ?? '—'}</span>
                          {elements.length > 0 && (
                            <span className="text-xs text-slate-400">Échantillon : {elements.length} élts</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          isConclu ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}>
                          {isConclu ? 'Conclu' : 'En cours'}
                        </span>
                        <button
                          onClick={(e) => handleDelete(s.id, e)}
                          className="p-1 rounded hover:bg-red-50 hover:text-red-500 text-slate-400 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </button>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="border-t border-border px-4 pb-4"
                        >
                          <SondageDetail
                            sondage={s}
                            projetId={projetId!}
                            onRefresh={loadSondages}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <CreateModal onClose={() => setShowModal(false)} onCreate={handleCreate} />
      )}
    </div>
  )
}
