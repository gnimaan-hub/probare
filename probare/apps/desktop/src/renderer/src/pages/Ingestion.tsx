import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload, CheckCircle, ArrowRight, Info, X, AlertCircle, FileText,
  FileSpreadsheet, Loader2, Layers, Scissors, File, ChevronDown, ChevronRight,
  Sparkles, AlertTriangle
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { StepFooter } from '../components/mission/StepFooter'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useMissionProgress } from '../hooks/useMissionProgress'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatDate } from '../lib/utils'
import { stepParRoute } from '../lib/mission'

// ─── Types ────────────────────────────────────────────────────────────────────

interface FichierImporte {
  id: string
  nom: string
  type: string
  type_document: string
  nature_ia?: string
  description_ia?: string
  correspond_a?: string
  statut_checklist?: string  // "valide" | "non_attendu" | "analyse_en_cours"
  onglets_disponibles?: string[]
  onglet?: string
  importe_le: string
  analyse_ia?: any
}

interface DocRequis {
  type: string
  label: string
  requis: boolean
  importe: boolean
  nb_fichiers: number
  description?: string
}

interface OngletAnalyse {
  nom_onglet: string
  nom?: string
  nature?: string
  type_comptable?: string
  description?: string
  correspond_a?: string
  confiance?: number
  recommande_import?: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getFileIcon(nom: string) {
  const ext = nom.split('.').pop()?.toLowerCase()
  if (ext && ['xlsx', 'xls', 'xlsm', 'csv'].includes(ext)) return FileSpreadsheet
  if (ext && ['pdf', 'doc', 'docx'].includes(ext)) return FileText
  return File
}

function statutBadge(statut?: string, correspond_a?: string) {
  if (statut === 'analyse_en_cours') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
      <Loader2 className="w-3 h-3 animate-spin" />
      Analyse…
    </span>
  )
  if (statut === 'valide' && correspond_a) return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
      <CheckCircle className="w-3 h-3" />
      Validé — {correspond_a.replace(/_/g, ' ')}
    </span>
  )
  if (statut === 'non_attendu') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-xs font-medium">
      <Info className="w-3 h-3" />
      Référencé
    </span>
  )
  return null
}

// ─── Checklist ────────────────────────────────────────────────────────────────

