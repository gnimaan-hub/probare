import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { MissionCockpit } from './pages/MissionCockpit'
import { Cadrage } from './pages/Cadrage'
import { Ingestion } from './pages/Ingestion'
import { Controles } from './pages/Controles'
import { EvaluationCI } from './pages/EvaluationCI'
import { Exceptions } from './pages/Exceptions'
import { Diligences } from './pages/Diligences'
import { Ajustements } from './pages/Ajustements'
import { FeuillesMaitresses } from './pages/FeuillesMaitresses'
import { JournalEntries } from './pages/JournalEntries'
import { DossierTravail } from './pages/DossierTravail'
import { RapportAudit } from './pages/RapportAudit'
import { Journal } from './pages/Journal'
import { DossierBrut } from './pages/DossierBrut'
import { Planification } from './pages/Planification'
import { DossiersPermanents } from './pages/DossiersPermanents'
import { DossierPermanent } from './pages/DossierPermanent'
import { Configuration } from './pages/Configuration'
import { NotFound } from './pages/NotFound'
import { useProjetStore } from './stores/projetStore'
import { Spinner } from './components/ui/Spinner'

function LogoProbare({ className = 'w-8 h-8 text-white' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  )
}

function SplashScreen({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 bg-white flex flex-col items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        <div className="w-14 h-14 rounded-2xl bg-primary-600 flex items-center justify-center shadow-lg">
          <LogoProbare />
        </div>
        <div className="text-center">
          <h1 className="text-xl font-bold text-slate-900">Probare</h1>
          {/* Le message dit l'étape en cours : un premier démarrage après
              installation prend plusieurs secondes et un écran figé sur
              « Initialisation… » se lit comme une application bloquée. */}
          <p className="text-sm text-slate-500 mt-1 min-h-[1.25rem]">{message}</p>
        </div>
        <Spinner />
      </motion.div>
    </div>
  )
}

function ConnectionError({ detail, onRetry }: { detail: string; onRetry: () => void }) {
  return (
    <div className="fixed inset-0 bg-white flex flex-col items-center justify-center z-50 p-6">
      <div className="flex flex-col items-center gap-4 max-w-xl w-full text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-100 flex items-center justify-center">
          <svg className="w-7 h-7 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div>
          <h2 className="font-semibold text-slate-900 mb-1">Moteur non disponible</h2>
          <p className="text-sm text-slate-500">
            Le moteur d'audit n'a pas pu démarrer. Probare ne peut pas fonctionner sans lui.
          </p>
        </div>
        {/* La cause réelle vient du sidecar. Sans elle, l'écran laisse
            l'utilisateur — et le support — sans point de départ. */}
        {detail && (
          <pre className="w-full max-h-56 overflow-auto text-left text-xs font-mono bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-600 whitespace-pre-wrap break-words">
            {detail}
          </pre>
        )}
        <button onClick={onRetry} className="btn-primary">
          Réessayer
        </button>
      </div>
    </div>
  )
}

// Le moteur peut mettre plusieurs secondes à répondre au premier lancement
// (déballage des dépendances, analyse antivirus sur un poste Windows neuf).
// On sonde jusqu'à ce délai avant de conclure à un échec.
const DELAI_DEMARRAGE_MS = 45_000
const INTERVALLE_SONDAGE_MS = 400

const attendre = (ms: number) => new Promise((r) => setTimeout(r, ms))

