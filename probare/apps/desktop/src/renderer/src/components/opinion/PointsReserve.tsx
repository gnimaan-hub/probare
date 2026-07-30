import { useEffect, useState } from 'react'
import { Plus, Trash2, Check, X, ShieldAlert, Lightbulb } from 'lucide-react'
import { Spinner } from '../ui/Spinner'
import { useApi } from '../../hooks/useApi'
import { useToast } from '../../hooks/useToast'
import { normeLabel, formatMontant } from '../../lib/utils'

export interface PointReserve {
  id: string
  type: string
  libelle: string
  description?: string
  rubrique?: string
  montant_concerne?: number | null
  impact_opinion: string
  statut: string
  resolution?: string
  source?: string
  reference?: string
}

interface Candidat {
  type: string
  libelle: string
  description?: string
  cycle?: string
  montant_concerne?: number | null
  source: string
  reference: string
}

const TYPES = [
  { id: 'limitation', label: "Limitation de l'étendue des travaux" },
  { id: 'incertitude', label: 'Incertitude significative' },
  { id: 'desaccord', label: 'Désaccord avec la direction' },
]

const IMPACTS = [
  { id: 'reserve', label: 'Réserve' },
  { id: 'defavorable', label: 'Opinion défavorable' },
  { id: 'impossibilite', label: "Impossibilité d'exprimer une opinion" },
  { id: 'aucun', label: 'Sans incidence (mention en observation)' },
]

const VIDE = {
  type: 'limitation', libelle: '', description: '', rubrique: '',
  montant_concerne: '', impact_opinion: 'reserve',
}

function typeLabel(id: string): string {
  return TYPES.find((t) => t.id === id)?.label || id
}

function impactStyle(impact: string): string {
  switch (impact) {
    case 'defavorable':
    case 'impossibilite': return 'bg-red-50 border-red-200 text-red-700'
    case 'reserve': return 'bg-amber-50 border-amber-200 text-amber-700'
    default: return 'bg-slate-50 border-slate-200 text-slate-600'
  }
}

/**
 * Registre des points de réserve QUALITATIFS (R3 — ISA 705).
 *
 * Se lit à côté du cumul ISA 450, jamais à sa place : une réserve peut naître
 * d'une anomalie chiffrée non corrigée (le cumul) comme d'une limitation
 * d'étendue, d'une incertitude ou d'un désaccord — qui, eux, ne se chiffrent
 * pas. Sans ce registre, une opinion avec réserve peut reposer sur un cumul
 * nul, ce qu'un contrôle qualité relève immédiatement.
 */
