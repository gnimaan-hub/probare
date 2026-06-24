import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText, Wand2, CheckCircle, AlertTriangle, FileSpreadsheet, RefreshCw, FileDown,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { OriginBadge } from '../components/ui/OriginBadge'
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
  const { get, post, patch, downloadBlob } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()
  useSyncProjet()

  const [feuilles, setFeuilles] = useState<any[]>([])
  const [exceptions, setExceptions] = useState<any[]>([])
  const [resultats, setResultats] = useState<any[]>([])
  const [generatingFeuille, setGeneratingFeuille] = useState(false)
  const [exportingDocx, setExportingDocx] = useState(false)
  const [exportingXlsx, setExportingXlsx] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [opinion, setOpinion] = useState<any>(null)
  const [formingOpinion, setFormingOpinion] = useState(false)
  const [narrativeAuditeur, setNarrativeAuditeur] = useState('')
  const [validatingOpinion, setValidatingOpinion] = useState(false)

  const loadData = async () => {
    if (!projetId) return null
    const [fData, eData, rData, oData] = await Promise.all([
      get(`/projets/${projetId}/feuilles`),
      get(`/projets/${projetId}/exceptions`),
      get(`/projets/${projetId}/controles`),
      get(`/projets/${projetId}/opinion`),
    ])
    const f = fData.feuilles || []
    setFeuilles(f)
    setExceptions(eData.exceptions || [])
    setResultats(rData.resultats || [])
    const op = oData.opinion || null
    setOpinion(op)
    if (op?.narrative_auditeur) setNarrativeAuditeur(op.narrative_auditeur)
    else if (op?.narrative_ia) setNarrativeAuditeur(op.narrative_ia)
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

  const handleExporterPdf = async () => {
    if (!projetId) return
    setExportingPdf(true)
    try {
      const { blob, filename } = await downloadBlob(`/projets/${projetId}/exporter-dossier-pdf`, 'GET')
      saveBlob(blob, filename)
      toast.success('Rapport PDF exporté.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setExportingPdf(false)
    }
  }

  const handleFormerOpinion = async () => {
    if (!projetId) return
    setFormingOpinion(true)
    try {
      const data = await post(`/projets/${projetId}/opinion/former`, {})
      setOpinion(data.opinion)
      setNarrativeAuditeur(data.opinion?.narrative_ia || '')
      toast.success("Opinion formée par l'IA.")
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setFormingOpinion(false)
    }
  }

  const handleValiderOpinion = async () => {
    if (!projetId) return
    setValidatingOpinion(true)
    try {
      const data = await patch(`/projets/${projetId}/opinion`, {
        narrative_auditeur: narrativeAuditeur,
        validee: 1,
        validee_par: 'auditeur',
      })
      setOpinion(data.opinion)
      toast.success('Opinion validée.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setValidatingOpinion(false)
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
                      <OriginBadge source="ia" />
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

          {/* Opinion */}
          {peutGenerer && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 }}
              className="card p-5"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h2 className="font-semibold text-slate-900">Formation de l'opinion</h2>
                  <p className="text-xs text-slate-500 mt-0.5">NEP 450 — Agrégation des anomalies + rédaction IA.</p>
                </div>
                <button
                  onClick={handleFormerOpinion}
                  disabled={formingOpinion}
                  className="btn-secondary text-sm"
                >
                  {formingOpinion ? <Spinner size="sm" /> : <Wand2 className="w-4 h-4" />}
                  {opinion ? 'Recalculer' : "Former l'opinion"}
                </button>
              </div>

              {opinion && (() => {
                const agg = opinion.agregation_json || {}
                const TYPE_COLORS: Record<string, string> = {
                  propre: 'bg-emerald-100 text-emerald-800 border-emerald-200',
                  propre_avec_observation: 'bg-amber-100 text-amber-800 border-amber-200',
                  reserve: 'bg-orange-100 text-orange-800 border-orange-200',
                  refus: 'bg-red-100 text-red-800 border-red-200',
                  incomplete: 'bg-slate-100 text-slate-600 border-slate-200',
                }
                const TYPE_LABELS: Record<string, string> = {
                  propre: 'Opinion sans réserve',
                  propre_avec_observation: 'Opinion sans réserve avec observation',
                  reserve: 'Opinion avec réserve',
                  refus: 'Refus de certifier',
                  incomplete: 'Exceptions ouvertes — formation impossible',
                }
                const colorClass = TYPE_COLORS[opinion.type_opinion] || TYPE_COLORS.incomplete
                const label = TYPE_LABELS[opinion.type_opinion] || opinion.type_opinion
                return (
                  <div className="space-y-4">
                    {/* Type d'opinion */}
                    <div className="flex items-center gap-3">
                      <div className={`px-3 py-1.5 rounded-lg border text-sm font-bold ${colorClass}`}>
                        {label}
                      </div>
                      <OriginBadge source="calcule" />
                    </div>

                    {/* Agrégation */}
                    <div className="grid grid-cols-4 gap-2 text-center">
                      <div className="bg-slate-50 rounded-lg p-2">
                        <div className="text-base font-bold text-slate-900">{agg.nb_total ?? 0}</div>
                        <div className="text-[10px] text-slate-500">Total</div>
                      </div>
                      <div className="bg-red-50 rounded-lg p-2">
                        <div className="text-base font-bold text-red-700">{agg.nb_critiques ?? 0}</div>
                        <div className="text-[10px] text-red-500">Critiques</div>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-2">
                        <div className="text-base font-bold text-amber-700">{agg.nb_significatives ?? 0}</div>
                        <div className="text-[10px] text-amber-500">Significatives</div>
                      </div>
                      <div className={`rounded-lg p-2 ${agg.depasse_seuil ? 'bg-red-50' : 'bg-emerald-50'}`}>
                        <div className={`text-base font-bold ${agg.depasse_seuil ? 'text-red-700' : 'text-emerald-700'}`}>
                          {agg.depasse_seuil ? 'Dépasse' : 'Sous'}
                        </div>
                        <div className={`text-[10px] ${agg.depasse_seuil ? 'text-red-500' : 'text-emerald-500'}`}>Seuil</div>
                      </div>
                    </div>

                    {/* Narrative IA */}
                    {opinion.narrative_ia && (
                      <div>
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-xs font-semibold text-slate-700">Narrative proposée</span>
                          <OriginBadge source="ia" />
                        </div>
                        <textarea
                          className="input text-xs leading-relaxed w-full"
                          rows={6}
                          value={narrativeAuditeur}
                          onChange={(e) => setNarrativeAuditeur(e.target.value)}
                          placeholder="Modifiez le texte de l'opinion si nécessaire..."
                        />
                        <p className="text-[10px] text-slate-400 mt-1">
                          Modifiez le texte ci-dessus si nécessaire, puis validez.
                        </p>
                      </div>
                    )}

                    {/* Validation */}
                    {opinion.narrative_ia && (
                      <div className="flex items-center gap-3">
                        <button
                          onClick={handleValiderOpinion}
                          disabled={validatingOpinion || !narrativeAuditeur}
                          className="btn-primary flex-1"
                        >
                          {validatingOpinion ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
                          Valider l'opinion
                        </button>
                        {opinion.validee === 1 && (
                          <div className="flex items-center gap-1.5 text-xs text-emerald-700">
                            <CheckCircle className="w-3.5 h-3.5" />
                            <span>Validée</span>
                            <OriginBadge source="saisie" />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })()}
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
              Chaque chiffre est tracé jusqu'à sa source (NEP 230). La génération échoue si un chiffre non sourcé est détecté.
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
                onClick={handleExporterPdf}
                disabled={exportingPdf || !peutGenerer}
                className="btn-secondary justify-center py-3"
              >
                {exportingPdf ? <Spinner size="sm" /> : <FileDown className="w-5 h-5" />}
                <div className="text-left">
                  <div className="text-sm font-semibold">Rapport d'audit</div>
                  <div className="text-xs opacity-75">Format .pdf — NEP 230</div>
                </div>
              </button>

              <button
                onClick={handleExporterExceptions}
                disabled={exportingXlsx}
                className="btn-secondary justify-center py-3 col-span-2"
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
