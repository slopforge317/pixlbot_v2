import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Box } from 'lucide-react'
import { useUser } from '../contexts'
import { useTelegram } from '../contexts'

interface HeaderProps {
  title: string
  showBack?: boolean
  onBack?: () => void
  leftLabel?: string
  rightAction?: { label: string; onClick: () => void }
}

export default function Header({ title, showBack = true, onBack, leftLabel, rightAction }: HeaderProps) {
  const navigate = useNavigate()
  const { balance, isLoading } = useUser()
  const { haptic } = useTelegram()

  const handleBack = () => {
    haptic.impact('light')
    if (onBack) {
      onBack()
    } else {
      navigate(-1)
    }
  }

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-4 py-3 bg-dark-bg/80 backdrop-blur-xl border-b border-dark-border/50">
      {/* Back button / left label */}
      {showBack ? (
        leftLabel ? (
          <button
            onClick={handleBack}
            className="px-3 py-2 text-sm font-semibold text-accent-purple active:scale-95 transition-all duration-200"
          >
            {leftLabel}
          </button>
        ) : (
          <button
            onClick={handleBack}
            className="w-10 h-10 flex items-center justify-center rounded-xl bg-dark-card hover:bg-dark-hover active:scale-95 transition-all duration-200"
            aria-label="Назад"
          >
            <ArrowLeft className="w-5 h-5 text-text-primary" />
          </button>
        )
      ) : (
        <div className="w-10" />
      )}

      {/* Title */}
      <h1 className="text-lg font-semibold text-text-primary">
        {title}
      </h1>

      {/* Right section: optional action + balance */}
      <div className="flex items-center gap-2">
        {rightAction && (
          <button
            onClick={rightAction.onClick}
            className="px-3 py-2 rounded-xl bg-gradient-purple text-white text-sm font-semibold active:scale-95 transition-all duration-200 shadow-glow-sm"
          >
            {rightAction.label}
          </button>
        )}
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-dark-card border border-dark-border">
          <Box className="w-4 h-4 text-accent-purple" />
          <span className="text-sm font-semibold text-text-primary">
            {isLoading ? '...' : balance}
          </span>
        </div>
      </div>
    </header>
  )
}
