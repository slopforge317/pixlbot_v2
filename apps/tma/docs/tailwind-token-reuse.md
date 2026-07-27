# Tailwind Token Reuse

Этот документ описывает, как переиспользовать текущую Tailwind-основу `base-ui` в другом проекте и какие классы уже реализованы через токены.

`DESIGN.md` остается источником продуктового описания темы и UX-правил. `src/index.css` остается техническим источником правды для CSS variables и Tailwind `@theme inline`.

## Что переносить в новый проект

Минимальный перенос:

1. Скопировать `src/index.css`.
2. Скопировать `components.json`, если проект использует shadcn.
3. Скопировать `src/lib/utils.ts`, чтобы использовать `cn`.
4. Скопировать `DESIGN.md`, чтобы сохранить описание визуальной системы.
5. Проверить зависимости: `tailwindcss`, `@tailwindcss/vite`, `react`, `react-dom`, `clsx`, `tailwind-merge`.

В новом проекте главный CSS-файл должен импортироваться из entrypoint, например в `src/main.tsx`:

```ts
import "./index.css"
```

Новые shadcn-компоненты не входят в минимальный перенос. Их нужно добавлять отдельно и только после явного решения.

## Как устроены токены

Tailwind v4 генерирует utility-классы из переменных внутри `@theme inline` в `src/index.css`.

Пример:

```css
@theme inline {
  --spacing: 1px;
  --spacing-24: 24px;
  --radius-card: 12px;
  --shadow-sm-4: rgba(34, 42, 53, 0.05) 0px 4px 8px 0px;
}
```

После этого можно использовать:

```tsx
<article className="rounded-card border border-border bg-card p-24 shadow-sm-4" />
```

Для проектных шаблонов лучше использовать семантические классы (`p-card`, `gap-section`, `max-w-page`), а для локальной компоновки - числовую spacing-шкалу (`gap-12`, `px-24`, `py-40`).

## Цвета

Базовые цветовые классы:

| Class | Token | Role |
|------|-------|------|
| `bg-ink`, `text-ink`, `border-ink` | `--color-ink` | Основной CTA, активные состояния, самый сильный темный тон. |
| `bg-action-blue`, `text-action-blue`, `border-action-blue` | `--color-action-blue` | Ссылки, информационные акценты, редкие вторичные действия. |
| `bg-white`, `text-white`, `border-white` | `--color-white` | Фон карточек, текст на темных поверхностях. |
| `bg-paper`, `text-paper`, `border-paper` | `--color-paper` | Основной фон страницы. |
| `bg-graphite`, `text-graphite`, `border-graphite` | `--color-graphite` | Заголовки и основной текст. |
| `bg-slate`, `text-slate`, `border-slate` | `--color-slate` | Вторичный текст, описания, disabled-состояния. |
| `bg-stone`, `text-stone`, `border-stone` | `--color-stone` | Placeholder и декоративные элементы. |
| `bg-silver`, `text-silver`, `border-silver` | `--color-silver` | Границы, разделители, тихие поверхности. |

Семантические shadcn-compatible классы:

| Class | Token |
|------|-------|
| `bg-background`, `text-foreground` | `--background`, `--foreground` |
| `bg-card`, `text-card-foreground` | `--card`, `--card-foreground` |
| `bg-popover`, `text-popover-foreground` | `--popover`, `--popover-foreground` |
| `bg-primary`, `text-primary-foreground` | `--primary`, `--primary-foreground` |
| `bg-secondary`, `text-secondary-foreground` | `--secondary`, `--secondary-foreground` |
| `bg-muted`, `text-muted-foreground` | `--muted`, `--muted-foreground` |
| `bg-accent`, `text-accent-foreground` | `--accent`, `--accent-foreground` |
| `border-border`, `border-input`, `outline-ring` | `--border`, `--input`, `--ring` |

Предпочтение для компонентов: использовать семантические классы (`bg-card`, `text-muted-foreground`, `border-border`) вместо прямых цветов, если роль элемента типовая.

## Типографика

Доступные font-классы:

| Class | Token | Role |
|------|-------|------|
| `font-sans` | `--font-sans` | Основной UI-текст, Onest. |
| `font-heading` | `--font-heading` | Заголовки, Onest. |
| `font-technical` | `--font-technical` | Метаданные, подписи, плотный UI, Inter. |
| `font-onest` | `--font-onest` | Прямой доступ к Onest. |
| `font-inter` | `--font-inter` | Прямой доступ к Inter. |

