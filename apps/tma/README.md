# Base UI

Репозиторий для общей дизайн-системы и UX-основы будущих проектов.

## Что значит "установить основные технологии"

На текущем этапе это значит подготовить фундамент, который можно воспроизвести в новом проекте без добавления UI-компонентов:

* Vite + React + TypeScript;
* Tailwind CSS v4 через `@tailwindcss/vite`;
* shadcn CLI и `components.json`;
* CSS variables и Tailwind theme tokens в `src/index.css`;
* `cn` utility в `src/lib/utils.ts`;
* `DESIGN.md` для темы и UX-правил;
* `AGENTS.md` и `docs/project-foundation.md` для правил проекта.

shadcn-компоненты сейчас не установлены. Это намеренно: `shadcn add ...` копирует конкретный компонент в репозиторий, поэтому такие компоненты нужно добавлять только явно.

## Команды

```bash
pnpm install
pnpm dev
pnpm build
pnpm check
```

## Версии

Версии закреплены в `package.json` без диапазонов:

* Tailwind CSS - 4.3.2
* shadcn - 4.12.0
* Radix UI - 1.6.1
* React - 19.2.7
* React DOM - 19.2.7
* Vite - 8.1.0
* Node.js - 24.18.0

## Как переносить основу в новый проект

Подробная инструкция: [docs/new-project-bootstrap.md](docs/new-project-bootstrap.md).

## Документация

* [DESIGN.md](DESIGN.md) - тема, цвета, типографика и UX-правила.
* [docs/project-foundation.md](docs/project-foundation.md) - техническая архитектура основы.
* [docs/new-project-bootstrap.md](docs/new-project-bootstrap.md) - bootstrap нового проекта.
