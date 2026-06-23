import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2, TrendingUp, Target, ShieldAlert, ClipboardList,
  Sparkles, ArrowRight, Save, Plus, Trash2, Check, X,
  Info, CheckCircle, AlertTriangle, BarChart3, Users,
  Lock, ArrowUpDown, Filter, RefreshCw,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { formatMontant, formatDate } from '../lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Dirigeant { nom: string; fonction: string; email?: string }

interface Planification {
  id: string
  projet_id: string
  forme_juridique?: string
  date_creation_entreprise?: string
  activites_principales?: string
  marches_principaux?: string
  dirigeants?: Dirigeant[]
  systeme_information?: string
  effectif?: number
  observations?: string
  facteurs_risque_inherent?: string[]
  balance_n1_fichier_id?: string
  variations_json?: Variation[]
  interpretation_variations?: string | InterpretationVariations
  variations_ia_horodatage?: string
  agregat_type?: string
  agregat_valeur?: number
  taux_signification?: number
  taux_planification?: number
  seuil_calcule?: number
  seuil_planification_calcule?: number
  agregats_json?: Record<string, number>
  statut?: string
  note_synthese?: string
}

interface NoteSyntheseSection { titre: string; contenu: string }
interface NoteSynthese {
  titre: string
  sections: NoteSyntheseSection[]
  conclusion: string
}

interface Variation {
  compte: string
  libelle: string
  solde_n: number
  solde_n1: number
  delta: number
  delta_pct: number
  significative: boolean
}

interface InterpretationVariations {
  synthese?: string
  zones_risque?: Array<{ cycle: string; libelle: string; niveau: string; explication: string }>
  facteurs_contextuels?: string
  alertes?: string[]
}

interface Risque {
  id: string
  projet_id: string
  libelle: string
  description?: string
  cycle?: string
  niveau: string
  assertions?: string[]
  source: string
  issu_ia: number
  valide_auditeur: number
  commentaire?: string
  cree_le?: string
}

interface ProgrammeItem {
  id: string
  projet_id: string
  cycle?: string
  controle_ref?: string
  libelle: string
  risque_id?: string
  priorite: string
  statut: string
  notes?: string
  issu_ia: number
}

