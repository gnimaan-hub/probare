import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Cadrage } from './pages/Cadrage'
import { Ingestion } from './pages/Ingestion'
import { Controles } from './pages/Controles'
import { EvaluationCI } from './pages/EvaluationCI'
import { Exceptions } from './pages/Exceptions'
import { Rapport } from './pages/Rapport'
import { Sondages } from './pages/Sondages'
import { Journal } from './pages/Journal'
import { DossierBrut } from './pages/DossierBrut'
import { Planification } from './pages/Planification'
import { DossiersPermanents } from './pages/DossiersPermanents'
import { DossierPermanent } from './pages/DossierPermanent'
import { NotFound } from './pages/NotFound'
import { useProjetStore } from './stores/projetStore'
import { Spinner } from './components/ui/Spinner'

function SplashScreen() {
  return (
    <div className="fixed inset-0 bg-white flex flex-col items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        <div className="w-14 h-14 rounded-2xl bg-primary-600 flex items-center justify-center shadow-lg">
          <svg className="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-bold text-slate-900">Probare</h1>
          <p className="text-sm text-slate-500 mt-1">Initialisation…</p>
        </div>
        <Spinner />
      </motion.div>
    </div>
  )
}

function ConnectionError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="fixed inset-0 bg-white flex flex-col items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4 max-w-sm text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-100 flex items-center justify-center">
          <svg className="w-7 h-7 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div>
          <h2 className="font-semibold text-slate-900 mb-1">Moteur non disponible</h2>
          <p className="text-sm text-slate-500">
            Le service Python n'a pas pu démarrer. Vérifiez que les dépendances sont installées.
          </p>
        </div>
        <button onClick={onRetry} className="btn-primary">
          Réessayer
        </button>
      </div>
    </div>
  )
}

export default function App() {
  const { setApiPort } = useProjetStore()
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  const init = async () => {
    setStatus('loading')
    try {
      // Récupérer le port du sidecar depuis Electron
      let port = 8765
      if (typeof window !== 'undefined' && window.electron?.getApiPort) {
        port = await window.electron.getApiPort()
        setApiPort(port)
        const res = await fetch(`http://127.0.0.1:${port}/api/health`)
        if (res.ok) { setStatus('ready'); return }
      }

      // En mode browser/dev sans Electron, chercher le sidecar sur plusieurs ports
      for (const p of [8767, 8766, 8765]) {
        try {
          const res = await fetch(`http://127.0.0.1:${p}/api/health`)
          if (res.ok) { setApiPort(p); setStatus('ready'); return }
        } catch { /* continuer */ }
      }
      setStatus('error')
    } catch {
      setStatus('error')
    }
  }

  useEffect(() => { init() }, [])

  if (status === 'loading') return <SplashScreen />
  if (status === 'error') return <ConnectionError onRetry={init} />

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projet/:projetId/cadrage" element={<Cadrage />} />
        <Route path="/projet/:projetId/ingestion" element={<Ingestion />} />
        <Route path="/projet/:projetId/evaluation-ci" element={<EvaluationCI />} />
        <Route path="/projet/:projetId/controles" element={<Controles />} />
        <Route path="/projet/:projetId/exceptions" element={<Exceptions />} />
        <Route path="/projet/:projetId/rapport" element={<Rapport />} />
        <Route path="/projet/:projetId/sondages" element={<Sondages />} />
        <Route path="/projet/:projetId/journal" element={<Journal />} />
        <Route path="/projet/:projetId/dossier-brut" element={<DossierBrut />} />
        <Route path="/projet/:projetId/planification" element={<Planification />} />
        <Route path="/dossiers-permanents" element={<DossiersPermanents />} />
        <Route path="/dossiers-permanents/:clientId" element={<DossierPermanent />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
