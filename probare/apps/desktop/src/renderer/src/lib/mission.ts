/**
 * Modèle de mission — source unique de vérité pour la structure du parcours d'audit.
 *
 * Distingue explicitement :
 *  - les ÉTAPES LINÉAIRES (le pipeline séquentiel cadrage → … → opinion) ;
 *  - les TRAVAUX TRANSVERSAUX (diligences qui s'exercent sur toute la mission,
 *    sans position fixe dans la séquence).
 *
 * Toute la navigation, la barre latérale, le cockpit et le guidage « prochaine
 * étape » lisent cette structure — plus de listes dupliquées ou désynchronisées.
 */
import {
  Settings, ShieldCheck, Upload, ClipboardList, BarChart2,
  AlertTriangle, FileText, Stamp, ScanSearch, ListChecks, Scale, Activity,
  type LucideIcon,
} from 'lucide-react'
import { getEtatIndex, ETATS_PIPELINE } from './utils'

export interface LinearStep {
  /** État du pipeline (backend). */
  etat: string
  /** Segment de route sous /projet/:id/. */
  route: string
  num: number
  label: string
  /** Libellé court pour la barre latérale. */
  short: string
  /** Références de normes (numéros seuls — préfixées par normeLabel à l'affichage). */
  norme?: string
  icon: LucideIcon
  /** Ce que l'auditeur accomplit ici, en une phrase. */
  but: string
}

export interface TransversalItem {
  id: string
  route: string
  label: string
  short: string
  norme?: string
  icon: LucideIcon
  but: string
  /** Diligence obligatoire pour boucler le dossier (verrou backend). */
  obligatoire?: boolean
  /** État du pipeline à partir duquel l'écran devient pertinent/accessible. */
  disponibleDes: string
}

export const LINEAR_STEPS: LinearStep[] = [
  { etat: 'cadrage', route: 'cadrage', num: 1, label: 'Cadrage de la mission', short: 'Cadrage',
    norme: '210, 300', icon: Settings,
    but: "Définir la mission, connaître l'entité et recueillir le consentement." },
  { etat: 'evaluation_ci', route: 'evaluation-ci', num: 2, label: 'Contrôle interne', short: 'Contrôle interne',
    norme: '315', icon: ShieldCheck,
    but: "Évaluer le dispositif de contrôle interne, cycle par cycle." },
  { etat: 'ingestion', route: 'ingestion', num: 3, label: 'Ingestion des documents', short: 'Ingestion',
    icon: Upload,
    but: "Importer la balance, le grand livre et les pièces justificatives." },
  { etat: 'planification', route: 'planification', num: 4, label: 'Planification', short: 'Planification',
    norme: '300, 320', icon: ClipboardList,
    but: "Procédures analytiques, seuils, cartographie des risques et programme de travail." },
  { etat: 'travaux_substantifs', route: 'controles', num: 5, label: 'Travaux substantifs', short: 'Travaux substantifs',
    norme: '330, 500, 505, 530', icon: BarChart2,
    but: "Exécuter les contrôles, circularisations et sondages sur les comptes." },
  { etat: 'revue', route: 'exceptions', num: 6, label: 'Revue des exceptions', short: 'Revue',
    norme: '450', icon: AlertTriangle,
    but: "Trancher chaque anomalie relevée et documenter la décision." },
  { etat: 'generation', route: 'dossier-travail', num: 7, label: 'Dossier de travail', short: 'Dossier de travail',
    norme: '230', icon: FileText,
    but: "Assembler les feuilles de travail et les livrables du dossier." },
  { etat: 'opinion', route: 'rapport-audit', num: 8, label: "Rapport d'audit", short: "Rapport d'audit",
    norme: '700', icon: Stamp,
    but: "Formuler l'opinion et produire le rapport et le mémorandum." },
]

export const TRANSVERSAL_ITEMS: TransversalItem[] = [
  { id: 'journal-entries', route: 'journal-entries', label: 'Écritures de journal', short: 'Écritures de journal',
    norme: '240', icon: ScanSearch, obligatoire: true, disponibleDes: 'travaux_substantifs',
    but: "Détecter le contournement des contrôles sur tout le grand livre (obligatoire)." },
  { id: 'diligences', route: 'diligences', label: 'Diligences de périphérie', short: 'Diligences',
    norme: '210, 240, 550, 560, 570, 580', icon: ListChecks, disponibleDes: 'cadrage',
    but: "Fraude, parties liées, continuité, événements postérieurs, déclarations écrites." },
  { id: 'ajustements', route: 'ajustements', label: "Écritures d'ajustement", short: 'Ajustements',
    norme: '450', icon: Scale, disponibleDes: 'travaux_substantifs',
    but: "Matérialiser les anomalies en propositions d'écritures et bâtir la balance ajustée." },
  { id: 'journal', route: 'journal', label: 'Historique', short: 'Historique',
    icon: Activity, disponibleDes: 'cadrage',
    but: "Piste d'audit : chaque action, appel IA et transition d'état est journalisé." },
]

/** Résout un état legacy vers l'ordre nominal. */
export function normaliserEtat(etat: string): string {
  return ({ controles: 'travaux_substantifs', extraction: 'ingestion' } as Record<string, string>)[etat] ?? etat
}

export type StepStatut = 'fait' | 'en_cours' | 'a_venir'

export function statutEtape(stepEtat: string, etatCourant: string): StepStatut {
  const i = getEtatIndex(stepEtat)
  const c = getEtatIndex(etatCourant)
  if (i < c) return 'fait'
  if (i === c) return 'en_cours'
  return 'a_venir'
}

/**
 * Accès de navigation. Une étape linéaire est accessible jusqu'à l'étape courante
 * incluse (on peut revisiter et corriger). Les étapes à venir sont verrouillées —
 * on y accède en franchissant la transition guidée, pas en cliquant en avance.
 */
export function accesEtape(stepEtat: string, etatCourant: string): { accessible: boolean; raison?: string } {
  const i = getEtatIndex(stepEtat)
  const c = getEtatIndex(etatCourant)
  if (i <= c) return { accessible: true }
  const precedente = ETATS_PIPELINE[i - 1]?.label ?? 'précédente'
  return { accessible: false, raison: `Accessible après l'étape « ${precedente} ».` }
}

export function accesTransversal(item: TransversalItem, etatCourant: string): { accessible: boolean; raison?: string } {
  const i = getEtatIndex(item.disponibleDes)
  const c = getEtatIndex(etatCourant)
  if (c >= i) return { accessible: true }
  const label = ETATS_PIPELINE[i]?.label ?? item.disponibleDes
  return { accessible: false, raison: `Disponible à partir de l'étape « ${label} ».` }
}

/** L'étape/écran doit-il être en lecture seule ? Verrouillé dès le lancement des travaux. */
export function estVerrouille(etatCourant: string): boolean {
  const e = normaliserEtat(etatCourant)
  return ['travaux_substantifs', 'revue', 'generation', 'opinion'].includes(e)
}

export function stepParRoute(route: string): LinearStep | undefined {
  return LINEAR_STEPS.find((s) => s.route === route)
}
