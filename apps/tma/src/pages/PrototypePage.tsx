import { type ChangeEvent, useCallback, useEffect, useMemo, useState } from "react"
import { BorderBeam } from "border-beam"

import { api, type FieldOptionValue, type Provider } from "@/api"
import { SurfaceCard } from "@/components/primitives/surface-card"
import {
  Attachment,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
  AttachmentTrigger,
} from "@/components/ui/attachment"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import {
  buildParameterValues,
  encodeOptionValue,
  findPricingVariant,
  getMinProviderPrice,
  getModelParameterFields,
  getReferenceField,
  getSelectableOptions,
  selectModelForReference,
  sortProviders,
} from "@/lib/model-catalog"

const promptPlaceholder =
  "Портрет в мягком студийном свете, чистый фон, естественная кожа, высокая детализация"
const promptPreviewLimit = 155

type ScreenId = "generation" | "history" | "payment"
type HistoryStatus = "Готово" | "В работе" | "Ошибка"
type ReferenceImage = {
  name: string
  url: string
}
type ModelsLoadStatus = "idle" | "loading" | "success" | "error"

function formatModelPrice(price: number | null) {
  return price === null ? "Цена не задана" : `от ${price} credits`
}

function getModelsErrorMessage(error: unknown) {
  if (error instanceof Error && error.name === "UnauthorizedError") {
    return "Нет Telegram initData. Откройте Mini App внутри Telegram."
  }

  if (error instanceof Error) {
    return `Не удалось загрузить модели: ${error.message}`
  }

  return "Не удалось загрузить модели."
}

const navItems: Array<{ id: ScreenId; label: string }> = [
  { id: "generation", label: "Генерация" },
  { id: "history", label: "История" },
  { id: "payment", label: "Оплата" },
]

const historyStatusVariants: Record<HistoryStatus, "green" | "orange" | "red"> = {
  Готово: "green",
  "В работе": "orange",
  Ошибка: "red",
}

const historyItems = [
  {
    id: "job-1842",
    title: "Студийный портрет",
    model: "Portrait Pro",
    meta: "4:5 · Standard · PNG",
    prompt:
      "Портрет в мягком студийном свете, чистый фон, естественная кожа, высокая детализация, взгляд в камеру, фотореализм, аккуратная ретушь и натуральные оттенки кожи.",
    status: "Готово" as HistoryStatus,
    time: "12 мин назад",
  },
  {
    id: "job-1839",
    title: "Карточка товара",
    model: "Product Shot",
    meta: "1:1 · HD · WEBP",
    prompt:
      "Минималистичная предметная съемка белых беспроводных наушников на светлом фоне, мягкие тени, коммерческий стиль, чистая композиция для карточки товара.",
    status: "В работе" as HistoryStatus,
    time: "Сегодня, 14:08",
  },
  {
    id: "job-1831",
    title: "Вариант по референсу",
    model: "Style Transfer",
    meta: "9:16 · Standard · JPG",
    prompt:
      "Сделай вертикальный fashion-кадр по референсу: городской вечерний свет, контрастная куртка, кинематографичный цвет, легкое зерно, уверенная поза.",
    status: "Ошибка" as HistoryStatus,
    time: "Вчера, 21:40",
  },
]

const paymentPackages = [
  {
    name: "Start",
    description: "Стоимость 1 генерации Pro = 29,5руб. (-20%)",
    includes: "20 Pro генераций или 50 Basic генераций",
    price: "590 руб.",
  },
  {
    name: "Pro",
    description: "Стоимость 1 генерации Pro = 26,5руб. (-10%)",
    includes: "60 Pro генераций или 150 Basic генераций",
    price: "1590 руб.",
  },
  {
    name: "Premier",
    description: "Стоимость 1 генерации Pro = 23,5руб. (-20%)",
    includes: "200 Pro генераций или 500 Basic генераций",
    price: "4700 руб.",
  },
]

