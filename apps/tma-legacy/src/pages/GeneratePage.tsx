import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ContentToggle from '../components/ContentToggle'
import ModelSelector from '../components/ModelSelector'
import PromptInput from '../components/PromptInput'
import ReferenceUpload from '../components/ReferenceUpload'
import ParamCarousel from '../components/ParamCarousel'
import ParamSwitch from '../components/ParamSwitch'
import GenerateButton from '../components/GenerateButton'
import InsufficientCreditsModal from '../components/InsufficientCreditsModal'
import GenerationStartedModal from '../components/GenerationStartedModal'
import { useUser, useProviders, useTelegram } from '../contexts'
import { api, InsufficientCreditsAPIError } from '../api'
import type { AIModel, Provider } from '../api'
import type { UploadedImage } from '../utils/upload'
import {
  buildPriceMap,
  getCurrentVariant,
  initFormValues,
  getSortedFields,
  isImageField,
  isPromptField,
  isCarouselField,
  isBooleanField,
  getMaxLength,
} from '../utils/pricing'

type ContentType = 'photo' | 'video'

const PLACEHOLDER_PROMPT = 'Хрустальный шар с миниатюрной Москвой внутри. Кремль, Собор Василия Блаженного и высотки отражаются в стеклянной сфере. Мягкий свет, снежинки кружатся внутри шара...'

