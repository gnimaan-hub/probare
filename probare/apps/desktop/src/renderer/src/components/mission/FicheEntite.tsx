import { useEffect, useState } from 'react'
import { Save, Plus, Check, X, Users } from 'lucide-react'
import { Spinner } from '../ui/Spinner'
import { useApi } from '../../hooks/useApi'
import { useToast } from '../../hooks/useToast'

interface Dirigeant { nom: string; fonction: string; email?: string }

const FORMES_JURIDIQUES = ['SA', 'SARL', 'SNC', 'SCS', 'GIE', 'Association', 'EP', 'EPA', 'Autre']

/**
 * Prise de connaissance de l'entité auditée (ISA 315).
 *
 * Rattachée au CADRAGE : « qui est l'entité » relève de la définition de la
 * mission, pas de la planification. Le composant s'auto-charge depuis
 * /planification (la ligne est créée à la volée) et sauvegarde via
 * /planification/fiche-entite — l'endpoint backend est inchangé, seule sa place
 * dans le parcours change (fin de la redondance avec l'ancienne étape 4).
 */
export function FicheEntite({ projetId, locked }: { projetId: string; locked: boolean }) {
  const { get, patch } = useApi()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    forme_juridique: '', date_creation_entreprise: '', activites_principales: '',
    marches_principaux: '', systeme_information: '', effectif: '', observations: '',
  })
  const [dirigeants, setDirigeants] = useState<Dirigeant[]>([])
  const [facteurs, setFacteurs] = useState<string[]>([])
  const [newFacteur, setNewFacteur] = useState('')
  const [newDir, setNewDir] = useState({ nom: '', fonction: '', email: '' })
  const [showAddDir, setShowAddDir] = useState(false)

  useEffect(() => {
    if (!projetId) return
    get(`/projets/${projetId}/planification`).then((res) => {
      const plan = res.planification || {}
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
    }).catch(() => {}).finally(() => setLoading(false))
  }, [projetId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await patch(`/projets/${projetId}/planification/fiche-entite`, {
        ...form,
        effectif: form.effectif ? parseInt(form.effectif) : undefined,
        dirigeants,
        facteurs_risque_inherent: facteurs,
      })
      toast.success("Connaissance de l'entité enregistrée.")
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

  if (loading) {
    return <div className="card p-8 flex justify-center"><Spinner /></div>
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
            Enregistrer la connaissance de l'entité
          </button>
        </div>
      )}
    </div>
  )
}
