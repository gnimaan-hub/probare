import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Settings, FolderOpen, Upload,
  ShieldCheck, AlertTriangle, FileText, ChevronLeft,
  Activity, ArrowLeft, ClipboardList, BarChart2, Building2
} from 'lucide-react'
import { useProjetStore } from '../../stores/projetStore'
import { ETATS_PIPELINE, getEtatIndex } from '../../lib/utils'
import { cn } from '../../lib/utils'

interface NavItemDef {
  to: string
  icon: React.ElementType
  label: string
  requiresProjet?: boolean
  minEtat?: string
}

const navItems: NavItemDef[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
]

const projetNavItems: NavItemDef[] = [
  { to: 'cadrage',          icon: Settings,      label: 'Cadrage',              minEtat: 'cadrage' },
  { to: 'evaluation-ci',    icon: ShieldCheck,   label: 'Contrôle interne',     minEtat: 'cadrage' },
  { to: 'ingestion',        icon: Upload,        label: 'Ingestion',            minEtat: 'evaluation_ci' },
  { to: 'planification',    icon: ClipboardList, label: 'Planification',        minEtat: 'ingestion' },
  { to: 'controles',        icon: BarChart2,     label: 'Travaux substantifs',  minEtat: 'planification' },
  { to: 'exceptions',       icon: AlertTriangle, label: 'Exceptions',           minEtat: 'travaux_substantifs' },
  { to: 'rapport',          icon: FileText,      label: 'Rapport',              minEtat: 'revue' },
  { to: 'journal',          icon: Activity,      label: 'Journal',              minEtat: 'cadrage' },
]

function PipelineProgress({ etatCourant }: { etatCourant: string }) {
  const currentIdx = getEtatIndex(etatCourant)
  return (
    <div className="px-3 pb-2">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Progression
      </div>
      <div className="space-y-0.5">
        {ETATS_PIPELINE.map((step, idx) => {
          const isDone = idx < currentIdx
          const isActive = idx === currentIdx
          return (
            <div
              key={step.id}
              className={cn(
                'flex items-center gap-2 px-2 py-1 rounded text-xs',
                isDone && 'text-emerald-600',
                isActive && 'text-primary-700 font-semibold',
                !isDone && !isActive && 'text-slate-400'
              )}
            >
              <div className={cn(
                'w-1.5 h-1.5 rounded-full flex-shrink-0',
                isDone && 'bg-emerald-500',
                isActive && 'bg-primary-500 animate-pulse-soft',
                !isDone && !isActive && 'bg-slate-300'
              )} />
              {step.label}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function Sidebar() {
  const navigate = useNavigate()
  const { projetActif, setProjetActif } = useProjetStore()
  const currentEtatIdx = projetActif ? getEtatIndex(projetActif.etat_courant) : -1

  return (
    <aside className="w-56 flex-shrink-0 h-screen bg-white border-r border-border flex flex-col select-none">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary-600 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-900 tracking-tight">Probare</span>
        </div>
      </div>

      {/* Navigation principale */}
      <nav className="flex-1 overflow-y-auto py-3 space-y-1 px-2">
        {/* Projets */}
        <NavLink
          to="/dashboard"
          className={({ isActive }) => cn('nav-item', isActive && 'nav-item-active')}
        >
          <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
          Tableau de bord
        </NavLink>

        {/* Projet actif */}
        <AnimatePresence>
          {projetActif && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="pt-3 pb-1">
                <button
                  onClick={() => { setProjetActif(null); navigate('/dashboard') }}
                  className="flex items-center gap-1.5 px-3 text-xs text-slate-500 hover:text-primary-600 transition-colors mb-2"
                >
                  <ArrowLeft className="w-3 h-3" />
                  Tous les projets
                </button>
                <div className="px-3 py-2 mb-2 bg-slate-50 rounded-lg">
                  <div className="text-xs font-semibold text-slate-700 truncate">{projetActif.nom}</div>
                  <div className="text-xs text-slate-500">{projetActif.exercice || 'Exercice N/A'}</div>
                </div>
              </div>

              <div className="section-title">Mission</div>
              {projetNavItems.map((item) => {
                const minIdx = getEtatIndex(item.minEtat || 'cadrage')
                const isAccessible = currentEtatIdx >= minIdx - 1
                return (
                  <NavLink
                    key={item.to}
                    to={`/projet/${projetActif.id}/${item.to}`}
                    className={({ isActive }) =>
                      cn('nav-item', isActive && 'nav-item-active',
                        !isAccessible && 'opacity-40 pointer-events-none')
                    }
                  >
                    <item.icon className="w-4 h-4 flex-shrink-0" />
                    {item.label}
                  </NavLink>
                )
              })}

              <div className="pt-3">
                <PipelineProgress etatCourant={projetActif.etat_courant} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border space-y-1">
        <NavLink
          to="/configuration"
          className={({ isActive }) => cn('nav-item text-slate-400 hover:text-slate-600', isActive && 'nav-item-active')}
        >
          <Building2 className="w-4 h-4 flex-shrink-0" />
          Cabinet
        </NavLink>
        <div className="text-xs text-slate-400 text-center pt-1">
          Probare v0.1 — MVP
        </div>
      </div>
    </aside>
  )
}