function ChecklistSection({ docs }: { docs: DocRequis[] }) {
  const [open, setOpen] = useState(true)
  if (!docs.length) return null

  const valides = docs.filter(d => d.importe).length
  const requis = docs.filter(d => d.requis).length
  const requisValides = docs.filter(d => d.requis && d.importe).length

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            requisValides === requis ? 'bg-emerald-100' : 'bg-amber-100'
          }`}>
            {requisValides === requis
              ? <CheckCircle className="w-4 h-4 text-emerald-600" />
              : <AlertTriangle className="w-4 h-4 text-amber-600" />
            }
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-slate-900">Documents attendus</p>
            <p className="text-xs text-slate-500">{valides}/{docs.length} importés · {requisValides}/{requis} requis validés</p>
          </div>
        </div>
        {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            className="overflow-hidden border-t border-border"
          >
            <div className="divide-y divide-border">
              {docs.map(doc => (
                <div key={doc.type} className="flex items-start gap-3 px-4 py-3">
                  <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                    doc.importe ? 'bg-emerald-100' : doc.requis ? 'bg-red-100' : 'bg-slate-100'
                  }`}>
                    {doc.importe
                      ? <CheckCircle className="w-3 h-3 text-emerald-600" />
                      : doc.requis
                        ? <AlertCircle className="w-3 h-3 text-red-500" />
                        : <div className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-800">{doc.label}</span>
                      {!doc.requis && (
                        <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">optionnel</span>
                      )}
                      {doc.nb_fichiers > 0 && (
                        <span className="text-xs text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                          {doc.nb_fichiers} fichier{doc.nb_fichiers > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    {doc.description && (
                      <p className="text-xs text-slate-400 mt-0.5">{doc.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Zone de dépôt universelle ────────────────────────────────────────────────

function DropZoneUniverselle({ onFiles, uploading }: {
  onFiles: (files: File[]) => void
  uploading: boolean
}) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length) onFiles(acceptedFiles)
  }, [onFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
  })

  return (
    <div
      {...getRootProps()}
      className={`relative flex flex-col items-center justify-center gap-3 p-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all ${
        isDragActive
          ? 'border-primary-400 bg-primary-50 scale-[1.01]'
          : uploading
            ? 'border-slate-200 bg-slate-50 cursor-not-allowed opacity-60'
            : 'border-slate-200 bg-slate-50/50 hover:border-primary-300 hover:bg-primary-50/30'
      }`}
    >
      <input {...getInputProps()} />
      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
        isDragActive ? 'bg-primary-100' : 'bg-white shadow-sm'
      }`}>
        {uploading
          ? <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          : <Upload className={`w-6 h-6 ${isDragActive ? 'text-primary-600' : 'text-slate-400'}`} />
        }
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-700">
          {uploading ? 'Import et analyse en cours…' : isDragActive ? 'Déposez ici' : 'Déposez vos documents'}
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Excel · CSV · PDF · Word · Image — tout format accepté
        </p>
      </div>
      {!uploading && (
        <span className="text-xs text-primary-600 font-medium underline">
          ou cliquez pour parcourir
        </span>
      )}
    </div>
  )
}

// ─── Carte fichier importé ────────────────────────────────────────────────────

function FichierCard({
  fichier,
  onOnglets,
  onDecouper,
  onDelete,
}: {
  fichier: FichierImporte
  onOnglets: () => void
  onDecouper: () => void
  onDelete: () => void
}) {
  const Icon = getFileIcon(fichier.nom)
  const ext = fichier.nom.split('.').pop()?.toLowerCase()
  const isExcel = ext && ['xlsx', 'xls', 'xlsm', 'csv'].includes(ext)
  const isTextDoc = ext && ['pdf', 'doc', 'docx'].includes(ext)
  const isOngletFils = Boolean(fichier.onglet)
  const hasOnglets = (fichier.onglets_disponibles?.length ?? 0) > 1

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className={`card p-4 flex items-start gap-3 ${
        fichier.statut_checklist === 'valide'
          ? 'border-l-2 border-l-emerald-400'
          : fichier.statut_checklist === 'analyse_en_cours'
            ? 'border-l-2 border-l-amber-300'
            : ''
      }`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isExcel ? 'bg-emerald-50' : isTextDoc ? 'bg-blue-50' : 'bg-slate-100'
      }`}>
        <Icon className={`w-5 h-5 ${
          isExcel ? 'text-emerald-600' : isTextDoc ? 'text-blue-600' : 'text-slate-500'
        }`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{fichier.nom}</p>
            {fichier.onglet && (
              <p className="text-xs text-slate-400">Onglet : {fichier.onglet}</p>
            )}
            <p className="text-xs text-slate-400">{formatDate(fichier.importe_le)}</p>
          </div>
          <button
            onClick={onDelete}
            className="flex-shrink-0 p-1 rounded hover:bg-red-50 hover:text-red-500 text-slate-300 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          {statutBadge(fichier.statut_checklist, fichier.correspond_a)}
          {fichier.nature_ia && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 text-xs">
              <Sparkles className="w-3 h-3" />
              {fichier.nature_ia.replace(/_/g, ' ')}
            </span>
          )}
        </div>

        {fichier.description_ia && (
          <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">{fichier.description_ia}</p>
        )}

        {/* Actions spécifiques */}
        <div className="mt-3 flex flex-wrap gap-2">
          {isExcel && !isOngletFils && hasOnglets && (
            <button
              onClick={onOnglets}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors"
            >
              <Layers className="w-3.5 h-3.5" />
              Onglets ({fichier.onglets_disponibles?.length})
            </button>
          )}
          {isTextDoc && (
            <button
              onClick={onDecouper}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-violet-50 text-violet-700 hover:bg-violet-100 transition-colors"
            >
              <Scissors className="w-3.5 h-3.5" />
              Détecter pièces
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Modal liasse ─────────────────────────────────────────────────────────────

function LiasseModal({ fichier, resultat, onClose }: {
  fichier: FichierImporte
  resultat: any
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col"
      >
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div>
            <h3 className="font-semibold text-slate-900">Analyse de la liasse</h3>
            <p className="text-xs text-slate-500 mt-0.5">{fichier.nom}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {resultat.description_globale && (
            <div className="bg-violet-50 rounded-xl p-3 text-sm text-violet-800">
              <Sparkles className="w-4 h-4 inline mr-1.5" />
              {resultat.description_globale}
            </div>
          )}
          {!resultat.est_liasse ? (
            <div className="text-center py-6 text-sm text-slate-500">
              Ce document semble être un document unique, non une liasse.
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">
                {resultat.nb_documents} pièce{resultat.nb_documents > 1 ? 's' : ''} identifiée{resultat.nb_documents > 1 ? 's' : ''}
              </p>
              {(resultat.documents || []).map((doc: any, i: number) => (
                <div key={i} className="border border-border rounded-xl p-3 space-y-1">
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-bold text-slate-400 bg-slate-100 rounded px-1.5 py-0.5 flex-shrink-0">
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{doc.titre}</p>
                      {doc.reference && (
                        <p className="text-xs text-slate-400">Réf. {doc.reference}</p>
                      )}
                    </div>
                  </div>
                  {doc.description && (
                    <p className="text-xs text-slate-500 ml-7">{doc.description}</p>
                  )}
                  {doc.type && (
                    <span className="ml-7 inline-block text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                      {doc.type.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              ))}
              <p className="text-xs text-slate-400 pt-2">
                Note : Probare référence chaque pièce identifiée pour les travaux substantifs.
                Le découpage physique sera disponible dans une prochaine version.
              </p>
            </>
          )}
        </div>

        <div className="p-5 border-t border-border flex justify-end">
          <button onClick={onClose} className="btn-primary">Fermer</button>
        </div>
      </motion.div>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function Ingestion() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post, del, uploadFile } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()
  useSyncProjet()

  const [fichiers, setFichiers] = useState<FichierImporte[]>([])
  const [documentsRequis, setDocumentsRequis] = useState<DocRequis[]>([])
  const [uploading, setUploading] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const { progression } = useMissionProgress(projetId)
  const step = stepParRoute('ingestion')!

  // Modals
  const [ongletsModal, setOngletsModal] = useState<{ fichier: FichierImporte; data: any } | null>(null)
  const [liasseModal, setLiasseModal] = useState<{ fichier: FichierImporte; resultat: any } | null>(null)

  const loadAll = useCallback(async () => {
    if (!projetId) return
    try {
      const [fichiersRes, checkRes] = await Promise.all([
        get(`/projets/${projetId}/fichiers`),
        get(`/projets/${projetId}/documents-requis`),
      ])
      setFichiers(fichiersRes.fichiers || [])
      setDocumentsRequis(checkRes.checklist || [])
    } catch (e: any) {
      toast.error(e.message)
    }
  }, [projetId])

  useEffect(() => { loadAll() }, [loadAll])

  // ── Upload ────────────────────────────────────────────────────────────────

  const handleFiles = async (files: File[]) => {
    if (!projetId) return
    setUploading(true)
    for (const file of files) {
      try {
        const fd = new FormData()
        fd.append('fichier', file)
        fd.append('type_fichier', 'grand_livre')  // chemin normal → Haiku corrige via update_fichier_ia
        const res = await uploadFile(`/projets/${projetId}/fichiers`, fd)

        // Recharger immédiatement pour afficher le fichier (même avec analyse en cours)
        await loadAll()

        // Si Excel multi-onglets, proposer le sélecteur d'onglets
        if (res.onglets_disponibles && res.onglets_disponibles.length > 1) {
          const fichiersActuels = await get(`/projets/${projetId}/fichiers`)
          const f = (fichiersActuels.fichiers || []).find((x: FichierImporte) => x.id === res.fichier_source_id)
          if (f) {
            await handleOuvreOnglets({ ...f, onglets_disponibles: res.onglets_disponibles })
          }
        }
      } catch (e: any) {
        toast.error(`Erreur upload "${file.name}" : ${e.message}`)
      }
    }
    setUploading(false)
    await loadAll()
  }

  // ── Onglets Excel ─────────────────────────────────────────────────────────

  const handleOuvreOnglets = async (fichier: FichierImporte) => {
    if (!projetId) return
    try {
      const data = await get(`/projets/${projetId}/fichiers/${fichier.id}/onglets`)
      setOngletsModal({ fichier, data })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleImportOnglets = async (fichier_id: string, selections: string[]) => {
    if (!projetId) return
    for (const sheet_name of selections) {
      await post(`/projets/${projetId}/fichiers/${fichier_id}/importer-onglet`, { sheet_name })
    }
    toast.success(`${selections.length} onglet${selections.length > 1 ? 's' : ''} importé${selections.length > 1 ? 's' : ''}.`)
    await loadAll()
  }

  // ── Liasse PDF/Word ───────────────────────────────────────────────────────

  const handleDecouper = async (fichier: FichierImporte) => {
    if (!projetId) return
    try {
      const resultat = await post(`/projets/${projetId}/fichiers/${fichier.id}/decouper-liasse`, {})
      setLiasseModal({ fichier, resultat })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  // ── Suppression ───────────────────────────────────────────────────────────

  const handleDelete = async (fichierId: string) => {
    if (!projetId) return
    try {
      await del(`/projets/${projetId}/fichiers/${fichierId}`)
      await loadAll()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  // ── Transition pipeline ───────────────────────────────────────────────────

  const manquantsRequis = documentsRequis.filter(d => d.requis && !d.importe)
  const canPasser = manquantsRequis.length === 0 && fichiers.length > 0

  const handlePasserExtraction = async () => {
    if (!projetId) return
    setTransitioning(true)
    try {
      const updated = await post(`/projets/${projetId}/transition`, {
        vers: 'planification',
        acteur: 'utilisateur',
      })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/planification`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const etatCourant = projetActif?.etat_courant || 'ingestion'
  const locked = ['travaux_substantifs', 'controles', 'revue', 'generation', 'opinion'].includes(etatCourant)

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Ingestion des documents"
        subtitle={projetActif?.nom}
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-5">

          {locked && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg border bg-emerald-50 border-emerald-200 text-emerald-800 text-xs">
              <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p>Les contrôles ont été lancés. La liste des documents est figée.</p>
            </div>
          )}

          {/* Checklist */}
          <ChecklistSection docs={documentsRequis} />

          {/* Drop zone */}
          {!locked && (
            <DropZoneUniverselle onFiles={handleFiles} uploading={uploading} />
          )}

          {!canPasser && fichiers.length > 0 && !locked && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg border bg-amber-50 border-amber-200 text-amber-800 text-xs">
              <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <p>
                Documents requis manquants :{' '}
                <strong>{manquantsRequis.map(d => d.label).join(', ')}</strong>.
                Importez-les pour continuer.
              </p>
            </div>
          )}

          {/* Liste des fichiers */}
          {fichiers.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {fichiers.length} document{fichiers.length > 1 ? 's' : ''} importé{fichiers.length > 1 ? 's' : ''}
              </h3>
              <AnimatePresence initial={false}>
                {fichiers.map(f => (
                  <FichierCard
                    key={f.id}
                    fichier={f}
                    onOnglets={() => handleOuvreOnglets(f)}
                    onDecouper={() => handleDecouper(f)}
                    onDelete={() => handleDelete(f.id)}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}

          {fichiers.length === 0 && !uploading && (
            <div className="text-center py-6 text-sm text-slate-400">
              Aucun document importé.
            </div>
          )}

          {!locked && (
            <StepFooter
              projetId={projetId!}
              step={step}
              progression={progression}
              onAdvance={handlePasserExtraction}
              advancing={transitioning}
              blockedReason={
                !canPasser
                  ? (fichiers.length === 0
                      ? 'Importez au moins un document comptable.'
                      : `Documents requis manquants : ${manquantsRequis.map(d => d.label).join(', ')}.`)
                  : undefined
              }
            />
          )}
        </div>
      </div>

      {/* Modal onglets */}
      {ongletsModal && (
        <OngletsModalWrapper
          fichier={ongletsModal.fichier}
          data={ongletsModal.data}
          projetId={projetId!}
          onClose={() => setOngletsModal(null)}
          onImport={handleImportOnglets}
        />
      )}

      {/* Modal liasse */}
      {liasseModal && (
        <LiasseModal
          fichier={liasseModal.fichier}
          resultat={liasseModal.resultat}
          onClose={() => setLiasseModal(null)}
        />
      )}
    </div>
  )
}

// ─── Wrapper modal onglets (a accès au projetId) ──────────────────────────────

function OngletsModalWrapper({ fichier, data, projetId, onClose, onImport }: {
  fichier: FichierImporte
  data: any
  projetId: string
  onClose: () => void
  onImport: (fichier_id: string, selections: string[]) => Promise<void>
}) {
  const toast = useToast()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [importing, setImporting] = useState(false)

  const onglets: any[] = data?.onglets || []
  const analyseIa: OngletAnalyse[] = data?.analyse_ia || []

  const toggleOnglet = (nom: string) => {
    setSelected(s => {
      const next = new Set(s)
      if (next.has(nom)) next.delete(nom)
      else next.add(nom)
      return next
    })
  }

  const handleImport = async () => {
    if (!selected.size) return
    setImporting(true)
    try {
      await onImport(fichier.id, Array.from(selected))
      onClose()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col"
      >
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div>
            <h3 className="font-semibold text-slate-900">Onglets détectés</h3>
            <p className="text-xs text-slate-500 mt-0.5">{fichier.nom}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        {onglets.length > 0 && (
          <div className="flex items-center justify-between px-5 py-2 border-b border-border bg-slate-50">
            <span className="text-xs text-slate-500">{selected.size}/{onglets.length} sélectionné{selected.size > 1 ? 's' : ''}</span>
            <button
              onClick={() => {
                if (selected.size === onglets.length) {
                  setSelected(new Set())
                } else {
                  setSelected(new Set(onglets.map((o: any) => o.nom)))
                }
              }}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              {selected.size === onglets.length ? 'Désélectionner tout' : 'Sélectionner tout'}
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-5 space-y-2">
          {onglets.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">Aucun onglet à afficher.</p>
          ) : onglets.map((o: any) => {
            const ia = analyseIa.find(a => (a.nom_onglet || a.nom) === o.nom)
            const isSelected = selected.has(o.nom)
            return (
              <button
                key={o.nom}
                onClick={() => toggleOnglet(o.nom)}
                className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                  isSelected ? 'border-primary-400 bg-primary-50' : 'border-border hover:border-slate-300'
                }`}
              >
                <div className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border-2 ${
                  isSelected ? 'border-primary-500 bg-primary-500' : 'border-slate-300'
                }`}>
                  {isSelected && <div className="w-2 h-2 bg-white rounded-sm" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">{o.nom}</p>
                  {ia && (
                    <>
                      {ia.description && <p className="text-xs text-slate-500 mt-0.5">{ia.description}</p>}
                      <div className="mt-1 flex gap-1.5 flex-wrap">
                        {ia.nature && (
                          <span className="text-xs bg-violet-50 text-violet-700 px-1.5 py-0.5 rounded">
                            {ia.nature.replace(/_/g, ' ')}
                          </span>
                        )}
                        {ia.correspond_a && (
                          <span className="text-xs bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded">
                            → {ia.correspond_a.replace(/_/g, ' ')}
                          </span>
                        )}
                        {ia.recommande_import && (
                          <span className="text-xs bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded">
                            recommandé
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </button>
            )
          })}
        </div>

        <div className="p-5 border-t border-border flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary" disabled={importing}>Annuler</button>
          <button
            onClick={handleImport}
            disabled={!selected.size || importing}
            className="btn-primary"
          >
            {importing ? <Spinner size="sm" /> : <Layers className="w-4 h-4" />}
            Importer {selected.size > 0 ? `(${selected.size})` : ''}
          </button>
        </div>
      </motion.div>
    </div>
  )
}
