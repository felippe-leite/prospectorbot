"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowDown, ArrowUp, ExternalLink } from "lucide-react"

import { ClassificationLabel, ScoreBadge, StatusBadge } from "@/components/score-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { LeadSummary } from "@/lib/api/types"
import { formatCategory, formatDate, formatHost } from "@/lib/format"
import { TAG_LABELS } from "@/lib/labels"
import { safeUrl } from "@/lib/links"
import { cn } from "@/lib/utils"

export type LeadColumn =
  | "score" | "business" | "category" | "location" | "rating" | "reviews"
  | "website" | "opportunities" | "status" | "classification" | "analyzed"

export const FULL_COLUMNS: LeadColumn[] = [
  "score", "business", "category", "location", "rating", "reviews", "website", "opportunities", "status",
]
export const RECENT_COLUMNS: LeadColumn[] = [
  "business", "category", "location", "score", "classification", "website", "analyzed",
]

type SortKey = "score" | "business" | "rating" | "reviews" | "opportunities" | "analyzed"

const SORTERS: Record<SortKey, (lead: LeadSummary) => number | string> = {
  score: (lead) => lead.score,
  business: (lead) => lead.name.toLocaleLowerCase(),
  rating: (lead) => lead.rating ?? -1,
  reviews: (lead) => lead.review_count ?? -1,
  opportunities: (lead) => lead.opportunity_count,
  analyzed: (lead) => lead.analyzed_at,
}

const HEADERS: Record<LeadColumn, { label: string; sort?: SortKey; className?: string }> = {
  score: { label: "Score", sort: "score", className: "w-20" },
  business: { label: "Business", sort: "business" },
  category: { label: "Category" },
  location: { label: "Location" },
  rating: { label: "Rating", sort: "rating", className: "text-right" },
  reviews: { label: "Reviews", sort: "reviews", className: "text-right" },
  website: { label: "Website" },
  opportunities: { label: "Opportunities", sort: "opportunities" },
  status: { label: "Status" },
  classification: { label: "Classification" },
  analyzed: { label: "Analysis date", sort: "analyzed" },
}

const Missing = () => <span className="text-muted-foreground/50">—</span>

function Cell({ column, lead }: { column: LeadColumn; lead: LeadSummary }) {
  switch (column) {
    case "score":
      return <ScoreBadge score={lead.score} classification={lead.classification} />
    case "business":
      return <span className="font-medium">{lead.name}</span>
    case "category":
      return formatCategory(lead.category) ?? <Missing />
    case "location":
      return lead.location
    case "rating":
      return lead.rating !== null ? lead.rating.toFixed(1) : <Missing />
    case "reviews":
      return lead.review_count ?? <Missing />
    case "website": {
      const url = safeUrl(lead.website)
      return url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          onClick={(event) => event.stopPropagation()}
          className="inline-flex max-w-44 items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          <span className="truncate">{formatHost(url)}</span>
          <ExternalLink className="size-3 shrink-0" />
        </a>
      ) : (
        <span className="text-xs text-muted-foreground/70">Not detected</span>
      )
    }
    case "opportunities":
      return (
        <span className="flex items-center gap-1.5">
          <span className="w-4 font-mono tabular-nums">{lead.opportunity_count}</span>
          {lead.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="rounded border px-1.5 py-0.5 text-[11px] text-muted-foreground">{TAG_LABELS[tag]}</span>
          ))}
          {lead.tags.length > 2 && <span className="text-[11px] text-muted-foreground">+{lead.tags.length - 2}</span>}
        </span>
      )
    case "status":
      return <StatusBadge status={lead.status} />
    case "classification":
      return <ClassificationLabel classification={lead.classification} />
    case "analyzed":
      return <span className="text-muted-foreground">{formatDate(lead.analyzed_at)}</span>
  }
}

/** Rows arrive sorted by the API; clicking a sortable header re-sorts locally. */
export function LeadTable({
  leads,
  columns = FULL_COLUMNS,
  scanId,
}: {
  leads: LeadSummary[]
  columns?: LeadColumn[]
  /** Open leads in the context of this scan instead of their latest analysis. */
  scanId?: string
}) {
  const router = useRouter()
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean } | null>(null)

  const rows = useMemo(() => {
    if (!sort) return leads
    const value = SORTERS[sort.key]
    return [...leads].sort((a, b) => {
      const [x, y] = [value(a), value(b)]
      const order = x < y ? -1 : x > y ? 1 : 0
      return sort.desc ? -order : order
    })
  }, [leads, sort])

  const toggle = (key: SortKey) =>
    setSort((current) => (current?.key === key ? { key, desc: !current.desc } : { key, desc: key !== "business" }))

  const hrefFor = (lead: LeadSummary) =>
    `/leads/${lead.business_id}${scanId ? `?scan=${encodeURIComponent(scanId)}` : ""}`

  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((column) => {
              const header = HEADERS[column]
              const active = sort && header.sort === sort.key
              return (
                <TableHead key={column} className={cn("h-10 text-xs text-muted-foreground", header.className)}>
                  {header.sort ? (
                    <button
                      type="button"
                      onClick={() => toggle(header.sort!)}
                      className={cn("inline-flex items-center gap-1 hover:text-foreground", active && "text-foreground")}
                    >
                      {header.label}
                      {active && (sort.desc ? <ArrowDown className="size-3" /> : <ArrowUp className="size-3" />)}
                    </button>
                  ) : (
                    header.label
                  )}
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((lead) => (
            <TableRow
              key={`${lead.scan_id}-${lead.business_id}`}
              onClick={() => router.push(hrefFor(lead))}
              className={cn("cursor-pointer", lead.classification === "Gold Nugget" && "bg-gold/[0.03]")}
            >
              {columns.map((column) => (
                <TableCell key={column} className={cn("py-3", HEADERS[column].className)}>
                  {column === "business" ? (
                    <Link href={hrefFor(lead)} onClick={(event) => event.stopPropagation()} className="hover:underline">
                      <Cell column={column} lead={lead} />
                    </Link>
                  ) : (
                    <Cell column={column} lead={lead} />
                  )}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
