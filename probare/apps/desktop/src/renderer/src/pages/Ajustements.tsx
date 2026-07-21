import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Scale, Plus, Trash2, X, CheckCircle, XCircle, ChevronDown, ChevronRight,
  Sparkles, Loader2, Info, Wand2, ArrowRight, TrendingUp, TrendingDown, Link2,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore, type Exception } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { formatMontant, formatDate, normeLabel } from '../lib/utils'

// ─── Types (miroir des routes /ajustements) ───────────────────────────────────

interface LigneAjustement {
  compte: string
  libelle?: string | null
  debit: number
  credit: number
  donnee_id?: string
}

interface EcritureAjustement {
  id: string
  projet_id: string
  exception_id?: string | null
  libelle: string
  type_anomalie: 'factuelle' | 'jugement' | 'extrapolee'
  statut: 'proposee' | 'acceptee_client' | 'passee' | 'refusee'
  statut_libelle: string
  type_libelle: string
  justification?: string | null
  total_debits: number
  total_credits: number
  effet_resultat: number
  effet_capitaux_propres: number
  issu_ia: number
  cree_par?: string | null
  cree_le?: string
  lignes: LigneAjustement[]
}

interface SyntheseAjustements {
  nb_total: number
  nb_passees: number
  nb_non_passees: number
  nb_refusees: number
  passees: { effet_resultat: number; effet_capitaux_propres: number; montant_total: number }
  non_passees: { effet_resultat: number; effet_capitaux_propres: number; montant_total: number }
}

interface LigneBalance {
  compte: string
  solde_brut: number
  ajustement: number
  solde_ajuste: number
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const STATUTS: Record<string, { label: string; cls: string }> = {
  proposee:        { label: 'Proposée au client',   cls: 'bg-blue-100 text-blue-700' },
  acceptee_client: { label: 'Acceptée par le client', cls: 'bg-amber-100 text-amber-700' },
  passee:          { label: 'Passée ✓',             cls: 'bg-emerald-100 text-emerald-700' },
  refusee:         { label: 'Refusée',              cls: 'bg-red-100 text-red-700' },
}

const TYPES: Record<string, { label: string; hint: string }> = {
  factuelle:  { label: 'Factuelle',  hint: 'Erreur avérée, sans ambiguïté' },
  jugement:   { label: 'De jugement', hint: 'Estimation ou méthode contestée' },
  extrapolee: { label: 'Extrapolée', hint: 'Projetée depuis un sondage' },
}

// Transitions autorisées (miroir du backend — le backend reste l'autorité)
const TRANSITIONS: Record<string, string[]> = {
  proposee: ['acceptee_client', 'passee', 'refusee'],
  acceptee_client: ['passee', 'refusee', 'proposee'],
  refusee: ['proposee'],
  passee: [],
}

const ACTIONS_STATUT: Record<string, { label: string; cls: string }> = {
  acceptee_client: { label: 'Acceptée par le client', cls: 'btn-secondary' },
  passee:          { label: 'Marquer passée',         cls: 'btn-primary' },
  refusee:         { label: 'Refusée par le client',  cls: 'btn-secondary text-red-600' },
  proposee:        { label: 'Re-proposer',            cls: 'btn-secondary' },
}

function EffetBadge({ label, valeur }: { label: string; valeur: number }) {
  if (valeur === 0) return null
  const positif = valeur > 0
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
      positif ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
    }`}>
      {positif ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {label} {positif ? '+' : ''}{valeur.toLocaleString('fr-FR')}
    </span>
  )
}

// ─── Éditeur de lignes (équilibre en direct) ──────────────────────────────────

interface LigneEdit { compte: string; libelle: string; debit: string; credit: string }

function lignesVides(): LigneEdit[] {
  return [
    { compte: '', libelle: '', debit: '', credit: '' },
    { compte: '', libelle: '', debit: '', credit: '' },
  ]
}

function num(v: string): number {
  const n = parseFloat((v || '').replace(',', '.'))
  return isNaN(n) ? 0 : n
}

function LignesEditor({
  lignes, onChange,
}: {
  lignes: LigneEdit[]
  onChange: (lignes: LigneEdit[]) => void
}) {
  const totalD = lignes.reduce((s, l) => s + num(l.debit), 0)
  const totalC = lignes.reduce((s, l) => s + num(l.credit), 0)
  const equilibre = Math.abs(totalD - totalC) < 0.01 && totalD > 0

  const setLigne = (i: number, patch: Partial<LigneEdit>) => {
    const next = lignes.map((l, j) => (j === i ? { ...l, ...patch } : l))
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[7rem_1fr_7rem_7rem_2rem] gap-2 text-xs font-medium text-slate-500 px-1">
        <span>Compte</span><span>Libellé</span>
        <span className="text-right">Débit</span><span className="text-right">Crédit</span><span />
      </div>
      {lignes.map((l, i) => (
        <div key={i} className="grid grid-cols-[7rem_1fr_7rem_7rem_2rem] gap-2 items-center">
          <input className="input-field text-sm" placeholder="601000" value={l.compte}
            onChange={(e) => setLigne(i, { compte: e.target.value })} />
          <input className="input-field text-sm" placeholder="Libellé de la ligne" value={l.libelle}
            onChange={(e) => setLigne(i, { libelle: e.target.value })} />
          <input className="input-field text-sm text-right" type="number" min="0" step="any"
            placeholder="0" value={l.debit}
            onChange={(e) => setLigne(i, { debit: e.target.value, credit: e.target.value ? '' : l.credit })} />
          <input className="input-field text-sm text-right" type="number" min="0" step="any"
            placeholder="0" value={l.credit}
            onChange={(e) => setLigne(i, { credit: e.target.value, debit: e.target.value ? '' : l.debit })} />
          <button
            onClick={() => onChange(lignes.filter((_, j) => j !== i))}
            disabled={lignes.length <= 2}
            className="p-1 text-slate-300 hover:text-red-500 disabled:opacity-30 transition-colors"
            title="Supprimer la ligne"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
      <div className="flex items-center justify-between pt-1">
        <button
          onClick={() => onChange([...lignes, { compte: '', libelle: '', debit: '', credit: '' }])}
          className="text-xs text-primary-600 hover:text-primary-800 flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" /> Ajouter une ligne
        </button>
        <div className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${
          equilibre ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
        }`}>
          Débits {totalD.toLocaleString('fr-FR')} · Crédits {totalC.toLocaleString('fr-FR')}
          {equilibre ? ' — équilibrée ✓' : totalD || totalC ? ' — déséquilibrée' : ''}
        </div>
      </div>
    </div>
  )
}

