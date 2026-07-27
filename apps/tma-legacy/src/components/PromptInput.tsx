import { useRef, useEffect } from 'react'

interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  maxLength?: number
}

export default function PromptInput({ value, onChange, placeholder, maxLength }: PromptInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const exceeded = maxLength !== undefined && value.length > maxLength

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.max(120, textarea.scrollHeight)}px`
    }
  }, [value])

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary px-1">Запрос</h3>

      <div className="relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || 'Опишите, что вы хотите сгенерировать...'}
          className={`w-full min-h-[120px] p-4 bg-dark-card rounded-2xl border text-text-primary text-sm leading-relaxed placeholder:text-text-muted resize-none focus:ring-1 transition-all duration-200 ${
            exceeded
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
              : 'border-dark-border focus:border-accent-purple/50 focus:ring-accent-purple/20'
          }`}
          rows={4}
        />

        {/* Character count */}
        {maxLength !== undefined ? (
          <span className={`absolute bottom-3 right-3 text-xs ${
            exceeded ? 'text-red-500 font-medium' : 'text-text-muted'
          }`}>
            {value.length}/{maxLength}
          </span>
        ) : (
          value.length > 0 && (
            <span className="absolute bottom-3 right-3 text-xs text-text-muted">
              {value.length}
            </span>
          )
        )}
      </div>
    </div>
  )
}
