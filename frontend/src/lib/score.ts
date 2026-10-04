import type { Classification } from "@/lib/api/types"

// Mirrors Score.classification in src/prospector/models.py.
export const CLASSIFICATIONS: { value: Classification; min: number; max: number }[] = [
  { value: "Gold Nugget", min: 85, max: 100 },
  { value: "High", min: 70, max: 84 },
  { value: "Good", min: 50, max: 69 },
  { value: "Moderate", min: 30, max: 49 },
  { value: "Low", min: 0, max: 29 },
]

export const GOLD_NUGGET_SCORE = 85

export const TIER_STYLES: Record<Classification, { badge: string; text: string; bar: string }> = {
  "Gold Nugget": {
    badge: "border-gold/40 bg-gold/12 text-gold shadow-[0_0_12px_-4px_var(--gold)]",
    text: "text-gold",
    bar: "bg-gold",
  },
  High: { badge: "border-positive/30 bg-positive/10 text-positive", text: "text-positive", bar: "bg-positive" },
  Good: { badge: "border-positive/20 bg-positive/5 text-positive/85", text: "text-positive/85", bar: "bg-positive/70" },
  Moderate: { badge: "border-border bg-muted text-foreground/80", text: "text-foreground/80", bar: "bg-foreground/50" },
  Low: { badge: "border-border bg-transparent text-muted-foreground", text: "text-muted-foreground", bar: "bg-muted-foreground/50" },
}
