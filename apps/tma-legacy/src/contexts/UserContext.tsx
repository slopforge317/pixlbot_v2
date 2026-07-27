/**
 * User Context
 *
 * Manages current user state and balance.
 * Loads user profile from /api/me on initialization.
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
import { api, type User } from "../api";
import { useTelegram } from "./TelegramContext";

// =============================================================================
// Context Types
// =============================================================================

interface UserContextValue {
  /** Current user data */
  user: User | null;

  /** Loading state */
  isLoading: boolean;

  /** Error message if loading failed */
  error: string | null;

  /** User's current balance */
  balance: number;

  /** Refetch user data from API */
  refetch: () => Promise<void>;

  /** Update balance locally (optimistic update) */
  updateBalance: (newBalance: number) => void;

  /** Deduct credits from balance (optimistic update) */
  deductCredits: (amount: number) => void;
}

const UserContext = createContext<UserContextValue | null>(null);

// =============================================================================
// Provider Component
// =============================================================================

interface UserProviderProps {
  children: ReactNode;
}

export function UserProvider({ children }: UserProviderProps) {
  const { isReady, initData } = useTelegram();

  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch user data
  const fetchUser = useCallback(async () => {
    if (!initData) {
      setIsLoading(false);
      setError("No authorization data");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const userData = await api.getMe();
      setUser(userData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load user";
      setError(message);
      console.error("Failed to fetch user:", err);
    } finally {
      setIsLoading(false);
    }
  }, [initData]);

  // Load user when Telegram is ready
  useEffect(() => {
    if (isReady && initData) {
      fetchUser();
    }
  }, [isReady, initData, fetchUser]);

  // Refetch user data
  const refetch = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  // Update balance locally
  const updateBalance = useCallback((newBalance: number) => {
    setUser((prev) => (prev ? { ...prev, balance: newBalance } : null));
  }, []);

  // Deduct credits from balance
  const deductCredits = useCallback((amount: number) => {
    setUser((prev) =>
      prev ? { ...prev, balance: Math.max(0, prev.balance - amount) } : null
    );
  }, []);

  // Current balance
  const balance = user?.balance ?? 0;

  // Build context value
  const value = useMemo<UserContextValue>(
    () => ({
      user,
      isLoading,
      error,
      balance,
      refetch,
      updateBalance,
      deductCredits,
    }),
    [user, isLoading, error, balance, refetch, updateBalance, deductCredits]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Access user context
 * @throws Error if used outside UserProvider
 */
export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within UserProvider");
  }
  return context;
}
