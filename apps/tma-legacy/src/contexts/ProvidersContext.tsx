/**
 * Providers Context
 *
 * Manages providers, models, and pricing state.
 * Loads providers from /api/providers on initialization.
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
import { api, type AIModel, type Provider } from "../api";
import { useTelegram } from "./TelegramContext";

// =============================================================================
// Context Types
// =============================================================================

interface ProvidersContextValue {
  providers: Provider[];
  isLoading: boolean;
  error: string | null;
  imageProviders: Provider[];
  videoProviders: Provider[];
  getProviderById: (id: number) => Provider | undefined;
  getModelById: (id: number) => AIModel | undefined;
  refetch: () => Promise<void>;
}

const ProvidersContext = createContext<ProvidersContextValue | null>(null);

// =============================================================================
// Provider Component
// =============================================================================

interface ProvidersProviderProps {
  children: ReactNode;
}

export function ProvidersProvider({ children }: ProvidersProviderProps) {
  const { isReady, initData } = useTelegram();

  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProviders = useCallback(async () => {
    if (!initData) {
      setIsLoading(false);
      setError("No authorization data");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getProviders();
      setProviders(response.providers);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load providers";
      setError(message);
      console.error("Failed to fetch providers:", err);
    } finally {
      setIsLoading(false);
    }
  }, [initData]);

  useEffect(() => {
    if (isReady && initData) {
      fetchProviders();
    }
  }, [isReady, initData, fetchProviders]);

  const refetch = useCallback(async () => {
    await fetchProviders();
  }, [fetchProviders]);

  const imageProviders = useMemo(
    () => providers.filter((p) => p.gen_type === "image"),
    [providers]
  );

  const videoProviders = useMemo(
    () => providers.filter((p) => p.gen_type === "video"),
    [providers]
  );

  const getProviderById = useCallback(
    (id: number) => providers.find((p) => p.id === id),
    [providers]
  );

  const getModelById = useCallback(
    (id: number): AIModel | undefined => {
      for (const provider of providers) {
        const model = provider.models.find((m) => m.id === id);
        if (model) return model;
      }
      return undefined;
    },
    [providers]
  );

  const value = useMemo<ProvidersContextValue>(
    () => ({
      providers,
      isLoading,
      error,
      imageProviders,
      videoProviders,
      getProviderById,
      getModelById,
      refetch,
    }),
    [
      providers,
      isLoading,
      error,
      imageProviders,
      videoProviders,
      getProviderById,
      getModelById,
      refetch,
    ]
  );

  return (
    <ProvidersContext.Provider value={value}>
      {children}
    </ProvidersContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

export function useProviders(): ProvidersContextValue {
  const context = useContext(ProvidersContext);
  if (!context) {
    throw new Error("useProviders must be used within ProvidersProvider");
  }
  return context;
}
