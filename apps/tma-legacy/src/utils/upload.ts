/**
 * S3 upload utilities for direct file uploads via presigned URLs
 */

import { api } from '../api'

const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"])

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

export interface UploadedImage {
  objectKey: string
  previewUrl: string
}

export class UploadValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "UploadValidationError"
  }
}

export class UploadError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "UploadError"
  }
}

/**
 * Validate a file before upload.
 * Throws UploadValidationError if the file is invalid.
 */
export function validateFile(file: File, maxSizeMb?: number): void {
  if (!ALLOWED_TYPES.has(file.type)) {
    throw new UploadValidationError(
      "Неподдерживаемый формат. Допустимые: JPEG, PNG, WebP"
    )
  }

  const maxBytes = maxSizeMb ? maxSizeMb * 1024 * 1024 : MAX_FILE_SIZE_BYTES
  if (file.size > maxBytes) {
    const limitMb = maxBytes / (1024 * 1024)
    throw new UploadValidationError(
      `Файл слишком большой (макс. ${limitMb} МБ)`
    )
  }
}

/**
 * Upload a file to S3 via presigned URL.
 *
 * 1. Validates the file
 * 2. Gets a presigned PUT URL from the backend
 * 3. PUTs the file directly to S3
 * 4. Returns the object key and a local preview URL
 */
export async function uploadFileToS3(
  file: File,
  maxSizeMb?: number,
): Promise<UploadedImage> {
  validateFile(file, maxSizeMb)

  // Get presigned URL from backend
  const { upload_url, object_key, content_type } = await api.presignUpload({
    content_type: file.type,
    file_size: file.size,
  })

  // PUT file directly to S3
  const response = await fetch(upload_url, {
    method: "PUT",
    headers: {
      "Content-Type": content_type,
    },
    body: file,
  })

  if (!response.ok) {
    throw new UploadError(
      `Ошибка загрузки файла: ${response.status} ${response.statusText}`
    )
  }

  return {
    objectKey: object_key,
    previewUrl: URL.createObjectURL(file),
  }
}
