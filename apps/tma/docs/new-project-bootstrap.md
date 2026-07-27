# Bootstrap нового проекта

Эта инструкция описывает минимальную основу для нового проекта на базе `base-ui`.

## 1. Создать Vite React TypeScript project

```bash
pnpm create vite@8.1.0 my-app --template react-ts
cd my-app
```

## 2. Зафиксировать package manager и Node.js

Добавить:

```text
.node-version
.nvmrc
```

Содержимое обоих файлов:

```text
24.18.0
```

В `package.json` добавить:

```json
{
  "packageManager": "pnpm@11.7.0",
  "engines": {
    "node": ">=24.18.0 <25",
    "pnpm": ">=11 <12"
  }
}
```

## 3. Установить базовые зависимости

```bash
pnpm add react@19.2.7 react-dom@19.2.7 clsx@2.1.1 tailwind-merge@3.6.0 radix-ui@1.6.1
pnpm add -D vite@8.1.0 @vitejs/plugin-react@6.0.3 typescript@6.0.3 tailwindcss@4.3.2 @tailwindcss/vite@4.3.2 shadcn@4.12.0 @types/react@19.2.17 @types/react-dom@19.2.3
```

## 4. Подключить Tailwind CSS v4

В `vite.config.ts` должны быть `react()` и `tailwindcss()`:

```ts
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
})
```

В `src/index.css` перенести токены из `base-ui`.

## 5. Настроить shadcn без компонентов

Скопировать `components.json` из `base-ui`.

Важно: не выполнять `pnpm shadcn add ...` на этапе минимальной базы.

Правила Tailwind/shadcn описаны в `docs/project-foundation.md`.

## 6. Добавить `cn`

Скопировать `src/lib/utils.ts`:

```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

## 7. Скопировать правила проекта

Скопировать:

* `DESIGN.md`;
* `AGENTS.md`;
* `docs/project-foundation.md`;
* `.npmrc`;
* `.node-version`;
* `.nvmrc`.

## 8. Проверить

```bash
pnpm install
pnpm check
pnpm build
```
