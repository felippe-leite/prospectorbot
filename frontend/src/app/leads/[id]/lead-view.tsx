"use client"

import { useCallback } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { ArrowLeft, ExternalLink, AtSign, Globe, History, MapPin, MessageCircle } from "lucide-react"

import { EvidenceItem, EvidenceList } from "@/components/evidence-list"
import { LeadEnrichment } from "@/components/lead-enrichment"
import { NotesEditor, StatusSelect } from "@/components/lead-tracking"
import { OpportunityCard } from "@/components/opportunity-card"
import { ScoreBadge, ScoreMeter } from "@/components/score-badge"
import { ErrorState } from "@/components/states"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { WebsiteAnalysis } from "@/components/website-analysis"
import { ApiError } from "@/lib/api/client"
import { leadPath } from "@/lib/api/leads"
import type { LeadDetail, LeadTracking } from "@/lib/api/types"
import { formatCategory, formatDate, formatDateTime, formatHost } from "@/lib/format"
import { leadLinks, safeUrl } from "@/lib/links"
import { cn } from "@/lib/utils"

function Section({ title, description, children, className }: {
  title: string
  description?: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={cn("flex flex-col gap-4 rounded-xl border bg-card p-5 sm:p-6", className)}>
      <div className="flex flex-col gap-1">
        <h2 className="font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  )
}

function ExternalButton({ href, icon: Icon, children }: {
  href: string
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <Button asChild variant="outline" size="sm">
      <a href={href} target="_blank" rel="noopener noreferrer nofollow">
        <Icon /> {children} <ExternalLink className="text-muted-foreground" />
      </a>
    </Button>
  )
}

const ByYou = () => <span className="ml-1.5 rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">added by you</span>

const NotAvailable = ({ children = "Not available" }: { children?: React.ReactNode }) => (
  <span className="text-muted-foreground/70">{children}</span>
)

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 border-b py-2.5 last:border-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm break-words">{children}</dd>
    </div>
  )
}

function Overview({ lead }: { lead: LeadDetail }) {
  const { business, analysis, tracking } = lead
  const website = safeUrl(tracking.website ?? business.website)
  const phone = tracking.phone ?? business.phone
  const social = [...new Set([tracking.instagram, ...(analysis?.social_links ?? [])]
    .map(safeUrl).filter((url): url is string => url !== null))]
  return (
    <dl className="flex flex-col">
      <Field label="Category">{formatCategory(business.category) ?? <NotAvailable />}</Field>
      <Field label="Address">{business.address ?? <NotAvailable />}</Field>
      <Field label="Website">
        {website ? (
          <a href={website} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 hover:underline">
            {formatHost(website)} <ExternalLink className="size-3 text-muted-foreground" />
          </a>
        ) : tracking.no_website ? (
          <span>None — you confirmed it<ByYou /></span>
        ) : (
          <NotAvailable>Not detected (not listed by the source)</NotAvailable>
        )}
        {website && tracking.website && <ByYou />}
      </Field>
      <Field label="Phone">
        {phone ? <span className="font-mono">{phone}</span> : <NotAvailable />}
        {tracking.phone && <ByYou />}
      </Field>
      <Field label="Rating">{business.rating !== null ? `${business.rating.toFixed(1)} / 5` : <NotAvailable />}</Field>
      <Field label="Reviews">{business.review_count ?? <NotAvailable />}</Field>
      <Field label="Social links">
        {social.length > 0 ? (
          <span className="flex flex-col gap-1">
            {social.map((url) => (
              <a key={url} href={url} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 truncate hover:underline">
                {formatHost(url)}{new URL(url).pathname.replace(/\/$/, "")} <ExternalLink className="size-3 shrink-0 text-muted-foreground" />
                {url === safeUrl(tracking.instagram) && <ByYou />}
              </a>
            ))}
          </span>
        ) : (
          <NotAvailable>{analysis ? "None detected on the homepage" : "Not checked"}</NotAvailable>
        )}
      </Field>
      <Field label="Source">
        <span className="capitalize">{business.source}</span>
        <span className="text-muted-foreground"> · discovered {formatDate(business.discovered_at)}</span>
      </Field>
    </dl>
  )
}

function LeadSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label="Loading lead">
      <Skeleton className="h-36 rounded-xl" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-6">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    </div>
  )
}

