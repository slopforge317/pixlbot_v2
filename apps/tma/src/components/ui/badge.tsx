import * as React from "react"
import { Slot } from "radix-ui"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-md border border-transparent font-semibold whitespace-nowrap transition-colors focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2.5 py-0.5 text-sm",
        lg: "px-3 py-1 text-sm",
      },
      variant: {
        default: "border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
        destructive:
          "border-transparent bg-destructive text-white focus-visible:ring-destructive/20 dark:bg-destructive/60 dark:focus-visible:ring-destructive/40 [a&]:hover:bg-destructive/90",
        outline:
          "border-border text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        ghost:
          "border-transparent [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        link: "border-transparent text-primary underline-offset-4 [a&]:hover:underline",
        red: "border-transparent bg-red-500/10 text-red-500 [a&]:hover:bg-red-500/15",
        blue: "border-transparent bg-blue-500/10 text-blue-500 [a&]:hover:bg-blue-500/15",
        green:
          "border-transparent bg-green-500/10 text-green-500 [a&]:hover:bg-green-500/15",
        yellow:
          "border-transparent bg-yellow-500/10 text-yellow-500 [a&]:hover:bg-yellow-500/15",
        purple:
          "border-transparent bg-purple-500/10 text-purple-500 [a&]:hover:bg-purple-500/15",
        pink: "border-transparent bg-pink-500/10 text-pink-500 [a&]:hover:bg-pink-500/15",
        orange:
          "border-transparent bg-orange-500/10 text-orange-500 [a&]:hover:bg-orange-500/15",
        cyan: "border-transparent bg-cyan-500/10 text-cyan-500 [a&]:hover:bg-cyan-500/15",
        indigo:
          "border-transparent bg-indigo-500/10 text-indigo-500 [a&]:hover:bg-indigo-500/15",
        violet:
          "border-transparent bg-violet-500/10 text-violet-500 [a&]:hover:bg-violet-500/15",
        rose: "border-transparent bg-rose-500/10 text-rose-500 [a&]:hover:bg-rose-500/15",
        amber:
          "border-transparent bg-amber-500/10 text-amber-500 [a&]:hover:bg-amber-500/15",
        lime: "border-transparent bg-lime-500/10 text-lime-500 [a&]:hover:bg-lime-500/15",
        emerald:
          "border-transparent bg-emerald-500/10 text-emerald-500 [a&]:hover:bg-emerald-500/15",
        sky: "border-transparent bg-sky-500/10 text-sky-500 [a&]:hover:bg-sky-500/15",
        fuchsia:
          "border-transparent bg-fuchsia-500/10 text-fuchsia-500 [a&]:hover:bg-fuchsia-500/15",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "sm",
    },
  },
)

function Badge({
  className,
  variant = "default",
  size = "sm",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-size={size}
      data-variant={variant}
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
