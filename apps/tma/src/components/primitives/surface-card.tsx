import * as React from "react"

import { cn } from "@/lib/utils"

function SurfaceCard({
  className,
  ...props
}: React.ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "grid gap-12 rounded-card border border-border bg-card p-16 shadow-sm-4",
        className,
      )}
      {...props}
    />
  )
}

export { SurfaceCard }
