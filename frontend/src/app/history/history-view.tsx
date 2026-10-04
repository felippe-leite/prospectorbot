"use client"

import Link from "next/link"
import useSWR from "swr"
import { ChevronRight, Gem, History } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states"
import { isActive, scansPath } from "@/lib/api/scans"
import type { ScanSummary } from "@/lib/api/types"
import { formatDateTime } from "@/lib/format"
import { MANUAL_SCAN_LABEL } from "@/lib/labels"
import { cn } from "@/lib/utils"
import { ScanStatusBadge } from "./scan-status"

function ScanRow({ summary }: { summary: ScanSummary }) {
  const { scan, analyzed, gold_nuggets, progress } = summary
  return (
    <Link href={`/history/${scan.id}`} className="group flex items-center gap-6 px-5 py-4 transition-colors hover:bg-accent/40">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center gap-3">
          {scan.kind === "manual" && <span className="rounded bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">{MANUAL_SCAN_LABEL}</span>}
          <span className="truncate font-medium">{scan.query}</span>
          <ScanStatusBadge status={scan.status} />
        </div>
        <span className="truncate text-sm text-muted-foreground">{scan.location}</span>
        {scan.error && <span className="truncate text-xs text-negative/90">{scan.error}</span>}
      </div>
      <div className="hidden flex-col items-end gap-1 text-sm sm:flex">
        <span>
          <span className="font-mono tabular-nums">{isActive(summary) && progress?.total ? `${progress.analyzed} / ${progress.total}` : analyzed}</span>
          <span className="text-muted-foreground"> businesses analyzed</span>
        </span>
        <span className={cn("inline-flex items-center gap-1", gold_nuggets > 0 ? "text-gold" : "text-muted-foreground")}>
          <Gem className="size-3" />
          <span className="font-mono tabular-nums">{gold_nuggets}</span> Gold Nugget{gold_nuggets === 1 ? "" : "s"}
        </span>
      </div>
      <div className="hidden w-40 text-right text-xs text-muted-foreground md:block">{formatDateTime(scan.created_at)}</div>
      <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </Link>
  )
}

export function HistoryView() {
  const { data, error, mutate } = useSWR<ScanSummary[]>(scansPath, {
    refreshInterval: (scans) => (scans?.some(isActive) ? 2000 : 0),
  })
  return (
    <>
      <PageHeader title="History" description="Previous prospecting sessions. Open one to see its results." />
      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : !data ? (
        <TableSkeleton rows={4} />
      ) : data.length === 0 ? (
        <EmptyState icon={History} />
      ) : (
        <div className="divide-y overflow-hidden rounded-xl border bg-card">
          {data.map((summary) => <ScanRow key={summary.scan.id} summary={summary} />)}
        </div>
      )}
    </>
  )
}
