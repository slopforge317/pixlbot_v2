/// <reference types="vite/client" />

interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    user?: {
      id: number
      first_name: string
      last_name?: string
      username?: string
      language_code?: string
      is_premium?: boolean
    }
    auth_date: number
    hash: string
  }
  ready: () => void
  expand: () => void
  close: () => void
}

interface Telegram {
  WebApp: TelegramWebApp
}

declare global {
  interface Window {
    Telegram?: Telegram
  }
}

export {}
