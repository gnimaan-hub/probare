import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle, ClipboardPaste, Play, Scale, Info } from 'lucide-react'
import { Spinner } from '../ui/Spinner'
import { useApi } from '../../hooks/useApi'
import { useToast } from '../../hooks/useToast'
import { formatMontant, normeLabel } from '../../lib/utils'

interface Poste {
  id: string
  cote: string
  libelle: string
  montant: number
  rubrique_ref: string | null
}

interface LigneRapprochement {
  rubrique_ref: string
  rubrique_libelle: string
  cote: string
  cote_libelle: string
  postes: { id: string; libelle: string; montant: number }[]
  montant_presente: number
  montant_audite: number
  ecart: number
  ecart_pct: number | null
  statut: string
}

interface Rubrique { ref: string; libelle: string; type: string; groupe: string }

const COTES = [
  { id: 'actif', label: 'Bilan — Actif', types: ['bilan_actif', 'bilan_mixte'] },
  { id: 'passif', label: 'Bilan — Passif', types: ['bilan_passif', 'bilan_mixte'] },
  { id: 'charges', label: 'Résultat — Charges', types: ['resultat_charges'] },
  { id: 'produits', label: 'Résultat — Produits', types: ['resultat_produits'] },
]

const STATUT_STYLE: Record<string, string> = {
  concordant: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  ecart: 'bg-amber-50 text-amber-700 border-amber-200',
  ecart_significatif: 'bg-red-50 text-red-700 border-red-200',
}

const STATUT_LABEL: Record<string, string> = {
  concordant: 'Cadre',
  ecart: 'Écart sous le seuil',
  ecart_significatif: 'Écart significatif',
}

/**
 * Analyse un tableau collé depuis le bilan ou le compte de résultat du client.
 * Une ligne = un poste : libellé, puis le montant en dernière colonne. Les
 * séparateurs usuels d'un copier-coller (tabulation, point-virgule) sont
 * acceptés ; les montants suivent la notation française (espaces, virgule).
 */
export function parserPostes(texte: string): { libelle: string; montant: number }[] {
  const out: { libelle: string; montant: number }[] = []
  for (const brute of texte.split('\n')) {
    const ligne = brute.trim()
    if (!ligne) continue
    const cellules = ligne.split(/\t|;|\s{2,}/).map((c) => c.trim()).filter(Boolean)
    if (cellules.length < 2) continue
    const libelle = cellules.slice(0, -1).join(' ').trim()
    const brut = cellules[cellules.length - 1]
      .replace(/[\s ]/g, '')
      .replace(/[^0-9,.\-()]/g, '')
    const negatifParenthese = /^\(.*\)$/.test(cellules[cellules.length - 1].trim())
    const normalise = brut.replace(/[()]/g, '').replace(/\.(?=\d{3}\b)/g, '').replace(',', '.')
    const montant = Number(normalise)
    if (!libelle || !Number.isFinite(montant)) continue
    out.push({ libelle, montant: negatifParenthese ? -Math.abs(montant) : montant })
  }
  return out
}

/**
 * Cadrage des états financiers PRÉSENTÉS par l'entité avec la balance auditée (P2-a).
 *
 * L'auditeur colle le bilan et le compte de résultat publiés ; chaque poste est
 * rattaché à une rubrique de la feuille maîtresse et l'écart est calculé en
 * Python. Au-delà du seuil, l'écart devient une exception standard.
 */
