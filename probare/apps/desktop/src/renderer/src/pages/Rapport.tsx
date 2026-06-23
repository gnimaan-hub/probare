import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText, Download, Wand2, CheckCircle, AlertTriangle, FileSpreadsheet, RefreshCw
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'

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
  const [generatingFeuille, setGeneratingFeuille] = useState(false)
  const [exportingDocx, setExportingDocx] = useState(false)
  const [exportingXlsx, setExportingXlsx] = useState(false)

  const loadData = async () => {
    if (!projetId) return null
    const [fData, eData, rData] = await Promise.all([
      get(`/projets/${projetId}/feuilles`),
      get(`/projets/${projetId}/exceptions`),
      get(`/projets/${projetId}/controles`),
    ])
    const f = fData.feuilles || []
    setFeuilles(f)
    setExceptions(eData.exceptions || [])
    setResultats(rData.resultats || [])
    return f
  }

  useEffect(() => {
    loadData().then(async (f) => {
      // Auto-générer la feuille si on vient d'entrer en phase generation et qu'il n'y en a pas encore
      if (projetActif?.etat_courant === 'generation' && f && f.length === 0) {
        await handleGenererFeuille()
      }
    })
  }, [projetId])

  const handleGenererFeuille = async () => {
    if (!projetId) return
    setGeneratingFeuille(true)
    try {
      await post(`/projets/${projetId}/generer-feuille`, { cycle: 'tresorerie' })
      toast.success("Feuille de travail redigee par l'IA.")
      await loadData()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGeneratingFeuille(false)
    }
  }

  const handleExporterDossier = async () => {
    if (!projetId) return
    setExportingDocx(true)
    try {
      const { blob, filename } = await downloadBlob(`/projets/${projetId}/exporter-dossier`)
      saveBlob(blob, filename)
      toast.success('Dossier de travail exporté.')

      // Passer en opinion si pas encore fait
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

          {/* Feuilles de travail */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-slate-900">Feuilles de travail</h2>
                <p className="text-xs text-slate-500 mt-0.5">Rédigées par l'IA à partir des résultats calculés.</p>
              </div>
              <button
                onClick={handleGenererFeuille}
                disabled={generatingFeuille || !peutGenerer}
                className="btn-secondary text-sm"
              >
                {generatingFeuille ? <Spinner size="sm" /> : <Wand2 className="w-4 h-4" />}
                Rédiger avec l'IA
              </button>
            </div>

            {feuilles.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-400">
                Aucune feuille de travail générée.
              </div>
            ) : (
              <div className="space-y-3">
                {feuilles.map((ft) => (
                  <motion.div
                    key={ft.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="bg-slate-50 rounded-xl p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-4 h-4 text-primary-600" />
                      <span className="text-sm font-semibold text-slate-800">
                        Cycle {ft.cycle} — {ft.nep_ref}
                      </span>
                      <code className="ml-auto text-xs bg-white border border-border px-2 py-0.5 rounded">
                        {formatDate(ft.genere_le)}
                      </code>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed line-clamp-4 whitespace-pre-wrap">
                      {ft.contenu_redige}
                    </p>
                    {ft.sources && ft.sources.length > 0 && (
                      <div className="mt-2 text-xs text-slate-400">
                        Sources : {ft.sources.length} résultat(s) de contrôle(s)
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
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
