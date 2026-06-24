import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText, Wand2, CheckCircle, AlertTriangle, FileSpreadsheet,
  RefreshCw, ChevronDown, ChevronUp, Layers,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'

const CYCLE_LABELS: Record<string, string> = {
  tresorerie: 'Trésorerie',
  achats: 'Achats-Fournisseurs',
  ventes: 'Ventes-Clients',
  immobilisations: 'Immobilisations',
  stocks: 'Stocks',
  paie: 'Paie / Personnel',
  impots: 'Impôts & Taxes',
  capitaux_propres: 'Capitaux propres',
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function Rapport() {
  const { projetId } = useParams<{ projetId: string }>()
  const { get, post, downloadBlob } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()
  useSyncProjet()

  const [feuilles, setFeuilles] = useState<any[]>([])
  const [exceptions, setExceptions] = useState<any[]>([])
  const [resultats, setResultats] = useState<any[]>([])
  const [generatingCycle, setGeneratingCycle] = useState<string | null>(null)
  const [generatingAll, setGeneratingAll] = useState(false)
  const [exportingDocx, setExportingDocx] = useState(false)
  const [exportingXlsx, setExportingXlsx] = useState(false)
  const [expandedCycle, setExpandedCycle] = useState<string | null>(null)

  const cycles: string[] = Array.isArray(projetActif?.cycles_couverts)
    ? projetActif.cycles_couverts
    : ['tresorerie', 'achats', 'ventes']

  const loadData = async () => {
    if (!projetId) return
    const [fData, eData, rData] = await Promise.all([
      get(`/projets/${projetId}/feuilles`),
      get(`/projets/${projetId}/exceptions`),
      get(`/projets/${projetId}/controles`),
    ])
    setFeuilles(fData.feuilles || [])
    setExceptions(eData.exceptions || [])
    setResultats(rData.resultats || [])
  }

  useEffect(() => { loadData() }, [projetId])

  const handleGenererCycle = async (cycle: string) => {
    if (!projetId) return
    setGeneratingCycle(cycle)
    setExpandedCycle(cycle)
    try {
      await post(`/projets/${projetId}/generer-feuille`, { cycle })
      toast.success(`Feuille ${CYCLE_LABELS[cycle] ?? cycle} rédigée.`)
      await loadData()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGeneratingCycle(null)
    }
  }

  const handleGenererTout = async () => {
    if (!projetId) return
    setGeneratingAll(true)
    let ok = 0
    for (const cycle of cycles) {
      setGeneratingCycle(cycle)
      setExpandedCycle(cycle)
      try {
        await post(`/projets/${projetId}/generer-feuille`, { cycle })
        ok++
      } catch (e: any) {
        toast.error(`${CYCLE_LABELS[cycle] ?? cycle} : ${e.message}`)
      }
    }
    setGeneratingCycle(null)
    setGeneratingAll(false)
    if (ok > 0) {
      toast.success(`${ok} feuille${ok > 1 ? 's' : ''} rédigée${ok > 1 ? 's' : ''}.`)
      await loadData()
    }
  }

  const handleExporterDossier = async () => {
    if (!projetId) return
    setExportingDocx(true)
    try {
      const { blob, filename } = await downloadBlob(`/projets/${projetId}/exporter-dossier`)
      saveBlob(blob, filename)
      toast.success('Dossier de travail exporté.')
      if (projetActif?.etat_courant === 'generation') {
        const updated = await post(`/projets/${projetId}/transition`, { vers: 'opinion', acteur: 'utilisateur' })
        setProjetActif(updated)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setExportingDocx(false)
    }
  }

  const handleExporterExceptions = async () => {
    if (!projetId) return
    setExportingXlsx(true)
    try {
      const { blob, filename } = await downloadBlob(`/projets/${projetId}/exporter-exceptions`)
      saveBlob(blob, filename)
      toast.success('Tableau des exceptions exporté.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setExportingXlsx(false)
    }
  }

  const nbOuvertes = exceptions.filter((e) => e.statut === 'ouverte').length
  const etatCourant = projetActif?.etat_courant || ''
  const peutGenerer = ['generation', 'revue'].includes(etatCourant) && nbOuvertes === 0
  const feuillesByCycle = (cycle: string) => feuilles.filter((f) => f.cycle === cycle)
  const cyclesDone = cycles.filter((c) => feuillesByCycle(c).length > 0).length

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dossier de travail & Rapport"
        subtitle="NEP 230 — Génération des livrables"
        actions={
          <button onClick={loadData} className="btn-ghost">
            <RefreshCw className="w-4 h-4" />
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-5">

          {/* Avertissement exceptions ouvertes */}
          {nbOuvertes > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl"
            >
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
              <div>
                <div className="text-sm font-semibold text-amber-800">
                  {nbOuvertes} exception{nbOuvertes !== 1 ? 's' : ''} ouverte{nbOuvertes !== 1 ? 's' : ''} non tranchée{nbOuvertes !== 1 ? 's' : ''}
                </div>
                <div className="text-xs text-amber-700 mt-0.5">
                  Toutes les exceptions doivent être tranchées avant la génération.
                </div>
              </div>
            </motion.div>
          )}

          {/* Feuilles de travail — par cycle */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-slate-900">Feuilles de travail</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  {cyclesDone} / {cycles.length} cycle{cycles.length !== 1 ? 's' : ''} — rédigées par l'IA.
                </p>
              </div>
              <button
                onClick={handleGenererTout}
                disabled={generatingAll || generatingCycle !== null || !peutGenerer}
                className="btn-secondary text-sm"
              >
                {generatingAll ? <Spinner size="sm" /> : <Layers className="w-4 h-4" />}
                Tout générer
              </button>
            </div>

            <div className="space-y-2">
              {cycles.map((cycle) => {
                const fts = feuillesByCycle(cycle)
                const hasFeuille = fts.length > 0
                const isGenerating = generatingCycle === cycle
                const isExpanded = expandedCycle === cycle
                const latest = fts[fts.length - 1]

                return (
                  <div key={cycle} className="border border-border rounded-xl overflow-hidden">
                    {/* En-tête cycle */}
                    <div className="flex items-center gap-3 px-4 py-3 bg-slate-50">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${hasFeuille ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                      <span className="text-sm font-medium text-slate-800 flex-1">
                        {CYCLE_LABELS[cycle] ?? cycle}
                      </span>
                      {hasFeuille && (
                        <span className="text-xs text-slate-400">{formatDate(latest.genere_le)}</span>
                      )}
                      <button
                        onClick={() => handleGenererCycle(cycle)}
                        disabled={isGenerating || generatingAll || !peutGenerer}
                        className="btn-ghost text-xs py-1 px-2"
                        title={hasFeuille ? 'Regénérer' : 'Générer'}
                      >
                        {isGenerating ? <Spinner size="sm" /> : <Wand2 className="w-3.5 h-3.5" />}
                        {hasFeuille ? 'Regénérer' : 'Générer'}
                      </button>
                      {hasFeuille && (
                        <button
                          onClick={() => setExpandedCycle(isExpanded ? null : cycle)}
                          className="btn-ghost text-xs p-1"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      )}
                    </div>

                    {/* Contenu feuille */}
                    <AnimatePresence>
                      {isExpanded && latest && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 py-3 border-t border-border">
                            <div className="flex items-center gap-2 mb-2">
                              <FileText className="w-3.5 h-3.5 text-primary-600" />
                              <span className="text-xs font-medium text-slate-600">{latest.nep_ref}</span>
                              {latest.sources && latest.sources.length > 0 && (
                                <span className="ml-auto text-xs text-slate-400">
                                  {latest.sources.length} source{latest.sources.length !== 1 ? 's' : ''}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">
                              {latest.contenu_redige}
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* Statistiques */}
          {resultats.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="card p-5"
            >
              <h2 className="font-semibold text-slate-900 mb-3">Récapitulatif</h2>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-slate-50 rounded-lg p-3">
                  <div className="text-xl font-bold text-slate-900">{resultats.length}</div>
                  <div className="text-xs text-slate-500">Contrôles</div>
                </div>
                <div className="bg-emerald-50 rounded-lg p-3">
                  <div className="text-xl font-bold text-emerald-700">
                    {resultats.filter((r) => r.statut === 'ok').length}
                  </div>
                  <div className="text-xs text-emerald-600">Sans anomalie</div>
                </div>
                <div className="bg-red-50 rounded-lg p-3">
                  <div className="text-xl font-bold text-red-700">
                    {exceptions.length}
                  </div>
                  <div className="text-xs text-red-600">Exceptions</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Export */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card p-5"
          >
            <h2 className="font-semibold text-slate-900 mb-1">Export des livrables</h2>
            <p className="text-xs text-slate-500 mb-4">
              Chaque chiffre est tracé jusqu'à sa source. La génération échoue si un chiffre non sourcé est détecté.
            </p>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleExporterDossier}
                disabled={exportingDocx || !peutGenerer}
                className="btn-primary justify-center py-3"
              >
                {exportingDocx ? <Spinner size="sm" /> : <FileText className="w-5 h-5" />}
                <div className="text-left">
                  <div className="text-sm font-semibold">Dossier de travail</div>
                  <div className="text-xs opacity-75">Format .docx — NEP 230</div>
                </div>
              </button>

              <button
                onClick={handleExporterExceptions}
                disabled={exportingXlsx}
                className="btn-secondary justify-center py-3"
              >
                {exportingXlsx ? <Spinner size="sm" /> : <FileSpreadsheet className="w-5 h-5" />}
                <div className="text-left">
                  <div className="text-sm font-semibold">Tableau des exceptions</div>
                  <div className="text-xs opacity-75">Format .xlsx</div>
                </div>
              </button>
            </div>

            {projetActif?.etat_courant === 'opinion' && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-lg"
              >
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <p className="text-xs text-emerald-800">
                  Mission en phase d'opinion. L'opinion d'audit finale est à la charge exclusive de l'auditeur habilité.
                  Probare ne signe pas.
                </p>
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
