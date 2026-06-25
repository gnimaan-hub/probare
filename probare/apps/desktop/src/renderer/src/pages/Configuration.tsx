import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Building2, Save, CheckCircle, Phone, Mail, Globe, MapPin,
  User, Hash, Briefcase, Info, Upload, X,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../hooks/useToast'

// ─── Types ────────────────────────────────────────────────────────────────────

interface CabinetConfig {
  nom: string
  forme_juridique: string
  adresse_rue: string
  adresse_code_postal: string
  adresse_ville: string
  adresse_pays: string
  telephone: string
  email: string
  site_web: string
  numero_agrement: string
  numero_ordre: string
  responsable_nom: string
  responsable_titre: string
  logo_data_url: string
}

const DEFAULT_CONFIG: CabinetConfig = {
  nom: '',
  forme_juridique: '',
  adresse_rue: '',
  adresse_code_postal: '',
  adresse_ville: '',
  adresse_pays: 'Djibouti',
  telephone: '',
  email: '',
  site_web: '',
  numero_agrement: '',
  numero_ordre: '',
  responsable_nom: '',
  responsable_titre: 'Commissaire aux comptes',
  logo_data_url: '',
}

const STORAGE_KEY = 'probare_cabinet_config'

const FORMES_JURIDIQUES = ['SCP', 'SARL', 'SA', 'SAS', 'Exercice individuel', 'Association', 'Autre']
const TITRES = ['Commissaire aux comptes', 'Expert-comptable', 'Auditeur', 'Associé', 'Directeur', 'Autre']

// ─── Helpers ──────────────────────────────────────────────────────────────────

function loadConfig(): CabinetConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return { ...DEFAULT_CONFIG }
}