export function PointsReserve({ projetId, onChange }: {
  projetId: string
  onChange?: () => void
}) {
  const { get, post, put, del } = useApi()
  const toast = useToast()
  const [points, setPoints] = useState<PointReserve[]>([])
  const [candidats, setCandidats] = useState<Candidat[]>([])
  const [synthese, setSynthese] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ ...VIDE })
  const [leveeEnCours, setLeveeEnCours] = useState<string | null>(null)
  const [resolution, setResolution] = useState('')

  const charger = async () => {
    try {
      const [r, c] = await Promise.all([
        get(`/projets/${projetId}/points-reserve`),
        get(`/projets/${projetId}/points-reserve/candidats`).catch(() => ({ candidats: [] })),
      ])
      setPoints(r.points || [])
      setSynthese(r.synthese || null)
      setCandidats(c.candidats || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (projetId) charger() }, [projetId])

  const apresEcriture = async () => {
    await charger()
    onChange?.()
  }

  const handleCreer = async (payload: Record<string, any>) => {
    setSaving(true)
    try {
      await post(`/projets/${projetId}/points-reserve`, payload)
      setShowForm(false)
      setForm({ ...VIDE })
      toast.success('Point de réserve enregistré.')
      await apresEcriture()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleAjout = () => {
    if (!form.libelle.trim()) {
      toast.warning('Donnez un libellé au point de réserve.')
      return
    }
    handleCreer({
      ...form,
      montant_concerne: form.montant_concerne ? Number(form.montant_concerne) : undefined,
      description: form.description || undefined,
      rubrique: form.rubrique || undefined,
    })
  }

  const handleLever = async (p: PointReserve) => {
    if (!resolution.trim()) {
      toast.warning("Documentez l'élément probant qui lève la limitation.")
      return
    }
    setSaving(true)
    try {
      await put(`/projets/${projetId}/points-reserve/${p.id}`, {
        type: p.type, libelle: p.libelle, description: p.description,
        rubrique: p.rubrique, montant_concerne: p.montant_concerne ?? undefined,
        impact_opinion: p.impact_opinion, statut: 'leve', resolution,
      })
      setLeveeEnCours(null)
      setResolution('')
      toast.success('Point levé — il ne pèse plus sur l\'opinion.')
      await apresEcriture()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleSupprimer = async (p: PointReserve) => {
    setSaving(true)
    try {
      await del(`/projets/${projetId}/points-reserve/${p.id}`)
      await apresEcriture()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card p-5 flex justify-center"><Spinner /></div>

  const ouverts = points.filter((p) => p.statut === 'ouvert')
  const leves = points.filter((p) => p.statut !== 'ouvert')

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-primary-600" />
          <h2 className="font-semibold text-slate-900">Points de réserve qualitatifs</h2>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-secondary text-xs">
          {showForm ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
          {showForm ? 'Annuler' : 'Ajouter'}
        </button>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Limitations de l'étendue des travaux, incertitudes et désaccords : le fondement
        d'une réserve qui ne se chiffre pas et n'entre donc pas au cumul {normeLabel('450')}.
        Les deux se lisent ensemble.
      </p>

      {synthese && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: 'Ouverts', val: synthese.nb_ouverts },
            { label: "Pesant sur l'opinion", val: synthese.nb_impactants },
            { label: 'Postes concernés', val: formatMontant(synthese.montant_concerne_total) },
          ].map((s) => (
            <div key={s.label} className="bg-slate-50 rounded-xl p-3">
              <div className="text-[11px] text-slate-500">{s.label}</div>
              <div className="text-sm font-semibold text-slate-800 mt-0.5">{s.val}</div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="border border-border rounded-xl p-4 mb-4 space-y-3 bg-slate-50/60">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Nature</label>
              <select className="input-field text-sm" value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {TYPES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Incidence sur l'opinion</label>
              <select className="input-field text-sm" value={form.impact_opinion}
                onChange={(e) => setForm({ ...form, impact_opinion: e.target.value })}>
                {IMPACTS.map((i) => <option key={i.id} value={i.id}>{i.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Libellé</label>
            <input className="input-field text-sm" value={form.libelle}
              placeholder="ex : Provisions pour risques non justifiées"
              onChange={(e) => setForm({ ...form, libelle: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Base de la réserve (reprise telle quelle au fondement du rapport)
            </label>
            <textarea className="input-field text-sm min-h-[70px]" value={form.description}
              placeholder="Nous n'avons pas pu obtenir d'éléments probants suffisants sur…"
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Rubrique concernée</label>
              <input className="input-field text-sm" value={form.rubrique}
                placeholder="ex : Provisions pour risques et charges"
                onChange={(e) => setForm({ ...form, rubrique: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Montant du poste concerné
              </label>
              <input className="input-field text-sm" type="number" value={form.montant_concerne}
                onChange={(e) => setForm({ ...form, montant_concerne: e.target.value })} />
              <p className="text-[11px] text-slate-400 mt-1">
                Ce n'est pas une anomalie chiffrée : il n'entre jamais au cumul {normeLabel('450')}.
              </p>
            </div>
          </div>
          <button onClick={handleAjout} disabled={saving} className="btn-primary text-sm">
            {saving ? <Spinner size="sm" /> : <Check className="w-4 h-4" />}
            Enregistrer le point
          </button>
        </div>
      )}

      {candidats.length > 0 && (
        <div className="border border-dashed border-amber-300 bg-amber-50/40 rounded-xl p-3 mb-4">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 mb-2">
            <Lightbulb className="w-3.5 h-3.5" />
            Limitations déjà établies par le dossier ({candidats.length})
          </div>
          <p className="text-[11px] text-amber-700/80 mb-2">
            Contrôles non exécutés et confirmations restées sans réponse. À vous de décider
            si le fait pèse sur votre opinion — rien n'est enregistré d'office.
          </p>
          <div className="space-y-1.5">
            {candidats.map((c) => (
              <div key={`${c.source}:${c.reference}`}
                className="flex items-center justify-between gap-2 bg-white rounded-lg px-2.5 py-1.5">
                <span className="text-[11px] text-slate-700 truncate">{c.libelle}</span>
                <button
                  onClick={() => handleCreer({ ...c, impact_opinion: 'reserve' })}
                  disabled={saving}
                  className="text-[11px] text-primary-600 underline whitespace-nowrap"
                >
                  Enregistrer
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {points.length === 0 && (
        <p className="text-xs text-slate-400">
          Aucun point de réserve enregistré. Une opinion avec réserve exigera soit un point ici,
          soit des anomalies chiffrées non corrigées.
        </p>
      )}

      <div className="space-y-2">
        {[...ouverts, ...leves].map((p) => (
          <div key={p.id} className={`border rounded-xl p-3 ${
            p.statut === 'ouvert' ? 'border-border' : 'border-border bg-slate-50/60 opacity-75'}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-slate-800">{p.libelle}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${impactStyle(p.impact_opinion)}`}>
                    {IMPACTS.find((i) => i.id === p.impact_opinion)?.label || p.impact_opinion}
                  </span>
                  {p.statut !== 'ouvert' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-emerald-50 border-emerald-200 text-emerald-700">
                      Levé
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {[typeLabel(p.type), p.rubrique,
                    p.montant_concerne ? formatMontant(p.montant_concerne) : null,
                  ].filter(Boolean).join(' · ')}
                </div>
                {p.description && <p className="text-xs text-slate-600 mt-1.5">{p.description}</p>}
                {p.resolution && (
                  <p className="text-[11px] text-emerald-700 mt-1.5 italic">Levé — {p.resolution}</p>
                )}
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {p.statut === 'ouvert' && (
                  <button
                    onClick={() => { setLeveeEnCours(leveeEnCours === p.id ? null : p.id); setResolution('') }}
                    className="text-[11px] text-primary-600 underline whitespace-nowrap"
                  >
                    Lever
                  </button>
                )}
                <button onClick={() => handleSupprimer(p)} disabled={saving}
                  className="p-1 text-slate-400 hover:text-red-500" title="Supprimer">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {leveeEnCours === p.id && (
              <div className="mt-3 pt-3 border-t border-border">
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Élément probant finalement obtenu
                </label>
                <textarea className="input-field text-sm min-h-[60px]" value={resolution}
                  placeholder="ex : détail du calcul et attestation d'avocat obtenus le 12/03."
                  onChange={(e) => setResolution(e.target.value)} />
                <button onClick={() => handleLever(p)} disabled={saving}
                  className="btn-secondary text-xs mt-2">
                  {saving ? <Spinner size="sm" /> : <Check className="w-3.5 h-3.5" />}
                  Confirmer la levée
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