Доступные text-классы:

| Class | Size | Line Height |
|------|------|-------------|
| `text-caption` | 12px | 1.4 |
| `text-body-sm` | 14px | 1.5 |
| `text-body` | 16px | 1.5 |
| `text-subheading` | 18px | 1.4 |
| `text-heading-sm` | 20px | 1.3 |
| `text-heading` | 24px | 1.3 |
| `text-heading-lg` | 48px | 1.1 |
| `text-display` | 64px | 1.1 |

Пример:

```tsx
<h1 className="text-heading-lg font-bold sm:text-display">
  Базовая страница для оценки дизайн-системы
</h1>
<p className="text-body text-muted-foreground">
  Описание интерфейсного блока.
</p>
<span className="font-technical text-caption font-medium uppercase">
  STATUS: ACTIVE
</span>
```

## Spacing

В `base-ui` задана компактная плотность. Базовая переменная `--spacing: 1px` делает числовые Tailwind spacing-классы прямым отображением в пиксели.

| Classes | Value |
|---------|-------|
| `p-4`, `m-4`, `gap-4`, `w-4`, `h-4` | 4px |
| `p-5`, `m-5`, `gap-5`, `w-5`, `h-5` | 5px |
| `p-6`, `m-6`, `gap-6`, `w-6`, `h-6` | 6px |
| `p-8`, `m-8`, `gap-8`, `w-8`, `h-8` | 8px |
| `p-10`, `m-10`, `gap-10`, `w-10`, `h-10` | 10px |
| `p-12`, `m-12`, `gap-12`, `w-12`, `h-12` | 12px |
| `p-16`, `m-16`, `gap-16`, `w-16`, `h-16` | 16px |
| `p-20`, `m-20`, `gap-20`, `w-20`, `h-20` | 20px |
| `p-24`, `m-24`, `gap-24`, `w-24`, `h-24` | 24px |
| `p-28`, `m-28`, `gap-28`, `w-28`, `h-28` | 28px |
| `p-32`, `m-32`, `gap-32`, `w-32`, `h-32` | 32px |
| `p-40`, `m-40`, `gap-40`, `w-40`, `h-40` | 40px |
| `p-48`, `m-48`, `gap-48`, `w-48`, `h-48` | 48px |
| `p-80`, `m-80`, `gap-80`, `w-80`, `h-80` | 80px |

Семантические spacing-классы:

| Class | Value | Use |
|------|-------|-----|
| `p-card` | 24px | Внутренний отступ карточек и повторяемых surface-блоков. |
| `gap-section` | 96px | Вертикальная дистанция между крупными секциями страницы. |

Пример страницы:

```tsx
<main className="min-h-svh bg-background text-foreground">
  <div className="mx-auto flex w-full max-w-page flex-col gap-section px-24 py-40 sm:px-32 sm:py-48 lg:px-40">
    <section className="grid gap-24">
      <article className="rounded-card border border-border bg-card p-card shadow-sm-4" />
    </section>
  </div>
</main>
```

## Layout

| Class | Token | Value |
|------|-------|-------|
| `max-w-page` | `--container-page` | 1200px |
| `max-w-mini-app` | `--container-mini-app` | 430px |

Использование:

```tsx
<div className="mx-auto w-full max-w-page px-24 sm:px-32 lg:px-40">
  ...
</div>
```

Для Telegram Mini App и других мобильных shell-шаблонов используйте отдельный container:

```tsx
<div className="mx-auto min-h-svh w-full max-w-mini-app px-16 py-16">
  ...
</div>
```

## Radii

| Class | Token | Value | Use |
|------|-------|-------|-----|
| `rounded-sm` | `--radius-sm` | 4px | Малые внутренние элементы. |
| `rounded-md` | `--radius-md` | 8px | Базовые прямоугольные controls. |
| `rounded-lg` | `--radius-lg` | 12px | Базовый shadcn-compatible радиус. |
| `rounded-xl` | `--radius-xl` | 16px | Увеличенные поверхности. |
| `rounded-tag` | `--radius-tag` | 9999px | Tags, badges, pills. |
| `rounded-card` | `--radius-card` | 12px | Cards. |
| `rounded-input` | `--radius-input` | 8px | Inputs, preview tiles. |
| `rounded-button` | `--radius-button` | 9999px | Pill buttons. |
| `rounded-button-rect` | `--radius-button-rect` | 8px | Rectangular buttons. |

