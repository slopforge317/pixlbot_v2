import { motion } from 'motion/react'
import { useTelegram } from '../contexts'
import type { AIModel, Provider } from '../api'

// Provider icons mapping
const PROVIDER_ICONS: Record<string, string> = {
  'Nano Banana Pro': '🍌',
  'Seedream 4.5': '🌱',
  'GPT Image 1.5': '🤖',
  'Veo 3.1': '⚡',
  'Kling 2.6': '🎬',
  'Sora 2 Pro': '🎥',
}

function getProviderIcon(title: string): string {
  return PROVIDER_ICONS[title] || '🎨'
}

const STATUS_STYLES: Record<string, string> = {
  'Pro': 'bg-accent-purple/20 text-accent-purple border border-accent-purple/40',
  'Basic': 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  'Basic*': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
}

const STATUS_STYLES_SELECTED: Record<string, string> = {
  'Pro': 'bg-white/90 text-accent-purple border border-white/40',
  'Basic': 'bg-white/90 text-emerald-600 border border-white/40',
  'Basic*': 'bg-white/90 text-amber-600 border border-white/40',
}

function StatusBadge({ status, isSelected }: { status: string | null | undefined; isSelected?: boolean }) {
  if (!status) return null
  const styles = isSelected
    ? (STATUS_STYLES_SELECTED[status] ?? 'bg-white/90 text-gray-700 border border-white/40')
    : (STATUS_STYLES[status] ?? 'bg-dark-hover text-text-secondary border border-dark-border')
  return (
    <span className={`absolute -top-2 -right-2 px-1.5 py-0.5 text-[10px] font-semibold rounded-full leading-tight ${styles}`}>
      {status}
    </span>
  )
}

interface ModelSelectorProps {
  providers: Provider[]
  selectedProviderId: number | null
  selectedModelId: number | null
  onProviderChange: (provider: Provider) => void
  onModelChange: (model: AIModel) => void
  isLoading?: boolean
}

export default function ModelSelector({
  providers,
  selectedProviderId,
  selectedModelId,
  onProviderChange,
  onModelChange,
  isLoading = false,
}: ModelSelectorProps) {
  const { haptic } = useTelegram()

  const selectedProvider = providers.find((p) => p.id === selectedProviderId) ?? null

  const handleProviderSelect = (provider: Provider) => {
    haptic.selectionChanged()
    onProviderChange(provider)
  }

  const handleModelSelect = (model: AIModel) => {
    haptic.selectionChanged()
    onModelChange(model)
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-text-secondary px-1">AI Модель</h3>
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-shrink-0 h-10 w-28 rounded-full bg-dark-card/50 border border-dark-border animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  // No providers
  if (providers.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-text-secondary px-1">AI Модель</h3>
        <div className="p-4 text-center text-text-secondary text-sm">
          Нет доступных моделей
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-text-secondary px-1">AI Модель</h3>

      {/* Level 1: Provider pills */}
      <div className="flex gap-2 overflow-x-auto pt-3 pb-2 -mx-4 px-4 scrollbar-hide">
        {providers.map((provider) => {
          const isSelected = selectedProviderId === provider.id
          const modelStatus = provider.models[0]?.status
          return (
            <div key={provider.id} className="relative flex-shrink-0">
              <motion.button
                onClick={() => handleProviderSelect(provider)}
                whileTap={{ scale: 0.95 }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-full border transition-all duration-200 ${
                  isSelected
                    ? 'bg-gradient-to-r from-accent-purple to-accent-violet border-transparent text-white shadow-lg shadow-accent-purple/25'
                    : 'bg-dark-card/50 border-dark-border text-text-secondary hover:border-text-muted'
                }`}
              >
                <span className="text-lg">{getProviderIcon(provider.title)}</span>
                <span className="text-sm font-medium whitespace-nowrap">{provider.title}</span>
              </motion.button>
              <StatusBadge status={modelStatus} isSelected={isSelected} />
            </div>
          )
        })}
      </div>

      {/* Level 2: Model pills (only if provider has >1 model) */}
      {selectedProvider && selectedProvider.models.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide"
        >
          {selectedProvider.models.map((model) => {
            const isSelected = selectedModelId === model.id
            return (
              <motion.button
                key={model.id}
                onClick={() => handleModelSelect(model)}
                whileTap={{ scale: 0.95 }}
                className={`flex-shrink-0 px-4 py-2.5 rounded-full border transition-all duration-200 ${
                  isSelected
                    ? 'bg-accent-purple/20 border-accent-purple/50 text-text-primary'
                    : 'bg-dark-card/50 border-dark-border text-text-secondary hover:border-text-muted'
                }`}
              >
                <span className="text-sm font-medium whitespace-nowrap">{model.title}</span>
              </motion.button>
            )
          })}
        </motion.div>
      )}
    </div>
  )
}
