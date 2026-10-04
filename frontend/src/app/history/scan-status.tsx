import { CircleAlert, CircleCheck, Loader2 } from "lucide-react"

import type { ScanStatus } from "@/lib/api/types"
import { SCAN_STATUS_LABELS } from "@/lib/labels"
import { cn } from "@/lib/utils"

export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  const Icon = status === "completed" ? CircleCheck : status === "failed" ? CircleAlert : Loader2
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs",
        status === "completed" && "text-muted-foreground",
        status === "failed" && "text-negative",
        (status === "running" || status === "pending") && "text-gold",
      )}
    >
      <Icon className={cn("size-3.5", (status === "running" || status === "pending") && "animate-spin")} />
      {SCAN_STATUS_LABELS[status]}
    </span>
  )
}
