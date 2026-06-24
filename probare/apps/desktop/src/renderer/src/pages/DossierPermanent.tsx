import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, Upload, Trash2, FileText, Users, BookOpen,
  Folder, Mail, BarChart2, FileCheck, Clipboard, Plus,
  Edit3, Check, X, ChevronDown, ChevronRight, FolderOpen,
  RefreshCw, Building2
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { formatDate } from '../lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client {
  id: string
  nom: string
  nif: string
  secteur?: string
  adresse?: string
  dirigeants?: string
  systemes_info?: string
  notes?: string
  cree_le: string
  modifie_le: string
  nb_fichiers_permanents: number
  fichiers_permanents: FichierPermanent[]
  categories: Record<string, string>
}

interface FichierPermanent {
  id: string
  client_id: string
  nom: string
  chemin_relatif: string
  categorie: string
  description: string
  taille_octets: number
  ajoute_le: string
  modifie_le: string
}

// ─── Config catégories ────────────────────────────────────────────────────────

const CAT_ICONS: Record<string, React.ElementType> = {
  statuts: FileCheck,
  pv_ag: Clipboard,
  contrats: FileText,
  organigramme: Users,
  politique_comptable: BookOpen,
  rapports_anterieurs: BarChart2,
  correspondances: Mail,
  autres: Folder,
}

const CAT_COLORS: Record<string, string> = {
  statuts: 'text-violet-600 bg-violet-50 border-violet-200',
  pv_ag: 'text-blue-600 bg-blue-50 border-blue-200',
  contrats: 'text-amber-600 bg-amber-50 border-amber-200',
  organigramme: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  politique_comptable: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  rapports_anterieurs: 'text-rose-600 bg-rose-50 border-rose-200',
  correspondances: 'text-cyan-600 bg-cyan-50 border-cyan-200',
  autres: 'text-slate-600 bg-slate-50 border-slate-200',
}

function formatBytes(bytes: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

// ─── Composant : formulaire client inline ────────────────────────────────────

function ClientInfoForm({
  client,
  onSave,
}: {
  client: Client
  onSave: (data: Partial<Client>) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    secteur: client.secteur || '',
    adresse: client.adresse || '',
    dirigeants: client.dirigeants || '',
    systemes_info: client.systemes_info || '',
    notes: client.notes || '',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(form)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ['Secteur d\'activité', client.secteur],
            ['Adresse', client.adresse],
            ['Dirigeants', client.dirigeants],
            ['Systèmes d\'information', client.systemes_info],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-slate-400 mb-0.5">{label}</p>
              <p className="text-slate-700">{value || <span className="text-slate-300 italic">Non renseigné</span>}</p>
            </div>
          ))}
        </div>
        {client.notes && (
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Notes</p>
            <p className="text-sm text-slate-700 whitespace-pre-line">{client.notes}</p>
          </div>
        )}
        <button
          onClick={() => setEditing(true)}
          className="btn-ghost text-xs gap-1.5 text-slate-500"
        >
          <Edit3 className="w-3.5 h-3.5" />
          Modifier la fiche client
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {[
          ['secteur', 'Secteur d\'activité', 'ex : Commerce, BTP, Services…'],
          ['adresse', 'Adresse', 'Siège social'],
          ['dirigeants', 'Dirigeants', 'DG, PDG, gérant…'],
          ['systemes_info', 'Systèmes d\'information', 'ERP, logiciel comptable…'],
        ].map(([key, label, placeholder]) => (
          <div key={key}>
            <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
            <input
              className="input-field text-sm"
              placeholder={placeholder}
              value={form[key as keyof typeof form]}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </div>
        ))}
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Notes</label>
        <textarea
          className="input-field text-sm resize-none"
          rows={3}
          placeholder="Informations complémentaires, observations…"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
      </div>
      <div className="flex gap-2">
        <button onClick={handleSave} disabled={saving} className="btn-primary text-sm gap-1.5">
          {saving ? <Spinner size="sm" /> : <Check className="w-3.5 h-3.5" />}
          Enregistrer
        </button>
        <button onClick={() => setEditing(false)} className="btn-secondary text-sm">
          Annuler
        </button>
      </div>
    </div>
  )
}

// ─── Composant : zone upload + liste fichiers par catégorie ──────────────────

