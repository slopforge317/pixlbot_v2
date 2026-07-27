/**
 * History Page
 *
 * Displays user's generation history with filtering and pagination.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { Plus, Loader2, RefreshCw } from 'lucide-react'
import Header from '../components/Header'
import GenerationCard from '../components/GenerationCard'
import { useTelegram } from '../contexts'
import { api, type GenerationDetail, type JobStatus } from '../api'

type FilterStatus = JobStatus | 'all'

const FILTERS: { value: FilterStatus; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'queue', label: 'В очереди' },
  { value: 'processing', label: 'В работе' },
  { value: 'done', label: 'Готово' },
  { value: 'error', label: 'Ошибки' },
]

const PAGE_SIZE = 10

export default function HistoryPage() {
  const navigate = useNavigate()
  const { haptic } = useTelegram()

  // State
  const [generations, setGenerations] = useState<GenerationDetail[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  // Fetch generations
  const fetchGenerations = useCallback(
    async (reset: boolean = false) => {
      const offset = reset ? 0 : generations.length

      if (reset) {
        setIsLoading(true)
      } else {
        setIsLoadingMore(true)
      }
      setError(null)

      try {
        const response = await api.getGenerations({
          limit: PAGE_SIZE,
          offset,
          status: filter === 'all' ? undefined : filter,
        })

        if (reset) {
          setGenerations(response.generations)
        } else {
          setGenerations((prev) => [...prev, ...response.generations])
        }

        setTotal(response.total)
        setHasMore(offset + response.generations.length < response.total)
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Не удалось загрузить историю'
        setError(message)
      } finally {
        setIsLoading(false)
        setIsLoadingMore(false)
      }
    },
    [filter, generations.length]
  )

  // Initial load and filter change
  useEffect(() => {
    fetchGenerations(true)
  }, [filter])

  // Handle filter change
  const handleFilterChange = (newFilter: FilterStatus) => {
    if (newFilter !== filter) {
      haptic.selectionChanged()
      setFilter(newFilter)
    }
  }

  // Handle load more
  const handleLoadMore = () => {
    haptic.impact('light')
    fetchGenerations(false)
  }

  // Handle refresh
  const handleRefresh = () => {
    haptic.impact('light')
    fetchGenerations(true)
  }

  // Handle card click
  const handleCardClick = (generation: GenerationDetail) => {
    haptic.impact('light')
    // Could navigate to detail page or show modal
    console.log('Generation clicked:', generation.job_id)
  }

  // Handle create new
  const handleCreateNew = () => {
    haptic.impact('medium')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-dark-bg pb-24">
      <Header title="История" showBack={false} />

      {/* Filters */}
      <div className="px-4 py-3 border-b border-dark-border/50">
        <div className="flex gap-2 overflow-x-auto scrollbar-hide -mx-4 px-4">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => handleFilterChange(f.value)}
              className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                filter === f.value
                  ? 'bg-accent-purple text-white'
                  : 'bg-dark-card text-text-secondary hover:text-text-primary'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="px-4 py-4">
        {/* Error state */}
        {error && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 bg-dark-card rounded-xl text-text-secondary hover:text-text-primary transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Повторить
            </button>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-dark-card border border-dark-border rounded-2xl overflow-hidden animate-pulse"
              >
                <div className="aspect-video bg-dark-bg/50" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-dark-bg/50 rounded w-1/3" />
                  <div className="h-4 bg-dark-bg/50 rounded w-2/3" />
                  <div className="h-3 bg-dark-bg/50 rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && generations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-20 h-20 mb-6 rounded-full bg-dark-card flex items-center justify-center">
              <svg
                className="w-10 h-10 text-zinc-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-medium text-text-primary mb-2">
              {filter === 'all' ? 'Нет генераций' : 'Ничего не найдено'}
            </h2>
            <p className="text-text-secondary max-w-xs mb-6">
              {filter === 'all'
                ? 'Создайте свою первую генерацию!'
                : 'Попробуйте другой фильтр'}
            </p>
            {filter === 'all' && (
              <button
                onClick={handleCreateNew}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-purple rounded-xl font-medium text-white shadow-glow"
              >
                <Plus className="w-5 h-5" />
                Создать
              </button>
            )}
          </div>
        )}

        {/* Generations grid */}
        {!isLoading && !error && generations.length > 0 && (
          <>
            {/* Stats */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-text-secondary">
                {total} {total === 1 ? 'генерация' : total < 5 ? 'генерации' : 'генераций'}
              </span>
              <button
                onClick={handleRefresh}
                className="p-2 rounded-lg hover:bg-dark-card transition-colors"
              >
                <RefreshCw className="w-4 h-4 text-text-secondary" />
              </button>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 gap-4">
              {generations.map((gen) => (
                <GenerationCard
                  key={gen.job_id}
                  generation={gen}
                  onClick={() => handleCardClick(gen)}
                />
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div className="mt-6 flex justify-center">
                <motion.button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-2 px-6 py-3 bg-dark-card border border-dark-border rounded-xl text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
                >
                  {isLoadingMore ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Загрузка...
                    </>
                  ) : (
                    <>
                      Загрузить ещё
                    </>
                  )}
                </motion.button>
              </div>
            )}
          </>
        )}
      </main>

      {/* FAB - Create new */}
      {!isLoading && generations.length > 0 && (
        <motion.button
          onClick={handleCreateNew}
          whileTap={{ scale: 0.95 }}
          className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-purple rounded-full shadow-glow-lg flex items-center justify-center"
        >
          <Plus className="w-6 h-6 text-white" />
        </motion.button>
      )}
    </div>
  )
}
