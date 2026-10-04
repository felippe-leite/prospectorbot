"use client"

import Link from "next/link"
import useSWR from "swr"
import { Gem, Globe, Sparkles } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { ClassificationLabel, StatusBadge } from "@/components/score-badge"
import { CardsSkeleton, EmptyState, ErrorState } from "@/components/states"
import { leadsPath } from "@/lib/api/leads"
import type { LeadSummary } from "@/lib/api/types"
import { formatCategory } from "@/lib/format"
import { TAG_LABELS } from "@/lib/labels"
import { GOLD_NUGGET_SCORE, TIER_STYLES } from "@/lib/score"
import { cn } from "@/lib/utils"

function NuggetCard({ lead, rank }: { lead: LeadSummary; rank: number }) {
  const gold = lead.classification === "Gold Nugget"
  return (
    <Link
      href={`/leads/${lead.business_id}`}
      className={cn(
        "group flex flex-col gap-4 rounded-xl border bg-card p-5 transition-colors hover:border-foreground/20",
        gold && "border-gold/25 bg-gradient-to-br from-gold/[0.06] to-card hover:border-gold/45",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-3">
          <span className="font-mono text-sm text-muted-foreground tabular-nums">#{rank}</span>
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="truncate font-medium group-hover:underline">{lead.name}</h3>
            <p className="truncate text-xs text-muted-foreground">
              {[formatCategory(lead.category), lead.location].filter(Boolean).join(" · ")}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={cn("font-mono text-2xl font-semibold tabular-nums", TIER_STYLES[lead.classification].text)}>{lead.score}</span>
          <ClassificationLabel classification={lead.classification} className="text-[10px]" />
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {lead.tags.map((tag) => (
          <span key={tag} className="rounded-md bg-secondary px-2 py-0.5 text-xs">{TAG_LABELS[tag]}</span>
        ))}
      </div>
      <div className="mt-auto flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1"><Sparkles className="size-3" />{lead.opportunity_count} opportunities</span>
          <span className="inline-flex items-center gap-1"><Globe className="size-3" />{lead.website ? "Website" : "No website listed"}</span>
        </span>
        <StatusBadge status={lead.status} />
      </div>
    </Link>
  )
}

export function GoldNuggetsView() {
  const nuggets = useSWR<LeadSummary[]>(leadsPath({ min_score: GOLD_NUGGET_SCORE }))
  const next = useSWR<LeadSummary[]>(nuggets.data?.length === 0 ? leadsPath({ min_score: 50, limit: 6 }) : null)

  return (
    <>
      <PageHeader
        title={<span className="inline-flex items-center gap-2"><Gem className="size-5 text-gold" /> Gold Nuggets</span>}
        description="The highest-potential prospects (score 85+), best first. Start your analysis here."
      />
      {nuggets.error ? (
        <ErrorState error={nuggets.error} onRetry={() => nuggets.mutate()} />
      ) : !nuggets.data ? (
        <CardsSkeleton count={6} className="xl:grid-cols-3" />
      ) : nuggets.data.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {nuggets.data.map((lead, index) => <NuggetCard key={lead.business_id} lead={lead} rank={index + 1} />)}
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          <EmptyState
            icon={Gem}
            title="No Gold Nuggets yet."
            description="No prospect has reached a score of 85. Keep prospecting, or review the best candidates found so far."
          />
          {next.data && next.data.length > 0 && (
            <section className="flex flex-col gap-4">
              <h2 className="text-lg font-semibold tracking-tight">Closest finds</h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {next.data.map((lead, index) => <NuggetCard key={lead.business_id} lead={lead} rank={index + 1} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  )
}
