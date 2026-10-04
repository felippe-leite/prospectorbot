"use client"

import { useCallback, useMemo } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import useSWR from "swr"
import { SearchX } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { activeFilterCount, filtersFromParams, filtersToParams, LeadFilters, toLeadQuery, type FilterState } from "@/components/lead-filters"
import { LeadTable } from "@/components/lead-table"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states"
import { leadsPath } from "@/lib/api/leads"
import type { LeadSummary } from "@/lib/api/types"

/** Filters live in the URL so a filtered view can be bookmarked or shared. */
export function useUrlFilters() {
  const params = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const filters = useMemo(() => filtersFromParams(new URLSearchParams(params.toString())), [params])
  const setFilters = useCallback(
    (next: FilterState) => {
      const search = filtersToParams(next).toString()
      router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false })
    },
    [router, pathname],
  )
  return [filters, setFilters] as const
}

export function FilteredLeads({ scanId, empty }: { scanId?: string; empty?: React.ReactNode }) {
  const [filters, setFilters] = useUrlFilters()
  const { data, error, mutate, isLoading } = useSWR<LeadSummary[]>(leadsPath({ ...toLeadQuery(filters), scan_id: scanId }))
  const filtered = activeFilterCount(filters) > 0

  return (
    <div className="flex flex-col gap-4">
      <LeadFilters value={filters} onChange={setFilters} />
      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : !data ? (
        <TableSkeleton />
      ) : data.length === 0 ? (
        filtered ? (
          <EmptyState icon={SearchX} title="No leads match these filters." description="Try lowering the minimum score or removing a filter." action={null} />
        ) : (
          (empty ?? <EmptyState />)
        )
      ) : (
        <>
          <p className="text-xs text-muted-foreground" aria-live="polite">
            {isLoading ? "Updating…" : `${data.length} lead${data.length === 1 ? "" : "s"}`} · sorted by Prospector Score
          </p>
          <LeadTable leads={data} scanId={scanId} />
        </>
      )}
    </div>
  )
}

export function LeadsView() {
  return (
    <>
      <PageHeader title="Leads" description="Every business found, with its most recent analysis. Click a lead to see the full evidence." />
      <FilteredLeads />
    </>
  )
}
