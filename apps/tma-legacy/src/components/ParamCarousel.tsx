import { useEffect, useRef } from 'react'
import { motion } from 'motion/react'

interface ParamCarouselProps {
  label: string
  values: string[]
  selected: string
  onChange: (value: string) => void
  isVariant?: boolean
}

export default function ParamCarousel({
  label,
  values,
  selected,
  onChange,
  isVariant,
}: ParamCarouselProps) {
  const selectedRef = useRef<HTMLButtonElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const btn = selectedRef.current
    const container = containerRef.current
    if (btn && container) {
      const scrollLeft = btn.offsetLeft - container.offsetWidth / 2 + btn.offsetWidth / 2
      container.scrollLeft = scrollLeft
    }
  }, [selected])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-1">
        <h3 className="text-sm font-medium text-text-secondary">{label}</h3>
        {isVariant && (
          <span className="text-[10px] text-accent-purple font-medium">Влияет на цену</span>
        )}
      </div>

      <div ref={containerRef} className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
        {values.map((value) => {
          const isSelected = selected === value
          return (
            <motion.button
              key={value}
              ref={isSelected ? selectedRef : undefined}
              onClick={() => onChange(value)}
              whileTap={{ scale: 0.95 }}
              className={`flex-shrink-0 px-4 py-2.5 rounded-full border transition-all duration-200 ${
                isSelected
                  ? 'bg-gradient-to-r from-accent-purple to-accent-violet border-transparent text-white shadow-lg shadow-accent-purple/25'
                  : 'bg-dark-card/50 border-dark-border text-text-secondary hover:border-text-muted'
              }`}
            >
              <span className="text-sm font-medium whitespace-nowrap">{value}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
