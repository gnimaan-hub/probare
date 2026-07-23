import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, ShieldCheck, ArrowLeft, Building2, Lock, LayoutGrid, CheckCircle,
} from 'lucide-react'
import { useProjetStore } from '../../stores/projetStore'
import {
  LINEAR_STEPS, TRANSVERSAL_ITEMS, accesEtape, accesTransversal, statutEtape,
} from '../../lib/mission'
import { cn } from '../../lib/utils'

function NavRow({
  to, icon: Icon, label, num, accessible, raison, statut,
}: {
  to: string
  icon: React.ElementType
  label: string
  num?: number
  accessible: boolean
  raison?: string
  statut?: 'fait' | 'en_cours' | 'a_venir'
}) {
  if (!accessible) {
    return (
      <div
        title={raison}
        className="nav-item opacity-40 cursor-not-allowed flex items-center gap-2"
      >
        {num != null ? <StepBullet num={num} statut={statut} /> : <Icon className="w-4 h-4 flex-shrink-0" />}
        <span className="flex-1 truncate">{label}</span>
        <Lock className="w-3 h-3 flex-shrink-0 text-slate-300" />
      </div>
    )
  }
  return (
    <NavLink
      to={to}
      className={({ isActive }) => cn('nav-item flex items-center gap-2', isActive && 'nav-item-active')}
    >
      {num != null ? <StepBullet num={num} statut={statut} /> : <Icon className="w-4 h-4 flex-shrink-0" />}
      <span className="flex-1 truncate">{label}</span>
      {statut === 'fait' && <CheckCircle className="w-3.5 h-3.5 flex-shrink-0 text-emerald-500" />}
    </NavLink>
  )
}

function StepBullet({ num, statut }: { num: number; statut?: 'fait' | 'en_cours' | 'a_venir' }) {
  return (
    <span className={cn(
      'w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0',
      statut === 'fait' ? 'bg-emerald-100 text-emerald-600'
      : statut === 'en_cours' ? 'bg-primary-600 text-white'
      : 'bg-slate-100 text-slate-400',
    )}>
      {num}
    </span>
  )
}

export function Sidebar() {
  const navigate = useNavigate()
  const { projetActif, setProjetActif } = useProjetStore()
  const etatCourant = projetActif?.etat_courant ?? 'cadrage'

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

      <nav className="flex-1 overflow-y-auto py-3 space-y-1 px-2">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => cn('nav-item', isActive && 'nav-item-active')}
        >
          <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
          Tableau de bord
        </NavLink>

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
                <div className="px-3 py-2 mb-1 bg-slate-50 rounded-lg">
                  <div className="text-xs font-semibold text-slate-700 truncate">{projetActif.nom}</div>
                  <div className="text-xs text-slate-500">{projetActif.exercice || 'Exercice N/A'}</div>
                </div>
              </div>

              {/* Plan de mission (cockpit) */}
              <NavLink
                to={`/projet/${projetActif.id}`}
                end
                className={({ isActive }) => cn('nav-item', isActive && 'nav-item-active')}
              >
                <LayoutGrid className="w-4 h-4 flex-shrink-0" />
                Plan de mission
              </NavLink>

              {/* Parcours linéaire */}
              <div className="section-title mt-2">Parcours de la mission</div>
              {LINEAR_STEPS.map((step) => {
                const { accessible, raison } = accesEtape(step.etat, etatCourant)
                return (
                  <NavRow
                    key={step.etat}
                    to={`/projet/${projetActif.id}/${step.route}`}
                    icon={step.icon}
                    label={step.short}
                    num={step.num}
                    statut={statutEtape(step.etat, etatCourant)}
                    accessible={accessible}
                    raison={raison}
                  />
                )
              })}

              {/* Travaux transversaux */}
              <div className="section-title mt-3">Travaux transversaux</div>
              {TRANSVERSAL_ITEMS.map((item) => {
                const { accessible, raison } = accesTransversal(item, etatCourant)
                return (
                  <NavRow
                    key={item.id}
                    to={`/projet/${projetActif.id}/${item.route}`}
                    icon={item.icon}
                    label={item.short}
                    accessible={accessible}
                    raison={raison}
                  />
                )
              })}
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
