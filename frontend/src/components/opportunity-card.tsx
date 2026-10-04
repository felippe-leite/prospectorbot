import type { Opportunity } from "@/lib/api/types"
import { OPPORTUNITY_TITLES } from "@/lib/labels"
import { cn } from "@/lib/utils"

// Potential follows the rule's scoring weight; unweighted rules are informational.
function potential(points: number) {
  if (points >= 15) return { label: "High", className: "border-gold/40 bg-gold/10 text-gold" }
  if (points >= 10) return { label: "Medium", className: "border-positive/25 bg-positive/10 text-positive" }
  if (points > 0) return { label: "Low", className: "border-border text-muted-foreground" }
  return { label: "Info", className: "border-border text-muted-foreground", hint: "Does not affect the score" }
}

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const level = potential(opportunity.points)
  return (
    <article className={cn("flex flex-col gap-4 rounded-xl border bg-card p-5", level.label === "High" && "border-gold/20")}>
      <header className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="font-medium">{OPPORTUNITY_TITLES[opportunity.rule_code] ?? opportunity.title}</h3>
          <p className="text-xs text-muted-foreground">{opportunity.title}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-[10px] tracking-wide text-muted-foreground uppercase">Potential</span>
          <span className={cn("rounded-md border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase", level.className)} title={level.hint}>
            {level.label}
          </span>
        </div>
      </header>

      <p className="text-sm text-foreground/80">{opportunity.description}</p>

      <section className="flex flex-col gap-1.5">
        <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Evidence</h4>
        <ul className="flex flex-col gap-1 text-sm text-foreground/85">
          {opportunity.evidence.map((item, index) => (
            <li key={index} className="flex gap-2">
              <span className="mt-2 size-1 shrink-0 rounded-full bg-muted-foreground" />
              <span>{item.description}</span>
            </li>
          ))}
        </ul>
      </section>

      {opportunity.suggested_services.length > 0 && (
        <section className="mt-auto flex flex-col gap-1.5 border-t pt-3">
          <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Possible solution</h4>
          <div className="flex flex-wrap gap-1.5">
            {opportunity.suggested_services.map((service) => (
              <span key={service} className="rounded-md bg-secondary px-2 py-1 text-xs">{service}</span>
            ))}
          </div>
        </section>
      )}
    </article>
  )
}
