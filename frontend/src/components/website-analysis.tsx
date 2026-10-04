import { Check, CircleHelp, ExternalLink, Minus } from "lucide-react"

import type { AnalysisStatus, Business, CheckStatus, LeadTracking, WebsiteAnalysis as Analysis } from "@/lib/api/types"
import { formatDateTime, formatDuration, formatHost } from "@/lib/format"
import { safeUrl } from "@/lib/links"
import { cn } from "@/lib/utils"

const STATUS_STYLE: Record<AnalysisStatus, string> = {
  completed: "text-positive",
  partial: "text-gold",
  failed: "text-negative",
}

/**
 * `problem` marks checks whose absence is a real gap (shown in red, quietly);
 * for the rest, absence is neutral information.
 */
function CheckValue({
  status,
  present = "Detected",
  absent = "Not detected",
  problem = false,
  detail,
}: {
  status: CheckStatus
  present?: string
  absent?: string
  problem?: boolean
  detail?: string | null
}) {
  if (status === "unknown") {
    return (
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        <CircleHelp className="size-3.5" /> Unknown
      </span>
    )
  }
  const ok = status === "present"
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      {ok ? <Check className="size-3.5 shrink-0 text-positive" /> : <Minus className={cn("size-3.5 shrink-0", problem ? "text-negative" : "text-muted-foreground")} />}
      <span className={cn(!ok && problem && "text-negative")}>{ok ? present : absent}</span>
      {detail && <span className="truncate text-muted-foreground" title={detail}>· {detail}</span>}
    </span>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-6 border-b py-2.5 text-sm last:border-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 text-right">{children}</span>
    </div>
  )
}

export function WebsiteAnalysis({ analysis, business, tracking }: {
  analysis: Analysis | null
  business: Business
  tracking: LeadTracking
}) {
  if (!analysis) {
    return (
      <p className="text-sm text-muted-foreground">
        {tracking.website
          ? "You added a website that has not been analyzed yet. Use “Update score” to analyze it."
          : business.website
            ? "This website was not analyzed in this scan."
            : tracking.no_website
              ? "You confirmed this business has no website, so there is nothing to analyze."
              : "No website was listed by the source, so no website analysis was performed. If you find one, add it under Contact & Web Presence."}
      </p>
    )
  }

  const finalUrl = safeUrl(analysis.final_url ?? analysis.requested_url)
  const broken = analysis.link_checks.filter((link) => link.status_code === 404 || link.status_code === 410)
  const httpOk = analysis.status_code !== null && analysis.status_code >= 200 && analysis.status_code < 300
  const slow = analysis.response_time_ms !== null && analysis.response_time_ms > 3000
  const performanceReport = safeUrl(analysis.evidence.find((item) => item.code === "mobile_performance")?.source_url)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>
          Status: <span className={cn("font-medium capitalize", STATUS_STYLE[analysis.status])}>{analysis.status}</span>
        </span>
        <span>Analyzed {formatDateTime(analysis.analyzed_at)}</span>
        {finalUrl && (
          <a href={finalUrl} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 hover:text-foreground">
            {formatHost(finalUrl)} <ExternalLink className="size-3" />
          </a>
        )}
      </div>

      <div className="grid gap-x-10 lg:grid-cols-2">
        <div>
          <Row label="HTTP status">
            {analysis.status_code !== null ? (
              <span className={cn("font-mono tabular-nums", !httpOk && "text-negative")}>{analysis.status_code}</span>
            ) : (
              <span className="text-muted-foreground">No response</span>
            )}
          </Row>
          <Row label="HTTPS"><CheckValue status={analysis.https} present="Yes" absent="No" problem /></Row>
          <Row label="Mobile viewport"><CheckValue status={analysis.mobile_viewport} present="Yes" absent="Missing" problem /></Row>
          <Row label="Performance">
            {analysis.mobile_performance_score !== null ? (
              <span className="inline-flex items-center gap-1.5">
                <span className={cn("font-mono tabular-nums", analysis.mobile_performance_score < 50 && "text-negative")}>
                  {Math.round(analysis.mobile_performance_score)}/100
                </span>
                {performanceReport && (
                  <a href={performanceReport} target="_blank" rel="noopener noreferrer nofollow" className="text-muted-foreground hover:text-foreground" title="Open the PageSpeed Insights report">
                    <ExternalLink className="size-3" />
                  </a>
                )}
              </span>
            ) : (
              <span className="text-muted-foreground">Not measured</span>
            )}
          </Row>
          <Row label="Response time">
            {analysis.response_time_ms !== null ? (
              <span className={cn("font-mono tabular-nums", slow && "text-negative")}>{formatDuration(analysis.response_time_ms)}</span>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </Row>
          <Row label="Title"><CheckValue status={analysis.title_status} absent="Missing" problem detail={analysis.title} /></Row>
          <Row label="Meta description">
            <CheckValue status={analysis.meta_description_status} absent="Missing" problem detail={analysis.meta_description} />
          </Row>
        </div>
        <div>
          <Row label="Call to action"><CheckValue status={analysis.cta} problem /></Row>
          <Row label="WhatsApp CTA"><CheckValue status={analysis.whatsapp} /></Row>
          <Row label="Contact form"><CheckValue status={analysis.contact_form} /></Row>
          <Row label="Booking"><CheckValue status={analysis.booking} /></Row>
          <Row label="Phone"><CheckValue status={analysis.phone} /></Row>
          <Row label="Social links">
            <CheckValue status={analysis.social_presence} detail={analysis.social_links.length ? `${analysis.social_links.length} found` : null} />
          </Row>
          <Row label="Internal links">
            {analysis.link_checks.length === 0 ? (
              <span className="text-muted-foreground">Not checked</span>
            ) : (
              <span className={cn(broken.length > 0 && "text-negative")}>
                {broken.length > 0 ? `${broken.length} broken` : "OK"}
                <span className="text-muted-foreground"> · {analysis.link_checks.length} sampled</span>
              </span>
            )}
          </Row>
        </div>
      </div>

      {analysis.redirect_chain.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Redirects: {analysis.redirect_chain.map(formatHost).join(" → ")} → {finalUrl ? formatHost(finalUrl) : "?"}
        </p>
      )}

      {analysis.errors.length > 0 && (
        <div className="rounded-lg bg-muted/60 px-4 py-3">
          <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">Inconclusive checks</p>
          <ul className="flex flex-col gap-1 text-sm text-foreground/80">
            {analysis.errors.map((error, index) => <li key={index}>{error}</li>)}
          </ul>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Checks cover the homepage HTML only. JavaScript-rendered content and other pages are not evaluated, and visual quality is never judged.
      </p>
    </div>
  )
}
