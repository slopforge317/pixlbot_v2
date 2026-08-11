import { api } from "@/api"

const allowedContentTypes = new Set(["image/jpeg", "image/png", "image/webp"])

export class R2UploadError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "R2UploadError"
  }
}

export async function uploadFileToR2(file: File, maxSizeMb: number) {
  if (!allowedContentTypes.has(file.type)) {
    throw new R2UploadError("Поддерживаются только JPG, PNG и WEBP")
  }
  if (file.size <= 0) {
    throw new R2UploadError("Нельзя загрузить пустой файл")
  }
  if (file.size > maxSizeMb * 1024 * 1024) {
    throw new R2UploadError(`Файл больше ${maxSizeMb} MB`)
  }

  const { upload_url, object_key, content_type } = await api.presignUpload({
    content_type: file.type,
    file_size: file.size,
  })

  let response: Response
  try {
    response = await fetch(upload_url, {
      method: "PUT",
      headers: {
        "Content-Type": content_type,
      },
      body: file,
    })
  } catch {
    throw new R2UploadError("Не удалось подключиться к хранилищу изображений")
  }

  if (!response.ok) {
    throw new R2UploadError(`Ошибка загрузки изображения (${response.status})`)
  }

  return object_key
}
