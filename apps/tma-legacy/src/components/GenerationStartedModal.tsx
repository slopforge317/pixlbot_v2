import { useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { X, Sparkles } from 'lucide-react'

interface GenerationStartedModalProps {
  isOpen: boolean
  onClose: () => void
  onDismiss: () => void
}

export default function GenerationStartedModal({ isOpen, onClose, onDismiss }: GenerationStartedModalProps) {
  // Block body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = ''
      }
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onDismiss}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="fixed inset-0 z-[101] flex items-center justify-center p-6"
          >
            <div className="w-full max-w-sm bg-dark-card rounded-2xl p-6 relative">
              {/* Close button */}
              <button
                onClick={onDismiss}
                className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-lg bg-dark-hover text-text-secondary hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>

              {/* Icon */}
              <div className="flex justify-center mb-5">
                <div className="w-16 h-16 rounded-full bg-accent-purple/20 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-accent-purple" />
                </div>
              </div>

              {/* Text */}
              <h2 className="text-xl font-bold text-text-primary text-center mb-2">
                Генерация запущена!
              </h2>
              <p className="text-sm text-text-secondary text-center mb-6">
                Ваша генерация выполняется. Результат пришлём в чат. Это окно можно закрыть.
              </p>

              {/* Close TMA button */}
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="w-full py-3.5 rounded-xl bg-gradient-purple text-white font-semibold text-base shadow-glow transition-all duration-200"
              >
                Закрыть
              </motion.button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