export function LeadView({ id }: { id: string }) {
  const scanId = useSearchParams().get("scan")
  const router = useRouter()
  const { mutate: revalidate } = useSWRConfig()
  const { data: lead, error, mutate } = useSWR<LeadDetail>(leadPath(id, scanId))
  // After a manual update the newest analysis is the one to show.
  const onRescored = useCallback(() => {
    revalidate((key) => typeof key === "string" && key.startsWith("/api/"))
    if (scanId) router.replace(`/leads/${id}`)
  }, [revalidate, router, id, scanId])

  if (error) {
    if (error instanceof ApiError && error.status === 404) {
      return <ErrorState error={new Error("This lead was not found.")} />
    }
    return <ErrorState error={error} onRetry={() => mutate()} />
  }
  if (!lead) return <LeadSkeleton />

  const links = leadLinks(lead)
  const latest = lead.appearances[0]
  const isLatest = !latest || latest.scan_id === lead.scan.id
  const saveTracking = (tracking: LeadTracking) => mutate({ ...lead, tracking }, { revalidate: false })

  return (
    <>
      <Button asChild variant="ghost" size="sm" className="self-start text-muted-foreground">
        <Link href={scanId ? `/history/${scanId}` : "/leads"}><ArrowLeft /> {scanId ? "Session results" : "Leads"}</Link>
      </Button>

      {!isLatest && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border px-4 py-2.5 text-sm text-muted-foreground">
          <History className="size-4" />
          Showing the analysis from {formatDateTime(lead.scan.created_at)}.
          <Link href={`/leads/${id}`} className="text-foreground hover:underline">View the latest analysis</Link>
        </div>
      )}

      <header className={cn(
        "flex flex-col gap-6 rounded-xl border bg-card p-6 sm:flex-row sm:items-start sm:justify-between",
        lead.classification === "Gold Nugget" && "border-gold/25 bg-gradient-to-br from-gold/[0.06] via-card to-card",
      )}>
        <div className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{lead.business.name}</h1>
            <p className="text-sm text-muted-foreground">
              {[formatCategory(lead.business.category), lead.scan.location].filter(Boolean).join(" • ")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {links.website && <ExternalButton href={links.website} icon={Globe}>Website</ExternalButton>}
            <ExternalButton href={links.maps} icon={MapPin}>Google Maps</ExternalButton>
            {links.instagram && <ExternalButton href={links.instagram} icon={AtSign}>Instagram</ExternalButton>}
            {links.whatsapp && (
              <ExternalButton href={links.whatsapp.url} icon={MessageCircle}>
                WhatsApp{!links.whatsapp.confirmed && <span className="text-muted-foreground">(probable)</span>}
              </ExternalButton>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-muted-foreground">Status</span>
            <StatusSelect tracking={lead.tracking} onSaved={saveTracking} />
          </div>
        </div>
        <div className="w-full shrink-0 sm:w-56">
          <ScoreMeter score={lead.score} classification={lead.classification} />
        </div>
      </header>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Section title="Score Breakdown" description="Why this business received its score. Expand a line to see the evidence.">
            <EvidenceList contributions={lead.contributions} score={lead.score} scoringVersion={lead.scoring_version} />
          </Section>

          <section className="flex flex-col gap-4">
            <div className="flex items-baseline justify-between">
              <h2 className="font-semibold tracking-tight">Opportunities</h2>
              <span className="text-xs text-muted-foreground">{lead.opportunities.length} found</span>
            </div>
            {lead.opportunities.length > 0 ? (
              <div className="grid gap-4 xl:grid-cols-2">
                {lead.opportunities.map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} />)}
              </div>
            ) : (
              <p className="rounded-xl border border-dashed px-5 py-8 text-center text-sm text-muted-foreground">
                No relevant opportunities identified by the available rules.
              </p>
            )}
          </section>

          <Section title="Website Analysis">
            <WebsiteAnalysis analysis={lead.analysis} business={lead.business} tracking={lead.tracking} />
          </Section>
        </div>

        <aside className="flex flex-col gap-6">
          <Section
            title="Contact & Web Presence"
            description="Found it on Google Maps or Instagram? Add what you verified; the score is updated with it."
          >
            <LeadEnrichment
              key={lead.tracking.business_id}
              tracking={lead.tracking}
              onSaved={saveTracking}
              onRescored={onRescored}
            />
          </Section>

          <Section title="Overview">
            <Overview lead={lead} />
          </Section>

          <Section title="Personal Notes" description="Only for your own organization.">
            <NotesEditor key={lead.tracking.business_id} tracking={lead.tracking} onSaved={saveTracking} />
          </Section>

          {lead.business.evidence.length > 0 && (
            <Section title="Discovery Evidence">
              <ul className="flex flex-col gap-3">
                {lead.business.evidence.map((item, index) => <EvidenceItem key={index} evidence={item} />)}
              </ul>
            </Section>
          )}

          {lead.appearances.length > 1 && (
            <Section title="Scan History">
              <ul className="flex flex-col divide-y">
                {lead.appearances.map((item) => (
                  <li key={item.scan_id}>
                    <Link
                      href={`/leads/${id}?scan=${item.scan_id}`}
                      className={cn("flex items-center justify-between gap-3 py-2.5 text-sm hover:text-foreground", item.scan_id === lead.scan.id ? "text-foreground" : "text-muted-foreground")}
                    >
                      <span className="flex flex-col">
                        <span>{formatDate(item.created_at)}</span>
                        <span className="text-xs text-muted-foreground">{item.query} · {item.location}</span>
                      </span>
                      <ScoreBadge score={item.score} classification={item.classification} />
                    </Link>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </aside>
      </div>

      <p className="text-xs text-muted-foreground">
        The score prioritizes human review; it does not prove need or intent to hire. Validate the evidence before contacting the business.
        Data: Geoapify · © OpenStreetMap contributors.
      </p>
    </>
  )
}
