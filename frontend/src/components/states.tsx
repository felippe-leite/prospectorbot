import Link from "next/link"
import { Pickaxe, RotateCw, Unplug } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api/client"
import { cn } from "@/lib/utils"

export function EmptyState({
  title = "No prospects yet.",
  description = "Start your first prospecting session to discover potential opportunities.",
  action = { href: "/prospect", label: "Start Prospecting" },
  icon: Icon = Pickaxe,
  className,
}: {
  title?: string
  description?: React.ReactNode
  action?: { href: string; label: string } | null
  icon?: React.ComponentType<{ className?: string }>
  className?: string
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-14 text-center", className)}>
      <span className="flex size-10 items-center justify-center rounded-full border border-gold/25 bg-gold/5 text-gold/80">
        <Icon className="size-4.5" />
      </span>
      <div className="flex max-w-sm flex-col gap-1">
        <p className="font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {action && (
        <Button asChild className="mt-2">
          <Link href={action.href}>{action.label}</Link>
        </Button>
      )}
    </div>
  )
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const offline = error instanceof ApiError && error.offline
  const message = offline || !(error instanceof Error) ? "Unable to connect to ProspectorBot API." : error.message
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 rounded-xl border border-negative/20 bg-negative/[0.03] px-6 py-12 text-center", className)}>
      <span className="flex size-10 items-center justify-center rounded-full bg-negative/10 text-negative">
        <Unplug className="size-4.5" />
      </span>
      <div className="flex max-w-md flex-col gap-1">
        <p className="font-medium">{message}</p>
        {offline && (
          <p className="text-sm text-muted-foreground">
            Make sure the backend is running: <code className="font-mono text-xs">prospector serve</code>
          </p>
        )}
      </div>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-2">
          <RotateCw /> Retry
        </Button>
      )}
    </div>
  )
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border p-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-9 w-full" />
      ))}
    </div>
  )
}

export function CardsSkeleton({ count = 4, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 xl:grid-cols-4", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} className="h-28 rounded-xl" />
      ))}
    </div>
  )
}
