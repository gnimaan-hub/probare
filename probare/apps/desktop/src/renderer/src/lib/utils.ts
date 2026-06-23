import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMontant(val: number | undefined | null, devise = 'FDJ'): string {
  if (val === undefined || val === null) return '—'
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(val) + ` ${devise}`
}

export function formatDate(iso: string | undefined | null): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function truncate(s: string, n = 80): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

export const ETATS_PIPELINE = [
  { id: 'cadrage',             label: 'Cadrage',             description: 'Paramètres de mission' },
  { id: 'evaluation_ci',       label: 'Contrôle interne',    description: 'Évaluation du dispositif de contrôle interne' },
  { id: 'ingestion',           label: 'Ingestion',           description: 'Import des fichiers' },
  { id: 'planification',       label: 'Planification',       description: 'Analyse & cartographie des risques' },
  { id: 'travaux_substantifs', label: 'Travaux substantifs', description: 'Procédures analytiques & contrôles de détail' },
  { id: 'revue',               label: 'Revue',               description: 'Traitement des exceptions' },
  { id: 'generation',          label: 'Génération',          description: 'Dossier de travail' },
  { id: 'opinion',             label: 'Opinion',             description: 'Validation finale' },
] as const

export type EtatPipeline = typeof ETATS_PIPELINE[number]['id']

// Compatibilité : anciens projets en "controles" → équivalent "travaux_substantifs"
const ETAT_ALIAS: Record<string, string> = {
  controles:  'travaux_substantifs',
  extraction: 'ingestion',
}

export function getEtatIndex(etat: string): number {
  const resolved = ETAT_ALIAS[etat] ?? etat
  return ETATS_PIPELINE.findIndex((e) => e.id === resolved)
}