export default function GeneratePage() {
  const navigate = useNavigate()
  const { balance, deductCredits } = useUser()
  const { imageProviders, videoProviders, isLoading: providersLoading } = useProviders()
  const { haptic, showAlert, close } = useTelegram()

  // Content type state
  const [contentType, setContentType] = useState<ContentType>('photo')

  // Selection state
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null)
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null)

  // Form state
  const [prompt, setPrompt] = useState('')
  const [formValues, setFormValues] = useState<Record<string, unknown>>({})
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([])

  // Upload & generation state
  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [showCreditsModal, setShowCreditsModal] = useState(false)
  const [showGenerationStartedModal, setShowGenerationStartedModal] = useState(false)

  // Current providers based on content type
  const currentProviders = contentType === 'photo' ? imageProviders : videoProviders

  // Derive selected model
  const selectedModel = useMemo((): AIModel | null => {
    if (!selectedProviderId || !selectedModelId) return null
    const provider = currentProviders.find((p) => p.id === selectedProviderId)
    return provider?.models.find((m) => m.id === selectedModelId) ?? null
  }, [currentProviders, selectedProviderId, selectedModelId])

  // Price map and current variant
  const priceMap = useMemo(
    () => (selectedModel ? buildPriceMap(selectedModel) : new Map()),
    [selectedModel]
  )

  const currentVariant = useMemo(
    () => (selectedModel ? getCurrentVariant(selectedModel, priceMap, formValues) : undefined),
    [selectedModel, priceMap, formValues]
  )

  // Sorted fields from schema
  const sortedFields = useMemo(
    () => (selectedModel ? getSortedFields(selectedModel.input_schema) : []),
    [selectedModel]
  )

  // Prompt max length from schema
  const promptMaxLength = useMemo(() => {
    if (!selectedModel) return undefined
    const promptField = selectedModel.input_schema['prompt']
    return promptField ? getMaxLength(promptField) : undefined
  }, [selectedModel])

  const promptExceeded = promptMaxLength !== undefined && prompt.length > promptMaxLength

  // Credits
  const credits = currentVariant?.price ?? 0

  // Image field info from schema
  const imageFieldInfo = useMemo(() => {
    if (!selectedModel) return null
    for (const [key, field] of Object.entries(selectedModel.input_schema)) {
      if (isImageField(key, field)) {
        return { key, field }
      }
    }
    return null
  }, [selectedModel])

  // Check if images are required but missing
  const requiredImagesMissing = imageFieldInfo
    ? imageFieldInfo.field.required && uploadedImages.length === 0
    : false

  // Select model helper — initializes form values
  const selectModel = useCallback((model: AIModel) => {
    setSelectedModelId(model.id)
    setFormValues(initFormValues(model.input_schema))
    setUploadedImages([])
  }, [])

  // Auto-select first provider → first model on load / content type change
  useEffect(() => {
    if (currentProviders.length > 0) {
      const firstProvider = currentProviders[0]
      setSelectedProviderId(firstProvider.id)
      if (firstProvider.models.length > 0) {
        selectModel(firstProvider.models[0])
      } else {
        setSelectedModelId(null)
        setFormValues({})
        setUploadedImages([])
      }
    } else {
      setSelectedProviderId(null)
      setSelectedModelId(null)
      setFormValues({})
      setUploadedImages([])
    }
  }, [currentProviders, selectModel])

  // Handlers
  const handleContentTypeChange = (type: ContentType) => {
    haptic.selectionChanged()
    setContentType(type)
    // Preserve prompt across switches
  }

  const handleProviderChange = (provider: Provider) => {
    setSelectedProviderId(provider.id)
    if (provider.models.length > 0) {
      selectModel(provider.models[0])
    }
  }

  const handleModelChange = (model: AIModel) => {
    selectModel(model)
  }

  const handleFormValueChange = (key: string, value: unknown) => {
    setFormValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleGenerate = async () => {
    if (!currentVariant || !selectedModel || !prompt.trim()) return

    if (balance < credits) {
      haptic.notification('error')
      setShowCreditsModal(true)
      return
    }

    setIsGenerating(true)
    haptic.impact('medium')

    try {
      deductCredits(credits)

      // Build input: all form values + prompt + uploaded images (as object keys)
      const input: Record<string, unknown> = { ...formValues }
      input.prompt = prompt.trim()
      if (imageFieldInfo && uploadedImages.length > 0) {
        input[imageFieldInfo.key] = uploadedImages.map(img => img.objectKey)
      }

      await api.createGeneration({
        model: {
          id: selectedModel.id,
          api_model_id: selectedModel.api_model_id,
          title: selectedModel.title,
        },
        variant: {
          id: currentVariant.id,
          price: currentVariant.price,
          variant_values: currentVariant.variant_values,
        },
        input,
      })

      haptic.notification('success')
      setShowGenerationStartedModal(true)
    } catch (error) {
      haptic.notification('error')

      if (error instanceof InsufficientCreditsAPIError) {
        setShowCreditsModal(true)
      } else {
        const message = error instanceof Error ? error.message : 'Ошибка генерации'
        await showAlert(message)
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const handleBack = () => {
    navigate('/history')
  }

  const isDisabled =
    !prompt.trim() ||
    promptExceeded ||
    !currentVariant ||
    requiredImagesMissing ||
    isUploading ||
    isGenerating

  return (
    <div className="min-h-screen bg-dark-bg pb-24">
      <Header
        title="Генерация"
        leftLabel="История"
        onBack={handleBack}
        rightAction={{ label: 'Пополнить', onClick: () => navigate('/packages') }}
      />

      <main className="px-4 py-6 space-y-6">
        {/* Content type toggle — hidden when no video providers available */}
        {videoProviders.length > 0 && (
          <ContentToggle value={contentType} onChange={handleContentTypeChange} />
        )}

        {/* Provider & Model selection */}
        <ModelSelector
          providers={currentProviders}
          selectedProviderId={selectedProviderId}
          selectedModelId={selectedModelId}
          onProviderChange={handleProviderChange}
          onModelChange={handleModelChange}
          isLoading={providersLoading}
        />

        {/* Available generations informer */}
        {credits > 0 && (
          <p className="text-sm text-text-secondary px-1">
            Доступно генераций:{' '}
            <span className="font-semibold text-text-primary">{Math.floor(balance / credits)}</span>
          </p>
        )}

        {/* Dynamic form fields from input_schema */}
        {selectedModel && sortedFields.map(([key, field]) => {
          // Prompt field
          if (isPromptField(key, field)) {
            return (
              <PromptInput
                key={key}
                value={prompt}
                onChange={setPrompt}
                placeholder={PLACEHOLDER_PROMPT}
                maxLength={promptMaxLength}
              />
            )
          }

          // Image upload field
          if (isImageField(key, field)) {
            return (
              <ReferenceUpload
                key={key}
                images={uploadedImages}
                onChange={setUploadedImages}
                onUploadingChange={setIsUploading}
                label={field.ui_label}
                maxImages={field.max_images}
                maxImageSizeMb={field.max_image_size_mb}
                required={field.required}
              />
            )
          }

          // Carousel field (string with values)
          if (isCarouselField(field)) {
            return (
              <ParamCarousel
                key={key}
                label={field.ui_label}
                values={field.values!}
                selected={formValues[key] as string}
                onChange={(v) => handleFormValueChange(key, v)}
                isVariant={field.variant}
              />
            )
          }

          // Boolean toggle field
          if (isBooleanField(field)) {
            return (
              <ParamSwitch
                key={key}
                label={field.ui_label}
                checked={formValues[key] as boolean}
                onChange={(v) => handleFormValueChange(key, v)}
                isVariant={field.variant}
              />
            )
          }

          return null
        })}
      </main>

      {/* Generate button (fixed at bottom) */}
      <GenerateButton
        disabled={isDisabled}
        loading={isGenerating}
        onClick={handleGenerate}
      />

      {/* Insufficient credits modal */}
      <InsufficientCreditsModal
        isOpen={showCreditsModal}
        onClose={() => setShowCreditsModal(false)}
        onTopUp={() => {
          setShowCreditsModal(false)
          navigate('/packages')
        }}
      />

      {/* Generation started modal */}
      <GenerationStartedModal
        isOpen={showGenerationStartedModal}
        onClose={close}
        onDismiss={() => setShowGenerationStartedModal(false)}
      />
    </div>
  )
}