function saveConfig(config: CabinetConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ icon: Icon, title, subtitle, children }: {
  icon: React.ElementType
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-start gap-3 mb-2">
        <div className="w-9 h-9 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-primary-600" />
        </div>
        <div>
          <h2 className="font-semibold text-slate-900">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

function Field({ label, required, children }: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function Configuration() {
  const toast = useToast()
  const [form, setForm] = useState<CabinetConfig>(loadConfig)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [logoPreview, setLogoPreview] = useState(form.logo_data_url || '')

  useEffect(() => {
    setLogoPreview(form.logo_data_url || '')
  }, [form.logo_data_url])

  const set = (field: keyof CabinetConfig) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSave = async () => {
    if (!form.nom.trim()) {
      toast.error('Le nom du cabinet est obligatoire.')
      return
    }
    setSaving(true)
    await new Promise((r) => setTimeout(r, 300))
    saveConfig(form)
    setSaving(false)
    setSaved(true)
    toast.success('Configuration du cabinet enregistrée.')
    setTimeout(() => setSaved(false), 3000)
  }

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Le logo ne doit pas dépasser 2 Mo.')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setLogoPreview(dataUrl)
      setForm((f) => ({ ...f, logo_data_url: dataUrl }))
    }
    reader.readAsDataURL(file)
  }

  const handleRemoveLogo = () => {
    setLogoPreview('')
    setForm((f) => ({ ...f, logo_data_url: '' }))
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Configuration"
        subtitle="Fiche identité du cabinet d'audit"
        actions={
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary gap-2"
          >
            {saving ? (
              <Spinner size="sm" />
            ) : saved ? (
              <CheckCircle className="w-4 h-4 text-emerald-300" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saved ? 'Enregistré' : 'Enregistrer'}
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">

          {/* Bandeau info */}
          <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-blue-50 border border-blue-200">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700 leading-relaxed">
              Ces informations identifient votre cabinet dans les documents produits par Probare
              (notes de planification, rapports, lettres de circularisation, etc.).
              Elles sont stockées localement sur votre poste.
            </p>
          </div>

          {/* Section 1 : Identité du cabinet */}
          <Section icon={Building2} title="Identité du cabinet" subtitle="Raison sociale et forme juridique">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Field label="Nom du cabinet" required>
                  <input
                    className="input-field"
                    placeholder="ex : Cabinet NIMAAN & Associés"
                    value={form.nom}
                    onChange={set('nom')}
                  />
                </Field>
              </div>
              <Field label="Forme juridique">
                <select className="input-field" value={form.forme_juridique} onChange={set('forme_juridique')}>
                  <option value="">— Sélectionner —</option>
                  {FORMES_JURIDIQUES.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </Field>
              <div />
            </div>

            {/* Logo */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Logo du cabinet</label>
              {logoPreview ? (
                <div className="flex items-center gap-4">
                  <img
                    src={logoPreview}
                    alt="Logo"
                    className="h-16 w-auto object-contain rounded-lg border border-border bg-slate-50 p-1"
                  />
                  <button
                    onClick={handleRemoveLogo}
                    className="btn-ghost text-xs text-red-500 gap-1"
                  >
                    <X className="w-3.5 h-3.5" />
                    Supprimer
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center gap-2 p-6 border-2 border-dashed border-slate-200 rounded-xl cursor-pointer hover:border-primary-300 hover:bg-primary-50/30 transition-all">
                  <Upload className="w-6 h-6 text-slate-400" />
                  <span className="text-xs text-slate-500">Cliquez pour charger un logo (PNG, JPG, max 2 Mo)</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleLogoUpload} />
                </label>
              )}
            </div>
          </Section>

          {/* Section 2 : Coordonnées */}
          <Section icon={MapPin} title="Coordonnées" subtitle="Adresse et contacts">
            <div className="space-y-4">
              <Field label="Adresse (rue, BP…)">
                <input
                  className="input-field"
                  placeholder="ex : Boulevard de la République, BP 2214"
                  value={form.adresse_rue}
                  onChange={set('adresse_rue')}
                />
              </Field>
              <div className="grid grid-cols-3 gap-3">
                <Field label="Code postal">
                  <input
                    className="input-field"
                    placeholder="ex : 99000"
                    value={form.adresse_code_postal}
                    onChange={set('adresse_code_postal')}
                  />
                </Field>
                <Field label="Ville">
                  <input
                    className="input-field"
                    placeholder="ex : Djibouti"
                    value={form.adresse_ville}
                    onChange={set('adresse_ville')}
                  />
                </Field>
                <Field label="Pays">
                  <input
                    className="input-field"
                    placeholder="ex : Djibouti"
                    value={form.adresse_pays}
                    onChange={set('adresse_pays')}
                  />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Téléphone">
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      className="input-field pl-9"
                      placeholder="+253 77 XX XX XX"
                      value={form.telephone}
                      onChange={set('telephone')}
                    />
                  </div>
                </Field>
                <Field label="E-mail">
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      className="input-field pl-9"
                      type="email"
                      placeholder="contact@cabinet.dj"
                      value={form.email}
                      onChange={set('email')}
                    />
                  </div>
                </Field>
              </div>
              <Field label="Site web">
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    className="input-field pl-9"
                    placeholder="https://www.cabinet.dj"
                    value={form.site_web}
                    onChange={set('site_web')}
                  />
                </div>
              </Field>
            </div>
          </Section>

          {/* Section 3 : Agrément et références professionnelles */}
          <Section icon={Hash} title="Références professionnelles" subtitle="Agrément, ordre et numéros réglementaires">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Numéro d'agrément H2A">
                <input
                  className="input-field"
                  placeholder="ex : H2A-DJ-2025-001"
                  value={form.numero_agrement}
                  onChange={set('numero_agrement')}
                />
              </Field>
              <Field label="Numéro d'inscription à l'Ordre">
                <input
                  className="input-field"
                  placeholder="ex : CAC-DJ-042"
                  value={form.numero_ordre}
                  onChange={set('numero_ordre')}
                />
              </Field>
            </div>
          </Section>

          {/* Section 4 : Responsable signataire */}
          <Section icon={User} title="Responsable signataire" subtitle="Associé ou auditeur responsable de la mission">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Field label="Nom complet du responsable" required>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      className="input-field pl-9"
                      placeholder="Prénom Nom"
                      value={form.responsable_nom}
                      onChange={set('responsable_nom')}
                    />
                  </div>
                </Field>
              </div>
              <Field label="Titre / Qualité">
                <select className="input-field" value={form.responsable_titre} onChange={set('responsable_titre')}>
                  {TITRES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
            </div>
          </Section>

          {/* Aperçu en-tête document */}
          {(form.nom || form.responsable_nom) && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-5 border-dashed border-2 border-primary-200 bg-primary-50/20"
            >
              <p className="text-xs font-semibold text-primary-600 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5" />
                Aperçu de l'en-tête document
              </p>
              <div className="flex items-start gap-4">
                {logoPreview && (
                  <img src={logoPreview} alt="Logo" className="h-12 w-auto object-contain" />
                )}
                <div>
                  {form.nom && <p className="font-bold text-slate-900 text-sm">{form.nom}</p>}
                  {form.forme_juridique && <p className="text-xs text-slate-500">{form.forme_juridique}</p>}
                  {(form.adresse_rue || form.adresse_ville) && (
                    <p className="text-xs text-slate-500 mt-0.5">
                      {[form.adresse_rue, form.adresse_code_postal, form.adresse_ville, form.adresse_pays].filter(Boolean).join(' — ')}
                    </p>
                  )}
                  {form.telephone && <p className="text-xs text-slate-500">Tél. {form.telephone}</p>}
                  {form.email && <p className="text-xs text-slate-500">{form.email}</p>}
                  {(form.numero_agrement || form.numero_ordre) && (
                    <p className="text-xs text-slate-400 mt-1">
                      {[form.numero_agrement && `Agrément ${form.numero_agrement}`, form.numero_ordre && `Ordre ${form.numero_ordre}`].filter(Boolean).join(' · ')}
                    </p>
                  )}
                  {form.responsable_nom && (
                    <p className="text-xs text-slate-600 mt-1.5 font-medium">
                      {form.responsable_titre} : {form.responsable_nom}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {/* Bouton save en bas */}
          <div className="flex justify-end pb-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary gap-2"
            >
              {saving ? <Spinner size="sm" /> : saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              {saved ? 'Enregistré !' : 'Enregistrer la configuration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
