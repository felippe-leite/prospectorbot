"use client"

import Link from "next/link"
import useSWR from "swr"
import { ArrowRight, Gauge, Gem, Loader2, Radar, Sparkles, Store } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { LeadTable, RECENT_COLUMNS } from "@/components/lead-table"
import { StatCard } from "@/components/stat-card"
import { CardsSkeleton, EmptyState, ErrorState, TableSkeleton } from "@/components/states"
import { Button } from "@/components/ui/button"
import { leadsPath } from "@/lib/api/leads"
import { isActive, scansPath } from "@/lib/api/scans"
import { statsPath } from "@/lib/api/system"
import type { LeadSummary, ScanSummary, Stats } from "@/lib/api/types"

function RunningScanBanner() {
  const { data } = useSWR<ScanSummary[]>(scansPath, { refreshInterval: (scans) => (scans?.some(isActive) ? 2000 : 0) })
  const running = data?.find(isActive)
  if (!running) return null
  const { scan, progress } = running
  return (
    <Link
      href={`/history/${scan.id}`}
      className="flex items-center gap-3 rounded-xl border border-gold/25 bg-gold/[0.05] px-4 py-3 text-sm transition-colors hover:bg-gold/[0.08]"
    >
      <Loader2 className="size-4 animate-spin text-gold" />
      <span className="flex-1">
        Prospecting <span className="font-medium">{scan.query}</span> in <span className="font-medium">{scan.location}</span>
        {progress?.total ? <span className="text-muted-foreground"> · {progress.analyzed} / {progress.total} analyzed</span> : null}
      </span>
      <span className="inline-flex items-center gap-1 text-muted-foreground">View <ArrowRight className="size-3.5" /></span>
    </Link>
  )
}

export function DashboardView() {
  const stats = useSWR<Stats>(statsPath, { refreshInterval: 10_000 })
  const recent = useSWR<LeadSummary[]>(leadsPath({ sort: "recent", limit: 10 }), { refreshInterval: 10_000 })
  const error = stats.error ?? recent.error

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Everything ProspectorBot has unearthed so far."
        actions={
          <Button asChild>
            <Link href="/prospect"><Radar /> New prospect</Link>
          </Button>
        }
      />

      <RunningScanBanner />

      {error ? (
        <ErrorState error={error} onRetry={() => { stats.mutate(); recent.mutate() }} />
      ) : (
        <>
          {stats.data ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Businesses Scanned" value={stats.data.businesses} icon={Store}
                hint={`Across ${stats.data.scans} prospecting session${stats.data.scans === 1 ? "" : "s"}`} />
              <StatCard label="Opportunities" value={stats.data.opportunities} icon={Sparkles} hint="Evidence-backed improvement points" />
              <StatCard label="Gold Nuggets" value={stats.data.gold_nuggets} icon={Gem} highlight={stats.data.gold_nuggets > 0} hint="Score of 85 or higher" />
              <StatCard label="Average Score" value={stats.data.average_score ?? "—"} icon={Gauge} hint="Prospector Score, 0–100" />
            </div>
          ) : (
            <CardsSkeleton />
          )}

          <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight">Recent Prospects</h2>
              {recent.data && recent.data.length > 0 && (
                <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
                  <Link href="/leads">All leads <ArrowRight /></Link>
                </Button>
              )}
            </div>
            {!recent.data ? (
              <TableSkeleton rows={5} />
            ) : recent.data.length === 0 ? (
              <EmptyState />
            ) : (
              <LeadTable leads={recent.data} columns={RECENT_COLUMNS} />
            )}
          </section>
        </>
      )}
    </>
  )
}
