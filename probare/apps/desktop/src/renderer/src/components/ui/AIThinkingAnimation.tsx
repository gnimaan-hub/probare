import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../../lib/utils'

export type AIThinkingVariant =
  | 'analyse'
  | 'catalogue'
  | 'extraction'
  | 'verification'
  | 'calcul'
  | 'redaction'
  | 'opinion'
  | 'conclusion'

interface VariantConfig {
  emoji: string
  ringColor: string
  dotColor: string
  textColor: string
  bgColor: string
  borderColor: string
  label: string
  hints: string[]
}

const VARIANTS: Record<AIThinkingVariant, VariantConfig> = {
  analyse: {
    emoji: '🦉',
    ringColor: 'bg-amber-400',
    dotColor: 'bg-amber-500',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-100',
    label: 'Analyse en cours…',
    hints: [
      'Lecture des indices comptables…',
      'Évaluation des risques…',
      'Formulation des hypothèses…',
      'Rédaction de la décision…',
    ],
  },
  catalogue: {
    emoji: '🦔',
    ringColor: 'bg-blue-400',
    dotColor: 'bg-blue-500',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-100',
    label: 'Catalogage IA…',
    hints: [
      'Identification du document…',
      'Extraction des métadonnées…',
      'Classification du type…',
      'Indexation terminée…',
    ],
  },
  extraction: {
    emoji: '🐝',
    ringColor: 'bg-yellow-400',
    dotColor: 'bg-yellow-500',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-100',
    label: 'Extraction des données…',
    hints: [
      'Lecture des lignes comptables…',
      'Structuration des entrées…',
      'Validation des montants…',
      'Assemblage du résultat…',
    ],
  },
  verification: {
    emoji: '🦅',
    ringColor: 'bg-emerald-400',
    dotColor: 'bg-emerald-500',
    textColor: 'text-emerald-700',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-100',
    label: 'Vérification IA…',
    hints: [
      'Contrôle de cohérence…',
      'Vérification des soldes…',
      'Détection des anomalies…',
      'Calcul du score de confiance…',
    ],
  },
  calcul: {
    emoji: '🦦',
    ringColor: 'bg-cyan-400',
    dotColor: 'bg-cyan-500',
    textColor: 'text-cyan-700',
    bgColor: 'bg-cyan-50',
    borderColor: 'border-cyan-100',
    label: 'Contrôles en cours…',
    hints: [
      'Application des 52 contrôles…',
      'Calcul des écarts…',
      'Levée des exceptions…',
      'Compilation des résultats…',
    ],
  },
  redaction: {
    emoji: '🦊',
    ringColor: 'bg-violet-400',
    dotColor: 'bg-violet-500',
    textColor: 'text-violet-700',
    bgColor: 'bg-violet-50',
    borderColor: 'border-violet-100',
    label: 'Rédaction en cours…',
    hints: [
      'Analyse des résultats calculés…',
      'Structuration de la feuille…',
      'Rédaction à la 1ère personne…',
      'Finalisation de la narrative…',
    ],
  },
  opinion: {
    emoji: '🦁',
    ringColor: 'bg-rose-400',
    dotColor: 'bg-rose-500',
    textColor: 'text-rose-700',
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-100',
    label: "Formation de l'opinion…",
    hints: [
      'Agrégation des anomalies…',
      'Comparaison au seuil de signification…',
      'Détermination du type d\'opinion…',
      'Rédaction de la narrative…',
    ],
  },
  conclusion: {
    emoji: '🐺',
    ringColor: 'bg-indigo-400',
    dotColor: 'bg-indigo-500',
    textColor: 'text-indigo-700',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-100',
    label: 'Conclusion en cours…',
    hints: [
      "Analyse de l'échantillon…",
      "Calcul du taux d'erreur observé…",
      'Projection sur la population…',
      'Formulation de la conclusion…',
    ],
  },
}

interface AIThinkingAnimationProps {
  variant?: AIThinkingVariant
  message?: string
  size?: 'sm' | 'md'
  className?: string
}

function useCyclingHints(hints: string[], intervalMs = 1800) {
  const [index, setIndex] = useState(0)
  useEffect(() => {
    setIndex(0)
    const id = setInterval(() => setIndex((i) => (i + 1) % hints.length), intervalMs)
    return () => clearInterval(id)
  }, [hints, intervalMs])
  return index
}

// ─── Size SM — horizontal strip ──────────────────────────────────────────────