export function CadrageEtatsFinanciers({ projetId, referentiel }: {
  projetId: string
  referentiel?: string
}) {
  const { get, put, post } = useApi()
  const toast = useToast()
  const [postes, setPostes] = useState<Poste[]>([])
  const [rap, setRap] = useState<any>(null)
  const [rubriques, setRubriques] = useState<Rubrique[]>([])
  const [chargement, setChargement] = useState(true)
  const [envoi, setEnvoi] = useState(false)
  const [cadrageEnCours, setCadrageEnCours] = useState(false)
  const [saisie, setSaisie] = useState<Record<string, string>>({})
  const [modeSaisie, setModeSaisie] = useState(false)

  const charger = async () => {
    try {
      const [d, r] = await Promise.all([
        get(`/projets/${projetId}/etats-financiers-presentes`),
        get(`/rubriques${referentiel ? `?referentiel=${referentiel}` : ''}`),
      ])
      setPostes(d.postes || [])
      setRap(d.rapprochement || null)
      setRubriques(r.rubriques || [])
      setModeSaisie((d.postes || []).length === 0)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setChargement(false)
    }
  }

  useEffect(() => { if (projetId) charger() }, [projetId])

  const apercu = useMemo(
    () => COTES.map((c) => ({ cote: c.id, lignes: parserPostes(saisie[c.id] || '') })),
    [saisie],
  )
  const nbSaisis = apercu.reduce((n, a) => n + a.lignes.length, 0)

  const enregistrer = async () => {
    const corps = apercu.flatMap((a) =>
      a.lignes.map((l) => ({ cote: a.cote, libelle: l.libelle, montant: l.montant })))
    if (corps.length === 0) {
      toast.warning('Collez au moins un poste avant d\'enregistrer.')
      return
    }
    setEnvoi(true)
    try {
      const d = await put(`/projets/${projetId}/etats-financiers-presentes`,
                          { postes: corps, rattacher_auto: true })
      setPostes(d.postes || [])
      setRap(d.rapprochement || null)
      setModeSaisie(false)
      toast.success(`${corps.length} poste(s) enregistré(s), ${d.nb_rattaches_auto} rattaché(s) automatiquement.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setEnvoi(false)
    }
  }

  const rattacher = async (posteId: string, ref: string) => {
    try {
      const d = await put(`/projets/${projetId}/etats-financiers-presentes/${posteId}/rubrique`,
                          { rubrique_ref: ref || null })
      setPostes(d.postes || [])
      setRap(d.rapprochement || null)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const lancerCadrage = async () => {
    setCadrageEnCours(true)
    try {
      const d = await post(`/projets/${projetId}/controles/cadrage-etats-financiers`)
      setRap(d.rapprochement || null)
      toast.success(d.nb_exceptions === 0
        ? 'Les états financiers présentés cadrent avec la balance auditée.'
        : `${d.nb_exceptions} exception(s) levée(s) — à trancher dans Exceptions.`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setCadrageEnCours(false)
    }
  }

  if (chargement) return <div className="card p-6 flex justify-center"><Spinner /></div>

  const syn = rap?.synthese
  const totaux = rap?.totaux

  return (
    <div className="space-y-4">
      <div className="card p-4 flex gap-3">
        <Info className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-600">
          Rapprochement des états financiers <strong>présentés par l'entité</strong> avec la balance
          auditée, poste par poste. Chaque poste publié est rattaché à une rubrique de la feuille
          maîtresse ; tout écart supérieur au seuil de signification devient une exception standard
          ({normeLabel('700')}). Saisissez les montants tels qu'ils sont publiés — positifs des deux
          côtés du bilan.
        </p>
      </div>

      {(modeSaisie || postes.length === 0) && (
        <div className="card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <ClipboardPaste className="w-4 h-4 text-primary-600" />
            <h3 className="font-semibold text-slate-900">Coller les états financiers publiés</h3>
          </div>
          <p className="text-xs text-slate-500">
            Une ligne par poste : libellé puis montant (« Clients et comptes rattachés ⇥ 5 400 000 »).
            Un copier-coller depuis Excel convient tel quel.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {COTES.map((c) => (
              <div key={c.id}>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  {c.label}
                  {(saisie[c.id] || '').trim() && (
                    <span className="text-slate-400 font-normal">
                      {' '}— {parserPostes(saisie[c.id] || '').length} poste(s) reconnu(s)
                    </span>
                  )}
                </label>
                <textarea
                  className="input-field text-sm min-h-[120px] font-mono text-[11px]"
                  value={saisie[c.id] || ''}
                  onChange={(e) => setSaisie({ ...saisie, [c.id]: e.target.value })}
                />
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={enregistrer} disabled={envoi || nbSaisis === 0} className="btn-primary text-sm">
              {envoi ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
              Enregistrer {nbSaisis > 0 ? `${nbSaisis} poste(s)` : ''}
            </button>
            {postes.length > 0 && (
              <button onClick={() => setModeSaisie(false)} className="btn-secondary text-sm">
                Annuler
              </button>
            )}
          </div>
        </div>
      )}

      {postes.length > 0 && !modeSaisie && (
        <>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-primary-600" />
              <h3 className="font-semibold text-slate-900">
                Cadrage — {syn?.nb_lignes || 0} rubrique(s) rapprochée(s)
              </h3>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setModeSaisie(true)} className="btn-secondary text-sm">
                Remplacer les états
              </button>
              <button onClick={lancerCadrage} disabled={cadrageEnCours} className="btn-primary text-sm">
                {cadrageEnCours ? <Spinner size="sm" /> : <Play className="w-4 h-4" />}
                Lancer le cadrage
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Cadrent', val: syn?.nb_concordants ?? 0 },
              { label: 'Écarts significatifs', val: syn?.nb_ecarts_significatifs ?? 0,
                alerte: (syn?.nb_ecarts_significatifs ?? 0) > 0 },
              { label: 'Postes non rattachés', val: syn?.nb_non_rattaches ?? 0,
                alerte: (syn?.nb_non_rattaches ?? 0) > 0 },
              { label: 'Rubriques absentes des EF', val: syn?.nb_absentes ?? 0,
                alerte: (syn?.nb_absentes ?? 0) > 0 },
            ].map((s) => (
              <div key={s.label} className="card p-3">
                <div className="text-[11px] text-slate-500">{s.label}</div>
                <div className={`text-lg font-semibold mt-0.5 ${s.alerte ? 'text-red-600' : 'text-slate-800'}`}>
                  {s.val}
                </div>
              </div>
            ))}
          </div>

          {rap?.equilibre_bilan?.applicable && !rap.equilibre_bilan.equilibre && (
            <div className="card p-4 border-red-200 bg-red-50 flex gap-3">
              <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">
                <strong>Le bilan présenté ne s'équilibre pas.</strong> Actif{' '}
                {formatMontant(totaux?.actif_presente)} contre passif{' '}
                {formatMontant(totaux?.passif_presente)}, écart {formatMontant(rap.equilibre_bilan.ecart)}.
              </p>
            </div>
          )}
          {rap?.coherence_resultat?.applicable && !rap.coherence_resultat.coherent && (
            <div className="card p-4 border-red-200 bg-red-50 flex gap-3">
              <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">
                <strong>Le résultat présenté ne correspond pas au résultat audité.</strong>{' '}
                {formatMontant(totaux?.resultat_presente)} présenté contre{' '}
                {formatMontant(totaux?.resultat_audite)} issu de la balance auditée, écart{' '}
                {formatMontant(rap.coherence_resultat.ecart)}.
              </p>
            </div>
          )}

          <div className="card overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead>
                <tr className="border-b border-border text-xs text-slate-500">
                  <th className="text-left px-4 py-2 font-medium">Rubrique</th>
                  <th className="text-right px-4 py-2 font-medium">Présenté</th>
                  <th className="text-right px-4 py-2 font-medium">Audité</th>
                  <th className="text-right px-4 py-2 font-medium">Écart</th>
                  <th className="text-left px-4 py-2 font-medium">Statut</th>
                </tr>
              </thead>
              <tbody>
                {(rap?.lignes || []).map((l: LigneRapprochement) => (
                  <tr key={`${l.cote}:${l.rubrique_ref}`} className="border-b border-border/60">
                    <td className="px-4 py-2">
                      <div className="text-slate-800">{l.rubrique_libelle}</div>
                      <div className="text-[11px] text-slate-400">
                        {l.cote_libelle} · {l.postes.map((p) => p.libelle).join(', ')}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">{formatMontant(l.montant_presente)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{formatMontant(l.montant_audite)}</td>
                    <td className={`px-4 py-2 text-right tabular-nums ${
                      l.statut === 'ecart_significatif' ? 'text-red-600 font-medium' : ''}`}>
                      {formatMontant(l.ecart)}
                      {l.ecart_pct !== null && Math.abs(l.ecart) > 1 && (
                        <span className="text-[11px] text-slate-400"> ({l.ecart_pct} %)</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`text-[11px] px-1.5 py-0.5 rounded border ${
                        STATUT_STYLE[l.statut] || 'bg-slate-50 border-slate-200 text-slate-600'}`}>
                        {STATUT_LABEL[l.statut] || l.statut}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(rap?.non_rattaches || []).length > 0 && (
            <div className="card p-4">
              <h4 className="text-sm font-semibold text-slate-800 mb-1">
                Postes présentés non rattachés ({rap.non_rattaches.length})
              </h4>
              <p className="text-xs text-slate-500 mb-3">
                Le rattachement automatique n'a pas tranché. Tant qu'un poste n'est pas rattaché,
                il n'est comparé à rien — choisissez sa rubrique.
              </p>
              <div className="space-y-2">
                {rap.non_rattaches.map((p: any) => (
                  <div key={p.id} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-slate-800">{p.libelle}</span>
                      <span className="text-[11px] text-slate-400"> · {formatMontant(p.montant)}</span>
                    </div>
                    <select
                      className="input-field text-xs max-w-[320px]"
                      defaultValue=""
                      onChange={(e) => rattacher(p.id, e.target.value)}
                    >
                      <option value="">— Rattacher à une rubrique —</option>
                      {rubriques
                        .filter((r) => (COTES.find((c) => c.id === p.cote)?.types || []).includes(r.type))
                        .map((r) => <option key={r.ref} value={r.ref}>{r.libelle}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(rap?.rubriques_absentes || []).length > 0 && (
            <div className="card p-4 border-amber-200 bg-amber-50/40">
              <h4 className="text-sm font-semibold text-amber-800 mb-1">
                Rubriques auditées absentes des états présentés ({rap.rubriques_absentes.length})
              </h4>
              <p className="text-xs text-amber-700/80 mb-3">
                Ces postes existent dans la balance auditée pour un montant supérieur au seuil,
                mais n'apparaissent dans aucun poste publié.
              </p>
              <div className="space-y-1">
                {rap.rubriques_absentes.map((a: any) => (
                  <div key={a.rubrique_ref} className="flex justify-between gap-3 text-sm">
                    <span className="text-slate-700">{a.rubrique_libelle}</span>
                    <span className="tabular-nums text-slate-800">{formatMontant(a.montant_audite)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