Пример:

```tsx
<span className="rounded-tag border border-border px-12 py-6 text-caption">
  Token
</span>
<button className="rounded-button bg-primary px-20 py-10 text-primary-foreground">
  Action
</button>
```

## Badge

`Badge` добавлен как целевой shadcn-компонент для компактных статусов, тегов и metadata labels. Цветные статусы оформлены как встроенные варианты самого компонента:

```tsx
import { Badge } from "@/components/ui/badge"

<Badge variant="red">Red</Badge>
<Badge variant="blue">Blue</Badge>
<Badge variant="green">Green</Badge>
<Badge variant="yellow">Yellow</Badge>
<Badge variant="purple">Purple</Badge>
<Badge variant="pink">Pink</Badge>
<Badge variant="orange">Orange</Badge>
<Badge variant="cyan">Cyan</Badge>
<Badge variant="indigo">Indigo</Badge>
<Badge variant="violet">Violet</Badge>
<Badge variant="rose">Rose</Badge>
<Badge variant="amber">Amber</Badge>
<Badge variant="lime">Lime</Badge>
<Badge variant="emerald">Emerald</Badge>
<Badge variant="sky">Sky</Badge>
<Badge variant="fuchsia">Fuchsia</Badge>
```

Доступные цветные варианты: `red`, `blue`, `green`, `yellow`, `purple`, `pink`, `orange`, `cyan`, `indigo`, `violet`, `rose`, `amber`, `lime`, `emerald`, `sky`, `fuchsia`. Они используют Tailwind-классы внутри `src/components/ui/badge.tsx`, без отдельных CSS variables. Доступные размеры: `sm`, `md`, `lg`; дефолтный размер - `sm`.

## Shadows

| Class | Token | Use |
|------|-------|-----|
| `shadow-sm` | `--shadow-sm` | Легкая тень для небольших поверхностей. |
| `shadow-subtle` | `--shadow-subtle` | Внутренний светлый highlight. |
| `shadow-sm-2` | `--shadow-sm-2` | Альтернативная легкая тень с более холодной базой. |
| `shadow-sm-3` | `--shadow-sm-3` | Чуть более протяженная легкая тень. |
| `shadow-sm-4` | `--shadow-sm-4` | Самая спокойная surface-тень для карточек. |
| `shadow-subtle-2` | `--shadow-subtle-2` | Более явный внутренний белый highlight. |
| `shadow-subtle-3` | `--shadow-subtle-3` | Стандартная тихая двухслойная тень. |

Для обычных карточек сейчас используется `shadow-sm-4`:

```tsx
<article className="rounded-card border border-border bg-card p-card shadow-sm-4">
  ...
</article>
```

## Рекомендуемые паттерны

Карточка:

```tsx
<article className="grid gap-16 rounded-card border border-border bg-card p-card shadow-sm-4">
  <h3 className="text-body font-semibold">Название</h3>
  <p className="text-body-sm text-muted-foreground">Описание</p>
</article>
```

Секция:

```tsx
<section className="grid gap-24">
  <div className="grid gap-8">
    <p className="font-technical text-caption font-medium uppercase text-muted-foreground">
      Section label
    </p>
    <h2 className="text-heading font-semibold">Заголовок секции</h2>
  </div>
</section>
```

Плотная metadata-строка:

```tsx
<p className="font-technical text-caption font-medium uppercase text-muted-foreground">
  Base UI · Visual Foundation
</p>
```

## Правила использования

1. Сначала добавлять новый визуальный токен в `DESIGN.md`, затем реализовывать его в `src/index.css`.
2. Не копировать случайные Tailwind-наборы между проектами без токенов, от которых они зависят.
3. Для повторяемых блоков предпочитать `bg-card`, `border-border`, `p-card`, `rounded-card`, `shadow-sm-4`.
4. Для цвета текста по умолчанию использовать `text-foreground`, для вторичного текста - `text-muted-foreground`.
5. Для крупных страниц использовать `max-w-page` и `gap-section`.
6. Если класс собирается динамически, держать полный class name в исходном коде или в явной map-константе, чтобы Tailwind мог его увидеть.
