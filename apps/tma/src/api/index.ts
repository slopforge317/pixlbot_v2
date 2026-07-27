/**
 * API module - re-export all API functionality
 */

// Client and errors
export {
  apiClient,
  APIClientError,
  InsufficientCreditsAPIError,
  UnauthorizedError,
} from "./client";

// API functions
export { api, getMe, getProviders, createGeneration, getGenerations, getGeneration, sendOriginal, getPackages, createPayment, getPaymentStatus, presignUpload } from "./endpoints";

// Types
export type {
  // Enums
  JobStatus,
  ContentType,
  // User
  User,
  UserBalance,
  // Provider → Model → PricingVariant
  FieldSchema,
  PricingVariant,
  AIModel,
  Provider,
  ProviderListResponse,
  // Generations
  GenerationCreateRequest,
  Generation,
  GenerationDetail,
  GenerationListResponse,
  // Packages
  CreditPackage,
  CreditPackageListResponse,
  // Payments
  CreatePaymentRequest,
  CreatePaymentResponse,
  PaymentStatusResponse,
  // Storage
  PresignUploadRequest,
  PresignUploadResponse,
  // Errors
  APIError,
  InsufficientCreditsError,
} from "./types";
