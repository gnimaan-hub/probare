import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, Trash2, ArrowLeft, Wand2, Database,
  CheckCircle, AlertCircle, Loader2, Download, ChevronDown,
  ChevronRight, FileSpreadsheet, Image, File, ShieldCheck,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'

// ─── Types ───────────────────────────────────────────────────────────────────

interface DocumentBrut {
  id: string
  projet_id: string
  nom: string
  taille_octets?: number
  type_mime?: string
  type_detecte?: string
  description_ia?: string
  statut: 'uploade' | 'catalogue' | 'extrait' | 'verifie' | 'importe' | 'erreur'
  catalogue_json?: {
    type_detecte?: string
    description?: string
    parties?: string[]
    dates?: string[]
    montants_cles?: string[]
    pertinence_audit?: string
  } | null
  extraction_json?: {
    type_sortie?: string
    lignes?: any[]
    nb_lignes?: number
    verification?: {
      score_global?: number
      lignes_verifiees?: Array<{ index: number; confiance: number; anomalie: boolean; commentaire: string }>
      resume_verification?: string
    }
  } | null
  erreur?: string
  ajoute_le?: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STATUT_CONFIG: Record<string, { label: string; color: string }> = {
  uploade:   { label: 'Déposé',     color: 'bg-slate-100 text-slate-600' },
  catalogue: { label: 'Catalogué',  color: 'bg-blue-100 text-blue-700' },
  extrait:   { label: 'Extrait',    color: 'bg-amber-100 text-amber-700' },
  verifie:   { label: 'Vérifié ✓',  color: 'bg-violet-100 text-violet-700' },
  importe:   { label: 'Importé ✓',  color: 'bg-emerald-100 text-emerald-700' },
  erreur:    { label: 'Erreur',     color: 'bg-red-100 text-red-700' },
}

const TYPE_ICON: Record<string, any> = {
  pdf:    FileText,
  image:  Image,
  excel:  FileSpreadsheet,
  csv:    FileSpreadsheet,
  autre:  File,
}

function getFileIcon(nom: string, mime?: string) {
  const ext = nom.split('.').pop()?.toLowerCase() || ''
  if (['pdf'].includes(ext)) return FileText
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return Image
  if (['xlsx', 'xls', 'xlsm'].includes(ext)) return FileSpreadsheet
  if (['csv', 'txt'].includes(ext)) return FileSpreadsheet
  return File
}

function formatOctets(n?: number) {
  if (!n) return ''
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

const PERTINENCE_BADGE: Record<string, string> = {
  elevee:  'bg-emerald-50 text-emerald-700',
  moyenne: 'bg-amber-50 text-amber-700',
  faible:  'bg-slate-50 text-slate-500',
}

// ─── Carte document ───────────────────────────────────────────────────────────

function DocCard({
  doc,
  onDelete,
  onCataloguer,
  onExtraire,
  onVerifier,
  onImporter,
  loading,
}: {
  doc: DocumentBrut
  onDelete: (id: string) => void
  onCataloguer: (id: string) => void
  onExtraire: (id: string) => void
  onVerifier: (id: string) => void
  onImporter: (id: string) => void
  loading: string | null
}) {
  const [expanded, setExpanded] = useState(false)
  const isLoading = loading === doc.id
  const cfg = STATUT_CONFIG[doc.statut] || STATUT_CONFIG.uploade
  const Icon = getFileIcon(doc.nom, doc.type_mime)
  const cat = doc.catalogue_json
  const ext = doc.extraction_json

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card overflow-hidden"
    >
      {/* En-tête de la carte */}
      <div className="flex items-start gap-3 p-4">
        <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-slate-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800 truncate">{doc.nom}</span>
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${cfg.color}`}>
              {cfg.label}
            </span>
            {cat?.pertinence_audit && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${PERTINENCE_BADGE[cat.pertinence_audit] || ''}`}>
                {cat.pertinence_audit}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {doc.type_detecte && (
              <span className="text-xs text-slate-500">{doc.type_detecte}</span>
            )}
            {doc.taille_octets && (
              <span className="text-xs text-slate-400">· {formatOctets(doc.taille_octets)}</span>
            )}
          </div>
          {doc.description_ia && (
            <p className="text-xs text-slate-600 mt-1 line-clamp-2">{doc.description_ia}</p>
          )}
          {doc.erreur && (
            <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              {doc.erreur}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Expand si catalogué */}
          {(cat || ext) && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          )}
          {/* Bouton Cataloguer */}
          {['uploade', 'erreur'].includes(doc.statut) && (
            <button
              onClick={() => onCataloguer(doc.id)}
              disabled={!!loading}
              className="text-xs px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
              Analyser
            </button>
          )}
          {/* Bouton Extraire */}
          {doc.statut === 'catalogue' && (
            <button
              onClick={() => onExtraire(doc.id)}
              disabled={!!loading}
              className="text-xs px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3" />}
              Extraire
            </button>
          )}
          {/* Bouton Vérifier */}
          {doc.statut === 'extrait' && (
            <button
              onClick={() => onVerifier(doc.id)}
              disabled={!!loading}
              className="text-xs px-2.5 py-1 rounded-lg bg-violet-50 text-violet-700 hover:bg-violet-100 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
              Vérifier
            </button>
          )}
          {/* Bouton Importer */}
          {doc.statut === 'verifie' && (
            <button
              onClick={() => onImporter(doc.id)}
              disabled={!!loading}
              className="text-xs px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              Importer
            </button>
          )}
          {/* Import sans vérification (skip) */}
          {doc.statut === 'extrait' && (
            <button
              onClick={() => onImporter(doc.id)}
              disabled={!!loading}
              title="Importer sans vérification"
              className="text-xs px-2 py-1 rounded-lg bg-slate-50 text-slate-500 hover:bg-slate-100 disabled:opacity-50 transition-colors"
            >
              ↓
            </button>
          )}
          {/* Importé */}
          {doc.statut === 'importe' && (
            <CheckCircle className="w-4 h-4 text-emerald-500" />
          )}
          {/* Supprimer */}
          <button
            onClick={() => onDelete(doc.id)}
            disabled={!!loading}
            className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Détails expandables */}
      <AnimatePresence>
        {expanded && (cat || ext) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-border"
          >
            <div className="px-4 py-3 bg-slate-50/50 space-y-3 text-xs">
              {/* Catalogue */}
              {cat && (
                <div className="space-y-1.5">
                  <p className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
                    Catalogue (Haiku)
                  </p>
                  {cat.parties && cat.parties.length > 0 && (
                    <p className="text-slate-600">
                      <span className="font-medium">Parties :</span> {cat.parties.join(', ')}
                    </p>
                  )}
                  {cat.dates && cat.dates.length > 0 && (
                    <p className="text-slate-600">
                      <span className="font-medium">Dates :</span> {cat.dates.join(', ')}
                    </p>
                  )}
                  {cat.montants_cles && cat.montants_cles.length > 0 && (
                    <p className="text-slate-600">
                      <span className="font-medium">Montants :</span> {cat.montants_cles.join(', ')}
                    </p>
                  )}
                </div>
              )}

              {/* Vérification */}
              {ext?.verification && (
                <div className="space-y-1.5">
                  <p className="font-semibold text-violet-600 uppercase tracking-wider text-[10px]">
                    Vérification (Sonnet) — score {Math.round((ext.verification.score_global ?? 0) * 100)}%
                  </p>
                  <p className="text-slate-600">{ext.verification.resume_verification}</p>
                  {ext.verification.lignes_verifiees && ext.verification.lignes_verifiees.some((l) => l.anomalie) && (
                    <div className="space-y-0.5">
                      {ext.verification.lignes_verifiees.filter((l) => l.anomalie).map((l) => (
                        <div key={l.index} className="flex items-start gap-1.5 text-amber-700 bg-amber-50 rounded p-1.5">
                          <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span>Ligne {l.index + 1} : {l.commentaire}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Extraction */}
              {ext && ext.lignes && ext.lignes.length > 0 && (
                <div className="space-y-1.5">
                  <p className="font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
                    Extraction (Opus) — {ext.nb_lignes} ligne{(ext.nb_lignes ?? 0) !== 1 ? 's' : ''} · {ext.type_sortie}
                  </p>
                  <div className="overflow-x-auto">
                    <table className="text-[10px] w-full border-collapse">
                      <thead>
                        <tr className="text-slate-400 border-b border-border">
                          {['Date', 'Compte', 'Libellé', 'Débit', 'Crédit', 'Réf.'].map((h) => (
                            <th key={h} className="text-left py-0.5 pr-2 font-medium">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {ext.lignes.slice(0, 8).map((l: any, i: number) => (
                          <tr key={i} className="border-b border-border/50 text-slate-600">
                            <td className="py-0.5 pr-2 whitespace-nowrap">{l.date || '—'}</td>
                            <td className="py-0.5 pr-2 font-mono">{l.compte || '—'}</td>
                            <td className="py-0.5 pr-2 max-w-[180px] truncate">{l.libelle}</td>
                            <td className="py-0.5 pr-2 text-right">{l.debit ? l.debit.toLocaleString('fr-FR') : ''}</td>
                            <td className="py-0.5 pr-2 text-right">{l.credit ? l.credit.toLocaleString('fr-FR') : ''}</td>
                            <td className="py-0.5 text-slate-400">{l.reference || ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(ext.lignes.length > 8) && (
                      <p className="text-slate-400 mt-1">… et {ext.lignes.length - 8} ligne(s) supplémentaire(s)</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ─── Pipeline steps indicator ─────────────────────────────────────────────────

function PipelineStep({
  step, label, active, done,
}: { step: number; label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors
        ${done ? 'bg-emerald-500 text-white' : active ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-400'}`}>
        {done ? '✓' : step}
      </div>
      <span className={`text-xs font-medium ${active ? 'text-primary-700' : done ? 'text-emerald-600' : 'text-slate-400'}`}>
        {label}
      </span>
    </div>
  )
}

// ─── Drop zone ───────────────────────────────────────────────────────────────

function DropZone({ onFiles, uploading }: {
  onFiles: (files: File[]) => void
  uploading: boolean
}) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length) onFiles(accepted)
  }, [onFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    disabled: uploading,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
        ${isDragActive ? 'border-primary-400 bg-primary-50' : 'border-border hover:border-primary-300 hover:bg-slate-50'}
        ${uploading ? 'opacity-50 cursor-default' : ''}`}
    >
      <input {...getInputProps()} />
      {uploading
        ? <Loader2 className="w-8 h-8 mx-auto mb-2 text-primary-500 animate-spin" />
        : <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragActive ? 'text-primary-500' : 'text-slate-300'}`} />
      }
      <p className="text-sm font-medium text-slate-600 mb-1">
        {uploading ? 'Upload en cours…' : 'Déposer vos documents ici ou cliquer pour parcourir'}
      </p>
      <p className="text-xs text-slate-400">
        PDF, images (JPG/PNG), Excel, CSV, Word — plusieurs fichiers à la fois
      </p>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function DossierBrut() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post, baseUrl } = useApi()
  const toast = useToast()
  const { projetActif } = useProjetStore()

  const [docs, setDocs] = useState<DocumentBrut[]>([])
  const [loadingDoc, setLoadingDoc] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [batchLoading, setBatchLoading] = useState<'cataloguer' | 'extraire' | 'verifier' | null>(null)
  const [loaded, setLoaded] = useState(false)

  const loadDocs = async () => {
    if (!projetId) return
    try {
      const data = await get(`/projets/${projetId}/dossier`)
      setDocs(data.documents || [])
    } catch (e: any) {
      toast.error('Impossible de charger le dossier : ' + e.message)
    } finally {
      setLoaded(true)
    }
  }

  useEffect(() => { loadDocs() }, [projetId])

  const handleFiles = async (files: File[]) => {
    if (!projetId) return
    setUploading(true)
    let uploaded = 0
    let failed = 0
    for (const file of files) {
      try {
        const form = new FormData()
        form.append('fichier', file)
        const res = await fetch(`${baseUrl}/projets/${projetId}/dossier/fichiers`, {
          method: 'POST',
          body: form,
        })
        if (!res.ok) throw new Error((await res.json()).detail || 'Erreur upload')
        uploaded++
      } catch (e: any) {
        failed++
        toast.error(`${file.name} : ${e.message}`)
      }
    }
    if (uploaded > 0) toast.success(`${uploaded} fichier(s) déposé(s).`)
    setUploading(false)
    await loadDocs()
  }

  const handleDelete = async (docId: string) => {
    if (!projetId) return
    const doc = docs.find((d) => d.id === docId)
    try {
      const res = await fetch(`${baseUrl}/projets/${projetId}/dossier/${docId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur suppression')
      setDocs((prev) => prev.filter((d) => d.id !== docId))
      toast.success(`${doc?.nom || 'Document'} supprimé.`)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleCataloguer = async (docId: string) => {
    if (!projetId) return
    setLoadingDoc(docId)
    try {
      const updated = await post(`/projets/${projetId}/dossier/${docId}/cataloguer`, {})
      setDocs((prev) => prev.map((d) => (d.id === docId ? updated : d)))
      toast.success(`Catalogué : ${updated.type_detecte}`)
    } catch (e: any) {
      toast.error(e.message)
      await loadDocs()
    } finally {
      setLoadingDoc(null)
    }
  }

  const handleExtraire = async (docId: string) => {
    if (!projetId) return
    setLoadingDoc(docId)
    try {
      const updated = await post(`/projets/${projetId}/dossier/${docId}/extraire`, {})
      setDocs((prev) => prev.map((d) => (d.id === docId ? updated : d)))
      const nb = updated.extraction_json?.nb_lignes ?? 0
      toast.success(`Extrait : ${nb} ligne(s) comptable(s).`)
    } catch (e: any) {
      toast.error(e.message)
      await loadDocs()
    } finally {
      setLoadingDoc(null)
    }
  }

  const handleImporter = async (docId: string) => {
    if (!projetId) return
    setLoadingDoc(docId)
    try {
      const result = await post(`/projets/${projetId}/dossier/${docId}/importer`, {})
      await loadDocs()
      toast.success(`Importé : ${result.nb_donnees_extraites} donnée(s) sourcée(s) — ${result.type_document}.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoadingDoc(null)
    }
  }

  const handleCataloguerTous = async () => {
    if (!projetId) return
    setBatchLoading('cataloguer')
    try {
      const result = await post(`/projets/${projetId}/dossier/cataloguer-tous`, {})
      setDocs(result.documents || [])
      toast.success(`${result.nb_ok} document(s) catalogué(s).${result.nb_erreur > 0 ? ` ${result.nb_erreur} erreur(s).` : ''}`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setBatchLoading(null)
    }
  }

  const handleExtraireTous = async () => {
    if (!projetId) return
    setBatchLoading('extraire')
    try {
      const result = await post(`/projets/${projetId}/dossier/extraire-tous`, {})
      setDocs(result.documents || [])
      toast.success(`${result.nb_ok} document(s) extrait(s).${result.nb_erreur > 0 ? ` ${result.nb_erreur} erreur(s).` : ''}`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setBatchLoading(null)
    }
  }

  const handleVerifier = async (docId: string) => {
    if (!projetId) return
    setLoadingDoc(docId)
    try {
      const updated = await post(`/projets/${projetId}/dossier/${docId}/verifier`, {})
      setDocs((prev) => prev.map((d) => (d.id === docId ? updated : d)))
      const score = updated.extraction_json?.verification?.score_global ?? 0
      const anomalies = (updated.extraction_json?.verification?.lignes_verifiees ?? []).filter((l: any) => l.anomalie).length
      toast.success(`Vérifié — score ${Math.round(score * 100)}%${anomalies > 0 ? ` · ${anomalies} anomalie(s)` : ' — aucune anomalie.'}`)
    } catch (e: any) {
      toast.error(e.message)
      await loadDocs()
    } finally {
      setLoadingDoc(null)
    }
  }

  const handleVerifierTous = async () => {
    if (!projetId) return
    setBatchLoading('verifier')
    try {
      const result = await post(`/projets/${projetId}/dossier/verifier-tous`, {})
      setDocs(result.documents || [])
      toast.success(`${result.nb_ok} document(s) vérifié(s).${result.nb_erreur > 0 ? ` ${result.nb_erreur} erreur(s).` : ''}`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setBatchLoading(null)
    }
  }

  // Stats
  const nbUploade   = docs.filter((d) => d.statut === 'uploade').length
  const nbCatalogue = docs.filter((d) => d.statut === 'catalogue').length
  const nbExtrait   = docs.filter((d) => d.statut === 'extrait').length
  const nbVerifie   = docs.filter((d) => d.statut === 'verifie').length
  const nbImporte   = docs.filter((d) => d.statut === 'importe').length
  const nbErreur    = docs.filter((d) => d.statut === 'erreur').length

  const pipelineStep = nbImporte > 0 ? 4
    : nbVerifie > 0 ? 3
    : nbExtrait > 0 ? 2
    : nbCatalogue > 0 ? 1
    : 0

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dossier brut"
        subtitle={`${docs.length} document(s) — pipeline IA : Haiku → Sonnet`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(`/projet/${projetId}/ingestion`)}
              className="btn-secondary"
            >
              <ArrowLeft className="w-4 h-4" />
              Retour à l'ingestion
            </button>
            {nbUploade > 0 && (
              <button
                onClick={handleCataloguerTous}
                disabled={!!batchLoading}
                className="btn-secondary text-blue-700 border-blue-200 hover:bg-blue-50"
              >
                {batchLoading === 'cataloguer'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Wand2 className="w-4 h-4" />}
                Cataloguer tous ({nbUploade})
              </button>
            )}
            {nbCatalogue > 0 && (
              <button
                onClick={handleExtraireTous}
                disabled={!!batchLoading}
                className="btn-secondary text-amber-700 border-amber-200 hover:bg-amber-50"
              >
                {batchLoading === 'extraire'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Database className="w-4 h-4" />}
                Extraire tous ({nbCatalogue})
              </button>
            )}
            {nbExtrait > 0 && (
              <button
                onClick={handleVerifierTous}
                disabled={!!batchLoading}
                className="btn-secondary text-violet-700 border-violet-200 hover:bg-violet-50"
              >
                {batchLoading === 'verifier'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <ShieldCheck className="w-4 h-4" />}
                Vérifier tous ({nbExtrait})
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Pipeline steps */}
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <PipelineStep step={1} label="Dépôt" active={nbUploade > 0} done={docs.length > 0 && nbUploade === 0} />
            <div className="h-px flex-1 bg-border" />
            <PipelineStep step={2} label="Catalogue (Haiku)" active={nbCatalogue > 0} done={pipelineStep >= 2} />
            <div className="h-px flex-1 bg-border" />
            <PipelineStep step={3} label="Extraction (Opus)" active={nbExtrait > 0} done={pipelineStep >= 3} />
            <div className="h-px flex-1 bg-border" />
            <PipelineStep step={4} label="Vérification (Sonnet)" active={nbVerifie > 0} done={pipelineStep >= 4} />
            <div className="h-px flex-1 bg-border" />
            <PipelineStep step={5} label="Import mission" active={nbImporte > 0} done={nbImporte > 0 && nbVerifie === 0 && nbExtrait === 0} />
          </div>

          {/* Stats compactes */}
          {docs.length > 0 && (
            <div className="flex gap-4 mt-4 pt-3 border-t border-border text-xs">
              {nbUploade > 0 && <span className="text-slate-500">{nbUploade} déposé(s)</span>}
              {nbCatalogue > 0 && <span className="text-blue-600">{nbCatalogue} catalogué(s)</span>}
              {nbExtrait > 0 && <span className="text-amber-600">{nbExtrait} extrait(s)</span>}
              {nbVerifie > 0 && <span className="text-violet-600">{nbVerifie} vérifié(s) ✓</span>}
              {nbImporte > 0 && <span className="text-emerald-600">{nbImporte} importé(s) ✓</span>}
              {nbErreur > 0 && <span className="text-red-600">{nbErreur} erreur(s)</span>}
            </div>
          )}
        </div>

        {/* Explication */}
        <div className="flex items-start gap-3 p-3.5 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-800">
          <Wand2 className="w-4 h-4 mt-0.5 flex-shrink-0 text-blue-500" />
          <div className="space-y-0.5">
            <p className="font-semibold">Comment ça fonctionne ?</p>
            <p>
              <span className="font-medium">1. Déposez</span> vos documents bruts (factures, relevés, contrats, attestations…).
              {' '}<span className="font-medium">2. Haiku</span> catalogue chaque fichier (type, parties, dates, montants clés).
              {' '}<span className="font-medium">3. Opus</span> extrait les écritures comptables structurées.
              {' '}<span className="font-medium">4. Sonnet</span> vérifie ligne par ligne l'extraction contre le source.
              {' '}<span className="font-medium">5. Importez</span> — les données vérifiées entrent dans Probare avec leur DonneeSourcee complète.
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <DropZone onFiles={handleFiles} uploading={uploading} />

        {/* Liste des documents */}
        {!loaded ? (
          <div className="flex justify-center py-12"><Spinner size="lg" /></div>
        ) : docs.length === 0 ? (
          <EmptyState
            icon={Upload}
            title="Aucun document déposé"
            description="Déposez vos documents bruts ci-dessus pour démarrer le pipeline IA."
          />
        ) : (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
              {docs.length} document{docs.length !== 1 ? 's' : ''}
            </p>
            {docs.map((doc) => (
              <DocCard
                key={doc.id}
                doc={doc}
                onDelete={handleDelete}
                onCataloguer={handleCataloguer}
                onExtraire={handleExtraire}
                onVerifier={handleVerifier}
                onImporter={handleImporter}
                loading={loadingDoc}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
