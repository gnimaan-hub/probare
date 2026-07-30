import { useEffect, useState, useCallback, useMemo, Fragment } from 'react'
import { useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Table2, ChevronDown, ChevronRight, CheckCircle, AlertTriangle, Info,
  Link2, Shuffle, RotateCcw, X, TrendingUp, TrendingDown,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { EmptyState } from '../components/ui/EmptyState'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useSyncProjet } from '../hooks/useProjet'
import { formatMontant, cn } from '../lib/utils'
import { CadrageEtatsFinanciers } from '../components/ef/CadrageEtatsFinanciers'

// ─── Types (miroir de /feuilles-maitresses) ───────────────────────────────────

interface CompteFeuille {
  compte: string
  libelle: string
  solde_brut: number
  ajustement: number
  solde_ajuste: number
  solde_n1: number
  variation_abs: number
  variation_pct: number | null
  variation_notable: boolean
  absent_n: boolean
  sources: string[]
  reaffecte: boolean
}

interface TravauxRubrique {
  controles: { controle_ref: string; statut: string; valeur: number | null }[]
  exceptions_ouvertes: { id: string; controle_ref: string; severite: string; description: string }[]
  exceptions_tranchees: { id: string; controle_ref: string; severite: string; description: string }[]
  sondages: { id: string; libelle: string; cycle: string; taille_echantillon: number; nb_anomalies: number }[]
  circularisations: { id: string; compte: string; tiers: string; statut: string; ecart: number | null }[]
  ajustements: { id: string; libelle: string; statut: string; statut_libelle: string; total_debits: number }[]
}

interface Rubrique {
  ref: string
  libelle: string
  type: string
  type_libelle: string
  groupe: string
  prefixes: string[]
  sens: string
  cycles: string[]
  ordre: number
  signe_presentation: number
  comptes: CompteFeuille[]
  nb_comptes: number
  montant_brut: number
  montant_ajustements: number
  montant_ajuste: number
  montant_n1: number
  variation_abs: number
  variation_pct: number | null
  montant_presente: number
  montant_n1_presente: number
  sens_anormal: boolean
  vide: boolean
  travaux: TravauxRubrique
  nb_travaux: number
}

interface Groupe {
  libelle: string
  type: string
  refs: string[]
  montant_presente: number
  montant_n1_presente: number
  variation_abs: number
  variation_pct: number | null
}

interface Matrice {
  referentiel_comptable: string
  plan_approxime: boolean
  rubriques: Rubrique[]
  groupes: Groupe[]
  totaux: {
    actif: number; passif: number; charges: number; produits: number
    resultat: number; double_sens_actif: number; double_sens_passif: number
  }
  bouclage: {
    total_rubriques: number; total_hors_plan: number; total_balance: number
    ecart: number; boucle: boolean
  }
  equilibre_bilan: {
    ecart: number; equilibre: boolean; resultat_deja_comptabilise: boolean
  }
  comptes_non_affectes: { compte: string; solde_ajuste: number; motif: string }[]
  rubriques_non_affectees: { ref: string; libelle: string; nb_comptes: number; comptes: string[] }[]
  nb_comptes: number
  nb_rubriques_servies: number
  avec_comparatif: boolean
  overrides: { compte: string; rubrique_ref: string; motif?: string; decide_par?: string }[]
}

// ─── Présentation ─────────────────────────────────────────────────────────────

/** Montant dans le sens de lecture des états financiers (passif/produits positifs). */
function montantPresente(valeur: number, signe: number): number {
  return valeur * signe
}

