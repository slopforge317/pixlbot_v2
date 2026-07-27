import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, RefreshCw, X } from 'lucide-react'
import Header from '../components/Header'
import PackageCard from '../components/PackageCard'
import { api } from '../api'
import type { CreditPackage } from '../api'
import { useTelegram, useUser } from '../contexts'

export default function PackagesPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { showAlert, haptic } = useTelegram()
  const { refetch: refetchUser } = useUser()

  const [packages, setPackages] = useState<CreditPackage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPurchasing, setIsPurchasing] = useState(false)
  const [emailModalPkg, setEmailModalPkg] = useState<CreditPackage | null>(null)
  const [email, setEmail] = useState(() => localStorage.getItem('payment_email') || '')

  const fetchPackages = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getPackages()
      setPackages(data.packages)
    } catch {
      setError('Не удалось загрузить пакеты')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPackages()
  }, [fetchPackages])

  // Discount calc: base price per credit from first (cheapest) package
  const getDiscount = (pkg: CreditPackage): number => {
    if (packages.length === 0) return 0
    const basePricePerCredit = packages[0].price / packages[0].credit_amount
    const pkgPricePerCredit = pkg.price / pkg.credit_amount
    const discount = Math.round((1 - pkgPricePerCredit / basePricePerCredit) * 100)
    return discount > 0 ? discount : 0
  }

  // Handle return from YooKassa — check actual payment status
  useEffect(() => {
    const paymentId = searchParams.get('payment_id')
    if (!paymentId) return

    setSearchParams({}, { replace: true })

    const checkStatus = async () => {
      try {
        const { status } = await api.getPaymentStatus(Number(paymentId))
        if (status === 'success') {
          refetchUser()
          haptic.notification('success')
          showAlert('Оплата прошла успешно! Кредиты зачислены на баланс.')
        } else if (status === 'failed') {
          haptic.notification('error')
          showAlert('Оплата не прошла. Попробуйте ещё раз.')
        } else {
          // pending — webhook hasn't arrived yet
          haptic.notification('warning')
          showAlert('Оплата обрабатывается. Вы получите уведомление в Telegram, когда кредиты будут зачислены.')
        }
      } catch {
        // Can't check status — show neutral message
        showAlert('Оплата обрабатывается. Вы получите уведомление в Telegram.')
      }
    }

    checkStatus()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handlePurchase = (pkg: CreditPackage) => {
    setEmailModalPkg(pkg)
  }

  const handleConfirmPurchase = async () => {
    if (!emailModalPkg || isPurchasing) return
    const trimmed = email.trim()
    if (!trimmed || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      await showAlert('Введите корректный email')
      return
    }
    setIsPurchasing(true)
    localStorage.setItem('payment_email', trimmed)
    try {
      const response = await api.createPayment({
        credit_package_id: emailModalPkg.id,
        email: trimmed,
      })
      // Save payment_id so return URL can check status
      localStorage.setItem('last_payment_id', String(response.payment_id))
      window.location.href = response.confirmation_url
    } catch {
      await showAlert('Не удалось создать платёж. Попробуйте позже.')
      setIsPurchasing(false)
    }
    setEmailModalPkg(null)
  }

  return (
    <div className="min-h-screen bg-dark-bg">
      <Header title="Пополнить баланс" onBack={() => navigate('/')} />

      <main className="py-8">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-accent-purple animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-20 px-4 gap-4">
            <p className="text-text-secondary text-center">{error}</p>
            <button
              onClick={fetchPackages}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-dark-card border border-dark-border text-text-primary text-sm hover:border-accent-purple/30 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Повторить
            </button>
          </div>
        )}

        {!isLoading && !error && packages.length > 0 && (
          <div className="flex flex-col gap-4 px-4">
            {packages.map((pkg, i) => (
              <PackageCard
                key={pkg.id}
                pkg={pkg}
                discountPercent={getDiscount(pkg)}
                isRecommended={i === 1}
                onPurchase={handlePurchase}
                disabled={isPurchasing}
              />
            ))}
          </div>
        )}
      </main>

      {/* Email modal */}
      {emailModalPkg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="w-full max-w-sm rounded-2xl bg-dark-card border border-dark-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Email для чека</h3>
              <button
                onClick={() => setEmailModalPkg(null)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-text-secondary hover:text-text-primary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-text-secondary mb-4">
              На этот адрес придёт электронный чек об оплате
            </p>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleConfirmPurchase()}
              placeholder="you@example.com"
              autoFocus
              className="w-full px-4 py-3 rounded-xl bg-dark-bg border border-dark-border text-text-primary placeholder-text-secondary/50 text-sm focus:outline-none focus:border-accent-purple/50 mb-4"
            />
            <button
              onClick={handleConfirmPurchase}
              disabled={isPurchasing}
              className="w-full py-3 rounded-xl font-semibold text-base bg-gradient-purple text-white shadow-glow active:scale-95 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isPurchasing ? 'Подождите...' : `Оплатить ${emailModalPkg.price_formatted}`}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
