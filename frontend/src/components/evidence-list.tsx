import { ExternalLink } from "lucide-react"

import type { Evidence, ScoreContribution } from "@/lib/api/types"
import { ruleLabel } from "@/lib/labels"
import { safeUrl } from "@/lib/links"
import { formatHost } from "@/lib/format"

const SOURCE_LABELS: Record<string, string> = {
  website_html: "Website HTML",
  website_http: "Website HTTP",
  geoapify: "Geoapify",
  pagespeed_insights: "PageSpeed Insights",
  manual: "You (verified manually)",
}

export function EvidenceItem({ evidence }: { evidence: Evidence }) {
  const url = safeUrl(evidence.source_url)
  return (
    <li className="flex flex-col gap-0.5">
      <span className="text-sm text-foreground/85">{evidence.description}</span>
      <span className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
        <span>Source: {SOURCE_LABELS[evidence.source] ?? evidence.source}</span>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 hover:text-foreground">
            {formatHost(url)} <ExternalLink className="size-3" />
          </a>
        )}
      </span>
    </li>
  )
}

/** Score breakdown: each line is a rule that fired, with the evidence behind it. */
export function EvidenceList({
  contributions,
  score,
  scoringVersion,
}: {
  contributions: ScoreContribution[]
  score: number
  scoringVersion: string
}) {
  const sum = contributions.reduce((total, item) => total + item.points, 0)
  if (contributions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No scoring criteria were confirmed by the rules. Unknown signals never add points.
      </p>
    )
  }
  return (
    <div className="flex flex-col">
      <ul className="flex flex-col divide-y divide-border">
        {contributions.map((item) => (
          <li key={item.rule_code}>
            <details className="group py-2.5">
              <summary className="flex cursor-pointer list-none items-center gap-4 [&::-webkit-details-marker]:hidden">
                <span className="w-10 text-right font-mono text-sm font-semibold text-positive tabular-nums">+{item.points}</span>
                <span className="flex-1 text-sm">{ruleLabel(item.rule_code)}</span>
                <span className="text-xs text-muted-foreground group-open:hidden">
                  {item.evidence.length} evidence
                </span>
                <span className="hidden text-xs text-muted-foreground group-open:inline">Hide</span>
              </summary>
              <ul className="mt-2 ml-14 flex flex-col gap-2 border-l pl-4">
                {item.evidence.map((evidence, index) => (
                  <EvidenceItem key={index} evidence={evidence} />
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
      <div className="mt-1 flex items-center gap-4 border-t border-foreground/15 pt-3">
        <span className="w-10" />
        <span className="flex-1 text-sm font-medium">Total</span>
        <span className="font-mono text-sm font-semibold tabular-nums">{score} / 100</span>
      </div>
      {sum > score && <p className="mt-2 text-xs text-muted-foreground">Points add up to {sum}; the score is capped at 100.</p>}
      <p className="mt-3 text-xs text-muted-foreground">Scoring version {scoringVersion}</p>
    </div>
  )
}
