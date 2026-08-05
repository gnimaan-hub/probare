import { Outlet } from 'react-router-dom'
import { BotOff } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { ToastContainer } from '../ui/ToastContainer'
import { useProjetStore } from '../../stores/projetStore'

/**
 * Probare interprète chaque exception par l'IA dès qu'elle est levée. Sans clé
 * API, le moteur saute ces interprétations sans rien dire : le dossier paraît
 * alors complet et simplement muet, ce qu'un auditeur lirait comme « l'IA n'a
 * rien trouvé à signaler ». Ce bandeau lève l'ambiguïté.
 */
function BandeauIaIndisponible() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border-b border-amber-200 flex-shrink-0">
      <BotOff className="w-4 h-4 text-amber-500 flex-shrink-0" />
      <p className="text-xs text-amber-800">
        Assistance IA indisponible — aucune clé API n'est configurée. Les contrôles
        déterministes fonctionnent normalement, mais les exceptions ne seront pas
        interprétées et les projets de rédaction ne seront pas produits.
      </p>
    </div>
  )
}

export function Layout() {
  const llmDisponible = useProjetStore((s) => s.llmDisponible)

  return (
    <div className="flex h-screen overflow-hidden bg-surface-secondary">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {!llmDisponible && <BandeauIaIndisponible />}
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  )
}
