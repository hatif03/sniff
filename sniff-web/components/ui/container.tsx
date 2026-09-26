import * as React from "react"
import { cn } from "cn"

/**
 * Single container width for every page/section. Previously every
 * page/section hand-wrote its own max-w-{3xl,5xl,6xl,7xl} ad hoc - this is
 * the one shared wrapper everything should use instead.
 */
export function Container({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mx-auto max-w-6xl px-6 md:px-8", className)} {...props} />
}

/** Narrower variant for single-column forms/reading (e.g. new-run). */
export function ContainerNarrow({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mx-auto max-w-3xl px-6", className)} {...props} />
}