function Pct({ value }: { value: number | null }) {
  if (value === null) return <span className="text-slate-300">—</span>
  const hausse = value > 0
  return (
    <span className={cn('inline-flex items-center gap-0.5 tabular-nums',
      Math.abs(value) >= 0.1 ? (hausse ? 'text-amber-600' : 'text-sky-600') : 'text-slate-500')}>
      {hausse ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {(value * 100).toFixed(1)} %
    </span>
  )
}

function Montant({ value, alerte }: { value: number; alerte?: boolean }) {
  if (Math.abs(value) < 0.01) return <span className="text-slate-300 tabular-nums">—</span>
  return (
    <span className={cn('tabular-nums', alerte && 'text-red-600 font-medium',
      value < 0 && !alerte && 'text-slate-500')}>
      {formatMontant(value, '')}
    </span>
  )
}

function BadgeBouclage({ bouclage }: { bouclage: Matrice['bouclage'] }) {
  if (bouclage.boucle) {
    return (
      <span className="badge-ok" title="Σ des rubriques = Σ de la balance ajustée">
        <CheckCircle className="w-3 h-3" /> Bouclage vérifié
      </span>
    )
  }
  return (
    <span className="badge-exception" title={`Écart de ${formatMontant(bouclage.ecart)}`}>
      <AlertTriangle className="w-3 h-3" /> Écart de bouclage {formatMontant(bouclage.ecart)}
    </span>
  )
}

// ─── Travaux rattachés ────────────────────────────────────────────────────────

function TravauxRattaches({ travaux }: { travaux: TravauxRubrique }) {
  const items: { label: string; detail: string; ton: string }[] = []
  if (travaux.controles.length) {
    const exc = travaux.controles.filter((c) => c.statut === 'exception').length
    items.push({
      label: `${travaux.controles.length} contrôle(s) exécuté(s)`,
      detail: exc ? `${exc} ayant levé une exception` : 'aucune anomalie relevée',
      ton: exc ? 'text-amber-700 bg-amber-50 border-amber-200' : 'text-emerald-700 bg-emerald-50 border-emerald-200',
    })
  }
  if (travaux.circularisations.length) {
    const recues = travaux.circularisations.filter(
      (c) => c.statut === 'reponse_recue' || c.statut === 'clos').length
    items.push({
      label: `${travaux.circularisations.length} confirmation(s) externe(s)`,
      detail: `${recues} réponse(s) reçue(s)`,
      ton: 'text-sky-700 bg-sky-50 border-sky-200',
    })
  }
  if (travaux.sondages.length) {
    const anomalies = travaux.sondages.reduce((n, s) => n + (s.nb_anomalies || 0), 0)
    items.push({
      label: `${travaux.sondages.length} sondage(s) sur pièces`,
      detail: `${anomalies} anomalie(s) relevée(s)`,
      ton: 'text-sky-700 bg-sky-50 border-sky-200',
    })
  }
  if (travaux.ajustements.length) {
    items.push({
      label: `${travaux.ajustements.length} écriture(s) d'ajustement`,
      detail: travaux.ajustements.map((a) => a.statut_libelle || a.statut).join(', '),
      ton: 'text-violet-700 bg-violet-50 border-violet-200',
    })
  }
  if (travaux.exceptions_tranchees.length) {
    items.push({
      label: `${travaux.exceptions_tranchees.length} anomalie(s) tranchée(s)`,
      detail: 'décision documentée au dossier',
      ton: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    })
  }
  if (travaux.exceptions_ouvertes.length) {
    items.push({
      label: `${travaux.exceptions_ouvertes.length} anomalie(s) ouverte(s)`,
      detail: travaux.exceptions_ouvertes.map((e) => e.controle_ref).join(', '),
      ton: 'text-red-700 bg-red-50 border-red-200',
    })
  }

  if (!items.length) {
    return (
      <p className="text-xs text-slate-400 italic px-3 py-2">
        Aucun travail d'audit n'est rattaché à cette rubrique.
      </p>
    )
  }
  return (
    <div className="flex flex-wrap gap-2 px-3 py-2">
      {items.map((it, i) => (
        <div key={i} className={cn('text-xs rounded-lg border px-2.5 py-1.5', it.ton)}>
          <span className="font-medium">{it.label}</span>
          <span className="opacity-70"> — {it.detail}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Réaffectation d'un compte ────────────────────────────────────────────────

function DialogueReaffectation({
  compte, rubriqueActuelle, rubriques, onFermer, onValider,
}: {
  compte: CompteFeuille
  rubriqueActuelle: Rubrique
  rubriques: Rubrique[]
  onFermer: () => void
  onValider: (ref: string, motif: string) => Promise<void>
}) {
  const [ref, setRef] = useState(rubriqueActuelle.ref)
  const [motif, setMotif] = useState('')
  const [envoi, setEnvoi] = useState(false)

  const parGroupe = useMemo(() => {
    const map = new Map<string, Rubrique[]>()
    rubriques.forEach((r) => {
      if (!map.has(r.groupe)) map.set(r.groupe, [])
      map.get(r.groupe)!.push(r)
    })
    return [...map.entries()]
  }, [rubriques])

  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50 p-4"
         onClick={onFermer}>
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
        className="card w-full max-w-lg p-5" onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-semibold text-slate-900">Réaffecter un compte</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {compte.compte} {compte.libelle && `— ${compte.libelle}`}
            </p>
          </div>
          <button onClick={onFermer} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-500 mb-3">
          Le plan de rubriques est un défaut par référentiel comptable. Votre jugement prime :
          la réaffectation est tracée dans l'historique et reprise dans les livrables.
        </p>

        <label className="block text-xs font-medium text-slate-600 mb-1">Rubrique d'états financiers</label>
        <select className="input-field mb-3" value={ref} onChange={(e) => setRef(e.target.value)}>
          {parGroupe.map(([groupe, rubs]) => (
            <optgroup key={groupe} label={groupe}>
              {rubs.map((r) => (
                <option key={r.ref} value={r.ref}>{r.libelle}</option>
              ))}
            </optgroup>
          ))}
        </select>

        <label className="block text-xs font-medium text-slate-600 mb-1">
          Motif de la réaffectation
        </label>
        <textarea
          className="input-field mb-4" rows={3} value={motif}
          onChange={(e) => setMotif(e.target.value)}
          placeholder="Ex. : compte 471000 apuré en compte de tiers après analyse du détail."
        />

        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onFermer}>Annuler</button>
          <button
            className="btn-primary" disabled={envoi || ref === rubriqueActuelle.ref}
            onClick={async () => {
              setEnvoi(true)
              try { await onValider(ref, motif) } finally { setEnvoi(false) }
            }}
          >
            {envoi ? <Spinner size="sm" /> : <Shuffle className="w-4 h-4" />}
            Réaffecter
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function FeuillesMaitresses() {
  useSyncProjet()
  const { projetId } = useParams<{ projetId: string }>()
  const { get, put, del } = useApi()
  const toast = useToast()

  const [matrice, setMatrice] = useState<Matrice | null>(null)
  const [chargement, setChargement] = useState(true)
  const [erreur, setErreur] = useState<string | null>(null)
  const [ouvertes, setOuvertes] = useState<Set<string>>(new Set())
  const [aReaffecter, setAReaffecter] = useState<{ compte: CompteFeuille; rubrique: Rubrique } | null>(null)
  // Le cadrage des états présentés se lit contre ces mêmes feuilles maîtresses :
  // deux vues d'un même objet, d'où l'onglet plutôt qu'un écran séparé.
  const [onglet, setOnglet] = useState<'feuilles' | 'cadrage'>('feuilles')

  const charger = useCallback(async () => {
    if (!projetId) return
    setChargement(true)
    try {
      setMatrice(await get<Matrice>(`/projets/${projetId}/feuilles-maitresses`))
      setErreur(null)
    } catch (e: any) {
      setErreur(e.message || 'Chargement impossible.')
    } finally {
      setChargement(false)
    }
  }, [projetId])

  useEffect(() => { charger() }, [charger])

  const basculer = (ref: string) => setOuvertes((s) => {
    const n = new Set(s)
    n.has(ref) ? n.delete(ref) : n.add(ref)
    return n
  })

  const reaffecter = async (compte: string, rubrique_ref: string, motif: string) => {
    await put(`/projets/${projetId}/feuilles-maitresses/affectations/${compte}`,
              { rubrique_ref, motif })
    toast.success(`Compte ${compte} réaffecté.`)
    setAReaffecter(null)
    await charger()
  }

  const retablirDefaut = async (compte: string) => {
    try {
      await del(`/projets/${projetId}/feuilles-maitresses/affectations/${compte}`)
      toast.success(`Affectation par défaut rétablie pour ${compte}.`)
      await charger()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  // Rubriques servies, indexées par grand poste pour l'affichage.
  const parGroupe = useMemo(() => {
    if (!matrice) return []
    const servies = matrice.rubriques.filter((r) => r.nb_comptes > 0)
    return matrice.groupes
      .map((g) => ({ groupe: g, rubriques: servies.filter((r) => g.refs.includes(r.ref)) }))
      .filter((x) => x.rubriques.length > 0)
  }, [matrice])

  if (chargement && !matrice) {
    return (
      <div className="flex-1 flex flex-col">
        <Header title="Feuilles maîtresses" />
        <div className="flex-1 flex items-center justify-center"><Spinner /></div>
      </div>
    )
  }

  if (erreur || !matrice) {
    return (
      <div className="flex-1 flex flex-col">
        <Header title="Feuilles maîtresses" />
        <EmptyState
          icon={Table2} title="Feuilles maîtresses indisponibles"
          description={erreur ?? 'Importez la balance de l’exercice pour construire les feuilles maîtresses.'}
        />
      </div>
    )
  }

  if (!matrice.nb_comptes) {
    return (
      <div className="flex-1 flex flex-col">
        <Header title="Feuilles maîtresses" />
        <EmptyState
          icon={Table2} title="Aucun compte à présenter"
          description="Importez la balance de l’exercice à l’étape Ingestion : les feuilles maîtresses en découlent automatiquement."
        />
      </div>
    )
  }

  const t = matrice.totaux
  // Sans balance N-1, les colonnes comparatives sont retirées : une variation
  // égale au solde N se lirait « tout le poste a varié », alors qu'il n'y a
  // simplement rien à comparer.
  const avecN1 = matrice.avec_comparatif

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Header
        title="Feuilles maîtresses"
        subtitle={`${matrice.nb_comptes} comptes · ${matrice.nb_rubriques_servies} rubriques d'états financiers`}
        actions={<BadgeBouclage bouclage={matrice.bouclage} />}
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Onglets : la balance regroupée d'un côté, son cadrage avec les EF publiés de l'autre */}
        <div className="flex gap-1 border-b border-border">
          {([
            ['feuilles', 'Feuilles maîtresses'],
            ['cadrage', 'Cadrage des états présentés'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setOnglet(id)}
              className={cn('px-4 py-2 text-sm border-b-2 -mb-px transition-colors',
                onglet === id
                  ? 'border-primary-500 text-primary-700 font-medium'
                  : 'border-transparent text-slate-500 hover:text-slate-700')}
            >
              {label}
            </button>
          ))}
        </div>

        {onglet === 'cadrage' && projetId && (
          <CadrageEtatsFinanciers projetId={projetId} referentiel={matrice.referentiel_comptable} />
        )}

        {onglet === 'feuilles' && (<>
        {/* Bandeau d'explication */}
        <div className="card p-4 flex gap-3">
          <Info className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-slate-600">
            Chaque rubrique d'états financiers regroupe les comptes qui la composent : solde issu de
            la balance importée, incidence des écritures d'ajustement passées et solde audité
            {avecN1 ? ', comparatif N-1 et variation' : ''}. Dépliez une rubrique pour voir le détail
            par compte et les travaux d'audit qui s'y rattachent. Les montants sont présentés dans le
            sens de lecture des états financiers — les postes de passif et de produits figurent en positif.
          </p>
        </div>

        {/* Alertes structurelles */}
        {!matrice.bouclage.boucle && (
          <div className="card p-4 border-red-200 bg-red-50 flex gap-3">
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-800">
              <p className="font-medium">Les feuilles maîtresses ne bouclent pas avec la balance.</p>
              <p className="mt-1">
                Total des rubriques {formatMontant(matrice.bouclage.total_rubriques)} contre
                {' '}{formatMontant(matrice.bouclage.total_balance)} en balance ajustée — écart de
                {' '}{formatMontant(matrice.bouclage.ecart)}. Un compte est perdu ou compté deux fois :
                la génération du dossier et du mémorandum reste bloquée tant que l'écart subsiste.
              </p>
            </div>
          </div>
        )}
        {!avecN1 && (
          <div className="card p-4 border-slate-200 bg-slate-50 flex gap-3">
            <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-slate-600">
              Aucune balance de l'exercice précédent n'est rattachée à la mission : les colonnes
              comparatives et les variations sont masquées, faute de terme de comparaison.
              Renseignez-la à l'étape Planification pour les faire apparaître ici et dans les livrables.
            </p>
          </div>
        )}
        {!matrice.equilibre_bilan.equilibre && !matrice.equilibre_bilan.resultat_deja_comptabilise && (
          <div className="card p-4 border-red-200 bg-red-50 flex gap-3">
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-800">
              <p className="font-medium">L'identité actif − passif = résultat n'est pas vérifiée.</p>
              <p className="mt-1">
                Écart de {formatMontant(matrice.equilibre_bilan.ecart)}, alors que le résultat n'est
                pas encore comptabilisé au bilan. Le bouclage ci-dessus ne teste que l'affectation des
                comptes — il tient même sur des soldes erronés. Cet écart-ci signale une balance
                incomplète ou mal interprétée à l'import : fiabilisez les soldes avant de vous appuyer
                sur ces feuilles maîtresses.
              </p>
            </div>
          </div>
        )}
        {matrice.plan_approxime && (
          <div className="card p-4 border-amber-200 bg-amber-50 flex gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800">
              Le référentiel comptable déclaré pour l'entité n'a pas de plan de rubriques propre :
              celui du Plan Comptable Général de Djibouti est appliqué. Relisez l'affectation des
              comptes et corrigez-la là où elle ne convient pas.
            </p>
          </div>
        )}
        {matrice.rubriques_non_affectees.length > 0 && (
          <div className="card p-4 border-amber-200 bg-amber-50">
            <p className="text-sm font-medium text-amber-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Comptes sans rubrique
            </p>
            <p className="text-sm text-amber-800 mt-1">
              {matrice.rubriques_non_affectees.map((r) => r.comptes.join(', ')).join(' · ')} —
              affectez-les à une rubrique avant de présenter les comptes.
            </p>
          </div>
        )}

        {/* Totaux de présentation */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Total actif', valeur: t.actif },
            { label: 'Total passif', valeur: t.passif },
            { label: 'Total charges', valeur: t.charges },
            { label: 'Résultat (produits − charges)', valeur: t.resultat },
          ].map((c) => (
            <div key={c.label} className="card p-4">
              <p className="text-xs text-slate-500">{c.label}</p>
              <p className={cn('text-lg font-semibold mt-1 tabular-nums',
                c.valeur < 0 ? 'text-red-600' : 'text-slate-900')}>
                {formatMontant(c.valeur)}
              </p>
            </div>
          ))}
        </div>

        {/* Feuilles maîtresses par grand poste */}
        {parGroupe.map(({ groupe, rubriques }) => (
          <div key={groupe.libelle} className="card overflow-hidden">
            <div className="px-4 py-2.5 bg-slate-50 border-b border-border flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">{groupe.libelle}</h2>
              <div className="flex items-center gap-6 text-sm">
                <span className="text-slate-500 text-xs">Sous-total</span>
                <span className="font-semibold text-slate-900 tabular-nums w-32 text-right">
                  {formatMontant(groupe.montant_presente)}
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="text-xs text-slate-500 border-b border-border">
                  <th className="text-left font-medium px-4 py-2 min-w-[16rem]">Rubrique</th>
                  <th className="text-right font-medium px-3 py-2 w-32">Solde importé</th>
                  <th className="text-right font-medium px-3 py-2 w-28">Ajustements</th>
                  <th className="text-right font-medium px-3 py-2 w-32">Solde audité</th>
                  {avecN1 && <th className="text-right font-medium px-3 py-2 w-32">N-1</th>}
                  {avecN1 && <th className="text-right font-medium px-3 py-2 w-28">Variation</th>}
                  <th className="text-right font-medium px-3 py-2 w-28">{avecN1 ? '%' : ''}</th>
                </tr>
              </thead>
              <tbody>
                {rubriques.map((r) => {
                  const ouverte = ouvertes.has(r.ref)
                  const s = r.signe_presentation
                  return (
                    <Fragment key={r.ref}>
                      <tr
                        onClick={() => basculer(r.ref)}
                        className="border-b border-border hover:bg-slate-50 cursor-pointer"
                      >
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            {ouverte ? <ChevronDown className="w-4 h-4 text-slate-400" />
                                     : <ChevronRight className="w-4 h-4 text-slate-400" />}
                            <span className="font-medium text-slate-800">{r.libelle}</span>
                            <span className="text-xs text-slate-400">({r.nb_comptes})</span>
                            {r.sens_anormal && (
                              <span className="badge-exception" title="Solde de sens contraire à celui attendu">
                                <AlertTriangle className="w-3 h-3" /> sens inhabituel
                              </span>
                            )}
                            {r.nb_travaux > 0 && (
                              <span className="badge-primary" title="Travaux d'audit rattachés">
                                <Link2 className="w-3 h-3" /> {r.nb_travaux}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-right"><Montant value={montantPresente(r.montant_brut, s)} /></td>
                        <td className="px-3 py-2.5 text-right"><Montant value={montantPresente(r.montant_ajustements, s)} /></td>
                        <td className="px-3 py-2.5 text-right font-medium">
                          <Montant value={r.montant_presente} alerte={r.sens_anormal} />
                        </td>
                        {avecN1 && <td className="px-3 py-2.5 text-right"><Montant value={r.montant_n1_presente} /></td>}
                        {avecN1 && (
                          <td className="px-3 py-2.5 text-right">
                            <Montant value={r.montant_presente - r.montant_n1_presente} />
                          </td>
                        )}
                        <td className="px-3 py-2.5 text-right">{avecN1 && <Pct value={r.variation_pct} />}</td>
                      </tr>

                      <AnimatePresence>
                        {ouverte && (
                          <tr key={`${r.ref}-detail`}>
                            <td colSpan={avecN1 ? 7 : 5} className="p-0">
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="overflow-hidden bg-slate-50/60 border-b border-border"
                              >
                                <table className="w-full text-xs min-w-[900px]">
                                  <tbody>
                                    {r.comptes.map((c) => (
                                      <tr key={c.compte} className="border-b border-slate-100 last:border-0 group">
                                        <td className="pl-11 pr-4 py-1.5">
                                          <span className="font-mono text-slate-700">{c.compte}</span>
                                          <span className="text-slate-500 ml-2">{c.libelle}</span>
                                          {c.reaffecte && (
                                            <span className="badge-primary ml-2" title="Réaffecté par l'auditeur">
                                              <Shuffle className="w-3 h-3" /> réaffecté
                                            </span>
                                          )}
                                          {c.absent_n && (
                                            <span className="badge-ouverte ml-2" title="Mouvementé en N-1, soldé en N">
                                              absent en N
                                            </span>
                                          )}
                                        </td>
                                        <td className="px-3 py-1.5 text-right w-32"><Montant value={montantPresente(c.solde_brut, s)} /></td>
                                        <td className="px-3 py-1.5 text-right w-28"><Montant value={montantPresente(c.ajustement, s)} /></td>
                                        <td className="px-3 py-1.5 text-right w-32"><Montant value={montantPresente(c.solde_ajuste, s)} /></td>
                                        {avecN1 && <td className="px-3 py-1.5 text-right w-32"><Montant value={montantPresente(c.solde_n1, s)} /></td>}
                                        {avecN1 && (
                                          <td className="px-3 py-1.5 text-right w-28">
                                            <Montant value={montantPresente(c.variation_abs, s)} alerte={c.variation_notable} />
                                          </td>
                                        )}
                                        <td className="px-3 py-1.5 text-right w-28">
                                          <div className="flex items-center justify-end gap-1">
                                            {avecN1 && <Pct value={c.variation_pct} />}
                                            <button
                                              title="Réaffecter ce compte à une autre rubrique"
                                              className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-primary-600 transition-opacity"
                                              onClick={(e) => { e.stopPropagation(); setAReaffecter({ compte: c, rubrique: r }) }}
                                            >
                                              <Shuffle className="w-3.5 h-3.5" />
                                            </button>
                                            {c.reaffecte && (
                                              <button
                                                title="Rétablir l'affectation par défaut du plan"
                                                className="text-slate-400 hover:text-primary-600"
                                                onClick={(e) => { e.stopPropagation(); retablirDefaut(c.compte) }}
                                              >
                                                <RotateCcw className="w-3.5 h-3.5" />
                                              </button>
                                            )}
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                <TravauxRattaches travaux={r.travaux} />
                              </motion.div>
                            </td>
                          </tr>
                        )}
                      </AnimatePresence>
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
            </div>
          </div>
        ))}
        </>)}
      </div>

      {aReaffecter && matrice && (
        <DialogueReaffectation
          compte={aReaffecter.compte}
          rubriqueActuelle={aReaffecter.rubrique}
          rubriques={matrice.rubriques}
          onFermer={() => setAReaffecter(null)}
          onValider={async (ref, motif) => {
            try {
              await reaffecter(aReaffecter.compte.compte, ref, motif)
            } catch (e: any) {
              toast.error(e.message)
            }
          }}
        />
      )}
    </div>
  )
}
