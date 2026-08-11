import type {
  AIModel,
  FieldOption,
  FieldOptionValue,
  FieldSchema,
  PricingVariant,
  Provider,
} from "@/api"

export type ModelParameterField = {
  key: string
  schema: FieldSchema
}

export function sortProviders(providers: Provider[]) {
  return [...providers].sort(
    (left, right) => left.sort_order - right.sort_order || left.id - right.id,
  )
}

export function selectModelForReference(
  provider: Provider | null,
  hasReference: boolean,
) {
  if (!provider) {
    return null
  }

  const models = [...provider.models].sort(
    (left, right) => left.sort_order - right.sort_order || left.id - right.id,
  )
  const preferredModes = hasReference
    ? (["image_required", "image_optional"] as const)
    : (["text_only", "image_optional"] as const)

  for (const mode of preferredModes) {
    const model = models.find((candidate) => candidate.input_mode === mode)
    if (model) {
      return model
    }
  }

  return null
}

export function getFieldOptions(schema: FieldSchema): FieldOption[] {
  if (schema.options) {
    return [...schema.options].sort(
      (left, right) => left.sort_order - right.sort_order,
    )
  }

  return (schema.values ?? []).map((value, index) => ({
    value,
    label: String(value),
    sort_order: (index + 1) * 10,
  }))
}

export function getModelParameterFields(model: AIModel | null) {
  if (!model) {
    return []
  }

  return Object.entries(model.input_schema)
    .filter(([key, schema]) => key !== "prompt" && schema.type !== "array")
    .map(([key, schema]) => ({ key, schema }))
    .sort(
      (left, right) =>
        (left.schema.ui_order ?? 0) - (right.schema.ui_order ?? 0) ||
        left.key.localeCompare(right.key),
    )
}

export function getReferenceField(provider: Provider | null) {
  if (!provider) {
    return null
  }

  const models = [...provider.models].sort(
    (left, right) => left.sort_order - right.sort_order || left.id - right.id,
  )

  for (const model of models) {
    const field = Object.entries(model.input_schema).find(
      ([, schema]) => schema.type === "array",
    )
    if (field) {
      return { key: field[0], schema: field[1] }
    }
  }

  return null
}

export function buildParameterValues(
  fields: ModelParameterField[],
  previous: Record<string, unknown>,
) {
  const values: Record<string, unknown> = {}

  for (const field of fields) {
    const options = getSelectableOptions(field.schema)
    const previousValue = previous[field.key]
    const canKeepPrevious = options.some(
      (option) => option.value === previousValue,
    )

    if (canKeepPrevious) {
      values[field.key] = previousValue
    } else if (field.schema.default !== undefined) {
      values[field.key] = field.schema.default
    } else if (field.schema.required && options.length > 0) {
      values[field.key] = options[0].value
    }
  }

  return values
}

export function getSelectableOptions(schema: FieldSchema): FieldOption[] {
  if (schema.type === "boolean") {
    return [
      { value: true, label: "Да", sort_order: 10 },
      { value: false, label: "Нет", sort_order: 20 },
    ]
  }

  return getFieldOptions(schema)
}

export function findPricingVariant(
  model: AIModel | null,
  parameters: Record<string, unknown>,
): PricingVariant | null {
  if (!model) {
    return null
  }

  return (
    model.pricing.find((variant) =>
      model.variant_keys.every(
        (key) => variant.variant_values[key] === parameters[key],
      ),
    ) ?? null
  )
}

export function encodeOptionValue(value: FieldOptionValue) {
  return `${typeof value}:${String(value)}`
}