// ─── Modal création / édition ─────────────────────────────────────────────────

function EcritureModal({
  projetId, initiale, exceptions, onClose, onSaved,
}: {
  projetId: string
  initiale: Partial<EcritureAjustement> & { lignes?: LigneAjustement[] } | null
  exceptions: Exception[]
  onClose: () => void
  onSaved: () => void
}) {
  const { post, patch } = useApi()
  const toast = useToast()
  const isEdit = !!initiale?.id

  const [libelle, setLibelle] = useState(initiale?.libelle || '')
  const [type, setType] = useState(initiale?.type_anomalie || 'factuelle')
  const [justification, setJustification] = useState(initiale?.justification || '')
  const [exceptionId, setExceptionId] = useState(initiale?.exception_id || '')
  const [lignes, setLignes] = useState<LigneEdit[]>(
    initiale?.lignes?.length
      ? initiale.lignes.map((l) => ({
          compte: l.compte, libelle: l.libelle || '',
          debit: l.debit ? String(l.debit) : '', credit: l.credit ? String(l.credit) : '',
        }))
      : lignesVides()
  )
  const [saving, setSaving] = useState(false)
  const [proposing, setProposing] = useState(false)

  const totalD = lignes.reduce((s, l) => s + num(l.debit), 0)
  const totalC = lignes.reduce((s, l) => s + num(l.credit), 0)
  const valide = libelle.trim().length >= 5 && Math.abs(totalD - totalC) < 0.01 && totalD > 0
    && lignes.every((l) => l.compte.trim())

  const handleProposerIA = async () => {
    if (!exceptionId) { toast.error('Choisissez d\'abord l\'exception liée.'); return }
    setProposing(true)
    try {
      const res = await post(`/projets/${projetId}/ajustements/proposer/${exceptionId}`)
      const p = res.proposition
      setLibelle(p.libelle || '')
      setType(p.type_anomalie || 'factuelle')
      setJustification(p.justification || '')
      setLignes((p.lignes || []).map((l: LigneAjustement) => ({
        compte: l.compte, libelle: l.libelle || '',
        debit: l.debit ? String(l.debit) : '', credit: l.credit ? String(l.credit) : '',
      })))
      toast.success(`Écriture proposée par l'IA (montant imposé par le moteur : ${formatMontant(p.montant)}). Relisez avant d'enregistrer.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setProposing(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    const payload = {
      libelle: libelle.trim(),
      type_anomalie: type,
      justification: justification || null,
      exception_id: exceptionId || null,
      lignes: lignes.map((l) => ({
        compte: l.compte.trim(), libelle: l.libelle || null,
        debit: num(l.debit), credit: num(l.credit),
      })),
    }
    try {
      if (isEdit) {
        await patch(`/projets/${projetId}/ajustements/${initiale!.id}`, payload)
        toast.success('Écriture modifiée.')
      } else {
        await post(`/projets/${projetId}/ajustements`, payload)
        toast.success('Écriture d\'ajustement créée (statut : proposée au client).')
      }
      onSaved()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const exceptionsAvecMontant = exceptions.filter(
    (e) => (e.montant_incidence && e.montant_incidence > 0) || (e.montant_estime && e.montant_estime > 0)
  )

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.97, y: 10 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.97, y: 10 }}
        className="bg-white rounded-2xl shadow-modal w-full max-w-2xl flex flex-col max-h-[90vh]"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
          <h2 className="font-semibold text-slate-900">
            {isEdit ? 'Modifier l\'écriture d\'ajustement' : 'Nouvelle écriture d\'ajustement'}
          </h2>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg"><X className="w-4 h-4" /></button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          {/* Exception liée + proposition IA */}
          <div className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-3 space-y-2">
            <label className="block text-xs font-semibold text-indigo-700">
              Exception liée (optionnel) — l'IA peut proposer le schéma comptable
            </label>
            <div className="flex items-center gap-2">
              <select
                className="input-field text-sm flex-1"
                value={exceptionId}
                onChange={(e) => setExceptionId(e.target.value)}
              >
                <option value="">— Saisie libre (aucune exception liée) —</option>
                {exceptionsAvecMontant.map((e) => (
                  <option key={e.id} value={e.id}>
                    [{e.controle_ref}] {(e.description || '').slice(0, 60)}… —{' '}
                    {(e.montant_incidence || e.montant_estime || 0).toLocaleString('fr-FR')} FDJ
                  </option>
                ))}
              </select>
              <button
                onClick={handleProposerIA}
                disabled={!exceptionId || proposing}
                className="btn-secondary text-xs py-2 flex-shrink-0"
              >
                {proposing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                Proposer par IA
              </button>
            </div>
            <p className="text-[11px] text-indigo-600/80 flex items-start gap-1">
              <Wand2 className="w-3 h-3 flex-shrink-0 mt-0.5" />
              Le montant vient toujours du moteur (incidence saisie ou écart calculé) — l'IA ne
              propose que les comptes et le sens, et le moteur vérifie l'équilibre.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Libellé de l'écriture <span className="text-red-500">*</span>
            </label>
            <input className="input-field" placeholder="Ex : Rattachement de la facture F-2025-118 à l'exercice"
              value={libelle} onChange={(e) => setLibelle(e.target.value)} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Nature de l'anomalie ({normeLabel('450')})
            </label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(TYPES).map(([val, t]) => (
                <label key={val} className={`p-2.5 rounded-lg border cursor-pointer transition-colors text-center ${
                  type === val ? 'border-indigo-400 bg-indigo-50' : 'border-border hover:border-slate-300'
                }`}>
                  <input type="radio" className="sr-only" checked={type === val}
                    onChange={() => setType(val as any)} />
                  <span className="block text-sm font-medium text-slate-800">{t.label}</span>
                  <span className="block text-[11px] text-slate-500">{t.hint}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Lignes de l'écriture <span className="text-red-500">*</span>
            </label>
            <LignesEditor lignes={lignes} onChange={setLignes} />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Justification</label>
            <textarea className="input-field min-h-20 resize-none text-sm"
              placeholder="Pourquoi cette écriture corrige l'anomalie (figure au dossier)…"
              value={justification} onChange={(e) => setJustification(e.target.value)} />
          </div>
        </div>

        <div className="flex gap-3 px-6 py-4 border-t border-border flex-shrink-0">
          <button onClick={onClose} className="btn-secondary flex-1">Annuler</button>
          <button onClick={handleSave} disabled={!valide || saving} className="btn-primary flex-1">
            {saving ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
            {isEdit ? 'Enregistrer les modifications' : 'Créer l\'écriture (proposée)'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ─── Carte écriture ───────────────────────────────────────────────────────────

function EcritureCard({
  e, onStatut, onEdit, onDelete, changing,
}: {
  e: EcritureAjustement
  onStatut: (id: string, statut: string) => void
  onEdit: (e: EcritureAjustement) => void
  onDelete: (id: string) => void
  changing: string | null
}) {
  const statut = STATUTS[e.statut]
  const transitions = TRANSITIONS[e.statut] || []
  const modifiable = e.statut !== 'passee'

  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`card p-5 border-l-4 ${
        e.statut === 'passee' ? 'border-l-emerald-400'
          : e.statut === 'refusee' ? 'border-l-red-400'
          : e.statut === 'acceptee_client' ? 'border-l-amber-400'
          : 'border-l-blue-300'
      }`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-slate-800">{e.libelle}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${statut.cls}`}>{statut.label}</span>
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
              {e.type_libelle}
            </span>
            {!!e.issu_ia && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                <Wand2 className="w-2.5 h-2.5 inline mr-0.5" />IA
              </span>
            )}
            {e.exception_id && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-orange-50 text-orange-600">
                <Link2 className="w-2.5 h-2.5 inline mr-0.5" />Exception liée
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">
              Montant : <strong>{formatMontant(e.total_debits)}</strong>
              {e.cree_le && <> · {formatDate(e.cree_le)}</>}
            </span>
            <EffetBadge label="Résultat" valeur={e.effet_resultat} />
            <EffetBadge label="Cap. propres" valeur={e.effet_capitaux_propres} />
          </div>
        </div>
      </div>

      {/* Lignes */}
      <div className="bg-slate-50 rounded-lg p-3 mb-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-400">
              <th className="text-left font-medium pb-1">Compte</th>
              <th className="text-left font-medium pb-1">Libellé</th>
              <th className="text-right font-medium pb-1">Débit</th>
              <th className="text-right font-medium pb-1">Crédit</th>
            </tr>
          </thead>
          <tbody>
            {e.lignes.map((l, i) => (
              <tr key={i} className="text-slate-700">
                <td className="py-0.5 font-mono">{l.compte}</td>
                <td className="py-0.5">{l.libelle || ''}</td>
                <td className="py-0.5 text-right">{l.debit ? l.debit.toLocaleString('fr-FR') : ''}</td>
                <td className="py-0.5 text-right">{l.credit ? l.credit.toLocaleString('fr-FR') : ''}</td>
              </tr>
            ))}
            <tr className="border-t border-slate-200 font-semibold text-slate-800">
              <td colSpan={2} className="pt-1">Totaux</td>
              <td className="pt-1 text-right">{e.total_debits.toLocaleString('fr-FR')}</td>
              <td className="pt-1 text-right">{e.total_credits.toLocaleString('fr-FR')}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {e.justification && (
        <p className="text-xs text-slate-500 mb-3 italic">{e.justification}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {transitions.map((s) => (
          <button
            key={s}
            onClick={() => onStatut(e.id, s)}
            disabled={changing === e.id}
            className={`${ACTIONS_STATUT[s].cls} text-xs py-1.5`}
          >
            {changing === e.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <ArrowRight className="w-3 h-3" />}
            {ACTIONS_STATUT[s].label}
          </button>
        ))}
        {modifiable && (
          <>
            <button onClick={() => onEdit(e)} className="btn-ghost text-xs py-1.5 text-slate-500">
              Modifier
            </button>
            {(e.statut === 'proposee' || e.statut === 'refusee') && (
              <button onClick={() => onDelete(e.id)} className="btn-ghost text-xs py-1.5 text-red-400 hover:text-red-600">
                <Trash2 className="w-3 h-3" /> Supprimer
              </button>
            )}
          </>
        )}
        {e.statut === 'passee' && (
          <span className="text-xs text-emerald-600 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            Comptabilisée — intégrée à la balance ajustée
          </span>
        )}
      </div>
    </motion.div>
  )
}

// ─── Balance ajustée ──────────────────────────────────────────────────────────

function BalanceAjusteeSection({ projetId, refresh }: { projetId: string; refresh: number }) {
  const { get } = useApi()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<{ lignes: LigneBalance[]; nb_comptes_ajustes: number;
    total_ajustements: number } | null>(null)

  useEffect(() => {
    if (!open) return
    get(`/projets/${projetId}/balance-ajustee?seulement_ajustes=true`)
      .then(setData).catch(() => setData(null))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, refresh, projetId])

  return (
    <div className="card p-5">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-sm font-semibold text-slate-800 w-full">
        {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        <Scale className="w-4 h-4 text-slate-500" />
        Balance ajustée
        <span className="text-xs font-normal text-slate-400">
          balance importée + écritures passées — comptes ajustés uniquement
        </span>
      </button>
      {open && (
        <div className="mt-4">
          {!data ? <Spinner size="sm" /> : data.nb_comptes_ajustes === 0 ? (
            <p className="text-xs text-slate-400">
              Aucune écriture passée : la balance ajustée est identique à la balance importée.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-400 border-b border-border">
                  <th className="text-left font-medium py-1.5">Compte</th>
                  <th className="text-right font-medium py-1.5">Solde brut</th>
                  <th className="text-right font-medium py-1.5">Ajustements</th>
                  <th className="text-right font-medium py-1.5">Solde ajusté</th>
                </tr>
              </thead>
              <tbody>
                {data.lignes.map((l) => (
                  <tr key={l.compte} className="border-b border-slate-50 text-slate-700">
                    <td className="py-1.5 font-mono">{l.compte}</td>
                    <td className="py-1.5 text-right">{l.solde_brut.toLocaleString('fr-FR')}</td>
                    <td className={`py-1.5 text-right font-semibold ${
                      l.ajustement > 0 ? 'text-emerald-600' : 'text-red-600'
                    }`}>
                      {l.ajustement > 0 ? '+' : ''}{l.ajustement.toLocaleString('fr-FR')}
                    </td>
                    <td className="py-1.5 text-right font-semibold text-slate-900">
                      {l.solde_ajuste.toLocaleString('fr-FR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function Ajustements() {
  const { projetId } = useParams<{ projetId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { get, patch, del } = useApi()
  const toast = useToast()
  useSyncProjet()

  const [ecritures, setEcritures] = useState<EcritureAjustement[]>([])
  const [synthese, setSynthese] = useState<SyntheseAjustements | null>(null)
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<Partial<EcritureAjustement> | null | false>(false)
  const [changing, setChanging] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)

  const load = useCallback(async () => {
    if (!projetId) return
    try {
      const [aj, exc] = await Promise.all([
        get(`/projets/${projetId}/ajustements`),
        get(`/projets/${projetId}/exceptions`),
      ])
      setEcritures(aj.ecritures || [])
      setSynthese(aj.synthese || null)
      setExceptions(exc.exceptions || [])
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetId])

  useEffect(() => { load() }, [load])

  // Arrivée depuis la page Exceptions : ?exception=ID → ouvre le modal pré-lié
  useEffect(() => {
    const excId = searchParams.get('exception')
    if (excId && !loading) {
      setModal({ exception_id: excId })
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading])

  const handleStatut = async (id: string, statut: string) => {
    setChanging(id)
    try {
      await patch(`/projets/${projetId}/ajustements/${id}`, { statut })
      if (statut === 'passee') {
        toast.success('Écriture passée : elle alimente désormais la balance ajustée. '
          + 'Pensez à trancher l\'exception liée comme « corrigée par le client ».')
      }
      await load()
      setRefresh((r) => r + 1)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setChanging(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Supprimer cette écriture proposée ?')) return
    try {
      await del(`/projets/${projetId}/ajustements/${id}`)
      await load()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const np = synthese?.non_passees

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Écritures d'ajustement"
        subtitle={`État récapitulatif des ajustements (${normeLabel('450')})`}
        actions={
          <button onClick={() => setModal(null)} className="btn-primary">
            <Plus className="w-4 h-4" />
            Nouvelle écriture
          </button>
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Synthèse (le « SUM ») */}
          {synthese && synthese.nb_total > 0 && (
            <div className="grid grid-cols-4 gap-3">
              <div className="card p-4">
                <p className="text-xs text-slate-400">Écritures</p>
                <p className="text-xl font-bold text-slate-800">{synthese.nb_total}</p>
                <p className="text-[11px] text-slate-400">{synthese.nb_passees} passée(s) · {synthese.nb_refusees} refusée(s)</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-slate-400">Anomalies subsistantes</p>
                <p className="text-xl font-bold text-slate-800">{synthese.nb_non_passees}</p>
                <p className="text-[11px] text-slate-400">écritures non passées</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-slate-400">Effet résultat (non passées)</p>
                <p className={`text-xl font-bold ${!np || np.effet_resultat === 0 ? 'text-slate-800' : np.effet_resultat > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {np ? `${np.effet_resultat > 0 ? '+' : ''}${np.effet_resultat.toLocaleString('fr-FR')}` : '—'}
                </p>
                <p className="text-[11px] text-slate-400">si toutes étaient passées</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-slate-400">Effet cap. propres (non passées)</p>
                <p className={`text-xl font-bold ${!np || np.effet_capitaux_propres === 0 ? 'text-slate-800' : np.effet_capitaux_propres > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {np ? `${np.effet_capitaux_propres > 0 ? '+' : ''}${np.effet_capitaux_propres.toLocaleString('fr-FR')}` : '—'}
                </p>
                <p className="text-[11px] text-slate-400">{normeLabel('450')}</p>
              </div>
            </div>
          )}

          <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 border border-blue-200">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-blue-800">
              Une écriture d'ajustement traduit une anomalie en langage comptable (comptes
              débités / crédités). Cycle de vie : <strong>proposée → acceptée par le client →
              passée</strong> (comptabilisée) ou <strong>refusée</strong>. Les écritures passées
              construisent la <strong>balance ajustée</strong> ; les non passées chiffrent les
              anomalies subsistantes de l'état récapitulatif {normeLabel('450')}, versé au dossier.
            </p>
          </div>

          {loading ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : ecritures.length === 0 ? (
            <EmptyState
              icon={Scale}
              title="Aucune écriture d'ajustement"
              description="Créez une écriture manuellement, ou depuis une exception tranchée « non corrigée » (l'IA propose le schéma comptable, le montant vient du moteur)."
            />
          ) : (
            <AnimatePresence>
              {ecritures.map((e) => (
                <EcritureCard
                  key={e.id}
                  e={e}
                  onStatut={handleStatut}
                  onEdit={(ec) => setModal(ec)}
                  onDelete={handleDelete}
                  changing={changing}
                />
              ))}
            </AnimatePresence>
          )}

          <BalanceAjusteeSection projetId={projetId!} refresh={refresh} />
        </div>
      </div>

      <AnimatePresence>
        {modal !== false && (
          <EcritureModal
            projetId={projetId!}
            initiale={modal}
            exceptions={exceptions}
            onClose={() => setModal(false)}
            onSaved={() => { setModal(false); load(); setRefresh((r) => r + 1) }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
