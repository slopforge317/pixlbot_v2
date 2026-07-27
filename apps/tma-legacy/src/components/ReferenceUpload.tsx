import { useState, useRef } from 'react'
import { ImagePlus, X, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { uploadFileToS3, UploadValidationError, UploadError } from '../utils/upload'
import type { UploadedImage } from '../utils/upload'

interface ReferenceUploadProps {
  images: UploadedImage[]
  onChange: (images: UploadedImage[]) => void
  onUploadingChange?: (uploading: boolean) => void
  label?: string
  maxImages?: number
  maxImageSizeMb?: number
  required?: boolean
}

export default function ReferenceUpload({
  images,
  onChange,
  onUploadingChange,
  label,
  maxImages = 1,
  maxImageSizeMb,
  required = false,
}: ReferenceUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const canAddMore = images.length < maxImages && !isUploading

  const handleFiles = async (files: File[]) => {
    const slots = maxImages - images.length
    const toUpload = files.slice(0, slots)
    if (toUpload.length === 0) return

    setError(null)
    setIsUploading(true)
    onUploadingChange?.(true)

    try {
      const results = await Promise.all(
        toUpload.map(file => uploadFileToS3(file, maxImageSizeMb))
      )
      onChange([...images, ...results])
    } catch (e) {
      if (e instanceof UploadValidationError) {
        setError(e.message)
      } else if (e instanceof UploadError) {
        setError(e.message)
      } else {
        setError('Ошибка загрузки файла')
      }
      setTimeout(() => setError(null), 3000)
    } finally {
      setIsUploading(false)
      onUploadingChange?.(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (isUploading) return
    handleFiles(Array.from(e.dataTransfer.files))
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(Array.from(e.target.files || []))
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const handleRemove = (index: number) => {
    const removed = images[index]
    URL.revokeObjectURL(removed.previewUrl)
    onChange(images.filter((_, i) => i !== index))
  }

  const restrictionParts: string[] = []
  if (maxImages > 1) restrictionParts.push(`Макс. ${maxImages} фото`)
  if (maxImageSizeMb) restrictionParts.push(`до ${maxImageSizeMb} МБ каждое`)
  const restrictionText = restrictionParts.join(', ')

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-1">
        <h3 className="text-sm font-medium text-text-secondary">
          {label || 'Фото для референса'}
        </h3>
        {!required && (
          <span className="text-xs text-text-muted">Необязательно</span>
        )}
      </div>

      {restrictionText && (
        <p className="text-xs text-text-muted px-1">{restrictionText}</p>
      )}

      {error && (
        <p className="text-xs text-red-400 px-1">{error}</p>
      )}

      {/* Image thumbnails grid */}
      {images.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {images.map((img, index) => (
            <motion.div
              key={img.objectKey}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="relative aspect-square rounded-xl overflow-hidden bg-dark-card border border-dark-border"
            >
              <img
                src={img.previewUrl}
                alt={`Reference ${index + 1}`}
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => handleRemove(index)}
                className="absolute top-1.5 right-1.5 w-6 h-6 flex items-center justify-center rounded-full bg-dark-bg/80 backdrop-blur-sm border border-dark-border hover:bg-dark-card transition-colors"
              >
                <X className="w-3 h-3 text-text-primary" />
              </button>
            </motion.div>
          ))}
        </div>
      )}

      {/* Dropzone / Add button */}
      <AnimatePresence>
        {canAddMore && (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !isUploading && inputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`flex flex-col items-center justify-center gap-3 p-8 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-200 ${
              isDragging
                ? 'border-accent-purple bg-accent-purple/5'
                : 'border-dark-border hover:border-text-muted bg-dark-card/30'
            }`}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
              isDragging ? 'bg-accent-purple/20' : 'bg-dark-card'
            }`}>
              <ImagePlus className={`w-6 h-6 ${isDragging ? 'text-accent-purple' : 'text-text-muted'}`} />
            </div>
            <span className={`text-sm font-medium ${isDragging ? 'text-accent-purple' : 'text-text-secondary'}`}>
              Загрузить изображение
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload loading indicator */}
      {isUploading && (
        <div className="flex items-center justify-center gap-2 py-4">
          <Loader2 className="w-4 h-4 text-accent-purple animate-spin" />
          <span className="text-sm text-text-muted">Загрузка...</span>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple={maxImages > 1}
        onChange={handleInputChange}
        className="hidden"
      />
    </div>
  )
}
