import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, FolderOpen, Clock, CheckCircle, AlertTriangle, Trash2, X,
  Building2, Search, Archive, Download, Upload
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useApi, authHeaders } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type Projet } from '../stores/projetStore'
import { formatDate, formatMontant, getEtatIndex, ETATS_PIPELINE } from '../lib/utils'

function EtatBadge({ etat }: { etat: string }) {
  const idx = getEtatIndex(etat)
  const step = ETATS_PIPELINE[idx]
  const isComplete = etat === 'opinion'
  const colors = isComplete
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : 'bg-primary-50 text-primary-700 border-primary-200'
  return (
    <span className={`badge border ${colors}`}>
      {isComplete ? <CheckCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
      {step?.label || etat}
    </span>
  )
}

function ProjetCard({ projet, onClick, onDelete, onSave }: {
  projet: Projet
  onClick: () => void
  onDelete: () => void
  onSave: () => void
}) {
  const idx = getEtatIndex(projet.etat_courant)
  const progress = Math.round(((idx + 1) / ETATS_PIPELINE.length) * 100)
  const isArchived = (projet as any).archive === 1 || (projet as any).archive === true

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
      onClick={onClick}
      className={`card-hover p-5 cursor-pointer group relative ${isArchived ? 'opacity-70' : ''}`}
    >
      {/* Actions au survol */}
      <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
        <button
          onClick={(e) => { e.stopPropagation(); onSave() }}
          title="Sauvegarder (ZIP)"
          className="p-1.5 rounded-lg text-slate-300 hover:text-primary-600 hover:bg-primary-50"
        >
          <Download className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          title="Supprimer"
          className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 pr-16">
          <div className="flex items-center gap-1.5">
            <h3 className="font-semibold text-slate-900 group-hover:text-primary-700 transition-colors truncate">
              {projet.nom}
            </h3>
            {isArchived && (
              <span className="badge bg-slate-100 text-slate-500 text-xs flex-shrink-0">
                <Archive className="w-2.5 h-2.5" />
                Archivé
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            {projet.client || 'Client non renseigné'} · {projet.exercice || 'N/A'}
          </p>
        </div>
        <EtatBadge etat={projet.etat_courant} />
      </div>

      {/* Barre de progression */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Progression</span>
          <span>{progress}%</span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
            className="h-full bg-primary-500 rounded-full"
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>
          Seuil : {projet.seuil_signification
            ? formatMontant(projet.seuil_signification)
            : 'à définir en planification'}
        </span>
        <span>{formatDate(projet.cree_le)}</span>
      </div>
    </motion.div>
  )
}

interface ClientSuggestion {
  id: string
  nom: string
  nif: string
  nb_fichiers_permanents: number
}

interface CreateDialogProps {
  open: boolean
  onClose: () => void
  onCreated: (projet: Projet) => void
}

function CreateDialog({ open, onClose, onCreated }: CreateDialogProps) {
  const { post, get } = useApi()
  const toast = useToast()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    nom: '',
    client: '',
    nif: '',
    exercice: new Date().getFullYear().toString(),
    consentement_client: false,
    nature_mission: 'contractuelle' as 'contractuelle' | 'legale',
    client_id: null as string | null,
  })
  const [nifSearch, setNifSearch] = useState('')
  const [suggestions, setSuggestions] = useState<ClientSuggestion[]>([])
  const [clientTrouve, setClientTrouve] = useState<ClientSuggestion | null>(null)
  const [searchingClient, setSearchingClient] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showRestore, setShowRestore] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canSubmit = form.nom.trim() && form.client.trim() && form.nif.trim() && form.exercice.trim()

  // Recherche client par NIF avec debounce
  const handleNifChange = (val: string) => {
    setNifSearch(val)
    setForm((f) => ({ ...f, nif: val, client_id: null }))
    setClientTrouve(null)
    setSuggestions([])
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (val.length < 3) return
    searchTimer.current = setTimeout(async () => {
      setSearchingClient(true)
      try {
        const data = await get(`/clients?q=${encodeURIComponent(val)}`)
        const clients: ClientSuggestion[] = data.clients || []
        const exact = clients.find((c) => c.nif === val)
        if (exact) {
          setClientTrouve(exact)
          setForm((f) => ({ ...f, client: exact.nom, nif: exact.nif, client_id: exact.id }))
          setSuggestions([])
        } else {
          setSuggestions(clients.slice(0, 4))
        }
      } catch { /* silencieux */ } finally {
        setSearchingClient(false)
      }
    }, 350)
  }

  const selectClient = (c: ClientSuggestion) => {
    setClientTrouve(c)
    setNifSearch(c.nif)
    setForm((f) => ({ ...f, client: c.nom, nif: c.nif, client_id: c.id }))
    setSuggestions([])
  }

  const clearClient = () => {
    setClientTrouve(null)
    setNifSearch('')
    setForm((f) => ({ ...f, client: '', nif: '', client_id: null }))
    setSuggestions([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    try {
      const payload: any = { ...form }
      // Si nouveau client (pas trouvé), le créer d'abord
      if (!form.client_id) {
        try {
          const newClient = await post('/clients', { nom: form.client, nif: form.nif })
          payload.client_id = newClient.id
        } catch { /* NIF déjà existant — liaison ignorée */ }
      }
      const projet = await post('/projets', payload)
      onCreated(projet)
      toast.success(`Mission « ${projet.nom} » créée.`)
      onClose()
      resetForm()
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setForm({ nom: '', client: '', nif: '', exercice: new Date().getFullYear().toString(),
      consentement_client: false, nature_mission: 'contractuelle', client_id: null })
    setNifSearch('')
    setClientTrouve(null)
    setSuggestions([])
  }

  const handleRestore = async (file: File) => {
    setRestoring(true)
    const formData = new FormData()
    formData.append('archive', file)
    try {
      const apiBase = (window as any).__PROBARE_API_BASE__ || 'http://127.0.0.1:8765/api'
      const response = await fetch(`${apiBase}/projets/restaurer`, { method: 'POST', headers: authHeaders(), body: formData })
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(err.detail || response.statusText)
      }
      const result = await response.json()
      toast.success(result.message || 'Dossier restauré.')
      onClose()
      resetForm()
      window.location.reload()
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setRestoring(false)
    }
  }

  if (!open) return null

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => e.target === e.currentTarget && (onClose(), resetForm())}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 12 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-2xl shadow-modal w-full max-w-md max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-border sticky top-0 bg-white z-10">
              <h2 className="font-semibold text-slate-900">Nouvelle mission d'audit</h2>
              <button onClick={() => { onClose(); resetForm() }} className="btn-ghost p-1.5 rounded-lg">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">

              {/* ── Nature de mission ── */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Type de mission
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { val: 'contractuelle', label: 'Contractuelle', desc: 'Périmètre négocié avec le client' },
                    { val: 'legale', label: 'Légale', desc: 'Commissariat aux comptes (V2)' },
                  ].map(({ val, label, desc }) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, nature_mission: val as any }))}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        form.nature_mission === val
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-border text-slate-500 hover:border-slate-300'
                      } ${val === 'legale' ? 'opacity-60 cursor-not-allowed' : ''}`}
                      disabled={val === 'legale'}
                    >
                      <p className="text-sm font-medium">{label}</p>
                      <p className="text-xs mt-0.5 opacity-75">{desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Client ── */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Client — NIF <span className="text-red-500">*</span>
                </label>

                {clientTrouve ? (
                  <div className="flex items-center gap-2 p-3 rounded-xl border border-emerald-300 bg-emerald-50">
                    <Building2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-emerald-800">{clientTrouve.nom}</p>
                      <p className="text-xs text-emerald-600">
                        NIF : {clientTrouve.nif} ·{' '}
                        {clientTrouve.nb_fichiers_permanents > 0
                          ? `${clientTrouve.nb_fichiers_permanents} doc. permanent${clientTrouve.nb_fichiers_permanents > 1 ? 's' : ''} disponible${clientTrouve.nb_fichiers_permanents > 1 ? 's' : ''}`
                          : 'Dossier permanent vide'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/dossiers-permanents/${clientTrouve.id}`)}
                      className="text-xs text-emerald-700 underline hover:no-underline flex-shrink-0"
                    >
                      Voir
                    </button>
                    <button type="button" onClick={clearClient}
                      className="p-1 rounded text-emerald-500 hover:bg-emerald-100">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      {searchingClient && (
                        <Spinner size="sm" className="absolute right-3 top-1/2 -translate-y-1/2" />
                      )}
                      <input
                        className="input-field pl-9"
                        placeholder="Saisir le NIF pour trouver ou créer le client"
                        value={nifSearch}
                        onChange={(e) => handleNifChange(e.target.value)}
                        autoFocus
                      />
                    </div>
                    {suggestions.length > 0 && (
                      <div className="absolute z-20 left-0 right-0 mt-1 bg-white border border-border rounded-xl shadow-lg overflow-hidden">
                        {suggestions.map((c) => (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => selectClient(c)}
                            className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-slate-50 transition-colors text-left"
                          >
                            <Building2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-700 truncate">{c.nom}</p>
                              <p className="text-xs text-slate-400">NIF : {c.nif}</p>
                            </div>
                            {c.nb_fichiers_permanents > 0 && (
                              <span className="text-xs text-emerald-600 badge bg-emerald-50">
                                {c.nb_fichiers_permanents} doc.
                              </span>
                            )}
                          </button>
                        ))}
                        <div className="px-3 py-2 border-t border-border">
                          <p className="text-xs text-slate-400">Ou saisissez un nouveau NIF pour créer le client</p>
                        </div>
                      </div>
                    )}
                    {nifSearch.length >= 3 && suggestions.length === 0 && !searchingClient && !clientTrouve && (
                      <p className="text-xs text-slate-400 mt-1.5">
                        Nouveau client — un dossier permanent sera créé automatiquement.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Raison sociale — visible uniquement si client non trouvé ou nouveau */}
              {!clientTrouve && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Raison sociale <span className="text-red-500">*</span>
                  </label>
                  <input
                    className="input-field"
                    placeholder="Société XYZ SARL"
                    value={form.client}
                    onChange={(e) => {
                      const client = e.target.value
                      const autoNom = `Audit ${form.exercice} ${client}`.trim()
                      const isAuto = !form.nom || form.nom === `Audit ${form.exercice} ${form.client}`.trim()
                      setForm((f) => ({ ...f, client, nom: isAuto ? autoNom : f.nom }))
                    }}
                    required
                  />
                </div>
              )}

              {/* ── Exercice ── */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Exercice <span className="text-red-500">*</span>
                </label>
                <input
                  className="input-field"
                  placeholder="2025"
                  value={form.exercice}
                  onChange={(e) => {
                    const exercice = e.target.value
                    const autoNom = `Audit ${exercice} ${form.client}`.trim()
                    const isAuto = !form.nom || form.nom === `Audit ${form.exercice} ${form.client}`.trim()
                    setForm((f) => ({ ...f, exercice, nom: isAuto ? autoNom : f.nom }))
                  }}
                  required
                />
              </div>

              {/* ── Nom de la mission ── */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Nom de la mission <span className="text-red-500">*</span>
                </label>
                <input
                  className="input-field"
                  placeholder={`Audit ${form.exercice || 'AAAA'} ${form.client || 'Raison sociale'}`.trim()}
                  value={form.nom}
                  onChange={(e) => setForm((f) => ({ ...f, nom: e.target.value }))}
                  required
                />
                {!form.nom && (form.exercice || form.client) && (
                  <p className="text-xs text-slate-400 mt-1">
                    Suggestion :{' '}
                    <button
                      type="button"
                      className="text-primary-600 underline"
                      onClick={() => setForm((f) => ({ ...f, nom: `Audit ${f.exercice} ${f.client}`.trim() }))}
                    >
                      Audit {form.exercice} {form.client}
                    </button>
                  </p>
                )}
              </div>

              {/* ── Consentement ── */}
              <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <input
                  type="checkbox"
                  id="consentement"
                  checked={form.consentement_client}
                  onChange={(e) => setForm((f) => ({ ...f, consentement_client: e.target.checked }))}
                  className="mt-0.5 accent-primary-600"
                />
                <label htmlFor="consentement" className="text-xs text-amber-800 cursor-pointer leading-relaxed">
                  Le client a donné son consentement éclairé pour le traitement de ses données
                  comptables par l'IA (requis pour les appels LLM).
                </label>
              </div>

              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => { onClose(); resetForm() }} className="btn-secondary flex-1">
                  Annuler
                </button>
                <button type="submit" disabled={loading || !canSubmit} className="btn-primary flex-1">
                  {loading ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
                  Créer la mission
                </button>
              </div>

              {/* ── Restaurer un dossier ── */}
              <div className="border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setShowRestore(!showRestore)}
                  className="text-xs text-slate-400 hover:text-slate-600 transition-colors w-full text-center"
                >
                  {showRestore ? '▲ Masquer' : '▼ Restaurer un dossier sauvegardé'}
                </button>
                {showRestore && (
                  <div className="mt-3">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".zip"
                      className="hidden"
                      onChange={(e) => e.target.files?.[0] && handleRestore(e.target.files[0])}
                    />
                    <button
                      type="button"
                      disabled={restoring}
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-slate-200 rounded-xl text-slate-500 hover:border-primary-300 hover:text-primary-600 hover:bg-primary-50 transition-colors text-sm"
                    >
                      {restoring ? <Spinner size="sm" /> : <Upload className="w-4 h-4" />}
                      {restoring ? 'Restauration en cours…' : 'Choisir un fichier .zip Probare'}
                    </button>
                  </div>
                )}
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function ConfirmDeleteDialog({ projet, onConfirm, onCancel }: { projet: Projet; onConfirm: () => void; onCancel: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-modal w-full max-w-sm p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">Supprimer le projet</h3>
            <p className="text-sm text-slate-500">Cette action est irréversible.</p>
          </div>
        </div>
        <p className="text-sm text-slate-700 mb-6">
          Le projet <span className="font-semibold">« {projet.nom} »</span> et toutes ses données
          (fichiers, contrôles, exceptions) seront définitivement supprimés.
        </p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1">Annuler</button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl transition-colors"
          >
            Supprimer définitivement
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

export function Dashboard() {
  const navigate = useNavigate()
  const { get, baseUrl } = useApi()
  const toast = useToast()
  const { projets, setProjets, setProjetActif, loading, setLoading } = useProjetStore()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Projet | null>(null)

  const loadProjets = async () => {
    setLoading(true)
    try {
      const data = await get('/projets')
      setProjets(data.projets || [])
    } catch (err: any) {
      toast.error('Impossible de charger les projets : ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setProjetActif(null)
    loadProjets()
  }, [])

  const handleOpenProjet = (projet: Projet) => {
    setProjetActif(projet)
    navigate(`/projet/${projet.id}`)
  }

  const handleCreated = (projet: Projet) => {
    setProjets([projet, ...projets])
    setProjetActif(projet)
    // Nouveau projet : on démarre directement au cadrage (première étape).
    navigate(`/projet/${projet.id}/cadrage`)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    try {
      const res = await fetch(`${baseUrl}/projets/${deleteTarget.id}`, { method: 'DELETE', headers: authHeaders() })
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur suppression')
      setProjets(projets.filter((p) => p.id !== deleteTarget.id))
      toast.success(`Projet « ${deleteTarget.nom} » supprimé.`)
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleSauvegarder = async (projet: Projet) => {
    try {
      const res = await fetch(`${baseUrl}/projets/${projet.id}/sauvegarder`, { headers: authHeaders() })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Erreur export')
      const blob = await res.blob()
      const disposition = res.headers.get('content-disposition') || ''
      const match = disposition.match(/filename="?([^";\n]+)"?/)
      const filename = match ? match[1] : `probare_${projet.id.slice(0, 8)}.zip`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
      toast.success(`Dossier « ${projet.nom} » sauvegardé.`)
    } catch (err: any) {
      toast.error(err.message)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Tableau de bord"
        subtitle={`${projets.length} mission${projets.length !== 1 ? 's' : ''}`}
        actions={
          <div className="flex gap-2">
            <button
              className="btn-secondary gap-2"
              onClick={() => navigate('/dossiers-permanents')}
            >
              <Building2 className="w-4 h-4" />
              Dossiers permanents
            </button>
            <button className="btn-primary gap-2" onClick={() => setCreateOpen(true)}>
              <Plus className="w-4 h-4" />
              Nouvelle mission
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        {loading && projets.length === 0 ? (
          <div className="flex items-center justify-center h-48">
            <Spinner size="lg" />
          </div>
        ) : projets.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="Aucun projet d'audit"
            description="Créez votre premier projet pour commencer une mission d'audit."
            action={
              <button className="btn-primary" onClick={() => setCreateOpen(true)}>
                <Plus className="w-4 h-4" />
                Nouveau projet
              </button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {projets.map((p) => (
              <ProjetCard
                key={p.id}
                projet={p}
                onClick={() => handleOpenProjet(p)}
                onDelete={() => setDeleteTarget(p)}
                onSave={() => handleSauvegarder(p)}
              />
            ))}
          </div>
        )}
      </div>

      <CreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={handleCreated}
      />

      <AnimatePresence>
        {deleteTarget && (
          <ConfirmDeleteDialog
            projet={deleteTarget}
            onConfirm={handleDeleteConfirm}
            onCancel={() => setDeleteTarget(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