interface FichierSource {
  id: string
  nom: string
  type?: string
  importe_le?: string
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const ASSERTIONS = [
  { id: 'existence',    label: 'Existence / Occurrence' },
  { id: 'exhaustivite', label: 'Exhaustivité' },
  { id: 'evaluation',  label: 'Évaluation / Exactitude' },
  { id: 'cut_off',     label: 'Cut-off (séparation des exercices)' },
  { id: 'droits',      label: 'Droits et obligations' },
  { id: 'presentation',label: 'Présentation' },
]

const CYCLES = [
  { id: 'tresorerie',  label: 'Trésorerie' },
  { id: 'achats',      label: 'Achats-Fournisseurs' },
  { id: 'ventes',      label: 'Ventes-Clients' },
  { id: 'transversal', label: 'Transversal' },
]

const NIVEAUX: Record<string, { label: string; color: string; bg: string }> = {
  eleve:  { label: 'Élevé',  color: 'text-red-700',    bg: 'bg-red-100' },
  moyen:  { label: 'Moyen',  color: 'text-amber-700',  bg: 'bg-amber-100' },
  faible: { label: 'Faible', color: 'text-emerald-700',bg: 'bg-emerald-100' },
}

const SOURCES: Record<string, string> = {
  analytique: 'Procédures analytiques',
  entite:     'Fiche entité',
  inherent:   'Risque inhérent',
  ia:         'Proposé par l\'IA',
  manuel:     'Manuel',
}

const AGREGATS = [
  { id: 'total_bilan',      label: 'Total bilan',         taux: 0.01,  desc: 'Recommandé pour la plupart des audits' },
  { id: 'chiffre_affaires', label: 'Chiffre d\'affaires', taux: 0.015, desc: 'Entités à fort CA, faible bilan' },
  { id: 'resultat_net',     label: 'Résultat net',        taux: 0.05,  desc: 'Entités bénéficiaires stables' },
]

const FORMES_JURIDIQUES = ['SA', 'SARL', 'SNC', 'SCS', 'GIE', 'Association', 'EP', 'EPA', 'Autre']

// ─── Utilitaires UI ──────────────────────────────────────────────────────────

function NiveauBadge({ niveau }: { niveau: string }) {
  const cfg = NIVEAUX[niveau] || NIVEAUX.moyen
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function SectionNav({
  sections,
  activeId,
  onSelect,
}: {
  sections: Array<{ id: string; label: string; icon: React.ElementType; done: boolean }>
  activeId: string
  onSelect: (id: string) => void
}) {
  return (
    <nav className="space-y-1">
      {sections.map((s) => {
        const Icon = s.icon
        const active = activeId === s.id
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm text-left transition-all ${
              active
                ? 'bg-primary-50 text-primary-700 font-medium'
                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
            }`}
          >
            <Icon className={`w-4 h-4 flex-shrink-0 ${active ? 'text-primary-600' : 'text-slate-400'}`} />
            <span className="flex-1 truncate">{s.label}</span>
            {s.done && <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />}
          </button>
        )
      })}
    </nav>
  )
}

// ─── Composant principal ──────────────────────────────────────────────────────

export function Planification() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, post, patch } = useApi()
  const toast = useToast()
  const { projetActif, setProjetActif } = useProjetStore()

  const [plan, setPlan] = useState<Planification | null>(null)
  const [risques, setRisques] = useState<Risque[]>([])
  const [programme, setProgramme] = useState<ProgrammeItem[]>([])
  const [balances, setBalances] = useState<FichierSource[]>([])
  const [noteSynthese, setNoteSynthese] = useState<NoteSynthese | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState('fiche-entite')
  const [transitioning, setTransitioning] = useState(false)

  const sectionRefs = useRef<Record<string, HTMLElement | null>>({})

  // ── Load ──────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    if (!projetId) return
    setLoading(true)
    try {
      const [planData, projData] = await Promise.all([
        get(`/projets/${projetId}/planification`),
        get(`/projets/${projetId}`),
      ])
      setPlan(planData.planification)
      setRisques(planData.risques || [])
      setProgramme(planData.programme || [])
      setBalances(planData.balances_disponibles || [])
      const rawNote = planData.planification?.note_synthese
      if (rawNote) {
        try {
          setNoteSynthese(typeof rawNote === 'string' ? JSON.parse(rawNote) : rawNote)
        } catch { /* ignore */ }
      }
      setProjetActif(projData)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }, [projetId])

  useEffect(() => { load() }, [load])

  // ── Sections completion ───────────────────────────────────────────────────

  const interpretation = (() => {
    const raw = plan?.interpretation_variations
    if (!raw) return null
    if (typeof raw === 'string') { try { return JSON.parse(raw) } catch { return null } }
    return raw as InterpretationVariations
  })()

  const doneFiche = !!(plan?.activites_principales || plan?.forme_juridique)
  const doneAnalytics = !!(plan?.variations_json?.length)
  const doneSeuils = !!(plan?.seuil_calcule)
  const doneRisques = risques.filter((r) => r.valide_auditeur).length > 0
  const doneProgramme = programme.filter((p) => p.statut === 'inclus').length > 0

  const sections = [
    { id: 'fiche-entite',  label: 'Fiche entité',           icon: Building2,     done: doneFiche },
    { id: 'analytique',    label: 'Procédures analytiques', icon: TrendingUp,    done: doneAnalytics },
    { id: 'seuils',        label: 'Calcul des seuils',      icon: Target,        done: doneSeuils },
    { id: 'risques',       label: 'Cartographie des risques',icon: ShieldAlert,   done: doneRisques },
    { id: 'programme',     label: 'Programme de travail',   icon: ClipboardList, done: doneProgramme },
  ]

  const scrollTo = (id: string) => {
    setActiveSection(id)
    sectionRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // ── Transition vers contrôles ─────────────────────────────────────────────

  const handlePasserControles = async () => {
    if (!projetId) return
    setTransitioning(true)
    try {
      const updated = await post(`/projets/${projetId}/transition`, { vers: 'controles', acteur: 'utilisateur' })
      setProjetActif(updated)
      navigate(`/projet/${projetId}/controles`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setTransitioning(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  const etatCourant = projetActif?.etat_courant || 'planification'
  const locked = ['controles', 'revue', 'generation', 'opinion'].includes(etatCourant)

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Planification"
        subtitle={projetActif?.nom}
        actions={
          !locked && (
            <button
              onClick={handlePasserControles}
              disabled={transitioning}
              className="btn-primary gap-2"
            >
              {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
              Passer aux contrôles
            </button>
          )
        }
      />

      <div className="flex-1 flex overflow-hidden">
        {/* ── Sidebar ── */}
        <aside className="w-56 flex-shrink-0 border-r border-border overflow-y-auto p-4">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Sections</p>
          <SectionNav sections={sections} activeId={activeSection} onSelect={scrollTo} />

          <div className="mt-6 p-3 bg-slate-50 rounded-xl">
            <p className="text-xs font-medium text-slate-600 mb-1">Progression</p>
            <div className="flex gap-1">
              {sections.map((s) => (
                <div
                  key={s.id}
                  className={`h-1.5 flex-1 rounded-full ${s.done ? 'bg-emerald-500' : 'bg-slate-200'}`}
                />
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-1.5">
              {sections.filter((s) => s.done).length}/{sections.length} sections complètes
            </p>
          </div>
        </aside>

        {/* ── Contenu ── */}
        <main className="flex-1 overflow-y-auto p-6 space-y-8">
          {locked && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
              <Lock className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-blue-800">
                Les contrôles ont été lancés. La planification est en lecture seule.
              </p>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════ */}
          {/* SECTION 1 — FICHE ENTITÉ                                       */}
          {/* ════════════════════════════════════════════════════════════════ */}
          <section
            ref={(el) => { sectionRefs.current['fiche-entite'] = el }}
            id="fiche-entite"
          >
            <SectionHeader icon={Building2} title="Fiche entité" done={doneFiche}
              subtitle="Prise de connaissance de l'entité auditée (PLA-01)" />
            <FicheEntiteForm
              plan={plan}
              locked={locked}
              onSaved={(updated) => setPlan(updated)}
              projetId={projetId!}
            />
          </section>

          {/* ════════════════════════════════════════════════════════════════ */}
          {/* SECTION 2 — PROCÉDURES ANALYTIQUES                             */}
          {/* ════════════════════════════════════════════════════════════════ */}
          <section
            ref={(el) => { sectionRefs.current['analytique'] = el }}
            id="analytique"
          >
            <SectionHeader icon={TrendingUp} title="Procédures analytiques N/N-1" done={doneAnalytics}
              subtitle="Calcul déterministe des variations de balance (PLA-02 + PLA-03)" />
            <AnalytiquesSection
              plan={plan}
              balances={balances}
              interpretation={interpretation}
              locked={locked}
              projetId={projetId!}
              seuil={projetActif?.seuil_signification}
              onUpdated={(p) => setPlan(p)}
            />
          </section>

          {/* ════════════════════════════════════════════════════════════════ */}
          {/* SECTION 3 — CALCUL DES SEUILS                                  */}
          {/* ════════════════════════════════════════════════════════════════ */}
          <section
            ref={(el) => { sectionRefs.current['seuils'] = el }}
            id="seuils"
          >
            <SectionHeader icon={Target} title="Calcul des seuils" done={doneSeuils}
              subtitle="Calcul automatique depuis un agrégat de la balance (PLA-04 + PLA-05)" />
            <SeuilsSection
              plan={plan}
              locked={locked}
              projetId={projetId!}
              currentSeuil={projetActif?.seuil_signification}
              onApplied={(p, proj) => { setPlan(p); setProjetActif(proj) }}
            />
          </section>

          {/* ════════════════════════════════════════════════════════════════ */}
          {/* SECTION 4 — CARTOGRAPHIE DES RISQUES                           */}
          {/* ════════════════════════════════════════════════════════════════ */}
          <section
            ref={(el) => { sectionRefs.current['risques'] = el }}
            id="risques"
          >
            <SectionHeader icon={ShieldAlert} title="Cartographie des risques" done={doneRisques}
              subtitle="Identification et évaluation des risques d'audit significatifs (PLA-06 + PLA-07)" />
            <RisquesSection
              risques={risques}
              locked={locked}
              projetId={projetId!}
              onChanged={setRisques}
            />
          </section>

          {/* ════════════════════════════════════════════════════════════════ */}
          {/* SECTION 5 — PROGRAMME DE TRAVAIL                               */}
          {/* ════════════════════════════════════════════════════════════════ */}
          <section
            ref={(el) => { sectionRefs.current['programme'] = el }}
            id="programme"
          >
            <SectionHeader icon={ClipboardList} title="Programme de travail" done={doneProgramme}
              subtitle="Plan des contrôles à conduire selon les risques identifiés (PLA-08)" />
            <ProgrammeSection
              programme={programme}
              risques={risques}
              locked={locked}
              projetId={projetId!}
              doneRisques={doneRisques}
              noteSynthese={noteSynthese}
              onChanged={setProgramme}
              onSyntheseGenerated={setNoteSynthese}
            />
          </section>

          {/* ── CTA finale ── */}
          {!locked && (
            <div className="card p-6 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">Planification terminée ?</p>
                <p className="text-sm text-slate-500 mt-0.5">
                  {doneRisques
                    ? `${risques.filter((r) => r.valide_auditeur).length} risque(s) validé(s) · ${programme.filter((p) => p.statut === 'inclus').length} contrôle(s) au programme`
                    : 'Identifiez et validez au moins un risque avant de continuer.'}
                </p>
              </div>
              <button
                onClick={handlePasserControles}
                disabled={transitioning}
                className="btn-primary gap-2 flex-shrink-0"
              >
                {transitioning ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                Passer aux contrôles
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

// ─── Composant SectionHeader ──────────────────────────────────────────────────

function SectionHeader({
  icon: Icon, title, subtitle, done
}: {
  icon: React.ElementType; title: string; subtitle: string; done: boolean
}) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
        done ? 'bg-emerald-100' : 'bg-primary-100'
      }`}>
        {done
          ? <CheckCircle className="w-5 h-5 text-emerald-600" />
          : <Icon className="w-5 h-5 text-primary-600" />}
      </div>
      <div>
        <h2 className="font-semibold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
    </div>
  )
}

// ─── SECTION 1 : Fiche entité ─────────────────────────────────────────────────

function FicheEntiteForm({
  plan, locked, onSaved, projetId
}: {
  plan: Planification | null
  locked: boolean
  onSaved: (p: Planification) => void
  projetId: string
}) {
  const { patch, post } = useApi()
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    forme_juridique: '',
    date_creation_entreprise: '',
    activites_principales: '',
    marches_principaux: '',
    systeme_information: '',
    effectif: '',
    observations: '',
  })
  const [dirigeants, setDirigeants] = useState<Dirigeant[]>([])
  const [facteurs, setFacteurs] = useState<string[]>([])
  const [newFacteur, setNewFacteur] = useState('')
  const [newDir, setNewDir] = useState({ nom: '', fonction: '', email: '' })
  const [showAddDir, setShowAddDir] = useState(false)

  useEffect(() => {
    if (!plan) return
    setForm({
      forme_juridique: plan.forme_juridique || '',
      date_creation_entreprise: plan.date_creation_entreprise || '',
      activites_principales: plan.activites_principales || '',
      marches_principaux: plan.marches_principaux || '',
      systeme_information: plan.systeme_information || '',
      effectif: plan.effectif?.toString() || '',
      observations: plan.observations || '',
    })
    setDirigeants(plan.dirigeants || [])
    setFacteurs(plan.facteurs_risque_inherent || [])
  }, [plan?.id])

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await patch(`/projets/${projetId}/planification/fiche-entite`, {
        ...form,
        effectif: form.effectif ? parseInt(form.effectif) : undefined,
        dirigeants,
        facteurs_risque_inherent: facteurs,
      })
      onSaved(res.planification)
      toast.success('Fiche entité enregistrée.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const addDirigeant = () => {
    if (!newDir.nom.trim()) return
    setDirigeants([...dirigeants, { ...newDir }])
    setNewDir({ nom: '', fonction: '', email: '' })
    setShowAddDir(false)
  }

  const addFacteur = () => {
    const f = newFacteur.trim()
    if (!f || facteurs.includes(f)) return
    setFacteurs([...facteurs, f])
    setNewFacteur('')
  }

  return (
    <div className="card p-5 space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Forme juridique</label>
          <select className="input-field" value={form.forme_juridique}
            onChange={(e) => setForm((f) => ({ ...f, forme_juridique: e.target.value }))}
            disabled={locked}>
            <option value="">— Sélectionner —</option>
            {FORMES_JURIDIQUES.map((fj) => <option key={fj} value={fj}>{fj}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Date de création</label>
          <input className="input-field" type="date" value={form.date_creation_entreprise}
            onChange={(e) => setForm((f) => ({ ...f, date_creation_entreprise: e.target.value }))}
            disabled={locked} />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">Activités principales</label>
        <textarea className="input-field min-h-[72px]" rows={3}
          placeholder="Décrivez les activités principales de l'entité auditée…"
          value={form.activites_principales}
          onChange={(e) => setForm((f) => ({ ...f, activites_principales: e.target.value }))}
          disabled={locked} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Marchés principaux</label>
          <input className="input-field" placeholder="ex : Local, Export, BTP, Grande distribution…"
            value={form.marches_principaux}
            onChange={(e) => setForm((f) => ({ ...f, marches_principaux: e.target.value }))}
            disabled={locked} />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Effectif</label>
          <input className="input-field" type="number" placeholder="Nombre de salariés"
            value={form.effectif}
            onChange={(e) => setForm((f) => ({ ...f, effectif: e.target.value }))}
            disabled={locked} />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">Système d'information</label>
        <input className="input-field"
          placeholder="ERP, logiciel comptable, version… ex : Sage 100 v21, Dext, Excel"
          value={form.systeme_information}
          onChange={(e) => setForm((f) => ({ ...f, systeme_information: e.target.value }))}
          disabled={locked} />
      </div>

      {/* Dirigeants */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-slate-700">Dirigeants et responsables clés</label>
          {!locked && (
            <button onClick={() => setShowAddDir(!showAddDir)}
              className="text-xs btn-ghost gap-1 text-primary-600">
              <Plus className="w-3 h-3" />Ajouter
            </button>
          )}
        </div>
        {showAddDir && (
          <div className="grid grid-cols-3 gap-2 mb-2 p-3 bg-slate-50 rounded-lg">
            <input className="input-field text-sm" placeholder="Nom" value={newDir.nom}
              onChange={(e) => setNewDir((d) => ({ ...d, nom: e.target.value }))} />
            <input className="input-field text-sm" placeholder="Fonction" value={newDir.fonction}
              onChange={(e) => setNewDir((d) => ({ ...d, fonction: e.target.value }))} />
            <div className="flex gap-1">
              <input className="input-field text-sm flex-1" placeholder="Email (opt.)" value={newDir.email}
                onChange={(e) => setNewDir((d) => ({ ...d, email: e.target.value }))} />
              <button onClick={addDirigeant} className="btn-primary px-2"><Check className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        )}
        {dirigeants.length > 0 ? (
          <div className="space-y-1.5">
            {dirigeants.map((d, i) => (
              <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-slate-50">
                <Users className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span className="text-sm font-medium text-slate-700">{d.nom}</span>
                <span className="text-xs text-slate-400">— {d.fonction}</span>
                {d.email && <span className="text-xs text-slate-400">{d.email}</span>}
                {!locked && (
                  <button onClick={() => setDirigeants(dirigeants.filter((_, j) => j !== i))}
                    className="ml-auto text-slate-300 hover:text-red-500 transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic">Aucun dirigeant renseigné.</p>
        )}
      </div>

      {/* Facteurs de risque inhérents */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Facteurs de risque inhérents identifiés
        </label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {facteurs.map((f) => (
            <span key={f}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-amber-50 text-amber-800 border border-amber-200">
              {f}
              {!locked && (
                <button onClick={() => setFacteurs(facteurs.filter((x) => x !== f))}>
                  <X className="w-2.5 h-2.5 ml-0.5" />
                </button>
              )}
            </span>
          ))}
        </div>
        {!locked && (
          <div className="flex gap-2">
            <input className="input-field text-sm flex-1"
              placeholder="ex : Forte saisonnalité, Transactions avec parties liées…"
              value={newFacteur}
              onKeyDown={(e) => e.key === 'Enter' && addFacteur()}
              onChange={(e) => setNewFacteur(e.target.value)} />
            <button onClick={addFacteur} className="btn-secondary px-3">
              <Plus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">Observations particulières</label>
        <textarea className="input-field" rows={2}
          placeholder="Autres informations utiles pour l'audit : litiges, restructuration, changement de direction…"
          value={form.observations}
          onChange={(e) => setForm((f) => ({ ...f, observations: e.target.value }))}
          disabled={locked} />
      </div>

      {!locked && (
        <div className="flex justify-end pt-1">
          <button onClick={handleSave} disabled={saving} className="btn-primary gap-2">
            {saving ? <Spinner size="sm" /> : <Save className="w-4 h-4" />}
            Enregistrer la fiche
          </button>
        </div>
      )}
    </div>
  )
}

// ─── SECTION 2 : Procédures analytiques ──────────────────────────────────────

function AnalytiquesSection({
  plan, balances, interpretation, locked, projetId, seuil, onUpdated
}: {
  plan: Planification | null
  balances: FichierSource[]
  interpretation: InterpretationVariations | null
  locked: boolean
  projetId: string
  seuil?: number
  onUpdated: (p: Planification) => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [fichierNId, setFichierNId] = useState('')
  const [fichierN1Id, setFichierN1Id] = useState(plan?.balance_n1_fichier_id || '')
  const [calculating, setCalculating] = useState(false)
  const [interpreting, setInterpreting] = useState(false)
  const [showSignificatives, setShowSignificatives] = useState(false)
  const [sortAsc, setSortAsc] = useState(false)

  const variations = plan?.variations_json || []
  const significatives = variations.filter((v) => v.significative)
  const displayed = showSignificatives ? significatives : variations

  const handleCalculer = async () => {
    if (!fichierNId) { toast.error('Sélectionnez la balance N.'); return }
    setCalculating(true)
    try {
      const res = await post(`/projets/${projetId}/planification/calculer-variations`, {
        fichier_n_id: fichierNId,
        fichier_n1_id: fichierN1Id || null,
      })
      onUpdated(res.planification)
      toast.success(`${res.variations.length} comptes analysés, ${res.variations.filter((v: Variation) => v.significative).length} variations significatives.`)
      // Auto-lancer l'interprétation IA si des variations significatives existent
      if (res.variations.some((v: Variation) => v.significative) && res.variations.length > 0) {
        setTimeout(() => handleInterpreter(), 500)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setCalculating(false)
    }
  }

  const handleInterpreter = async () => {
    setInterpreting(true)
    try {
      const res = await post(`/projets/${projetId}/planification/interpreter-variations`, {})
      onUpdated(res.planification)
      toast.success('Interprétation IA générée.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setInterpreting(false)
    }
  }

  if (balances.length === 0) {
    return (
      <div className="card p-6">
        <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-blue-800">
            Aucun fichier comptable importé. Passez d'abord à l'étape <strong>Ingestion</strong> pour importer la balance ou le grand livre.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Sélection des fichiers */}
      <div className="card p-5">
        <h3 className="text-sm font-medium text-slate-700 mb-1">Sélection des fichiers comptables</h3>
        <p className="text-xs text-slate-400 mb-3">Tous les fichiers importés en ingestion sont disponibles — sélectionnez le fichier N et, si disponible, le fichier N-1 pour la comparaison.</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fichier N — exercice audité *</label>
            <select className="input-field text-sm" value={fichierNId}
              onChange={(e) => setFichierNId(e.target.value)} disabled={locked}>
              <option value="">— Sélectionner —</option>
              {balances.map((b) => <option key={b.id} value={b.id}>{b.nom}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fichier N-1 — exercice précédent (optionnel)</label>
            <select className="input-field text-sm" value={fichierN1Id}
              onChange={(e) => setFichierN1Id(e.target.value)} disabled={locked}>
              <option value="">— Aucun (analyse N seul) —</option>
              {balances.map((b) => <option key={b.id} value={b.id}>{b.nom}</option>)}
            </select>
          </div>
        </div>
        {!locked && (
          <button onClick={handleCalculer} disabled={calculating || !fichierNId}
            className="btn-primary gap-2 mt-3">
            {calculating ? <Spinner size="sm" /> : <BarChart3 className="w-4 h-4" />}
            Calculer les variations
          </button>
        )}
      </div>

      {/* Tableau des variations */}
      {variations.length > 0 && (
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-3">
              <p className="text-sm font-medium text-slate-700">
                {variations.length} comptes · {significatives.length} variations significatives
              </p>
              {seuil && (
                <span className="text-xs text-slate-400">
                  Seuil : {formatMontant(seuil)}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowSignificatives(!showSignificatives)}
                className={`btn-ghost text-xs gap-1 ${showSignificatives ? 'text-primary-600' : ''}`}
              >
                <Filter className="w-3.5 h-3.5" />
                {showSignificatives ? 'Toutes' : 'Significatives uniquement'}
              </button>
              <button onClick={() => setSortAsc(!sortAsc)} className="btn-ghost text-xs gap-1">
                <ArrowUpDown className="w-3.5 h-3.5" />
                {sortAsc ? 'Plus faibles en tête' : 'Plus élevées en tête'}
              </button>
            </div>
          </div>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2.5">Compte</th>
                  <th className="text-left px-4 py-2.5">Libellé</th>
                  <th className="text-right px-4 py-2.5">Solde N</th>
                  <th className="text-right px-4 py-2.5">Solde N-1</th>
                  <th className="text-right px-4 py-2.5">Variation</th>
                  <th className="text-right px-4 py-2.5">%</th>
                  <th className="text-center px-4 py-2.5">Sign.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[...displayed]
                  .sort((a, b) => sortAsc
                    ? Math.abs(a.delta) - Math.abs(b.delta)
                    : Math.abs(b.delta) - Math.abs(a.delta))
                  .map((v) => (
                    <tr key={v.compte}
                      className={`${v.significative ? 'bg-red-50/40' : 'hover:bg-slate-50'} transition-colors`}>
                      <td className="px-4 py-2 font-mono text-xs text-slate-500">{v.compte}</td>
                      <td className="px-4 py-2 text-slate-700 max-w-[200px] truncate">{v.libelle || '—'}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-700">
                        {formatMontant(v.solde_n, '')}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-400">
                        {v.solde_n1 !== 0 ? formatMontant(v.solde_n1, '') : '—'}
                      </td>
                      <td className={`px-4 py-2 text-right tabular-nums font-medium ${
                        v.delta > 0 ? 'text-emerald-700' : v.delta < 0 ? 'text-red-700' : 'text-slate-400'
                      }`}>
                        {v.delta > 0 ? '+' : ''}{formatMontant(v.delta, '')}
                      </td>
                      <td className={`px-4 py-2 text-right text-xs ${
                        Math.abs(v.delta_pct) > 50 ? 'text-red-600 font-medium' : 'text-slate-500'
                      }`}>
                        {v.solde_n1 !== 0 ? `${v.delta_pct > 0 ? '+' : ''}${v.delta_pct.toFixed(1)}%` : 'N/A'}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {v.significative
                          ? <span className="inline-block w-2 h-2 rounded-full bg-red-500" title="Significative" />
                          : <span className="inline-block w-2 h-2 rounded-full bg-slate-200" />}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Interprétation IA */}
      {variations.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-violet-500" />
              <h3 className="text-sm font-medium text-slate-700">Interprétation IA des variations</h3>
              {plan?.variations_ia_horodatage && (
                <span className="text-xs text-slate-400">
                  · {formatDate(plan.variations_ia_horodatage)}
                </span>
              )}
            </div>
            {!locked && (
              <button onClick={handleInterpreter} disabled={interpreting}
                className="btn-ghost text-xs gap-1 text-violet-600">
                {interpreting ? <Spinner size="sm" /> : <RefreshCw className="w-3.5 h-3.5" />}
                {interpretation ? 'Relancer' : 'Analyser'}
              </button>
            )}
          </div>

          {interpreting && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Spinner size="sm" />
              <span>Sonnet analyse les variations significatives…</span>
            </div>
          )}

          {interpretation && !interpreting && (
            <div className="space-y-4">
              {interpretation.synthese && (
                <p className="text-sm text-slate-700 leading-relaxed">{interpretation.synthese}</p>
              )}

              {(interpretation.zones_risque || []).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Zones à risque identifiées</p>
                  <div className="space-y-2">
                    {interpretation.zones_risque!.map((z, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-50">
                        <NiveauBadge niveau={z.niveau} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-700">{z.libelle}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{z.explication}</p>
                        </div>
                        <span className="text-xs text-slate-400 flex-shrink-0">
                          {CYCLES.find((c) => c.id === z.cycle)?.label || z.cycle}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {interpretation.facteurs_contextuels && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs font-medium text-blue-600 mb-1">Facteurs contextuels</p>
                  <p className="text-sm text-blue-800">{interpretation.facteurs_contextuels}</p>
                </div>
              )}

              {(interpretation.alertes || []).length > 0 && (
                <div className="space-y-1">
                  {interpretation.alertes!.map((a, i) => (
                    <div key={i} className="flex items-start gap-2 p-2.5 bg-amber-50 rounded-lg">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-800">{a}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!interpretation && !interpreting && (
            <p className="text-sm text-slate-400 italic">
              {variations.length > 0
                ? 'Cliquez sur "Analyser" pour obtenir l\'interprétation IA des variations significatives.'
                : 'Calculez d\'abord les variations pour activer l\'analyse IA.'}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── SECTION 3 : Calcul des seuils ───────────────────────────────────────────

function SeuilsSection({
  plan, locked, projetId, currentSeuil, onApplied
}: {
  plan: Planification | null
  locked: boolean
  projetId: string
  currentSeuil?: number
  onApplied: (p: Planification, proj: any) => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [applying, setApplying] = useState(false)
  const [agregat, setAgregat] = useState(plan?.agregat_type || 'total_bilan')
  const [tauxSign, setTauxSign] = useState((plan?.taux_signification || 0.01) * 100)
  const [tauxPlan, setTauxPlan] = useState((plan?.taux_planification || 0.75) * 100)

  const agregats = plan?.agregats_json || {}
  const valeurAgregat = agregats[agregat] || 0
  const seuilCalcule = valeurAgregat * (tauxSign / 100)
  const seuilPlanCalc = seuilCalcule * (tauxPlan / 100)

  const handleApply = async () => {
    if (!valeurAgregat) {
      toast.error('Calculez d\'abord les variations analytiques pour obtenir les agrégats.')
      return
    }
    setApplying(true)
    try {
      const res = await post(`/projets/${projetId}/planification/calculer-seuils`, {
        agregat_type: agregat,
        taux_signification: tauxSign / 100,
        taux_planification: tauxPlan / 100,
      })
      onApplied(res.planification, res.projet)
      toast.success(`Seuils appliqués : ${formatMontant(res.seuils.seuil_signification)} de signification.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setApplying(false)
    }
  }

  const cfgAgregat = AGREGATS.find((a) => a.id === agregat)

  return (
    <div className="card p-5 space-y-5">
      {Object.keys(agregats).length === 0 && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-blue-800">
            Les agrégats sont calculés automatiquement lors du calcul des variations (section précédente).
            Importez une balance et calculez les variations pour activer cette section.
          </p>
        </div>
      )}

      {/* Agrégats disponibles */}
      {Object.keys(agregats).length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {AGREGATS.map((a) => {
            const val = agregats[a.id] || 0
            const selected = agregat === a.id
            return (
              <button
                key={a.id}
                onClick={() => { if (!locked) setAgregat(a.id) }}
                disabled={locked}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selected
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-border hover:border-slate-300'
                } ${!val ? 'opacity-50' : ''}`}
              >
                <p className={`text-xs font-medium mb-0.5 ${selected ? 'text-primary-700' : 'text-slate-600'}`}>
                  {a.label}
                </p>
                <p className={`text-base font-bold ${selected ? 'text-primary-800' : 'text-slate-700'}`}>
                  {val ? formatMontant(val) : '—'}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">{a.desc}</p>
              </button>
            )
          })}
        </div>
      )}

      {/* Taux */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Taux de signification (%)
          </label>
          <div className="relative">
            <input
              className="input-field pr-8"
              type="number"
              step="0.1"
              min="0.1"
              max="20"
              value={tauxSign}
              onChange={(e) => setTauxSign(parseFloat(e.target.value) || 1)}
              disabled={locked}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">%</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Défaut ISA 320 pour {cfgAgregat?.label} : {((cfgAgregat?.taux || 0.01) * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Taux de planification (% du seuil)
          </label>
          <div className="relative">
            <input
              className="input-field pr-8"
              type="number"
              step="1"
              min="50"
              max="100"
              value={tauxPlan}
              onChange={(e) => setTauxPlan(parseFloat(e.target.value) || 75)}
              disabled={locked}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">%</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Recommandé : 75% (rigueur accrue)</p>
        </div>
      </div>

      {/* Résultats calculés */}
      <div className="p-4 bg-slate-50 rounded-xl space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600">
            Agrégat sélectionné ({cfgAgregat?.label || agregat})
          </span>
          <span className="font-medium text-slate-800">
            {valeurAgregat ? formatMontant(valeurAgregat) : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600">
            × {tauxSign.toFixed(1)}% = Seuil de signification
          </span>
          <span className={`font-bold text-base ${seuilCalcule ? 'text-primary-700' : 'text-slate-400'}`}>
            {seuilCalcule ? formatMontant(seuilCalcule) : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm border-t border-border pt-2">
          <span className="text-slate-600">
            × {tauxPlan.toFixed(0)}% = Seuil de planification
          </span>
          <span className={`font-medium ${seuilPlanCalc ? 'text-slate-700' : 'text-slate-400'}`}>
            {seuilPlanCalc ? formatMontant(seuilPlanCalc) : '—'}
          </span>
        </div>
      </div>

      {currentSeuil && (
        <p className="text-xs text-slate-400">
          Seuil actuel de la mission (saisi manuellement) : {formatMontant(currentSeuil)}
          {plan?.seuil_calcule && ` → remplacé par ${formatMontant(plan.seuil_calcule)} après application`}
        </p>
      )}

      {!locked && (
        <button onClick={handleApply} disabled={applying || !valeurAgregat}
          className="btn-primary gap-2">
          {applying ? <Spinner size="sm" /> : <Target className="w-4 h-4" />}
          Appliquer ces seuils à la mission
        </button>
      )}
    </div>
  )
}

// ─── SECTION 4 : Cartographie des risques ─────────────────────────────────────

function RisquesSection({
  risques, locked, projetId, onChanged
}: {
  risques: Risque[]
  locked: boolean
  projetId: string
  onChanged: (r: Risque[]) => void
}) {
  const { post, patch } = useApi()
  const toast = useToast()
  const [proposing, setProposing] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [filterCycle, setFilterCycle] = useState('')
  const [filterNiveau, setFilterNiveau] = useState('')

  const handleProposer = async () => {
    setProposing(true)
    try {
      const res = await post(`/projets/${projetId}/planification/proposer-risques`, {})
      onChanged([...risques, ...res.risques_proposes])
      toast.success(`${res.total} risque(s) proposé(s) par l'IA. Validez ceux qui vous semblent pertinents.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setProposing(false)
    }
  }

  const handleValider = async (risque: Risque) => {
    try {
      const res = await patch(`/projets/${projetId}/planification/risques/${risque.id}`, {
        valide_auditeur: !risque.valide_auditeur,
      })
      onChanged(risques.map((r) => r.id === risque.id ? res.risque : r))
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/projets/${projetId}/planification/risques/${id}`, { method: 'DELETE' })
      onChanged(risques.filter((r) => r.id !== id))
    } catch { /* silencieux */ }
  }

  const filtered = risques.filter((r) => {
    if (filterCycle && r.cycle !== filterCycle) return false
    if (filterNiveau && r.niveau !== filterNiveau) return false
    return true
  })

  const valides = risques.filter((r) => r.valide_auditeur).length
  const proposes = risques.filter((r) => r.issu_ia && !r.valide_auditeur).length

  return (
    <div className="space-y-4">
      {/* Barre d'actions */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        {!locked && (
          <>
            <button onClick={handleProposer} disabled={proposing}
              className="btn-primary gap-2 bg-violet-600 hover:bg-violet-700 border-violet-700">
              {proposing ? <Spinner size="sm" /> : <Sparkles className="w-4 h-4" />}
              L'IA propose des risques
            </button>
            <button onClick={() => setShowAdd(!showAdd)} className="btn-secondary gap-2">
              <Plus className="w-4 h-4" />
              Ajouter manuellement
            </button>
          </>
        )}
        <div className="flex gap-2 ml-auto">
          <select className="input-field text-xs py-1.5 w-36" value={filterCycle}
            onChange={(e) => setFilterCycle(e.target.value)}>
            <option value="">Tous les cycles</option>
            {CYCLES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
          <select className="input-field text-xs py-1.5 w-32" value={filterNiveau}
            onChange={(e) => setFilterNiveau(e.target.value)}>
            <option value="">Tous niveaux</option>
            {Object.entries(NIVEAUX).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="flex gap-3">
        <div className="flex items-center gap-1.5 text-sm text-slate-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>{valides} validé{valides !== 1 ? 's' : ''}</span>
        </div>
        {proposes > 0 && (
          <div className="flex items-center gap-1.5 text-sm text-violet-600">
            <Sparkles className="w-3 h-3" />
            <span>{proposes} à valider</span>
          </div>
        )}
        {proposing && (
          <div className="flex items-center gap-1.5 text-sm text-slate-400">
            <Spinner size="sm" />
            <span>Sonnet analyse la fiche entité et les variations…</span>
          </div>
        )}
      </div>

      {/* Formulaire d'ajout */}
      {showAdd && !locked && (
        <AddRisqueForm
          projetId={projetId}
          onCreated={(r) => { onChanged([...risques, r]); setShowAdd(false) }}
          onCancel={() => setShowAdd(false)}
        />
      )}

      {/* Grille des risques */}
      {filtered.length === 0 ? (
        <div className="card p-8 text-center text-slate-400">
          <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">
            {risques.length === 0
              ? 'Aucun risque identifié. Utilisez l\'IA ou ajoutez-en manuellement.'
              : 'Aucun risque pour les filtres sélectionnés.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filtered.map((r) => (
            <RisqueCard
              key={r.id}
              risque={r}
              locked={locked}
              onValider={() => handleValider(r)}
              onDelete={() => handleDelete(r.id)}
              projetId={projetId}
              onUpdated={(updated) => onChanged(risques.map((x) => x.id === updated.id ? updated : x))}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function AddRisqueForm({ projetId, onCreated, onCancel }: {
  projetId: string
  onCreated: (r: Risque) => void
  onCancel: () => void
}) {
  const { post } = useApi()
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [reformulating, setReformulating] = useState(false)
  const [form, setForm] = useState({
    libelle: '', description: '', cycle: 'tresorerie', niveau: 'moyen',
    assertions: [] as string[], source: 'manuel', commentaire: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.libelle.trim()) return
    setSaving(true)
    try {
      const res = await post(`/projets/${projetId}/planification/risques`, form)
      // Auto-reformulation IA pour homogénéiser avec les risques générés
      setReformulating(true)
      try {
        const reformule = await post(`/projets/${projetId}/planification/risques/${res.risque.id}/reformuler`, {})
        onCreated(reformule.risque)
        toast.success('Risque ajouté et mis en forme par l\'IA.')
      } catch {
        // Si la reformulation échoue, on garde le risque tel quel
        onCreated(res.risque)
        toast.success('Risque ajouté.')
      } finally {
        setReformulating(false)
      }
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card p-4 space-y-3 border-2 border-primary-200">
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 mb-1">Libellé du risque *</label>
          <input className="input-field" placeholder="ex : Risque de reconnaissance de revenus prématurée…"
            value={form.libelle} onChange={(e) => setForm((f) => ({ ...f, libelle: e.target.value }))} required />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Cycle</label>
          <select className="input-field" value={form.cycle}
            onChange={(e) => setForm((f) => ({ ...f, cycle: e.target.value }))}>
            {CYCLES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Niveau</label>
          <select className="input-field" value={form.niveau}
            onChange={(e) => setForm((f) => ({ ...f, niveau: e.target.value }))}>
            {Object.entries(NIVEAUX).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 mb-1">Description (optionnelle)</label>
          <textarea className="input-field" rows={2} placeholder="Contexte et explication du risque…"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
        </div>
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Assertions concernées</label>
          <div className="flex flex-wrap gap-1.5">
            {ASSERTIONS.map((a) => {
              const checked = form.assertions.includes(a.id)
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setForm((f) => ({
                    ...f,
                    assertions: checked
                      ? f.assertions.filter((x) => x !== a.id)
                      : [...f.assertions, a.id],
                  }))}
                  className={`px-2 py-1 rounded-lg border text-xs transition-all ${
                    checked
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-border text-slate-500 hover:border-slate-300'
                  }`}
                >
                  {a.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button type="button" onClick={onCancel} className="btn-secondary" disabled={saving || reformulating}>Annuler</button>
        <button type="submit" disabled={saving || reformulating} className="btn-primary gap-1">
          {(saving || reformulating) ? <Spinner size="sm" /> : <Plus className="w-3.5 h-3.5" />}
          {reformulating ? 'Mise en forme IA…' : saving ? 'Ajout…' : 'Ajouter'}
        </button>
      </div>
      {reformulating && (
        <p className="text-xs text-violet-600 flex items-center gap-1">
          <Sparkles className="w-3 h-3" />
          L'IA reformule et met en forme votre risque…
        </p>
      )}
    </form>
  )
}

function RisqueCard({ risque, locked, onValider, onDelete, projetId, onUpdated }: {
  risque: Risque
  locked: boolean
  onValider: () => void
  onDelete: () => void
  projetId: string
  onUpdated: (r: Risque) => void
}) {
  const isIA = risque.issu_ia === 1
  const isValide = risque.valide_auditeur === 1

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card p-4 border transition-all ${
        isValide
          ? 'border-emerald-200 bg-emerald-50/30'
          : isIA
          ? 'border-violet-200 bg-violet-50/20'
          : 'border-border'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-medium text-slate-800">{risque.libelle}</p>
            <NiveauBadge niveau={risque.niveau} />
            {isIA && (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs bg-violet-100 text-violet-600">
                <Sparkles className="w-2.5 h-2.5" />IA
              </span>
            )}
            {isValide && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
          </div>
          {risque.description && (
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{risque.description}</p>
          )}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {risque.cycle && (
              <span className="text-xs text-slate-400">
                {CYCLES.find((c) => c.id === risque.cycle)?.label || risque.cycle}
              </span>
            )}
            {(risque.assertions || []).length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {risque.assertions!.map((a) => (
                  <span key={a} className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">
                    {ASSERTIONS.find((x) => x.id === a)?.label.split('/')[0].trim() || a}
                  </span>
                ))}
              </div>
            )}
            <span className="text-xs text-slate-400 ml-auto">{SOURCES[risque.source] || risque.source}</span>
          </div>
        </div>
        {!locked && (
          <div className="flex gap-1 flex-shrink-0">
            <button
              onClick={onValider}
              title={isValide ? 'Invalider ce risque' : 'Valider ce risque'}
              className={`p-1.5 rounded-lg transition-all ${
                isValide
                  ? 'text-emerald-600 bg-emerald-100 hover:bg-emerald-200'
                  : 'text-slate-300 hover:text-emerald-600 hover:bg-emerald-50'
              }`}
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onDelete}
              className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ─── SECTION 5 : Programme de travail ────────────────────────────────────────

function ProgrammeSection({
  programme, risques, locked, projetId, doneRisques, noteSynthese, onChanged, onSyntheseGenerated
}: {
  programme: ProgrammeItem[]
  risques: Risque[]
  locked: boolean
  projetId: string
  doneRisques: boolean
  noteSynthese: NoteSynthese | null
  onChanged: (p: ProgrammeItem[]) => void
  onSyntheseGenerated: (n: NoteSynthese) => void
}) {
  const { post, patch, downloadBlob } = useApi()
  const toast = useToast()
  const [generating, setGenerating] = useState(false)
  const [generatingSynthese, setGeneratingSynthese] = useState(false)
  const [docxPret, setDocxPret] = useState(!!noteSynthese)
  const [downloading, setDownloading] = useState(false)

  const handleGenererSynthese = async () => {
    setGeneratingSynthese(true)
    try {
      const res = await post(`/projets/${projetId}/planification/generer-synthese`, {})
      onSyntheseGenerated(res.note_synthese)
      if (res.docx_pret) setDocxPret(true)
      toast.success('Note de planification générée — le fichier .docx est prêt.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGeneratingSynthese(false)
    }
  }

  const handleTelecharger = async () => {
    setDownloading(true)
    try {
      const { blob, filename } = await downloadBlob(
        `/projets/${projetId}/planification/telecharger-note`,
        'GET'
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setDownloading(false)
    }
  }

  const handleGenerer = async () => {
    if (!doneRisques) {
      toast.error('Validez au moins un risque avant de générer le programme.')
      return
    }
    setGenerating(true)
    try {
      const res = await post(`/projets/${projetId}/planification/generer-programme`, {})
      onChanged(res.programme)
      const inclus = res.programme.filter((p: ProgrammeItem) => p.statut === 'inclus').length
      toast.success(`Programme généré : ${inclus} contrôle(s) inclus sur ${res.total}.`)
      // Auto-génération de la note de planification (.docx)
      setGeneratingSynthese(true)
      try {
        const synthRes = await post(`/projets/${projetId}/planification/generer-synthese`, {})
        onSyntheseGenerated(synthRes.note_synthese)
        if (synthRes.docx_pret) setDocxPret(true)
        toast.success('Note de planification .docx prête à télécharger.')
      } catch { /* non bloquant */ } finally {
        setGeneratingSynthese(false)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleToggle = async (item: ProgrammeItem) => {
    const newStatut = item.statut === 'inclus' ? 'exclu' : 'inclus'
    try {
      const res = await patch(`/projets/${projetId}/planification/programme/${item.id}`, {
        statut: newStatut,
      })
      onChanged(programme.map((p) => p.id === item.id ? res.item : p))
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const byPriorite: Record<string, ProgrammeItem[]> = {}
  for (const item of programme) {
    const key = item.priorite || 'normale'
    if (!byPriorite[key]) byPriorite[key] = []
    byPriorite[key].push(item)
  }

  const byCycle: Record<string, ProgrammeItem[]> = {}
  for (const item of programme) {
    const key = item.cycle || 'transversal'
    if (!byCycle[key]) byCycle[key] = []
    byCycle[key].push(item)
  }

  const inclus = programme.filter((p) => p.statut === 'inclus').length
  const risqueById = Object.fromEntries(risques.map((r) => [r.id, r]))

  const PRIORITE_ORDER = ['haute', 'normale', 'faible']
  const PRIORITE_LABELS: Record<string, { label: string; color: string }> = {
    haute:   { label: 'Priorité haute',   color: 'text-red-600' },
    normale: { label: 'Priorité normale', color: 'text-slate-600' },
    faible:  { label: 'Priorité faible',  color: 'text-slate-400' },
  }

  return (
    <div className="space-y-4">
      <div className="card p-4 flex flex-wrap items-center gap-3">
        {!locked && (
          <button
            onClick={handleGenerer}
            disabled={generating || generatingSynthese || !doneRisques}
            className="btn-primary gap-2 bg-violet-600 hover:bg-violet-700 border-violet-700"
            title={!doneRisques ? 'Validez d\'abord des risques' : undefined}
          >
            {generating ? <Spinner size="sm" /> : <Sparkles className="w-4 h-4" />}
            {programme.length > 0 ? 'Régénérer le programme' : 'Générer le programme de travail'}
          </button>
        )}
        {programme.length > 0 && (
          <p className="text-sm text-slate-500 ml-auto">
            <strong className="text-slate-700">{inclus}</strong> contrôle{inclus !== 1 ? 's' : ''} inclus
            · {programme.length - inclus} exclu{programme.length - inclus !== 1 ? 's' : ''}
          </p>
        )}
        {generating && (
          <p className="text-sm text-slate-400 flex items-center gap-1.5">
            <Spinner size="sm" />
            Sonnet adapte le programme aux risques identifiés…
          </p>
        )}
        {generatingSynthese && !generating && (
          <p className="text-sm text-violet-500 flex items-center gap-1.5">
            <Spinner size="sm" />
            Rédaction de la note de synthèse…
          </p>
        )}
      </div>

      {!doneRisques && programme.length === 0 && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-blue-800">
            Identifiez et validez des risques dans la section précédente pour générer le programme de travail.
          </p>
        </div>
      )}

      {programme.length > 0 && (
        <div className="space-y-4">
          {CYCLES.map((cycle) => {
            const items = byCycle[cycle.id] || []
            if (items.length === 0) return null
            const itemsByPriorite = PRIORITE_ORDER.reduce((acc, p) => {
              const filtered = items.filter((i) => (i.priorite || 'normale') === p)
              if (filtered.length) acc[p] = filtered
              return acc
            }, {} as Record<string, ProgrammeItem[]>)

            return (
              <div key={cycle.id} className="card overflow-hidden">
                <div className="px-4 py-3 bg-slate-50 border-b border-border flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-700">{cycle.label}</p>
                  <p className="text-xs text-slate-400">
                    {items.filter((i) => i.statut === 'inclus').length}/{items.length} contrôle{items.length !== 1 ? 's' : ''} inclus
                  </p>
                </div>
                <div className="divide-y divide-border">
                  {PRIORITE_ORDER.map((p) => {
                    const group = itemsByPriorite[p]
                    if (!group) return null
                    return group.map((item) => {
                      const risque = item.risque_id ? risqueById[item.risque_id] : null
                      const isInclus = item.statut === 'inclus'
                      return (
                        <div key={item.id}
                          className={`flex items-start gap-3 px-4 py-3 transition-colors ${
                            isInclus ? '' : 'opacity-50 bg-slate-50/50'
                          }`}
                        >
                          {!locked && (
                            <button
                              onClick={() => handleToggle(item)}
                              className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
                                isInclus
                                  ? 'border-emerald-500 bg-emerald-500 text-white'
                                  : 'border-slate-300 hover:border-emerald-400'
                              }`}
                            >
                              {isInclus && <Check className="w-3 h-3" />}
                            </button>
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className={`text-sm ${isInclus ? 'text-slate-800' : 'text-slate-500 line-through'}`}>
                                {item.libelle}
                              </p>
                              {item.controle_ref && (
                                <span className="text-xs font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                                  {item.controle_ref}
                                </span>
                              )}
                              <span className={`text-xs ${PRIORITE_LABELS[p]?.color || 'text-slate-400'}`}>
                                {PRIORITE_LABELS[p]?.label}
                              </span>
                            </div>
                            {risque && (
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className="text-xs text-slate-400">↳ Risque :</span>
                                <span className="text-xs text-slate-500">{risque.libelle}</span>
                                <NiveauBadge niveau={risque.niveau} />
                              </div>
                            )}
                            {item.notes && (
                              <p className="text-xs text-slate-400 italic mt-0.5">{item.notes}</p>
                            )}
                          </div>
                        </div>
                      )
                    })
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Note de planification .docx */}
      {(docxPret || generatingSynthese) && (
        <div className="card border-violet-200 bg-violet-50">
          <div className="px-5 py-4">
            {generatingSynthese && !docxPret ? (
              <div className="flex items-center gap-3 text-sm text-violet-700">
                <Spinner size="sm" />
                <div>
                  <p className="font-semibold">Rédaction de la Note de Planification…</p>
                  <p className="text-violet-500 text-xs mt-0.5">
                    Sonnet analyse les risques et rédige le document NEP 300 complet.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-violet-100 flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-5 h-5 text-violet-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-violet-900">Note de Planification de l'Audit</p>
                    <p className="text-xs text-violet-600 mt-0.5">
                      Document .docx complet · NEP 300, 315, 320, 330, 520 · 7 sections rédigées par l'IA
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Inclut : connaissance de l'entité, procédures analytiques, cartographie des risques,
                      seuils de signification, programme de travail et conclusion argumentée.
                    </p>
                  </div>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <button
                    onClick={handleTelecharger}
                    disabled={downloading}
                    className="btn-primary gap-2 bg-violet-600 hover:bg-violet-700 border-violet-700 whitespace-nowrap"
                  >
                    {downloading ? <Spinner size="sm" /> : <ArrowRight className="w-4 h-4" />}
                    {downloading ? 'Téléchargement…' : 'Télécharger (.docx)'}
                  </button>
                  {!locked && (
                    <button
                      onClick={handleGenererSynthese}
                      disabled={generatingSynthese}
                      className="btn-ghost text-xs gap-1 text-violet-600"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Regénérer le document
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
