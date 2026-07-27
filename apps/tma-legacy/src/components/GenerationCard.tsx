/**
 * Generation Card Component
 *
 * Displays a single generation job with status, preview, and details.
 */

import { useState } from 'react'
import { motion } from 'motion/react'
import { Clock, Loader2, CheckCircle, XCircle, Image, Film, Copy, Check, Send } from 'lucide-react'
import type { GenerationDetail, JobStatus } from '../api'
import { sendOriginal } from '../api'

interface GenerationCardProps {
  generation: GenerationDetail
  onClick?: () => void
}

const STATUS_CONFIG: Record<
  JobStatus,
  { icon: typeof Clock; label: string; color: string; bgColor: string }
> = {
  queue: {
    icon: Clock,
    label: 'В очереди',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/10',
  },
  processing: {
    icon: Loader2,
    label: 'Генерация...',
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/10',
  },
  done: {
    icon: CheckCircle,
    label: 'Готово',
    color: 'text-green-400',
    bgColor: 'bg-green-400/10',
  },
  error: {
    icon: XCircle,
    label: 'Ошибка',
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
  },
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Только что'
  if (diffMins < 60) return `${diffMins} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`

  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  })
}

function truncatePrompt(prompt: string, maxLength: number = 80): string {
  if (prompt.length <= maxLength) return prompt
  return prompt.slice(0, maxLength).trim() + '...'
}

export default function GenerationCard({ generation, onClick }: GenerationCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [sendState, setSendState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  const status = STATUS_CONFIG[generation.status]
  const StatusIcon = status.icon
  const isVideo = generation.provider_title?.toLowerCase().includes('veo') ||
    generation.provider_title?.toLowerCase().includes('kling') ||
    generation.provider_title?.toLowerCase().includes('sora')

  const isLongPrompt = generation.prompt.length > 80

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(generation.prompt)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handlePromptClick = (e: React.MouseEvent) => {
    if (isLongPrompt) {
      e.stopPropagation()
      setExpanded((prev) => !prev)
    }
  }

  const handleSendOriginal = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (sendState === 'loading') return
    setSendState('loading')
    try {
      await sendOriginal(generation.job_id)
      setSendState('success')
    } catch {
      setSendState('error')
    }
    setTimeout(() => setSendState('idle'), 2000)
  }

  return (
    <motion.div
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
      className="bg-dark-card border border-dark-border rounded-2xl overflow-hidden cursor-pointer hover:border-dark-border/80 transition-colors"
    >
      {/* Preview area */}
      <div className="relative aspect-video bg-dark-bg/50">
        {generation.result_url ? (
          isVideo ? (
            <video
              src={generation.result_url}
              muted
              playsInline
              preload="metadata"
              className="w-full h-full object-cover"
            />
          ) : (
            <img
              src={generation.result_url}
              alt={generation.prompt}
              className="w-full h-full object-cover"
            />
          )
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            {isVideo ? (
              <Film className="w-12 h-12 text-zinc-600" />
            ) : (
              <Image className="w-12 h-12 text-zinc-600" />
            )}
          </div>
        )}

        {/* Status badge */}
        <div
          className={`absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full ${status.bgColor}`}
        >
          <StatusIcon
            className={`w-3.5 h-3.5 ${status.color} ${
              generation.status === 'processing' ? 'animate-spin' : ''
            }`}
          />
          <span className={`text-xs font-medium ${status.color}`}>
            {status.label}
          </span>
        </div>

        {/* Cost badge */}
        <div className="absolute bottom-3 left-3 flex items-center gap-1 px-2 py-1 rounded-full bg-black/60 backdrop-blur-sm">
          <span className="text-xs text-zinc-300">
            {generation.cost_credit} кр
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-2">
        {/* Provider & Model */}
        <div className="flex items-center gap-2">
          {generation.provider_title && (
            <span className="text-xs font-medium text-accent-purple">
              {generation.provider_title}
            </span>
          )}
          {generation.model_title && (
            <>
              <span className="text-zinc-600">•</span>
              <span className="text-xs text-zinc-500">{generation.model_title}</span>
            </>
          )}
        </div>

        {/* Prompt */}
        <div className="flex items-start gap-2">
          <p
            onClick={handlePromptClick}
            className={`text-sm text-text-secondary flex-1 ${
              expanded ? '' : 'line-clamp-2'
            } ${isLongPrompt ? 'cursor-pointer active:text-text-primary' : ''}`}
          >
            {expanded ? generation.prompt : truncatePrompt(generation.prompt)}
          </p>
          <button
            onClick={handleCopy}
            className="flex-shrink-0 mt-0.5 p-1 rounded-md text-zinc-500 hover:text-text-primary hover:bg-dark-hover transition-colors"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Error message */}
        {generation.error_message && (
          <p className="text-xs text-red-400 line-clamp-1">
            {generation.error_message}
          </p>
        )}

        {/* Time */}
        <p className="text-xs text-zinc-500">{formatDate(generation.created_at)}</p>

        {/* Send original button */}
        {generation.status === 'done' && generation.result_url && (
          <button
            onClick={handleSendOriginal}
            disabled={sendState === 'loading'}
            className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              sendState === 'success'
                ? 'bg-green-500/10 text-green-400'
                : sendState === 'error'
                  ? 'bg-red-500/10 text-red-400'
                  : 'bg-accent-purple/10 text-accent-purple'
            }`}
          >
            {sendState === 'loading' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Отправка...
              </>
            ) : sendState === 'success' ? (
              <>
                <Check className="w-4 h-4" />
                Отправлено!
              </>
            ) : sendState === 'error' ? (
              <>
                <XCircle className="w-4 h-4" />
                Ошибка
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Получить оригинал
              </>
            )}
          </button>
        )}
      </div>
    </motion.div>
  )
}
