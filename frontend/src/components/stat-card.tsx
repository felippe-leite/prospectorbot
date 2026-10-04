import { cn } from "@/lib/utils"

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  highlight = false,
}: {
  label: string
  value: React.ReactNode
  hint?: React.ReactNode
  icon: React.ComponentType<{ className?: string }>
  highlight?: boolean
}) {
  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border bg-card p-5", highlight && "border-gold/25 bg-gradient-to-br from-gold/[0.07] to-card")}>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{label}</span>
        <Icon className={cn("size-4", highlight && "text-gold")} />
      </div>
      <div className={cn("font-mono text-3xl font-semibold tracking-tight tabular-nums", highlight && "text-gold")}>{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  )
}
