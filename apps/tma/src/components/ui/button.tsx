import * as React from "react"
import { Slot } from "radix-ui"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-button font-medium transition focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1 disabled:pointer-events-none disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        action:
          "bg-action-blue [color:var(--primary-foreground)] shadow-subtle hover:opacity-90",
        outline: "border border-border bg-background text-foreground hover:bg-muted",
        ghost: "text-foreground hover:bg-muted",
        link: "h-auto rounded-none p-0 text-action-blue underline-offset-4 hover:underline",
      },
      size: {
        sm: "min-h-32 px-12 py-6 text-caption",
        md: "min-h-40 px-16 text-body font-semibold",
        lg: "min-h-48 px-20 text-body font-semibold",
        icon: "h-32 w-32 rounded-button-rect p-0",
        "icon-xs": "h-24 w-24 rounded-button-rect p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button, buttonVariants }
