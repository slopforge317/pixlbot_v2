import { motion } from 'motion/react'
import type { CreditPackage } from '../api'

interface PackageCardProps {
  pkg: CreditPackage
  discountPercent: number
  isRecommended: boolean
  onPurchase: (pkg: CreditPackage) => void
  disabled?: boolean
}

export default function PackageCard({ pkg, discountPercent, isRecommended, onPurchase, disabled }: PackageCardProps) {
  const proGens = Math.floor(pkg.credit_amount / 5)
  const basicGens = Math.floor(pkg.credit_amount / 2)
  const pricePerProGen = ((pkg.price / 100) / proGens).toFixed(0)

  return (
    <motion.div
      whileTap={{ scale: 0.98 }}
      className={`flex flex-col rounded-2xl p-6 ${
        isRecommended
          ? 'glow-border border border-accent-purple/50 bg-dark-card'
          : 'border border-dark-border bg-dark-card'
      }`}
    >
      {/* Badges */}
      <div className="flex items-center gap-2 mb-4 min-h-[28px]">
        {discountPercent > 0 && (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400">
            -{discountPercent}%
          </span>
        )}
        {isRecommended && (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-accent-purple/20 text-accent-purple">
            Популярный
          </span>
        )}
      </div>

      {/* Name */}
      <h3 className={`text-2xl font-bold text-text-primary mb-1 ${isRecommended ? 'text-3xl' : ''}`}>
        {pkg.name}
      </h3>

      {/* Generations */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-accent-purple/20 text-accent-purple border border-accent-purple/40">Pro</span>
          <span className="text-lg font-semibold text-text-primary">{proGens} генераций</span>
        </div>
        <span className="text-text-muted">·</span>
        <div className="flex items-center gap-1.5">
          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Basic</span>
          <span className="text-lg font-semibold text-text-primary">{basicGens} генераций</span>
        </div>
      </div>

      {/* Description */}
      {pkg.description && (
        <p className="text-sm text-text-secondary mb-6 whitespace-pre-wrap">{pkg.description}</p>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Price */}
      <div className="mb-4">
        <div className="text-2xl font-bold text-text-primary">{pkg.price_formatted}</div>
        <div className="text-sm text-text-secondary">{pricePerProGen} ₽ за генерацию Pro</div>
      </div>

      {/* Buy button */}
      <motion.button
        whileTap={disabled ? undefined : { scale: 0.95 }}
        onClick={() => !disabled && onPurchase(pkg)}
        disabled={disabled}
        className={`w-full py-3.5 rounded-xl font-semibold text-base transition-all duration-200 ${
          disabled
            ? 'bg-dark-hover text-text-secondary opacity-60 cursor-not-allowed'
            : isRecommended
              ? 'bg-gradient-purple text-white shadow-glow'
              : 'bg-dark-hover text-text-primary border border-dark-border hover:border-accent-purple/30'
        }`}
      >
        {disabled ? 'Подождите...' : 'Купить'}
      </motion.button>
    </motion.div>
  )
}
