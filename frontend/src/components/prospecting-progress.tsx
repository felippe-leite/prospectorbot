import { Check, Circle, Loader2, Minus } from "lucide-react"

import { Progress } from "@/components/ui/progress"
import type { ScanStage, ScanSummary } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type StepState = "done" | "current" | "pending" | "skipped"

const ORDER: ScanStage[] = ["discovery", "website_analysis", "opportunity_analysis", "scoring"]

function Step({ state, children }: { state: StepState; children: React.ReactNode }) {
  return (
    <li className={cn("flex items-center gap-2.5 text-sm", state === "pending" && "text-muted-foreground", state === "skipped" && "text-muted-foreground/70")}>
      {state === "done" && <Check className="size-4 text-positive" />}
      {state === "current" && <Loader2 className="size-4 animate-spin text-gold" />}
      {state === "pending" && <Circle className="size-4 text-muted-foreground/50" />}
      {state === "skipped" && <Minus className="size-4" />}
      <span className={cn(state === "current" && "font-medium")}>{children}</span>
    </li>
  )
}

/** Reflects the live state reported by the API for the scan running in its process. */
export function ProspectingProgress({ summary }: { summary: ScanSummary }) {
  const { scan, progress } = summary

  if (!progress) {
    return (
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-6">
        <div className="flex items-center gap-2 font-medium">
          <Loader2 className="size-4 animate-spin text-gold" /> Prospecting
        </div>
        <p className="text-sm text-muted-foreground">
          This scan is marked as running, but it is not executing in this API process (it may have been started from the CLI).
          Results appear below as they are saved.
        </p>
      </div>
    )
  }

  const discovering = progress.stage === "discovery"
  const total = progress.total ?? 0
  const percent = total ? Math.round((progress.analyzed / total) * 100) : 0
  const at = ORDER.indexOf(progress.stage)
  const state = (stage: ScanStage): StepState => {
    const index = ORDER.indexOf(stage)
    return index < at ? "done" : index === at ? "current" : "pending"
  }

  return (
    <div className="flex flex-col gap-6 rounded-xl border border-gold/20 bg-gradient-to-b from-gold/[0.05] to-card p-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 font-medium">
          <Loader2 className="size-4 animate-spin text-gold" /> Prospecting
        </div>
        <p className="text-sm text-muted-foreground">
          {discovering
            ? `Searching for ${scan.query.toLowerCase()} in ${scan.location}…`
            : total === 0
              ? "No businesses found."
              : <><span className="font-mono text-foreground tabular-nums">{progress.analyzed} / {total}</span> businesses analyzed</>}
        </p>
      </div>

      {discovering ? (
        <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="absolute inset-y-0 w-1/3 animate-[prospect-scan_1.6s_ease-in-out_infinite] rounded-full bg-gold/70" />
        </div>
      ) : (
        <Progress value={percent} className="h-1.5" aria-label={`${percent}% analyzed`} />
      )}

      {discovering ? (
        <ul className="flex flex-col gap-2">
          <Step state="current">Discovering businesses</Step>
        </ul>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="text-sm">
            <span className="text-muted-foreground">Currently analyzing: </span>
            <span className="font-medium">{progress.current_business}</span>
          </div>
          <ul className="flex flex-col gap-2">
            <Step state="done">Business discovered</Step>
            {progress.has_website ? (
              <>
                <Step state="done">Website detected</Step>
                <Step state={state("website_analysis")}>Website analysis</Step>
              </>
            ) : (
              <Step state="skipped">No website listed · website analysis skipped</Step>
            )}
            <Step state={state("opportunity_analysis")}>Opportunity analysis</Step>
            <Step state={state("scoring")}>Score calculation</Step>
          </ul>
        </div>
      )}
    </div>
  )
}
