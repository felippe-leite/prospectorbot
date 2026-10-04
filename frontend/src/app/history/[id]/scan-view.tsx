"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import useSWR, { useSWRConfig } from "swr"
import { ArrowLeft, CircleAlert, Gem } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/page-header"
import { ProspectingProgress } from "@/components/prospecting-progress"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api/client"
import { isActive, scanPath } from "@/lib/api/scans"
import type { ScanSummary } from "@/lib/api/types"
import { formatDateTime } from "@/lib/format"
import { MANUAL_SCAN_LABEL } from "@/lib/labels"
import { FilteredLeads } from "../../leads/leads-view"
import { ScanStatusBadge } from "../scan-status"

export function ScanView({ id }: { id: string }) {
  const { mutate: revalidate } = useSWRConfig()
  const { data, error, mutate } = useSWR<ScanSummary>(scanPath(id), {
    refreshInterval: (summary) => (summary && isActive(summary) ? 1000 : 0),
  })
  const active = data ? isActive(data) : false
  const analyzed = data?.progress?.analyzed ?? data?.analyzed

  // Refresh results as businesses are saved, and once more when the scan ends.
  const wasActive = useRef(false)
  useEffect(() => {
    if (!data) return
    if (wasActive.current && !active) {
      if (data.scan.status === "completed") toast.success(`Prospecting finished: ${data.analyzed} businesses analyzed`)
      else if (data.scan.status === "failed") toast.error("Prospecting stopped before finishing")
    }
    wasActive.current = active
    revalidate((key) => typeof key === "string" && key.startsWith("/api/leads"))
  }, [active, analyzed, data, revalidate])

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState error={new Error("This prospecting session was not found.")} />
    }
    return <ErrorState error={error} onRetry={() => mutate()} />
  }
  if (!data) return <TableSkeleton />

  const { scan } = data
  return (
    <>
      <div className="flex flex-col gap-4">
        <Button asChild variant="ghost" size="sm" className="self-start text-muted-foreground">
          <Link href="/history"><ArrowLeft /> History</Link>
        </Button>
        <PageHeader
          eyebrow={scan.kind === "manual" ? MANUAL_SCAN_LABEL : undefined}
          title={scan.query}
          description={
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>{scan.location}</span>
              <span>·</span>
              <span>{formatDateTime(scan.created_at)}</span>
              <span>·</span>
              <span>up to {scan.limit} results</span>
              <span>·</span>
              <ScanStatusBadge status={scan.status} />
            </span>
          }
          actions={
            !active && (
              <div className="flex items-center gap-6 text-sm">
                <span><span className="font-mono tabular-nums">{data.analyzed}</span> <span className="text-muted-foreground">analyzed</span></span>
                <span className={data.gold_nuggets > 0 ? "text-gold" : "text-muted-foreground"}>
                  <Gem className="mr-1 inline size-3.5" />
                  <span className="font-mono tabular-nums">{data.gold_nuggets}</span> Gold Nuggets
                </span>
              </div>
            )
          }
        />
      </div>

      {active && <ProspectingProgress summary={data} />}

      {scan.status === "failed" && scan.error && (
        <div className="flex gap-3 rounded-xl border border-negative/25 bg-negative/[0.04] p-4 text-sm">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-negative" />
          <div className="flex flex-col gap-1">
            <span className="font-medium">Prospecting stopped</span>
            <span className="text-muted-foreground">{scan.error}</span>
          </div>
        </div>
      )}

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold tracking-tight">Results</h2>
        <FilteredLeads
          scanId={scan.id}
          empty={
            <EmptyState
              title={active ? "No results yet." : "No businesses were analyzed in this session."}
              description={active ? "Analyzed businesses appear here as soon as they are scored." : "The source returned no businesses for this search, or the session stopped early."}
              action={active ? null : { href: "/prospect", label: "New prospect" }}
            />
          }
        />
      </section>
    </>
  )
}
