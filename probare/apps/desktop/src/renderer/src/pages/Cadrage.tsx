import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Save, ArrowRight, Info, CheckCircle, Shield, ShoppingCart, TrendingUp, FolderOpen } from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { formatDate } from '../lib/utils'

// ─── Cycles disponibles ───────────────────────────────────────────────────────

const CYCLES_DISPONIBLES = [
  {
    id: 'tresorerie',
    label: 'Trésorerie',
    icon: Shield,
    description: 'Comptes 5xx — Caisse, banque, CCP',
    docs: 'Grand livre + Balance + Relevé bancaire (optionnel)',
  },
  {
    id: 'achats',
    label: 'Achats-Fournisseurs',
    icon: ShoppingCart,
    description: 'Comptes 40x + 60x-63x — Fournisseurs et charges',
    docs: 'Grand livre + Balance',
  },
  {
    id: 'ventes',
    label: 'Ventes-Clients',
    icon: TrendingUp,
    description: 'Comptes 41x + 70x-73x — Clients et produits',
    docs: 'Grand livre + Balance',
  },
]

// ─── Composants ───────────────────────────────────────────────────────────────

function InfoBanner({ icon: Icon, children, color = 'blue' }: any) {
  const colors: any = {
    blue: 'bg-blue-50 border-blue-200 text-blue-800',
    amber: 'bg-amber-50 border-amber-200 text-amber-800',
    green: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  }
  return (
    <div className={`flex items-start gap-2.5 p-3 rounded-lg border text-xs ${colors[color]}`}>
      <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
      <p className="leading-relaxed">{children}</p>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function Cadrage() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, patch, post } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()

  const [form, setForm] = useState({
    nom: '',
    client: '',
    nif: '',
    exercice: '',
    seuil_signification: '',
    seuil_planification: '',
    consentement_client: false,
    cycles_couverts: [] as string[],
    nature_mission: 'contractuelle' as string,
    client_id: null as string | null,
  })
  const [saving, setSaving] = useState(false)
  const [transitioning, setTransitioning] = useState(false)

  useEffect(() => {
    if (!projetId) return
    get(`/projets/${projetId}`).then((p) => {
      setProjetActif(p)
      setForm({
        nom: p.nom || '',
        client: p.client || '',
        nif: p.nif || '',
        exercice: p.exercice || '',
        seuil_signification: p.seuil_signification?.toString() || '',
        seuil_planification: p.seuil_planification?.toString() || '',
        consentement_client: Boolean(p.consentement_client),
        cycles_couverts: Array.isArray(p.cycles_couverts) ? p.cycles_couverts : [],
        nature_mission: p.nature_mission || 'contractuelle',
        client_id: p.client_id || null,
      })
    }).catch((e) => toast.error(e.message))
  }, [projetId])

  const toggleCycle = (cycleId: string) => {
    setForm((prev) => ({
      ...prev,
      cycles_couverts: prev.cycles_couverts.includes(cycleId)
        ? prev.cycles_couverts.filter((c) => c !== cycleId)
        : [...prev.cycles_couverts, cycleId],
    }))
  }

  const handleSave = async () => {
    if (!projetId) return
    if (form.cycles_couverts.length === 0) {
      toast.warning('Sélectionnez au moins un cycle d\'audit.')
      return
    }
    setSaving(true)
    try {
      const updated = await patch(`/projets/${projetId}`, {
        ...form,
        seuil_signification: form.seuil_signification ? Number(form.seuil_signification) : null,
        seuil_planification: form.seuil_planification ? Number(form.seuil_planification) : null,
      })
      setProjetActif(updated)
      toast.success('Paramètres enregistrés.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handlePasserIngestion = async () => {
    if (!projetId) return
    if (form.cycles_couverts.length === 0) {
      toast.warning('Sélectionnez au moins un cycle d\'audit.')
      return
    }
    setTransitioning(true)
    try {
      await handleSave()
      const updated = await post(`/projets/${projetId}/transition`, {
        vers: 'ingestion',
        acteur: 'utilisateur',
      })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/ingestion`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  const etatCourant = projetActif?.etat_courant || 'cadrage'
  // Verrouillé uniquement à partir des contrôles (irréversible dès qu'on calcule)
  const locked = ['controles', 'revue', 'generation', 'opinion'].includes(etatCourant)

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Cadrage de la mission"
        subtitle={projetActif?.nom}
        actions={
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={saving || locked} className="btn-secondary">
              {saving ? <Spinner size="sm" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
            {!locked && (
              <button onClick={handlePasserIngestion} disabled={transitioning} className="btn-primary">
                {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                Passer à l'ingestion
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">

          {locked ? (
            <InfoBanner icon={CheckCircle} color="green">
              Les contrôles ont été lancés. Le périmètre de la mission est figé.
            </InfoBanner>
          ) : etatCourant !== 'cadrage' && (
            <InfoBanner icon={Info} color="blue">
              La mission est en cours ({etatCourant}). Vous pouvez encore modifier les paramètres jusqu'au lancement des contrôles.
            </InfoBanner>
          )}

          {/* Identité */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-900">Identité de la mission</h2>
              {form.client_id && (
                <button
                  onClick={() => navigate(`/dossiers-permanents/${form.client_id}`)}
                  className="btn-ghost text-xs gap-1.5 text-primary-600"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  Dossier permanent
                </button>
              )}
            </div>

            {/* Nature de mission */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">Type de mission</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { val: 'contractuelle', label: 'Contractuelle', desc: 'Périmètre négocié librement' },
                  { val: 'legale', label: 'Légale (V2)', desc: 'Commissariat aux comptes' },
                ].map(({ val, label, desc }) => (
                  <button
                    key={val}
                    type="button"
                    disabled={locked || val === 'legale'}
                    onClick={() => !locked && setForm((f) => ({ ...f, nature_mission: val }))}
                    className={`p-2.5 rounded-xl border text-left transition-all text-sm ${
                      form.nature_mission === val
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-border text-slate-400'
                    } ${(locked || val === 'legale') ? 'opacity-50 cursor-not-allowed' : 'hover:border-slate-300'}`}
                  >
                    <p className="font-medium">{label}</p>
                    <p className="text-xs mt-0.5 opacity-75">{desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Client (raison sociale)</label>
                  <input className="input-field" value={form.client}
                    onChange={(e) => {
                      const client = e.target.value
                      const autoNom = `Audit ${form.exercice} ${client}`.trim()
                      const isAuto = !form.nom || form.nom === `Audit ${form.exercice} ${form.client}`.trim()
                      setForm((f) => ({ ...f, client, nom: isAuto ? autoNom : f.nom }))
                    }} disabled={locked} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Exercice</label>
                  <input className="input-field" value={form.exercice} placeholder="2025"
                    onChange={(e) => {
                      const exercice = e.target.value
                      const autoNom = `Audit ${exercice} ${form.client}`.trim()
                      const isAuto = !form.nom || form.nom === `Audit ${form.exercice} ${form.client}`.trim()
                      setForm((f) => ({ ...f, exercice, nom: isAuto ? autoNom : f.nom }))
                    }} disabled={locked} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Nom de la mission</label>
                <input className="input-field" value={form.nom}
                  placeholder={`Audit ${form.exercice || 'AAAA'} ${form.client || 'Raison sociale'}`.trim()}
                  onChange={(e) => setForm({ ...form, nom: e.target.value })} disabled={locked} />
                {!form.nom && (form.exercice || form.client) && (
                  <p className="text-xs text-slate-400 mt-1">
                    Suggestion : <button
                      type="button"
                      className="text-primary-600 underline"
                      onClick={() => setForm((f) => ({ ...f, nom: `Audit ${f.exercice} ${f.client}`.trim() }))}
                    >
                      Audit {form.exercice} {form.client}
                    </button>
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">NIF</label>
                <input className="input-field" value={form.nif}
                  onChange={(e) => setForm({ ...form, nif: e.target.value })} disabled={locked} />
              </div>
            </div>
          </motion.div>

          {/* Périmètre */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.04 }} className="card p-5"
          >
            <h2 className="font-semibold text-slate-900 mb-1">Périmètre de la mission</h2>
            <p className="text-sm text-slate-500 mb-4">
              Sélectionnez les cycles à auditer. Seuls les contrôles et documents correspondants seront activés.
            </p>

            <div className="space-y-3">
              {CYCLES_DISPONIBLES.map((cycle) => {
                const Icon = cycle.icon
                const selected = form.cycles_couverts.includes(cycle.id)
                return (
                  <button
                    key={cycle.id}
                    onClick={() => !locked && toggleCycle(cycle.id)}
                    disabled={locked}
                    className={`w-full flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all
                      ${selected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-border bg-white hover:border-slate-300'
                      } ${locked ? 'cursor-default' : 'cursor-pointer'}`}
                  >
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5
                      ${selected ? 'bg-primary-600' : 'bg-slate-100'}`}>
                      <Icon className={`w-4 h-4 ${selected ? 'text-white' : 'text-slate-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold ${selected ? 'text-primary-900' : 'text-slate-700'}`}>
                          {cycle.label}
                        </span>
                        {selected && (
                          <span className="text-xs bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded-full font-medium">
                            Sélectionné
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{cycle.description}</p>
                      <p className="text-xs text-slate-400 mt-1">Documents : {cycle.docs}</p>
                    </div>
                  </button>
                )
              })}
            </div>

            {form.cycles_couverts.length === 0 && (
              <p className="text-xs text-red-500 mt-3">Sélectionnez au moins un cycle.</p>
            )}
          </motion.div>

          {/* Consentement */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12 }} className="card p-5"
          >
            <h2 className="font-semibold text-slate-900 mb-1">Consentement client</h2>
            <p className="text-sm text-slate-500 mb-4">
              Requis avant tout appel à l'IA. Sans consentement, les analyses LLM sont bloquées.
            </p>
            <div className={`flex items-start gap-3 p-4 rounded-xl border transition-colors ${
              form.consentement_client
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-amber-50 border-amber-200'
            }`}>
              <input
                type="checkbox" id="consentement"
                checked={form.consentement_client}
                onChange={(e) => setForm({ ...form, consentement_client: e.target.checked })}
                disabled={locked}
                className="mt-0.5 accent-primary-600 w-4 h-4"
              />
              <label htmlFor="consentement" className="text-sm cursor-pointer leading-relaxed text-slate-700">
                Le client a donné son consentement éclairé et documenté pour le traitement de ses
                données comptables par l'IA (pseudonymisation appliquée avant tout envoi).
                <span className="block text-xs text-slate-500 mt-1">
                  {projetActif?.consentement_horodatage
                    ? `✓ Enregistré le ${formatDate(projetActif.consentement_horodatage)}`
                    : 'Non encore enregistré'}
                </span>
              </label>
            </div>
            <div className="mt-3">
              <InfoBanner icon={Info} color="blue">
                Les identifiants nominatifs (raison sociale, NIF, noms de tiers) sont automatiquement
                pseudonymisés avant tout envoi au modèle. La table de correspondance reste locale.
              </InfoBanner>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
