import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2, Plus, Search, FolderOpen, FileText,
  ChevronRight, Trash2, X, Check
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { formatDate } from '../lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client {
  id: string
  nom: string
  nif: string
  secteur?: string
  cree_le: string
  modifie_le: string
  nb_fichiers_permanents: number
}

// ─── Dialog création client ───────────────────────────────────────────────────

function CreateClientDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (client: Client) => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ nom: '', nif: '', secteur: '' })

  const canSubmit = form.nom.trim() && form.nif.trim()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setLoading(true)
    try {
      const client = await post('/clients', form)
      onCreated(client)
      toast.success(`Client « ${client.nom} » créé.`)
      onClose()
      setForm({ nom: '', nif: '', secteur: '' })
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.18 }}
          className="bg-white rounded-2xl shadow-modal w-full max-w-sm"
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 className="font-semibold text-slate-900">Nouveau client</h2>
            <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg">
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 leading-relaxed">
              Créer la fiche client crée automatiquement son dossier permanent.
              Vous pourrez y déposer statuts, contrats, PV d'AG, etc. — réutilisés à chaque mission.
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Raison sociale <span className="text-red-500">*</span>
              </label>
              <input
                className="input-field"
                placeholder="Société XYZ SARL"
                value={form.nom}
                onChange={(e) => setForm({ ...form, nom: e.target.value })}
                autoFocus
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                NIF <span className="text-red-500">*</span>
              </label>
              <input
                className="input-field"
                placeholder="Numéro d'identification fiscale"
                value={form.nif}
                onChange={(e) => setForm({ ...form, nif: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Secteur d'activité
              </label>
              <input
                className="input-field"
                placeholder="ex : Commerce, BTP, Services…"
                value={form.secteur}
                onChange={(e) => setForm({ ...form, secteur: e.target.value })}
              />
            </div>

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">
                Annuler
              </button>
              <button type="submit" disabled={loading || !canSubmit} className="btn-primary flex-1">
                {loading ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
                Créer
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Carte client ─────────────────────────────────────────────────────────────

function ClientCard({ client, onClick, onDelete }: {
  client: Client
  onClick: () => void
  onDelete: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.14 }}
      onClick={onClick}
      className="card-hover p-5 cursor-pointer group relative"
    >
      <button
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        className="absolute top-3 right-3 p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
        title="Supprimer le client"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>

      <div className="flex items-start gap-3 pr-8">
        <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-5 h-5 text-primary-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 group-hover:text-primary-700 transition-colors truncate">
            {client.nom}
          </h3>
          <p className="text-sm text-slate-500 mt-0.5">NIF : {client.nif}</p>
          {client.secteur && (
            <p className="text-xs text-slate-400 mt-0.5">{client.secteur}</p>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 transition-colors flex-shrink-0 mt-1" />
      </div>

      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <FileText className="w-3.5 h-3.5 text-slate-400" />
          <span>
            {client.nb_fichiers_permanents > 0
              ? `${client.nb_fichiers_permanents} document${client.nb_fichiers_permanents > 1 ? 's' : ''} permanent${client.nb_fichiers_permanents > 1 ? 's' : ''}`
              : 'Dossier permanent vide'}
          </span>
        </div>
        <span className="text-xs text-slate-300 ml-auto">
          Mis à jour {formatDate(client.modifie_le)}
        </span>
      </div>
    </motion.div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function DossiersPermanents() {
  const navigate = useNavigate()
  const { get, del } = useApi()
  const toast = useToast()

  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<Client | null>(null)

  const loadClients = async () => {
    setLoading(true)
    try {
      const data = await get('/clients')
      setClients(data.clients || [])
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadClients() }, [])

  const filtered = clients.filter((c) =>
    !search || c.nom.toLowerCase().includes(search.toLowerCase()) || c.nif.includes(search)
  )

  const handleDelete = async (client: Client) => {
    try {
      await del(`/clients/${client.id}`)
      setClients((prev) => prev.filter((c) => c.id !== client.id))
      toast.success(`Client « ${client.nom} » supprimé.`)
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setConfirmDelete(null)
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Header
        title={
          <div className="flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-primary-600" />
            <span>Dossiers permanents</span>
          </div>
        }
        subtitle="Pièces stables réutilisées d'une mission à l'autre"
        actions={
          <button onClick={() => setShowCreate(true)} className="btn-primary gap-2">
            <Plus className="w-4 h-4" />
            Nouveau client
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-5">

        {/* Explication */}
        <div className="card p-4 bg-amber-50 border-amber-200 flex items-start gap-3">
          <FolderOpen className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            <p className="font-medium mb-0.5">À quoi sert le dossier permanent ?</p>
            <p className="text-amber-700 text-xs leading-relaxed">
              Chaque client a un dossier permanent qui contient les pièces qui ne changent pas d'un
              exercice à l'autre : statuts, contrats, organigramme, politique comptable, rapports antérieurs.
              Lors de la création d'une mission, Probare lie automatiquement le dossier permanent du client.
            </p>
          </div>
        </div>

        {/* Barre de recherche */}
        {clients.length > 3 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              className="input-field pl-9 text-sm"
              placeholder="Rechercher par nom ou NIF…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Building2}
            title={search ? 'Aucun client trouvé' : 'Aucun client'}
            description={
              search
                ? 'Modifiez votre recherche.'
                : 'Créez votre premier client pour commencer à gérer ses dossiers permanents.'
            }
            action={
              !search ? (
                <button onClick={() => setShowCreate(true)} className="btn-primary gap-2">
                  <Plus className="w-4 h-4" />
                  Nouveau client
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((c) => (
              <ClientCard
                key={c.id}
                client={c}
                onClick={() => navigate(`/dossiers-permanents/${c.id}`)}
                onDelete={() => setConfirmDelete(c)}
              />
            ))}
          </div>
        )}
      </div>

      <CreateClientDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(c) => { setClients((prev) => [c, ...prev]); navigate(`/dossiers-permanents/${c.id}`) }}
      />

      {/* Confirm delete */}
      <AnimatePresence>
        {confirmDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={() => setConfirmDelete(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="bg-white rounded-2xl shadow-modal p-6 w-full max-w-sm"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="font-semibold text-slate-900 mb-2">Supprimer ce client ?</h3>
              <p className="text-sm text-slate-500 mb-5">
                Le client <strong>{confirmDelete.nom}</strong> et tous ses documents permanents
                seront supprimés définitivement. Les missions liées ne seront pas affectées.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setConfirmDelete(null)} className="btn-secondary flex-1">
                  Annuler
                </button>
                <button
                  onClick={() => handleDelete(confirmDelete)}
                  className="btn-danger flex-1"
                >
                  Supprimer
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
