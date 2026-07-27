import { Camera, Video } from 'lucide-react'
import { motion } from 'motion/react'

type ContentType = 'photo' | 'video'

interface ContentToggleProps {
  value: ContentType
  onChange: (value: ContentType) => void
}

export default function ContentToggle({ value, onChange }: ContentToggleProps) {
  const options: { id: ContentType; label: string; icon: typeof Camera }[] = [
    { id: 'photo', label: 'Фото', icon: Camera },
    { id: 'video', label: 'Видео', icon: Video },
  ]

  return (
    <div className="relative flex p-1 bg-dark-card rounded-2xl border border-dark-border">
      {/* Animated background */}
      <motion.div
        className="absolute top-1 bottom-1 rounded-xl bg-gradient-purple shadow-glow"
        initial={false}
        animate={{
          left: value === 'photo' ? '4px' : '50%',
          right: value === 'photo' ? '50%' : '4px',
        }}
        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      />

      {/* Options */}
      {options.map((option) => {
        const Icon = option.icon
        const isActive = value === option.id

        return (
          <button
            key={option.id}
            onClick={() => onChange(option.id)}
            className={`relative z-10 flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium transition-colors duration-200 ${
              isActive ? 'text-white' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span className="text-sm">{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}
