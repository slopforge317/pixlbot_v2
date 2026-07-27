import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "min-h-128 resize-none rounded-input border border-input bg-background px-12 py-10 text-body-sm text-foreground outline-none transition [font-size:var(--text-body-sm)] [line-height:var(--text-body-sm--line-height)] placeholder:text-stone focus:border-ink focus:bg-card disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20",
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