function SmAnimation({ cfg, message }: { cfg: VariantConfig; message?: string }) {
  const hintIndex = useCyclingHints(cfg.hints)

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-2.5 rounded-xl border',
        cfg.bgColor,
        cfg.borderColor
      )}
    >
      {/* Pulsing emoji */}
      <div className="relative flex-shrink-0 w-9 h-9 flex items-center justify-center">
        <motion.div
          className={cn('absolute inset-0 rounded-full', cfg.ringColor)}
          animate={{ scale: [1, 1.8], opacity: [0.25, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut' }}
        />
        <motion.div
          className={cn('absolute inset-0 rounded-full', cfg.ringColor)}
          animate={{ scale: [1, 1.4], opacity: [0.35, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut', delay: 0.5 }}
        />
        <motion.span
          className="relative text-xl select-none"
          animate={{ y: [-2, 2, -2] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
        >
          {cfg.emoji}
        </motion.span>
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <div className={cn('text-xs font-semibold leading-tight', cfg.textColor)}>
          {message ?? cfg.label}
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={hintIndex}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -3 }}
            transition={{ duration: 0.25 }}
            className="text-[10px] text-slate-400 mt-0.5 truncate"
          >
            {cfg.hints[hintIndex]}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Bouncing dots */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className={cn('w-1.5 h-1.5 rounded-full', cfg.dotColor)}
            animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: i * 0.18,
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Size MD — centered card ──────────────────────────────────────────────────

function MdAnimation({ cfg, message }: { cfg: VariantConfig; message?: string }) {
  const hintIndex = useCyclingHints(cfg.hints, 2000)

  // 8 floating particles
  const particles = [
    { x: -36, y: -28, delay: 0 },
    { x: 36, y: -28, delay: 0.3 },
    { x: -44, y: 4, delay: 0.6 },
    { x: 44, y: 4, delay: 0.9 },
    { x: -28, y: 32, delay: 1.2 },
    { x: 28, y: 32, delay: 1.5 },
    { x: -10, y: -44, delay: 0.15 },
    { x: 10, y: -44, delay: 0.75 },
  ]

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-5">
      {/* Rings + emoji + particles */}
      <div className="relative w-24 h-24 flex items-center justify-center">
        {/* Outer rings */}
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className={cn('absolute rounded-full', cfg.ringColor)}
            style={{ inset: 0 }}
            animate={{ scale: [1, 2.8 + i * 0.6], opacity: [0.18 - i * 0.04, 0] }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              ease: 'easeOut',
              delay: i * 0.6,
            }}
          />
        ))}

        {/* Floating particles */}
        {particles.map((p, i) => (
          <motion.div
            key={i}
            className={cn('absolute w-2 h-2 rounded-full', cfg.dotColor, 'opacity-60')}
            style={{ left: '50%', top: '50%' }}
            animate={{
              x: [0, p.x * 0.6, p.x, p.x * 0.6, 0],
              y: [0, p.y * 0.6, p.y, p.y * 0.6, 0],
              opacity: [0, 0.7, 0.4, 0.7, 0],
              scale: [0.5, 1, 0.8, 1, 0.5],
            }}
            transition={{
              duration: 3.2,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: p.delay,
            }}
          />
        ))}

        {/* Center emoji */}
        <motion.span
          className="relative z-10 text-5xl select-none"
          animate={{ y: [-5, 5, -5], rotate: [-4, 4, -4] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          {cfg.emoji}
        </motion.span>
      </div>

      {/* Label + cycling hint */}
      <div className="text-center space-y-1.5 px-4">
        <div className={cn('text-sm font-semibold', cfg.textColor)}>{message ?? cfg.label}</div>
        <AnimatePresence mode="wait">
          <motion.div
            key={hintIndex}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.35 }}
            className="text-xs text-slate-400"
          >
            {cfg.hints[hintIndex]}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Wave dots */}
      <div className="flex items-center gap-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className={cn('w-2 h-2 rounded-full', cfg.dotColor)}
            animate={{ y: [0, -6, 0], opacity: [0.3, 1, 0.3] }}
            transition={{
              duration: 1.3,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: i * 0.16,
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Public export ────────────────────────────────────────────────────────────

export function AIThinkingAnimation({
  variant = 'analyse',
  message,
  size = 'sm',
  className,
}: AIThinkingAnimationProps) {
  const cfg = VARIANTS[variant]
  return (
    <div className={className}>
      {size === 'sm' ? (
        <SmAnimation cfg={cfg} message={message} />
      ) : (
        <MdAnimation cfg={cfg} message={message} />
      )}
    </div>
  )
}
