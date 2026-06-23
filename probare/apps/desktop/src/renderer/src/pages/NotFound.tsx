import { useNavigate } from 'react-router-dom'
import { Home } from 'lucide-react'

export function NotFound() {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="text-5xl font-bold text-slate-200">404</div>
      <p className="text-sm text-slate-500">Page introuvable</p>
      <button className="btn-primary" onClick={() => navigate('/dashboard')}>
        <Home className="w-4 h-4" />
        Tableau de bord
      </button>
    </div>
  )
}
