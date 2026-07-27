# Назначение

Этот файл предназначен только для описания визуальной системы: темы, цветов, типографики, радиусов, теней, плотности интерфейса, UX-паттернов и правил композиции.

# Тема

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Ink | `#101010` | `--color-ink` | Primary CTAs, primary text, active states. Used as the strongest dark tone, providing maximum contrast and visual weight for key actions. |
| Action Blue | `#0099ff` | `--color-action-blue` | Tertiary links, informational banner text. A rare, functional splash of color reserved for secondary calls to action and informational highlights. |
| White | `#ffffff` | `--color-white` | Card backgrounds, text on dark buttons. |
| Paper | `#f4f4f4` | `--color-paper` | Main page background. |
| Graphite | `#242424` | `--color-graphite` | Headlines, primary body text. |
| Slate | `#6b7280` | `--color-slate` | Secondary text, descriptive copy, disabled states. |
| Stone | `#898989` | `--color-stone` | Placeholder text, decorative UI elements. |
| Silver | `#e5e7eb` | `--color-silver` | Borders, dividers, subtle backgrounds. |

## Tokens — Typography

### Onest — Primary heading font · `--font-heading`
- **Weights:** 600, 700
- **Sizes:** 20px, 24px, 48px, 64px
- **Line height:** 1.10 - 1.30
- **Letter spacing:** 0 for stable Cyrillic rendering.
- **Role:** Основной шрифт заголовков и display-типографики. Onest дает современный геометричный характер, но поддерживает кириллицу и остается читаемым в русскоязычных интерфейсах.

### Onest — Primary body and UI font · `--font-sans`
- **Weights:** 400, 500
- **Sizes:** 14px, 16px, 18px
- **Line height:** 1.40 - 1.50
- **Letter spacing:** 0 for body text; avoid tight negative tracking in Cyrillic paragraphs.
- **Role:** Основной шрифт интерфейса и текстовых блоков: абзацы, описания, формы, навигация и повторяемые UI-паттерны.

### Inter — Technical labels and dense UI font · `--font-technical`
- **Weights:** 400, 500
- **Sizes:** 10px, 12px, 14px, 16px
- **Line height:** 1.14 - 1.43
- **Letter spacing:** 0 for labels and data-heavy UI.
- **Role:** Технические подписи, metadata, captions, числовые значения, статусы и плотные интерфейсные элементы, где важна максимальная нейтральность и предсказуемость.

### Type Scale

| Role | Size | Line Height | Letter Spacing | Token |
|------|------|-------------|----------------|-------|
| caption | 12px | 1.4 | 0 | `--text-caption` |
| body-sm | 14px | 1.5 | 0 | `--text-body-sm` |
| body | 16px | 1.5 | 0 | `--text-body` |
| subheading | 18px | 1.4 | 0 | `--text-subheading` |
| heading-sm | 20px | 1.3 | 0 | `--text-heading-sm` |
| heading | 24px | 1.3 | 0 | `--text-heading` |
| heading-lg | 48px | 1.1 | 0 | `--text-heading-lg` |
| display | 64px | 1.1 | 0 | `--text-display` |

## Tokens — Spacing & Shapes

**Density:** compact

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 4 | 4px | `--spacing-4` |
| 5 | 5px | `--spacing-5` |
| 6 | 6px | `--spacing-6` |
| 8 | 8px | `--spacing-8` |
| 10 | 10px | `--spacing-10` |
| 12 | 12px | `--spacing-12` |
| 16 | 16px | `--spacing-16` |
| 20 | 20px | `--spacing-20` |
| 24 | 24px | `--spacing-24` |
| 28 | 28px | `--spacing-28` |
| 32 | 32px | `--spacing-32` |
| 40 | 40px | `--spacing-40` |
| 48 | 48px | `--spacing-48` |
| 80 | 80px | `--spacing-80` |

### Border Radius

| Element | Value |
|---------|-------|
| tags | 9999px |
| cards | 12px |
| inputs | 8px |
| buttons | 9999px (pills), 8px (rectangular) |

### Shadows

| Name | Value | Token |
|------|-------|-------|
| sm | `rgba(36, 36, 36, 0.7) 0px 1px 5px -4px, rgba(36, 36, 36, ...` | `--shadow-sm` |
| subtle | `rgba(255, 255, 255, 0.15) 0px 2px 0px 0px inset` | `--shadow-subtle` |
| sm-2 | `rgba(19, 19, 22, 0.7) 0px 1px 5px -4px, rgba(34, 42, 53, ...` | `--shadow-sm-2` |
| sm-3 | `rgba(19, 19, 22, 0.7) 0px 1px 5px -4px, rgba(34, 42, 53, ...` | `--shadow-sm-3` |
| sm-4 | `rgba(34, 42, 53, 0.05) 0px 4px 8px 0px` | `--shadow-sm-4` |
| subtle-2 | `rgb(255, 255, 255) 0px 2px 0px 0px inset` | `--shadow-subtle-2` |
| subtle-3 | `rgba(0, 0, 0, 0.1) 0px 1px 3px 0px, rgba(0, 0, 0, 0.06) 0...` | `--shadow-subtle-3` |

### Layout

- **Page max-width:** 1200px
- **Telegram Mini App max-width:** 430px
- **Section gap:** 96px
- **Card padding:** 24px

## Радиусы

Базовый радиус задается через `--radius`. Производные радиусы `sm`, `md`, `lg`, `xl` рассчитываются от него в Tailwind theme.

## UX-правила

* Интерфейсы должны быть спокойными, предсказуемыми и пригодными для повторного использования.
* Компоненты должны опираться на семантические токены, а не на случайные одноразовые цвета.
* Новые визуальные решения сначала описываются здесь, затем отражаются в токенах и компонентах.
