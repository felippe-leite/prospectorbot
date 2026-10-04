import { Gem } from "lucide-react"

import type { Classification, LeadStatus } from "@/lib/api/types"
import { STATUS_LABELS, STATUS_STYLES } from "@/lib/labels"
import { TIER_STYLES } from "@/lib/score"
import { cn } from "@/lib/utils"

/** Prospector Score (0–100), optionally followed by its classification. */
export function ScoreBadge({
  score,
  classification,
  showLabel = false,
  className,
}: {
  score: number
  classification: Classification
  showLabel?: boolean
  className?: string
}) {
  const tier = TIER_STYLES[classification]
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "inline-flex h-6 min-w-9 items-center justify-center rounded-md border px-1.5 font-mono text-xs font-semibold tabular-nums",
          tier.badge,
        )}
        title={`Prospector Score ${score}/100 · ${classification}`}
      >
        {score}
      </span>
      {showLabel && <ClassificationLabel classification={classification} />}
    </span>
  )
}

export function ClassificationLabel({ classification, className }: { classification: Classification; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium tracking-wide uppercase", TIER_STYLES[classification].text, className)}>
      {classification === "Gold Nugget" && <Gem className="size-3" />}
      {classification}
    </span>
  )
}

export function ScoreMeter({ score, classification }: { score: number; classification: Classification }) {
  const tier = TIER_STYLES[classification]
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Prospector Score</div>
      <div className="flex items-baseline gap-1.5 font-mono tabular-nums">
        <span className={cn("text-4xl font-semibold tracking-tight", tier.text)}>{score}</span>
        <span className="text-sm text-muted-foreground">/ 100</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", tier.bar)} style={{ width: `${score}%` }} />
      </div>
      <ClassificationLabel classification={classification} />
    </div>
  )
}

export function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs", STATUS_STYLES[status])}>
      <span className="size-1.5 rounded-full bg-current opacity-80" />
      {STATUS_LABELS[status]}
    </span>
  )
}
