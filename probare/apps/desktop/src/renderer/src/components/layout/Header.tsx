import { motion } from 'framer-motion'
import { useProjetStore } from '../../stores/projetStore'
import { Spinner } from '../ui/Spinner'

interface HeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const loading = useProjetStore((s) => s.loading)

  return (
    <div className="h-14 flex items-center justify-between px-6 bg-white border-b border-border flex-shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          key={title}
        >
          <h1 className="text-base font-semibold text-slate-900 truncate">{title}</h1>
          {subtitle && (
            <p className="text-xs text-slate-500 truncate">{subtitle}</p>
          )}
        </motion.div>
        {loading && <Spinner size="sm" className="ml-2" />}
      </div>
      {actions && (
        <div className="flex items-center gap-2 flex-shrink-0 ml-4">{actions}</div>
      )}
    </div>
  )
}
