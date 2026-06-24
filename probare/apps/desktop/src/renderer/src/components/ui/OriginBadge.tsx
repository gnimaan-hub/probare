type OriginType = 'calcule' | 'ia' | 'saisie' | 'importe'

const LABELS: Record<OriginType, string> = {
  calcule: 'Calculé Python',
  ia: 'Proposé par IA',
  saisie: 'Décision auditeur',
  importe: 'Importé',
}

const COLORS: Record<OriginType, string> = {
  calcule: 'bg-blue-100 text-blue-700 border-blue-200',
  ia: 'bg-amber-100 text-amber-700 border-amber-200',
  saisie: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  importe: 'bg-slate-100 text-slate-600 border-slate-200',
}

export function OriginBadge({ source }: { source: OriginType }) {
  return (
    <span className={`inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5 rounded border ${COLORS[source]}`}>
      {LABELS[source]}
    </span>
  )
}