export default function App() {
  const { setApiPort, setApiToken, setReferentiel, setLlmDisponible } = useProjetStore()
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [message, setMessage] = useState('Initialisation…')
  const [detailErreur, setDetailErreur] = useState('')

  // Charge le référentiel de normes (ISA/NEP) actif au démarrage du moteur.
  const chargerReferentiel = async (port: number) => {
    try {
      const token = useProjetStore.getState().apiToken
      const res = await fetch(`http://127.0.0.1:${port}/api/config`, {
        headers: token ? { 'X-Probare-Token': token } : {},
      })
      if (res.ok) {
        const cfg = await res.json()
        setReferentiel(cfg.referentiel_actif === 'nep' ? 'NEP' : 'ISA')
      }
    } catch { /* défaut ISA */ }
  }

  /** Sonde /health une fois. Rend true et retient l'état du moteur si prêt. */
  const sonder = async (port: number): Promise<boolean> => {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`)
      if (!res.ok) return false
      const sante = await res.json().catch(() => ({}))
      setApiPort(port)
      // Sans clé API, le moteur ignore silencieusement les interprétations
      // automatiques. L'interface doit pouvoir le dire.
      setLlmDisponible(Boolean(sante.llm_disponible))
      await chargerReferentiel(port)
      return true
    } catch {
      return false
    }
  }

  const init = async () => {
    setStatus('loading')
    setDetailErreur('')
    setMessage('Démarrage du moteur d’audit…')

    // Ports à sonder : celui annoncé par Electron, sinon la plage utilisée par
    // le sidecar en mode navigateur (npm run preview:renderer).
    let ports = [8765, 8766, 8767]
    if (typeof window !== 'undefined' && window.electron?.getApiPort) {
      try {
        const port = await window.electron.getApiPort()
        ports = [port]
        setApiPort(port)
      } catch { /* on retombe sur la plage par défaut */ }
      try {
        if (window.electron.getApiToken) setApiToken(await window.electron.getApiToken())
      } catch { /* dev sans jeton */ }
    }

    const echeance = Date.now() + DELAI_DEMARRAGE_MS
    let premierTour = true
    while (Date.now() < echeance) {
      for (const p of ports) {
        if (await sonder(p)) { setMessage('Moteur prêt.'); setStatus('ready'); return }
      }
      if (premierTour) {
        premierTour = false
        setMessage('Le moteur démarre, cela peut prendre quelques secondes…')
      }
      await attendre(INTERVALLE_SONDAGE_MS)
    }

    // Échec : montrer ce que le moteur a écrit sur sa sortie d'erreur.
    try {
      const journal = await window.electron?.getSidecarError?.()
      setDetailErreur(journal || '')
    } catch { /* pas d'Electron : aucun diagnostic à remonter */ }
    setStatus('error')
  }

  useEffect(() => { init() }, [])

  if (status === 'loading') return <SplashScreen message={message} />
  if (status === 'error') return <ConnectionError detail={detailErreur} onRetry={init} />

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/projet/:projetId" element={<MissionCockpit />} />
        <Route path="/projet/:projetId/cadrage" element={<Cadrage />} />
        <Route path="/projet/:projetId/ingestion" element={<Ingestion />} />
        <Route path="/projet/:projetId/evaluation-ci" element={<EvaluationCI />} />
        <Route path="/projet/:projetId/controles" element={<Controles />} />
        <Route path="/projet/:projetId/exceptions" element={<Exceptions />} />
        <Route path="/projet/:projetId/diligences" element={<Diligences />} />
        <Route path="/projet/:projetId/ajustements" element={<Ajustements />} />
        <Route path="/projet/:projetId/feuilles-maitresses" element={<FeuillesMaitresses />} />
        <Route path="/projet/:projetId/journal-entries" element={<JournalEntries />} />
        <Route path="/projet/:projetId/dossier-travail" element={<DossierTravail />} />
        <Route path="/projet/:projetId/rapport-audit" element={<RapportAudit />} />
        {/* Rétrocompatibilité : l'ancienne route /rapport pointe vers le dossier de travail */}
        <Route path="/projet/:projetId/rapport" element={<DossierTravail />} />
        <Route path="/projet/:projetId/journal" element={<Journal />} />
        <Route path="/projet/:projetId/dossier-brut" element={<DossierBrut />} />
        <Route path="/projet/:projetId/planification" element={<Planification />} />
        <Route path="/dossiers-permanents" element={<DossiersPermanents />} />
        <Route path="/dossiers-permanents/:clientId" element={<DossierPermanent />} />
        <Route path="/configuration" element={<Configuration />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
