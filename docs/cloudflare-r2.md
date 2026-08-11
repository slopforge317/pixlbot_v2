# Cloudflare R2

Пользовательские изображения хранятся в приватном Cloudflare R2 bucket.
Backend создаёт короткоживущие presigned PUT/GET URL через S3-compatible API;
постоянные R2 credentials никогда не передаются в TMA.

## Переменные окружения

```dotenv
R2_ACCESS_KEY_ID=<Access Key ID>
R2_SECRET_ACCESS_KEY=<Secret Access Key>
R2_BUCKET_NAME=<bucket name>
R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_REGION=auto
R2_UPLOAD_MAX_SIZE_BYTES=31457280
R2_PRESIGN_UPLOAD_EXPIRES=600
R2_PRESIGN_DOWNLOAD_EXPIRES=3600
```

Обычный bucket использует region `auto`. Для bucket с EU/FedRAMP jurisdiction
нужен соответствующий jurisdiction endpoint из Cloudflare dashboard.

## Bucket policy

Bucket остаётся приватным. Для browser upload через presigned PUT настройте CORS:

```json
[
  {
    "AllowedOrigins": [
      "https://tma.pixlbot.ru",
      "http://localhost:5173"
    ],
    "AllowedMethods": ["PUT"],
    "AllowedHeaders": ["Content-Type"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Для временных пользовательских файлов настройте lifecycle rule:

- prefix: `uploads/`;
- delete objects after: `1 day`;
- status: enabled.

Удаление lifecycle асинхронное: объект может оставаться доступным некоторое
время после наступления expiration.

## Upload flow

1. TMA вызывает `POST /api/storage/presign-upload`.
2. TMA отправляет файл напрямую в R2 через presigned PUT и точный
   `Content-Type` из ответа backend.
3. TMA отправляет `object_key` в поле изображения `POST /api/generations`.
4. Backend перед вызовом KIE заменяет `object_key` на presigned GET URL.

## Smoke test

1. Откройте TMA внутри Telegram и выберите модель с референсом.
2. Добавьте JPG, PNG или WEBP и запустите генерацию.
3. В browser network должны завершиться `presign-upload`, PUT в R2 и
   `POST /api/generations`.
4. В R2 должен появиться объект с prefix `uploads/<user_id>/`.
5. В backend logs не должно быть ошибок `Cloudflare R2 storage is not configured`
   или `SignatureDoesNotMatch`.

Документация Cloudflare:

- https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- https://developers.cloudflare.com/r2/buckets/cors/
- https://developers.cloudflare.com/r2/buckets/object-lifecycles/
