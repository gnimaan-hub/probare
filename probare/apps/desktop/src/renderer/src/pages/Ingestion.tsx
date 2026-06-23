import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileSpreadsheet, CheckCircle, ArrowRight, Info, Wand2, X,
  AlertCircle, FileText, Paperclip, ChevronDown, ChevronRight, Loader2,
  FolderOpen, Scan
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type DocumentRequis, type DocumentAnnexe } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'

// ─── Types document ───────────────────────────────────────────────────────────

const DOC_LABELS: Record<string, { label: string; hint: string }> = {
  grand_livre: {
    label: 'Grand livre comptable',
    hint: 'Fichier Excel/CSV avec toutes les écritures (date, compte, montant, libellé)',
  },
  balance: {
    label: 'Balance des comptes',
    hint: 'Résumé par compte : total débits, total crédits, solde final',
  },
  releve_bancaire: {
    label: 'Relevé bancaire',
    hint: 'Relevé de compte bancaire (optionnel — pour le rapprochement)',
  },
}

// ─── Drop zone par type de document ──────────────────────────────────────────

function DocDropZone({
  typeDoc, label, hint, requis, onFile, uploading, disabled,
}: {
  typeDoc: string
  label: string
  hint: string
  requis: boolean
  onFile: (file: File, typeDoc: string) => void
  uploading: boolean
  disabled: boolean
}) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) onFile(acceptedFiles[0], typeDoc)
  }, [onFile, typeDoc])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    multiple: false,
    disabled: disabled || uploading,
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all
        ${isDragActive ? 'border-primary-400 bg-primary-50'
          : disabled ? 'border-slate-200 bg-slate-50 cursor-default'
          : 'border-border hover:border-primary-300 hover:bg-slate-50'}`}
    >
      <input {...getInputProps()} />
      {uploading
        ? <Loader2 className="w-6 h-6 mx-auto mb-1 text-primary-500 animate-spin" />
        : <Upload className={`w-6 h-6 mx-auto mb-1 ${isDragActive ? 'text-primary-500' : 'text-slate-400'}`} />
      }
      <p className="text-xs font-medium text-slate-600">
        {uploading ? 'Import en cours…' : 'Déposer ou parcourir'}
      </p>
      <p className="text-[10px] text-slate-400 mt-0.5">xlsx · xls · csv</p>
    </div>
  )
}

// ─── Ligne de document dans la checklist ─────────────────────────────────────

function DocCheckRow({
  doc, fichiers, onFile, uploading, disabled,
}: {
  doc: DocumentRequis
  fichiers: any[]
  onFile: (file: File, typeDoc: string) => void
  uploading: boolean
  disabled: boolean
}) {
  const fichiersType = fichiers.filter(
    (f) => (f.type_document || f.type) === doc.type
  )
  const meta = DOC_LABELS[doc.type]

  return (
    <div className={`rounded-xl border overflow-hidden ${
      doc.importe ? 'border-emerald-200' : doc.requis ? 'border-amber-200' : 'border-border'
    }`}>
      {/* En-tête */}
      <div className={`flex items-center gap-3 px-4 py-3 ${
        doc.importe ? 'bg-emerald-50' : doc.requis ? 'bg-amber-50/60' : 'bg-white'
      }`}>
        {doc.importe
          ? <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
          : doc.requis
          ? <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
          : <Info className="w-4 h-4 text-slate-400 flex-shrink-0" />
        }
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-800">
              {meta?.label || doc.label}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
              doc.importe
                ? 'bg-emerald-100 text-emerald-700'
                : doc.requis
                ? 'bg-amber-100 text-amber-700'
                : 'bg-slate-100 text-slate-500'
            }`}>
              {doc.importe
                ? `${doc.nb_fichiers} fichier${doc.nb_fichiers !== 1 ? 's' : ''}`
                : doc.requis ? 'Requis' : 'Optionnel'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{meta?.hint || doc.description}</p>
        </div>
      </div>

      {/* Fichiers existants */}
      {fichiersType.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-100 bg-white">
          <div className="space-y-1">
            {fichiersType.map((f) => (
              <div key={f.id} className="flex items-center gap-2 text-xs text-slate-600">
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                <span className="truncate">{f.nom}</span>
                <span className="text-slate-400 ml-auto flex-shrink-0">{formatDate(f.importe_le)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zone d'import */}
      {!disabled && (
        <div className="px-4 py-3 border-t border-slate-100 bg-white">
          <DocDropZone
            typeDoc={doc.type}
            label={doc.label}
            hint={doc.description}
            requis={doc.requis}
            onFile={onFile}
            uploading={uploading}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  )
}

// ─── Section Annexes ──────────────────────────────────────────────────────────

function AnnexeCard({
  annexe, projetId, onUpdated,
}: {
  annexe: DocumentAnnexe
  projetId: string
  onUpdated: (a: DocumentAnnexe) => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [analysing, setAnalysing] = useState(false)
  const [open, setOpen] = useState(false)

  const handleAnalyser = async () => {
    setAnalysing(true)
    try {
      const updated = await post(`/projets/${projetId}/annexes/${annexe.id}/analyser`, {})
      onUpdated(updated)
      toast.success('Analyse IA terminée.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setAnalysing(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-border rounded-xl overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors"
      >
        <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-800 truncate">{annexe.nom}</span>
            {annexe.ia_analysee
              ? <span className="text-[10px] bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded-full">Analysé IA</span>
              : <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full">En attente</span>
            }
          </div>
          {annexe.description && (
            <p className="text-xs text-slate-500 mt-0.5 truncate">{annexe.description}</p>
          )}
        </div>
        {!annexe.ia_analysee && (
          <button
            onClick={(e) => { e.stopPropagation(); handleAnalyser() }}
            disabled={analysing}
            className="btn-secondary text-xs py-1 px-2 mr-2 flex-shrink-0"
          >
            {analysing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
            Analyser
          </button>
        )}
        {open
          ? <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
          : <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
        }
      </button>

      {open && annexe.ia_analysee ? (
        <div className="border-t border-border px-4 py-3 bg-slate-50/60 space-y-3">
          {annexe.resume_ia && (
            <div>
              <div className="text-xs font-semibold text-slate-600 mb-1">Résumé IA</div>
              <p className="text-xs text-slate-700 leading-relaxed">{annexe.resume_ia}</p>
            </div>
          )}
          {annexe.points_cles && annexe.points_cles.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-slate-600 mb-1">Points clés</div>
              <ul className="space-y-0.5">
                {annexe.points_cles.map((p, i) => (
                  <li key={i} className="text-xs text-slate-700 flex gap-1.5">
                    <span className="text-primary-400 flex-shrink-0">•</span>{p}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {annexe.alertes && annexe.alertes.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5">
              <div className="text-xs font-semibold text-amber-700 mb-1">Alertes</div>
              <ul className="space-y-0.5">
                {annexe.alertes.map((a, i) => (
                  <li key={i} className="text-xs text-amber-700 flex gap-1.5">
                    <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />{a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : open && !annexe.ia_analysee ? (
        <div className="border-t border-border px-4 py-3 bg-slate-50/60">
          <p className="text-xs text-slate-500">Cliquez sur "Analyser" pour lancer l'analyse IA.</p>
        </div>
      ) : null}
    </motion.div>
  )
}

function AnnexeDropZone({ onFile, uploading }: { onFile: (file: File, desc: string) => void; uploading: boolean }) {
  const [desc, setDesc] = useState('')
  const [pendingFile, setPendingFile] = useState<File | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) setPendingFile(acceptedFiles[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: uploading,
  })

  const handleConfirm = () => {
    if (pendingFile) {
      onFile(pendingFile, desc)
      setPendingFile(null)
      setDesc('')
    }
  }

  return (
    <div className="space-y-2">
      {pendingFile ? (
        <div className="border border-primary-200 bg-primary-50 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary-600" />
            <span className="text-sm font-medium text-primary-800">{pendingFile.name}</span>
            <button onClick={() => setPendingFile(null)} className="ml-auto btn-ghost p-1 rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <input
            className="input-field text-sm"
            placeholder="Description (ex : PV d'assemblée 2024, contrat de bail…)"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
          <button onClick={handleConfirm} disabled={uploading} className="btn-primary w-full text-sm">
            {uploading ? <Spinner size="sm" /> : <Paperclip className="w-4 h-4" />}
            Ajouter au dossier
          </button>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all
            ${isDragActive ? 'border-primary-400 bg-primary-50' : 'border-border hover:border-primary-300 hover:bg-slate-50'}`}
        >
          <input {...getInputProps()} />
          <Paperclip className="w-6 h-6 mx-auto mb-2 text-slate-400" />
          <p className="text-sm font-medium text-slate-600">Ajouter un document annexe</p>
          <p className="text-xs text-slate-400 mt-0.5">PV, contrats, confirmations, tout format</p>
        </div>
      )}
    </div>
  )
}

// ─── Modal mapping ────────────────────────────────────────────────────────────

function MappingModal({ fichier, onClose, onConfirmed }: {
  fichier: any; onClose: () => void; onConfirmed: () => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState<any>(null)
  const { projetActif } = useProjetStore()

  const handleSuggerer = async () => {
    if (!projetActif?.consentement_client) {
      toast.warning('Consentement client requis pour les suggestions IA.')
      return
    }
    setLoading(true)
    try {
      const result = await post(`/projets/${projetActif.id}/mapper-colonnes`, {
        colonnes: fichier.metadata?.colonnes || [],
        exemples: fichier.metadata?.mapping_detecte || {},
      })
      setSuggestion(result)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 12 }}
        className="bg-white rounded-2xl shadow-modal w-full max-w-lg"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-semibold text-slate-900">Vérification du mapping</h2>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="text-sm text-slate-600">Colonnes détectées :</div>
          <div className="bg-slate-50 rounded-lg p-3 text-xs font-mono space-y-1 max-h-48 overflow-y-auto">
            {Object.entries(fichier.metadata?.mapping_detecte || {}).map(([field, col]) => (
              <div key={field} className="flex justify-between gap-4">
                <span className="text-slate-500">{field}</span>
                <span className={col ? 'text-emerald-600 font-semibold' : 'text-slate-400'}>
                  {String(col) || 'non mappé'}
                </span>
              </div>
            ))}
          </div>
          {suggestion && (
            <div className="bg-primary-50 border border-primary-200 rounded-lg p-3">
              <div className="text-xs font-semibold text-primary-700 mb-1">
                Suggestion IA ({Math.round((suggestion.confiance || 0) * 100)}%)
              </div>
              <p className="text-xs text-primary-600">{suggestion.notes}</p>
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={handleSuggerer} disabled={loading} className="btn-secondary flex-1">
              {loading ? <Spinner size="sm" /> : <Wand2 className="w-4 h-4" />}
              Améliorer avec l'IA
            </button>
            <button onClick={onConfirmed} className="btn-primary flex-1">
              <CheckCircle className="w-4 h-4" />
              Confirmer
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function Ingestion() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, uploadFile, post } = useApi()
  const toast = useToast()
  const {
    projetActif, setProjetActif,
    fichiers, setFichiers,
    annexes, setAnnexes,
    documentsRequis, setDocumentsRequis,
  } = useProjetStore()
  useSyncProjet()

  const [uploading, setUploading] = useState(false)
  const [uploadingAnnexe, setUploadingAnnexe] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const [pendingFichier, setPendingFichier] = useState<any>(null)

  const loadAll = async () => {
    if (!projetId) return
    const [fRes, dRes, aRes] = await Promise.all([
      get(`/projets/${projetId}/fichiers`),
      get(`/projets/${projetId}/documents-requis`),
      get(`/projets/${projetId}/annexes`),
    ])
    setFichiers(fRes.fichiers || [])
    setDocumentsRequis(dRes.checklist || [])
    setAnnexes(aRes.annexes || [])
  }

  useEffect(() => {
    loadAll().catch((e) => toast.error(e.message))
  }, [projetId])

  const handleUploadComptable = async (file: File, typeDoc: string) => {
    if (!projetId) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('fichier', file)
      fd.append('type_fichier', typeDoc)
      const result = await uploadFile(`/projets/${projetId}/fichiers`, fd)
      toast.success(`${file.name} importé — ${result.nb_donnees_extraites} données extraites.`)
      await loadAll()
      if (result.metadata?.mapping_detecte) {
        setPendingFichier(result)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setUploading(false)
    }
  }

  const handleUploadAnnexe = async (file: File, description: string) => {
    if (!projetId) return
    setUploadingAnnexe(true)
    try {
      const fd = new FormData()
      fd.append('fichier', file)
      fd.append('type_fichier', 'annexe')
      fd.append('description', description)
      await uploadFile(`/projets/${projetId}/fichiers`, fd)
      toast.success(`${file.name} ajouté au dossier.`)
      const aRes = await get(`/projets/${projetId}/annexes`)
      setAnnexes(aRes.annexes || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setUploadingAnnexe(false)
    }
  }

  const handleAnnexeUpdated = (updated: DocumentAnnexe) => {
    setAnnexes(annexes.map((a) => a.id === updated.id ? updated : a))
  }

  const handlePasserPlanification = async () => {
    if (!projetId) return
    const nbImportes = documentsRequis.filter((d) => d.requis && d.importe).length
    const nbRequis = documentsRequis.filter((d) => d.requis).length
    if (nbImportes < nbRequis) {
      const manquants = documentsRequis.filter((d) => d.requis && !d.importe).map((d) => d.label)
      toast.warning(`Documents manquants : ${manquants.join(', ')}`)
      return
    }
    setTransitioning(true)
    try {
      let updated = await post(`/projets/${projetId}/transition`, { vers: 'extraction', acteur: 'utilisateur' })
      updated = await post(`/projets/${projetId}/transition`, { vers: 'planification', acteur: 'système' })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/planification`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const etatCourant = projetActif?.etat_courant || 'cadrage'
  const peutAjouter = ['ingestion', 'extraction'].includes(etatCourant)
  const nbRequis = documentsRequis.filter((d) => d.requis).length
  const nbImportes = documentsRequis.filter((d) => d.requis && d.importe).length
  const toutOk = nbRequis > 0 && nbImportes === nbRequis

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Ingestion des fichiers"
        subtitle={`${fichiers.length} fichier${fichiers.length !== 1 ? 's' : ''} importé${fichiers.length !== 1 ? 's' : ''}`}
        actions={
          peutAjouter && fichiers.length > 0 ? (
            <button onClick={handlePasserPlanification} disabled={transitioning} className="btn-primary">
              {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
              Passer à la planification
            </button>
          ) : undefined
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">

          {/* Progression */}
          {documentsRequis.length > 0 && nbRequis > 0 && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-slate-700">Documents obligatoires</span>
                <span className={`text-sm font-bold ${toutOk ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {nbImportes}/{nbRequis}
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(nbImportes / nbRequis) * 100}%` }}
                  className={`h-full rounded-full transition-all ${toutOk ? 'bg-emerald-500' : 'bg-amber-400'}`}
                />
              </div>
              {toutOk && (
                <p className="text-xs text-emerald-600 mt-2 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Tous les documents requis sont importés.
                </p>
              )}
            </motion.div>
          )}

          {/* Checklist documents par type */}
          {peutAjouter && documentsRequis.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 }} className="card p-5">
              <h2 className="font-semibold text-slate-900 mb-1">Fichiers comptables</h2>
              <p className="text-sm text-slate-500 mb-4">
                Importez les fichiers pour les cycles sélectionnés au cadrage.
                Un seul grand livre peut couvrir tous les cycles.
              </p>
              <div className="space-y-3">
                {documentsRequis.map((doc) => (
                  <DocCheckRow
                    key={doc.type}
                    doc={doc}
                    fichiers={fichiers}
                    onFile={handleUploadComptable}
                    uploading={uploading}
                    disabled={!peutAjouter}
                  />
                ))}
              </div>
              <div className="mt-3 flex items-start gap-2 text-xs text-slate-400">
                <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>
                  Chaque cellule importée est tracée vers sa source exacte (fichier, ligne, colonne).
                </span>
              </div>
            </motion.div>
          )}

          {/* Si état non ingestion : afficher les fichiers existants */}
          {!peutAjouter && fichiers.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Fichiers importés ({fichiers.length})</h2>
              <div className="space-y-2">
                {fichiers.map((f) => (
                  <div key={f.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                    <FileSpreadsheet className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 truncate">{f.nom}</div>
                      <div className="text-xs text-slate-500">
                        {f.type_document || f.type} · {formatDate(f.importe_le)}
                      </div>
                    </div>
                    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Mode Dossier Brut */}
          {peutAjouter && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 }} className="card p-5 border-dashed border-2 border-primary-200 bg-primary-50/30">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
                  <Scan className="w-5 h-5 text-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="font-semibold text-slate-900">Mode Dossier Brut (IA)</h2>
                  <p className="text-sm text-slate-500 mt-0.5 mb-3">
                    Vous avez des documents bruts à analyser ? Factures, relevés bancaires scannés, contrats PDF…
                    Déposez-les dans le pipeline IA : <strong>Haiku</strong> les catalogue,
                    <strong> Sonnet</strong> extrait les données comptables, et Probare les importe automatiquement.
                  </p>
                  <button
                    onClick={() => navigate(`/projet/${projetId}/dossier-brut`)}
                    className="btn-primary"
                  >
                    <FolderOpen className="w-4 h-4" />
                    Ouvrir le dossier brut
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Documents annexes */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }} className="card p-5">
            <h2 className="font-semibold text-slate-900 mb-1">Documents annexes</h2>
            <p className="text-sm text-slate-500 mb-4">
              PV d'assemblée, contrats, confirmations bancaires… L'IA peut analyser et résumer chaque document.
              Ces analyses sont purement textuelles — aucun chiffre extrait ne rentre dans les calculs.
            </p>

            {annexes.length > 0 && (
              <div className="space-y-2 mb-4">
                {annexes.map((a) => (
                  <AnnexeCard
                    key={a.id}
                    annexe={a}
                    projetId={projetId!}
                    onUpdated={handleAnnexeUpdated}
                  />
                ))}
              </div>
            )}

            <AnnexeDropZone onFile={handleUploadAnnexe} uploading={uploadingAnnexe} />
          </motion.div>

        </div>
      </div>

      {/* Modal mapping */}
      <AnimatePresence>
        {pendingFichier && (
          <MappingModal
            fichier={pendingFichier}
            onClose={() => setPendingFichier(null)}
            onConfirmed={() => { setPendingFichier(null); toast.success('Mapping confirmé.') }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