export function PrototypePage() {
  const [activeScreen, setActiveScreen] = useState<ScreenId>("generation")
  const [providers, setProviders] = useState<Provider[]>([])
  const [modelsLoadStatus, setModelsLoadStatus] = useState<ModelsLoadStatus>("idle")
  const [modelsError, setModelsError] = useState("")
  const [selectedProvider, setSelectedProvider] = useState("")
  const [prompt, setPrompt] = useState("")
  const [referenceImage, setReferenceImage] = useState<ReferenceImage | null>(null)
  const [referenceError, setReferenceError] = useState("")
  const [parameterValues, setParameterValues] = useState<Record<string, unknown>>({})
  const [status, setStatus] = useState<"idle" | "queued">("idle")

  const visibleProviders = useMemo(
    () => sortProviders(providers.filter((provider) => provider.gen_type === "image")),
    [providers],
  )

  const currentProvider = useMemo(
    () =>
      visibleProviders.find((provider) => provider.slug === selectedProvider) ?? null,
    [selectedProvider, visibleProviders],
  )

  const currentModel = useMemo(
    () => selectModelForReference(currentProvider, Boolean(referenceImage)),
    [currentProvider, referenceImage],
  )

  const parameterFields = useMemo(
    () => getModelParameterFields(currentModel),
    [currentModel],
  )
  const referenceField = useMemo(
    () => getReferenceField(currentProvider),
    [currentProvider],
  )
  const currentVariant = useMemo(
    () => findPricingVariant(currentModel, parameterValues),
    [currentModel, parameterValues],
  )
  const currentPrice = currentVariant?.price ?? null
  const promptSchema = currentModel?.input_schema.prompt
  const promptMaxLength =
    typeof promptSchema?.max_length === "number" ? promptSchema.max_length : 2000

  const referenceMaxSizeMb = referenceField?.schema.max_image_size_mb ?? 10

  const modelPrice = currentProvider
    ? currentPrice ?? getMinProviderPrice(currentProvider)
    : null

  const loadModels = useCallback(async () => {
    setModelsLoadStatus("loading")
    setModelsError("")

    try {
      const response = await api.getProviders("image")

      setProviders(response.providers)
      setModelsLoadStatus("success")
    } catch (error) {
      setProviders([])
      setModelsError(getModelsErrorMessage(error))
      setModelsLoadStatus("error")
    }
  }, [])

  useEffect(() => {
    void loadModels()
  }, [loadModels])

  useEffect(() => {
    if (visibleProviders.length === 0) {
      if (selectedProvider) {
        setSelectedProvider("")
      }

      return
    }

    if (!visibleProviders.some((provider) => provider.slug === selectedProvider)) {
      setSelectedProvider(visibleProviders[0].slug)
    }
  }, [selectedProvider, visibleProviders])

  useEffect(() => {
    setParameterValues((current) => buildParameterValues(parameterFields, current))
    setStatus("idle")
  }, [parameterFields])

  useEffect(() => {
    return () => {
      if (referenceImage) {
        URL.revokeObjectURL(referenceImage.url)
      }
    }
  }, [referenceImage])

  function handleReferenceChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]

    if (!file) {
      return
    }

    if (file.size > referenceMaxSizeMb * 1024 * 1024) {
      setReferenceError(`Файл больше ${referenceMaxSizeMb} MB`)
      return
    }

    setReferenceError("")
    setReferenceImage({
      name: file.name,
      url: URL.createObjectURL(file),
    })
    setStatus("idle")
  }

  return (
    <main
      className="h-svh bg-background text-foreground"
      data-active-api-model={currentModel?.api_model_id}
      data-selected-provider={currentProvider?.slug}
    >
      <Tabs
        className="mx-auto flex h-svh w-full max-w-mini-app flex-col overflow-hidden bg-background px-16 py-16 pb-[calc(16px+env(safe-area-inset-bottom))]"
        onValueChange={(value) => setActiveScreen(value as ScreenId)}
        value={activeScreen}
      >
        <div className="grid min-h-0 flex-1 content-start gap-12 overflow-y-auto pb-16 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="grid h-48 w-full grid-cols-3 gap-6 rounded-card border border-border bg-card p-6 shadow-sm-4">
            {navItems.map((item) => (
              <TabsTrigger
                className="min-h-36 rounded-button-rect px-8 text-caption font-medium text-muted-foreground shadow-none transition hover:bg-muted hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-none"
                key={item.id}
                value={item.id}
              >
                {item.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent className="grid gap-12" value="generation">
            <SurfaceCard className="gap-10">
              <div className="flex items-center justify-between gap-12">
                <label
                  className="font-technical text-caption font-medium text-muted-foreground"
                  htmlFor="generation-model"
                >
                  Выберите модель
                </label>
                <span className="font-technical text-caption text-muted-foreground">
                  {currentProvider ? formatModelPrice(modelPrice) : "Модели"}
                </span>
              </div>
              <Select
                onValueChange={(value) => {
                  setSelectedProvider(value)
                  setStatus("idle")
                }}
                disabled={
                  modelsLoadStatus === "loading" || visibleProviders.length === 0
                }
                value={selectedProvider}
              >
                <SelectTrigger id="generation-model">
                  <SelectValue
                    placeholder={
                      modelsLoadStatus === "loading"
                        ? "Загрузка моделей..."
                        : "Выберите модель"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {visibleProviders.map((provider) => (
                      <SelectItem key={provider.slug} value={provider.slug}>
                        {provider.title}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              {currentModel?.status ? (
                <Badge className="justify-self-start" variant="blue">
                  {currentModel.status}
                </Badge>
              ) : null}
              {modelsLoadStatus === "error" ? (
                <div className="grid gap-8">
                  <p className="text-caption text-red-600">{modelsError}</p>
                  <Button
                    onClick={() => void loadModels()}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    Повторить
                  </Button>
                </div>
              ) : null}
            </SurfaceCard>

            <SurfaceCard>
              <div className="flex items-start justify-between gap-12">
                <div className="font-technical text-caption font-medium text-muted-foreground">
                  Описание кадра
                </div>
                <p className="font-technical text-caption text-muted-foreground">
                  {prompt.length}/{promptMaxLength}
                </p>
              </div>
              <Textarea
                maxLength={promptMaxLength}
                onChange={(event) => {
                  setPrompt(event.target.value)
                  setStatus("idle")
                }}
                placeholder={promptPlaceholder}
                value={prompt}
              />
            </SurfaceCard>

            <SurfaceCard>
              <div className="grid gap-4">
                <div className="font-technical text-caption font-medium text-muted-foreground">
                  Фото для референса
                </div>
              </div>
              <Attachment
                className="grid min-h-112 w-full cursor-pointer place-items-center rounded-input bg-background p-16 text-center hover:bg-muted"
                state={referenceImage ? "done" : "idle"}
              >
                <AttachmentTrigger asChild>
                  <input
                    accept="image/*"
                    className="absolute inset-0 z-10 cursor-pointer opacity-0"
                    disabled={!referenceField}
                    key={referenceImage?.url ?? "empty-reference"}
                    onChange={handleReferenceChange}
                    type="file"
                  />
                </AttachmentTrigger>
                {referenceImage ? (
                  <div className="grid w-full grid-cols-[72px_1fr] items-center gap-12 text-left">
                    <AttachmentMedia
                      className="h-72 w-72 rounded-input"
                      variant="image"
                    >
                      <img alt="" src={referenceImage.url} />
                    </AttachmentMedia>
                    <AttachmentContent className="grid gap-4 leading-normal">
                      <AttachmentTitle className="text-body-sm">
                        {referenceImage.name}
                      </AttachmentTitle>
                      <AttachmentDescription className="mt-0 text-caption">
                        Изображение прикреплено
                      </AttachmentDescription>
                    </AttachmentContent>
                  </div>
                ) : (
                  <AttachmentContent className="grid place-items-center gap-6 leading-normal">
                    <AttachmentTitle className="text-body-sm">
                      Загрузить изображение
                    </AttachmentTitle>
                    <AttachmentDescription className="mt-0 text-caption">
                      {referenceField
                        ? `JPG, PNG или WEBP до ${referenceMaxSizeMb} MB`
                        : "Эта модель не поддерживает референс"}
                    </AttachmentDescription>
                  </AttachmentContent>
                )}
              </Attachment>
              {referenceImage ? (
                <button
                  className="justify-self-start rounded-button border border-border px-12 py-6 text-caption font-medium hover:bg-muted"
                  onClick={() => {
                    setReferenceImage(null)
                    setReferenceError("")
                  }}
                  type="button"
                >
                  Удалить референс
                </button>
              ) : null}
              {referenceError ? (
                <p className="text-caption text-red-600">{referenceError}</p>
              ) : null}
            </SurfaceCard>

            {parameterFields.length > 0 ? (
              <SurfaceCard>
                <div className="grid gap-4">
                  <div className="font-technical text-caption font-medium text-muted-foreground">
                    Параметры
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-8">
                  {parameterFields.map((field) => (
                    <DynamicSelectField
                      key={field.key}
                      label={field.schema.ui_label}
                      onChange={(value) => {
                        setParameterValues((current) => ({
                          ...current,
                          [field.key]: value,
                        }))
                        setStatus("idle")
                      }}
                      options={getSelectableOptions(field.schema)}
                      value={parameterValues[field.key] as FieldOptionValue | undefined}
                    />
                  ))}
                </div>
              </SurfaceCard>
            ) : null}
          </TabsContent>

          <TabsContent value="history">
            <HistoryScreen />
          </TabsContent>

          <TabsContent value="payment">
            <PaymentScreen />
          </TabsContent>
        </div>

        {activeScreen === "generation" ? (
          <footer className="grid gap-10 border-t border-border bg-background pt-12">
            <Button
              disabled={!currentModel || !currentVariant || prompt.trim().length === 0}
              onClick={() => setStatus("queued")}
              size="lg"
              type="button"
              variant="action"
            >
              {status === "queued" ? "Задача отправлена" : "Запустить генерацию"}
            </Button>
          </footer>
        ) : null}
      </Tabs>
    </main>
  )
}

function HistoryScreen() {
  const [expandedPromptIds, setExpandedPromptIds] = useState<Record<string, boolean>>({})
  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null)

  function togglePrompt(id: string) {
    setExpandedPromptIds((current) => ({
      ...current,
      [id]: !current[id],
    }))
  }

  async function copyPrompt(id: string, prompt: string) {
    await navigator.clipboard.writeText(prompt)
    setCopiedPromptId(id)
  }

  return (
    <section className="grid gap-12">
      <div className="grid gap-8">
        {historyItems.map((item) => {
          const isExpanded = Boolean(expandedPromptIds[item.id])
          const canExpand = item.prompt.length > promptPreviewLimit
          const visiblePrompt =
            !isExpanded && canExpand
              ? `${item.prompt.slice(0, promptPreviewLimit).trimEnd()}...`
              : item.prompt

          return (
            <SurfaceCard className="gap-10" key={item.id}>
              <div className="flex items-start justify-between gap-12">
                <div className="grid min-w-0 gap-4">
                  <h3 className="truncate text-body-sm font-semibold">{item.title}</h3>
                  <p className="font-technical text-caption text-muted-foreground">
                    {item.model} · {item.meta}
                  </p>
                </div>
                <Badge variant={historyStatusVariants[item.status]}>
                  {item.status}
                </Badge>
              </div>

              <div className="grid gap-8 border-t border-border pt-10">
                <div className="flex items-center justify-between gap-12">
                  <p className="font-technical text-caption font-medium uppercase text-muted-foreground">
                    Prompt
                  </p>
                  <button
                    aria-label="Скопировать промпт"
                    className="grid h-32 w-32 place-items-center rounded-button-rect border border-border bg-card text-muted-foreground transition hover:bg-muted hover:text-foreground"
                    onClick={() => void copyPrompt(item.id, item.prompt)}
                    type="button"
                  >
                    <CopyIcon />
                  </button>
                </div>
                <p className="text-body-sm text-foreground">{visiblePrompt}</p>
                <div className="flex min-h-24 items-center justify-between gap-12">
                  {canExpand ? (
                    <button
                      className="text-caption font-medium text-action-blue"
                      onClick={() => togglePrompt(item.id)}
                      type="button"
                    >
                      {isExpanded ? "Свернуть" : "Показать полностью"}
                    </button>
                  ) : (
                    <span />
                  )}
                  {copiedPromptId === item.id ? (
                    <span className="font-technical text-caption text-muted-foreground">
                      Скопировано
                    </span>
                  ) : null}
                </div>
              </div>

              <div className="flex items-center justify-between gap-12 border-t border-border pt-8">
                <span className="font-technical text-caption text-muted-foreground">
                  {item.time}
                </span>
                <Button size="sm" type="button" variant="outline">
                  Отправить оригинал
                </Button>
              </div>
            </SurfaceCard>
          )
        })}
      </div>
    </section>
  )
}

function CopyIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-14 w-14"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <rect height="14" rx="2" ry="2" width="14" x="8" y="8" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  )
}

function PaymentScreen() {
  return (
    <section className="grid gap-12">
      <div className="grid gap-8">
        {paymentPackages.map((item) => {
          const card = (
            <SurfaceCard>
            <div className="flex items-start justify-between gap-12">
              <div className="grid gap-4">
                <h3 className="text-body font-semibold">{item.name}</h3>
                <p className="text-caption text-muted-foreground">
                  {item.description}
                </p>
              </div>
              <p className="whitespace-nowrap font-technical text-caption font-medium text-foreground">
                {item.price}
              </p>
            </div>

            <p className="text-body-sm text-foreground">
              Пакет включает: {item.includes}
            </p>

            <Button type="button" variant="action">
              Купить
            </Button>
          </SurfaceCard>
          )

          return item.name === "Pro" ? (
            <BorderBeam
              colorVariant="ocean"
              key={item.name}
              size="pulse-outside"
              strength={0.9}
              theme="light"
            >
              {card}
            </BorderBeam>
          ) : (
            <div key={item.name}>{card}</div>
          )
        })}
      </div>
    </section>
  )
}

type DynamicSelectFieldProps = {
  label: string
  options: ReturnType<typeof getSelectableOptions>
  value: FieldOptionValue | undefined
  onChange: (value: FieldOptionValue) => void
}

function DynamicSelectField({
  label,
  options,
  value,
  onChange,
}: DynamicSelectFieldProps) {
  const encodedValue =
    value === undefined ? undefined : encodeOptionValue(value)

  return (
    <div className="grid min-w-0 gap-6">
      <span className="truncate text-caption font-medium text-muted-foreground">
        {label}
      </span>
      <Select
        onValueChange={(nextValue) => {
          const option = options.find(
            (candidate) => encodeOptionValue(candidate.value) === nextValue,
          )
          if (option) {
            onChange(option.value)
          }
        }}
        value={encodedValue}
      >
        <SelectTrigger className="h-40 px-8 text-caption [font-size:var(--text-caption)] [line-height:var(--text-caption--line-height)]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {options.map((option) => (
              <SelectItem
                key={encodeOptionValue(option.value)}
                value={encodeOptionValue(option.value)}
              >
                {option.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}
