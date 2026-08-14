/**
 * API Endpoints - typed functions for all backend API calls
 */

import { apiClient } from "./client";
import type {
  ProviderListResponse,
  CreditPackageListResponse,
  CreatePaymentRequest,
  CreatePaymentResponse,
  PaymentStatusResponse,
  Generation,
  GenerationCreateRequest,
  GenerationDetail,
  GenerationListResponse,
  JobStatus,
  User,
  ContentType,
  PresignUploadRequest,
  PresignUploadResponse,
} from "./types";

// =============================================================================
// User endpoints
// =============================================================================

/**
 * Get current user profile with balance
 * GET /api/me
 */
export function getMe(): Promise<User> {
  return apiClient.get<User>("/me");
}

// =============================================================================
// Providers endpoints
// =============================================================================

/**
 * Get list of providers with their models and pricing variants
 * GET /api/providers
 */
export function getProviders(genType?: ContentType): Promise<ProviderListResponse> {
  return apiClient.get<ProviderListResponse>("/providers", genType ? { gen_type: genType } : undefined);
}

// =============================================================================
// Generations endpoints
// =============================================================================

/**
 * Create a new generation job
 * POST /api/generations
 */
export function createGeneration(
  request: GenerationCreateRequest
): Promise<Generation> {
  return apiClient.post<Generation>("/generations", request);
}

/**
 * Get user's generation history with pagination
 * GET /api/generations
 */
export function getGenerations(options?: {
  limit?: number;
  offset?: number;
  status?: JobStatus;
}): Promise<GenerationListResponse> {
  return apiClient.get<GenerationListResponse>("/generations", options);
}

/**
 * Get details of a specific generation job
 * GET /api/generations/:id
 */
export function getGeneration(jobId: number): Promise<GenerationDetail> {
  return apiClient.get<GenerationDetail>(`/generations/${jobId}`);
}

/**
 * Send generation result as document (original quality) to user's Telegram chat
 * POST /api/generations/:id/send-original
 */
export function sendOriginal(jobId: number): Promise<{ success: boolean; message: string }> {
  return apiClient.post<{ success: boolean; message: string }>(`/generations/${jobId}/send-original`);
}

// =============================================================================
// Packages endpoints
// =============================================================================

/**
 * Get list of credit packages
 * GET /api/packages
 */
export function getPackages(): Promise<CreditPackageListResponse> {
  return apiClient.get<CreditPackageListResponse>("/packages");
}

// =============================================================================
// Payments endpoints
// =============================================================================

/**
 * Create a payment and send a Telegram invoice to the user's chat
 * POST /api/payments
 */
export function createPayment(
  request: CreatePaymentRequest
): Promise<CreatePaymentResponse> {
  return apiClient.post<CreatePaymentResponse>("/payments", request);
}

/**
 * Check payment status
 * GET /api/payments/:id/status
 */
export function getPaymentStatus(
  paymentId: number
): Promise<PaymentStatusResponse> {
  return apiClient.get<PaymentStatusResponse>(`/payments/${paymentId}/status`);
}

// =============================================================================
// Storage endpoints
// =============================================================================

/**
 * Get a presigned PUT URL for uploading a file to Cloudflare R2
 * POST /api/storage/presign-upload
 */
export function presignUpload(
  request: PresignUploadRequest
): Promise<PresignUploadResponse> {
  return apiClient.post<PresignUploadResponse>("/storage/presign-upload", request);
}

// =============================================================================
// Export all as api object for convenience
// =============================================================================

export const api = {
  // User
  getMe,

  // Providers
  getProviders,

  // Generations
  createGeneration,
  getGenerations,
  getGeneration,
  sendOriginal,

  // Packages
  getPackages,

  // Payments
  createPayment,
  getPaymentStatus,

  // Storage
  presignUpload,
};
