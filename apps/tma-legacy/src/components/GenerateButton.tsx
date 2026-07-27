import { Sparkles, Loader2 } from 'lucide-react'
import { motion } from 'motion/react'

interface GenerateButtonProps {
  disabled?: boolean
  loading?: boolean
  onClick: () => void
}

export default function GenerateButton({
  disabled,
  loading,
  onClick,
}: GenerateButtonProps) {
  const isDisabled = disabled || loading

  return (
    <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-dark-bg via-dark-bg to-transparent pt-8">
      <motion.button
        onClick={onClick}
        disabled={isDisabled}
        whileTap={{ scale: isDisabled ? 1 : 0.98 }}
        className={`w-full flex items-center justify-center gap-2 py-4 px-6 rounded-2xl font-semibold text-white transition-all duration-300 ${
          isDisabled
            ? 'bg-dark-card border border-dark-border text-text-muted cursor-not-allowed'
            : 'bg-gradient-purple shadow-glow-lg hover:shadow-glow active:shadow-glow-sm'
        }`}
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Генерация...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            <span>Генерировать</span>
          </>
        )}
      </motion.button>
    </div>
  )
}
