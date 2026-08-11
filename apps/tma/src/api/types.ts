/**
 * API Types - TypeScript types matching backend Pydantic schemas
 */

// =============================================================================
// Enums
// =============================================================================

export type JobStatus = "queue" | "processing" | "done" | "error";

export type ContentType = "image" | "video";

export type FieldOptionValue = string | number | boolean;

export interface FieldOption {
  value: FieldOptionValue;
  label: string;
  sort_order: number;
}

// =============================================================================
// User
// =============================================================================

export interface User {
  user_id: number;
  telegram_user_id: number;
  first_name: string;
  last_name: string | null;
  username: string | null;
  balance: number;
  created_at: string;
}

export interface UserBalance {
  balance: number;
}

// =============================================================================
// Provider → Model → PricingVariant hierarchy
// =============================================================================

export interface FieldSchema {
  type: "string" | "boolean" | "array";
  required: boolean;
  ui_label: string;
  ui_order?: number;
  default?: unknown;
  values?: FieldOptionValue[];
  options?: FieldOption[];
  max_length?: number | boolean; // can be `true` due to seed data bug
  variant?: boolean;
  max_images?: number;
  max_image_size_mb?: number;
}

export interface PricingVariant {
  id: number;
  variant_values: Record<string, unknown>;
  price: number;
}

export interface AIModel {
  id: number;
  api_model_id: string;
  title: string;
  input_mode: "text_only" | "image_required" | "image_optional";
  sort_order: number;
  input_schema: Record<string, FieldSchema>;
  variant_keys: string[];
  pricing: PricingVariant[];
  status: string | null;
}

export interface Provider {
  id: number;
  slug: string;
  title: string;
  gen_type: "image" | "video";
  sort_order: number;
  models: AIModel[];
}

export interface ProviderListResponse {
  providers: Provider[];
}

// =============================================================================
// Generations
// =============================================================================

export interface GenerationModelInfo {
  id: number;
  api_model_id: string;
  title: string;
}

export interface GenerationVariantInfo {
  id: number;
  price: number;
  variant_values: Record<string, unknown>;
}

export interface GenerationCreateRequest {
  model: GenerationModelInfo;
  variant: GenerationVariantInfo;
  input: Record<string, unknown>;
}

export interface Generation {
  job_id: number;
  status: JobStatus;
  pricing_variant_id: number;
  cost_credit: number;
  prompt: string;
  created_at: string;
}

export interface GenerationDetail extends Generation {
  model_title: string | null;
  provider_title: string | null;
  params: Record<string, unknown> | null;
  result_url: string | null;
  error_message: string | null;
  completed_at: string | null;
}

export interface GenerationListResponse {
  generations: GenerationDetail[];
  total: number;
  limit: number;
  offset: number;
}

// =============================================================================
// Credit Packages
// =============================================================================

export interface CreditPackage {
  id: number;
  name: string;
  description: string | null;
  credit_amount: number;
  price: number; // in kopeks
  price_formatted: string;
}

export interface CreditPackageListResponse {
  packages: CreditPackage[];
}

// =============================================================================
// Payments
// =============================================================================

export interface CreatePaymentRequest {
  credit_package_id: number;
  email: string;
}

export interface CreatePaymentResponse {
  payment_id: number;
  confirmation_url: string;
}

export interface PaymentStatusResponse {
  payment_id: number;
  status: 'pending' | 'success' | 'failed';
}

// =============================================================================
// Storage (S3 presigned uploads)
// =============================================================================

export interface PresignUploadRequest {
  content_type: string;
  file_size: number;
}

export interface PresignUploadResponse {
  upload_url: string;
  object_key: string;
  content_type: string;
}

// =============================================================================
// Errors
// =============================================================================

export interface APIError {
  detail: string;
}

export interface InsufficientCreditsError {
  detail: string;
  balance: number;
  required: number;
}
