import * as React from "react"
import { cn } from "cn"

/**
 * Single typography scale for the whole app. Every heading/body element
 * uses exactly one of these and nothing layered on top (no per-instance
 * font-bold/font-display) so the site shares one consistent hierarchy
 * instead of each section hand-picking its own text-* combination.
 */

type HeadingProps = React.HTMLAttributes<HTMLHeadingElement> & {
  as?: "h1" | "h2" | "h3" | "h4"
}

export function Display1({ as: Tag = "h1", className, ...props }: HeadingProps) {
  return (
    <Tag
      className={cn(
        "font-display font-semibold leading-[1.05] tracking-tight text-5xl md:text-6xl lg:text-7xl",
        className
      )}
      {...props}
    />
  )
}

export function Display2({ as: Tag = "h2", className, ...props }: HeadingProps) {
  return (
    <Tag
      className={cn(
        "font-display font-semibold leading-tight tracking-tight text-3xl md:text-4xl",
        className
      )}
      {...props}
    />
  )
}

export function Heading3({ as: Tag = "h3", className, ...props }: HeadingProps) {
  return (
    <Tag className={cn("font-display font-semibold leading-snug text-xl", className)} {...props} />
  )
}

export function BodyLg({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("font-body leading-relaxed text-lg md:text-xl", className)} {...props} />
}

export function Body({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("font-body leading-relaxed text-base", className)} {...props} />
}

export function Caption({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("font-body leading-snug text-sm text-muted-foreground", className)} {...props} />
}
