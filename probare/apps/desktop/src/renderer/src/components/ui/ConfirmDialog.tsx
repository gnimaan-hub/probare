import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, Info } from 'lucide-react'
import { Spinner } from './Spinner'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  /** Corps du message. Les sauts de ligne sont préservés. */
  message: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Style destructif (rouge) vs neutre. */
  danger?: boolean
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Dialogue de confirmation stylé — remplace window.confirm() pour rester dans
 * le langage visuel de l'application (les boîtes natives cassent la cohérence).
 */
export function ConfirmDialog({
  open, title, message, confirmLabel = 'Confirmer', cancelLabel = 'Annuler',
  danger = false, loading = false, onConfirm, onCancel,
}: ConfirmDialogProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => e.target === e.currentTarget && !loading && onCancel()}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-2xl shadow-modal w-full max-w-sm p-6"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                danger ? 'bg-red-100' : 'bg-primary-50'
              }`}>
                {danger
                  ? <AlertTriangle className="w-5 h-5 text-red-600" />
                  : <Info className="w-5 h-5 text-primary-600" />}
              </div>
              <h3 className="font-semibold text-slate-900">{title}</h3>
            </div>
            <div className="text-sm text-slate-600 mb-6 leading-relaxed whitespace-pre-line">
              {message}
            </div>
            <div className="flex gap-3">
              <button onClick={onCancel} disabled={loading} className="btn-secondary flex-1">
                {cancelLabel}
              </button>
              <button
                onClick={onConfirm}
                disabled={loading}
                className={`flex-1 justify-center ${
                  danger
                    ? 'px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2'
                    : 'btn-primary'
                }`}
              >
                {loading ? <Spinner size="sm" /> : null}
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
