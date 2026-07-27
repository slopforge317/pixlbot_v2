import type { AIModel, FieldSchema, PricingVariant } from "../api";

const IMAGE_FIELD_KEYS = new Set(["image_input", "image_urls", "input_urls"]);

/**
 * Build a lookup map from variant key combinations to PricingVariant.
 * Key format: "k1=v1|k2=v2" with keys sorted alphabetically.
 */
export function buildPriceMap(model: AIModel): Map<string, PricingVariant> {
  const map = new Map<string, PricingVariant>();
  for (const pv of model.pricing) {
    const key = model.variant_keys
      .slice()
      .sort()
      .map((k) => `${k}=${pv.variant_values[k]}`)
      .join("|");
    map.set(key, pv);
  }
  return map;
}

/**
 * Look up the current PricingVariant based on form values and variant keys.
 * Returns undefined if no match found.
 */
export function getCurrentVariant(
  model: AIModel,
  priceMap: Map<string, PricingVariant>,
  formValues: Record<string, unknown>
): PricingVariant | undefined {
  if (model.variant_keys.length === 0) {
    return model.pricing[0];
  }
  const key = model.variant_keys
    .slice()
    .sort()
    .map((k) => `${k}=${formValues[k]}`)
    .join("|");
  return priceMap.get(key);
}

/**
 * Initialize form values from an input_schema, using field defaults.
 * Guards against `default` not being in `values` — falls back to values[0].
 */
export function initFormValues(
  schema: Record<string, FieldSchema>
): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const [key, field] of Object.entries(schema)) {
    if (isImageField(key, field)) {
      // Image fields are managed separately
      continue;
    }
    if (isPromptField(key, field)) {
      // Prompt is managed separately
      continue;
    }
    if (field.type === "boolean") {
      values[key] = field.default ?? false;
    } else if (field.values && field.values.length > 0) {
      const def = field.default as string | undefined;
      if (def !== undefined && field.values.includes(def)) {
        values[key] = def;
      } else {
        values[key] = field.values[0];
      }
    } else if (field.default !== undefined) {
      values[key] = field.default;
    }
  }
  return values;
}

/**
 * Return schema fields sorted by ui_order (missing ui_order defaults to 10000).
 */
export function getSortedFields(
  schema: Record<string, FieldSchema>
): [string, FieldSchema][] {
  return Object.entries(schema).sort(
    ([, a], [, b]) => (a.ui_order ?? 10000) - (b.ui_order ?? 10000)
  );
}

/** Check if a field represents image upload. */
export function isImageField(key: string, field: FieldSchema): boolean {
  return field.type === "array" || IMAGE_FIELD_KEYS.has(key);
}

/** Check if a field is the prompt text area. */
export function isPromptField(key: string, field: FieldSchema): boolean {
  return (
    key === "prompt" &&
    field.type === "string" &&
    !field.values &&
    (typeof field.max_length === "number" || field.max_length === true)
  );
}

/** Check if a field should render as a carousel (string with values[]). */
export function isCarouselField(field: FieldSchema): boolean {
  return field.type === "string" && !!field.values && field.values.length > 0;
}

/** Check if a field should render as a toggle switch. */
export function isBooleanField(field: FieldSchema): boolean {
  return field.type === "boolean";
}

/**
 * Safely extract numeric max_length.
 * Guards against `max_length: true` (seed data bug in Kling).
 */
export function getMaxLength(field: FieldSchema): number | undefined {
  return typeof field.max_length === "number" ? field.max_length : undefined;
}