function CategorieSection({
  categorie,
  label,
  fichiers,
  clientId,
  onUpload,
  onDelete,
  onUpdateDesc,
}: {
  categorie: string
  label: string
  fichiers: FichierPermanent[]
  clientId: string
  onUpload: (cat: string, file: File, desc: string) => Promise<void>
  onDelete: (fid: string) => Promise<void>
  onUpdateDesc: (fid: string, desc: string) => Promise<void>
}) {
  const [open, setOpen] = useState(fichiers.length > 0)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [editingDesc, setEditingDesc] = useState<string | null>(null)
  const [descDraft, setDescDraft] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const Icon = CAT_ICONS[categorie] || Folder
  const colorClass = CAT_COLORS[categorie] || CAT_COLORS.autres

  const handleFiles = async (files: FileList | null) => {
    if (!files) return
    setUploading(true)
    try {
      for (const f of Array.from(files)) {
        await onUpload(categorie, f, '')
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${colorClass}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 text-left">
          <span className="text-sm font-medium text-slate-700">{label}</span>
          {fichiers.length > 0 && (
            <span className="ml-2 text-xs text-slate-400">{fichiers.length} document{fichiers.length > 1 ? 's' : ''}</span>
          )}
        </div>
        {open ? (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-400" />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3 border-t border-border">

              {/* Zone de dépôt */}
              <div
                className={`mt-3 border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors
                  ${dragOver ? 'border-primary-400 bg-primary-50' : 'border-slate-200 hover:border-primary-300 hover:bg-slate-50'}`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
              >
                {uploading ? (
                  <div className="flex items-center justify-center gap-2 text-primary-600">
                    <Spinner size="sm" />
                    <span className="text-xs">Chargement…</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2 text-slate-400">
                    <Upload className="w-4 h-4" />
                    <span className="text-xs">Déposer un fichier ou cliquer pour choisir</span>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  multiple
                  onChange={(e) => handleFiles(e.target.files)}
                />
              </div>

              {/* Liste des fichiers */}
              {fichiers.length > 0 && (
                <ul className="space-y-1.5">
                  {fichiers.map((f) => (
                    <li key={f.id} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-50 group">
                      <FileText className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-700 truncate">{f.nom}</p>
                        {editingDesc === f.id ? (
                          <div className="mt-1 flex gap-1">
                            <input
                              autoFocus
                              className="input-field text-xs py-0.5 flex-1"
                              value={descDraft}
                              placeholder="Description du document…"
                              onChange={(e) => setDescDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') { onUpdateDesc(f.id, descDraft); setEditingDesc(null) }
                                if (e.key === 'Escape') setEditingDesc(null)
                              }}
                            />
                            <button onClick={() => { onUpdateDesc(f.id, descDraft); setEditingDesc(null) }}
                              className="p-1 rounded text-emerald-600 hover:bg-emerald-50">
                              <Check className="w-3 h-3" />
                            </button>
                            <button onClick={() => setEditingDesc(null)}
                              className="p-1 rounded text-slate-400 hover:bg-slate-100">
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <p
                            className="text-xs text-slate-400 cursor-pointer hover:text-primary-600 transition-colors mt-0.5"
                            onClick={() => { setEditingDesc(f.id); setDescDraft(f.description || '') }}
                          >
                            {f.description || <span className="italic">Ajouter une description…</span>}
                          </p>
                        )}
                        <p className="text-xs text-slate-300 mt-0.5">
                          {formatBytes(f.taille_octets)} · {formatDate(f.ajoute_le)}
                        </p>
                      </div>
                      <button
                        onClick={() => onDelete(f.id)}
                        className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                        title="Supprimer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function DossierPermanent() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const { get, patch, uploadFile, del } = useApi()
  const toast = useToast()

  const [client, setClient] = useState<Client | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    if (!clientId) return
    setLoading(true)
    try {
      const data = await get(`/clients/${clientId}`)
      setClient(data)
    } catch {
      toast.error('Client introuvable.')
      navigate('/dossiers-permanents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [clientId])

  const handleSaveClient = async (data: Partial<Client>) => {
    if (!clientId) return
    const updated = await patch(`/clients/${clientId}`, data)
    setClient((prev) => prev ? { ...prev, ...updated } : prev)
    toast.success('Fiche client mise à jour.')
  }

  const handleUpload = async (categorie: string, file: File, description: string) => {
    if (!clientId) return
    const formData = new FormData()
    formData.append('fichier', file)
    formData.append('categorie', categorie)
    formData.append('description', description)
    await uploadFile(`/clients/${clientId}/permanent/fichiers`, formData)
    toast.success(`${file.name} ajouté au dossier permanent.`)
    await load()
  }

  const handleDelete = async (fid: string) => {
    if (!clientId) return
    await del(`/clients/${clientId}/permanent/${fid}`)
    toast.success('Document supprimé.')
    await load()
  }

  const handleUpdateDesc = async (fid: string, description: string) => {
    if (!clientId) return
    await patch(`/clients/${clientId}/permanent/${fid}`, { description })
    await load()
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (!client) return null

  const categories = client.categories || {}
  const fichiersByCategorie = (cat: string) =>
    (client.fichiers_permanents || []).filter((f) => f.categorie === cat)

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Header
        title={`Dossier permanent — ${client.nom}`}
        subtitle={`NIF : ${client.nif} · ${client.nb_fichiers_permanents} document${client.nb_fichiers_permanents !== 1 ? 's' : ''}`}
        actions={
          <button
            onClick={() => navigate('/dossiers-permanents')}
            className="btn-secondary"
          >
            <ArrowLeft className="w-4 h-4" />
            Tous les clients
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Bannière info */}
        <div className="card p-4 bg-blue-50 border-blue-200 flex items-start gap-3">
          <FolderOpen className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-0.5">Dossier permanent du client</p>
            <p className="text-blue-700 text-xs leading-relaxed">
              Ce dossier regroupe les pièces stables qui servent à toutes les missions d'audit de ce client.
              Ils sont réutilisés automatiquement à chaque nouvelle mission — inutile de les re-déposer chaque année.
              Mettez-les à jour dès qu'une version plus récente est disponible.
            </p>
          </div>
        </div>

        {/* Fiche client */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-slate-400" />
            Fiche client
          </h2>
          <ClientInfoForm client={client} onSave={handleSaveClient} />
        </div>

        {/* Documents par catégorie */}
        <div>
          <h2 className="font-semibold text-slate-900 mb-3">Documents permanents</h2>
          <div className="space-y-2">
            {Object.entries(categories).map(([cat, label]) => (
              <CategorieSection
                key={cat}
                categorie={cat}
                label={label}
                fichiers={fichiersByCategorie(cat)}
                clientId={client.id}
                onUpload={handleUpload}
                onDelete={handleDelete}
                onUpdateDesc={handleUpdateDesc}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
