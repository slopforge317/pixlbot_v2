/**
 * Telegram WebApp Context
 *
 * Provides access to Telegram WebApp API throughout the app.
 * Handles initialization, theme, and haptic feedback.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import {
  getTelegramWebApp,
  isTelegramWebApp,
  type WebApp,
  type TelegramUser,
  type ThemeParams,
  type HapticImpactStyle,
  type HapticNotificationType,
} from "../telegram/types";

// =============================================================================
// Context Types
// =============================================================================

interface TelegramContextValue {
  /** Telegram WebApp instance (null if not in TMA) */
  webApp: WebApp | null;

  /** Whether running inside Telegram WebApp */
  isTelegram: boolean;

  /** Whether WebApp is ready */
  isReady: boolean;

  /** Raw initData string for API auth */
  initData: string;

  /** Parsed user data from initData */
  user: TelegramUser | null;

  /** Current color scheme */
  colorScheme: "light" | "dark";

  /** Theme parameters */
  themeParams: ThemeParams;

  /** Haptic feedback helpers */
  haptic: {
    impact: (style?: HapticImpactStyle) => void;
    notification: (type: HapticNotificationType) => void;
    selectionChanged: () => void;
  };

  /** Show alert popup */
  showAlert: (message: string) => Promise<void>;

  /** Show confirm popup */
  showConfirm: (message: string) => Promise<boolean>;

  /** Open external link */
  openLink: (url: string) => void;

  /** Close WebApp */
  close: () => void;
}

const TelegramContext = createContext<TelegramContextValue | null>(null);

// =============================================================================
// Mock data for development
// =============================================================================

const MOCK_INIT_DATA = import.meta.env.VITE_MOCK_INIT_DATA || "";

const MOCK_USER: TelegramUser | null = MOCK_INIT_DATA
  ? {
      id: 123456789,
      first_name: "Dev",
      last_name: "User",
      username: "devuser",
      language_code: "en",
    }
  : null;

// =============================================================================
// Provider Component
// =============================================================================

interface TelegramProviderProps {
  children: ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const [webApp] = useState<WebApp | null>(() => getTelegramWebApp());

  // Initialize WebApp
  useEffect(() => {
    if (webApp) {
      // Signal that app is ready
      webApp.ready();

      // Expand to full height
      webApp.expand();

      // Disable closing confirmation for better UX
      // webApp.enableClosingConfirmation();

      setIsReady(true);
    } else if (MOCK_INIT_DATA) {
      // Dev mode without Telegram
      setIsReady(true);
    }
  }, [webApp]);

  // Haptic feedback helpers
  const haptic = useMemo(
    () => ({
      impact: (style: HapticImpactStyle = "medium") => {
        webApp?.HapticFeedback?.impactOccurred(style);
      },
      notification: (type: HapticNotificationType) => {
        webApp?.HapticFeedback?.notificationOccurred(type);
      },
      selectionChanged: () => {
        webApp?.HapticFeedback?.selectionChanged();
      },
    }),
    [webApp]
  );

  // Show alert as promise
  const showAlert = useCallback(
    (message: string): Promise<void> => {
      return new Promise((resolve) => {
        if (webApp) {
          webApp.showAlert(message, resolve);
        } else {
          window.alert(message);
          resolve();
        }
      });
    },
    [webApp]
  );

  // Show confirm as promise
  const showConfirm = useCallback(
    (message: string): Promise<boolean> => {
      return new Promise((resolve) => {
        if (webApp) {
          webApp.showConfirm(message, (confirmed) => resolve(confirmed));
        } else {
          resolve(window.confirm(message));
        }
      });
    },
    [webApp]
  );

  // Open external link
  const openLink = useCallback(
    (url: string) => {
      if (webApp) {
        webApp.openLink(url);
      } else {
        window.open(url, "_blank");
      }
    },
    [webApp]
  );

  // Close WebApp
  const close = useCallback(() => {
    webApp?.close();
  }, [webApp]);

  // Build context value
  const value = useMemo<TelegramContextValue>(
    () => ({
      webApp,
      isTelegram: isTelegramWebApp(),
      isReady,
      initData: webApp?.initData || MOCK_INIT_DATA,
      user: webApp?.initDataUnsafe?.user || MOCK_USER,
      colorScheme: webApp?.colorScheme || "light",
      themeParams: webApp?.themeParams || {},
      haptic,
      showAlert,
      showConfirm,
      openLink,
      close,
    }),
    [webApp, isReady, haptic, showAlert, showConfirm, openLink, close]
  );

  return (
    <TelegramContext.Provider value={value}>
      {children}
    </TelegramContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Access Telegram WebApp context
 * @throws Error if used outside TelegramProvider
 */
export function useTelegram(): TelegramContextValue {
  const context = useContext(TelegramContext);
  if (!context) {
    throw new Error("useTelegram must be used within TelegramProvider");
  }
  return context;
}

/**
 * Access Telegram WebApp context (returns null if outside provider)
 */
export function useTelegramOptional(): TelegramContextValue | null {
  return useContext(TelegramContext);
}
