"use client"

import { useEffect, useState } from "react"
import { ChevronDown, Search, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Classification, LeadQuery, LeadStatus, OpportunityTag } from "@/lib/api/types"
import { STATUS_LABELS, TAG_LABELS } from "@/lib/labels"
import { CLASSIFICATIONS } from "@/lib/score"
import { cn } from "@/lib/utils"

export interface FilterState {
  q: string
  minScore: string
  classification: Classification[]
  website: "any" | "has" | "none"
  tag: OpportunityTag[]
  status: LeadStatus[]
}

const pick = <T extends string>(values: string[], allowed: readonly T[]) =>
  values.filter((value): value is T => (allowed as readonly string[]).includes(value))

const CLASSIFICATION_VALUES = CLASSIFICATIONS.map((item) => item.value)
const TAG_VALUES = Object.keys(TAG_LABELS) as OpportunityTag[]
const STATUS_VALUES = Object.keys(STATUS_LABELS) as LeadStatus[]

export function filtersFromParams(params: URLSearchParams): FilterState {
  const website = params.get("website")
  return {
    q: params.get("q") ?? "",
    minScore: params.get("min_score") ?? "",
    classification: pick(params.getAll("classification"), CLASSIFICATION_VALUES),
    website: website === "has" || website === "none" ? website : "any",
    tag: pick(params.getAll("tag"), TAG_VALUES),
    status: pick(params.getAll("status"), STATUS_VALUES),
  }
}

export function filtersToParams(filters: FilterState): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.q.trim()) params.set("q", filters.q.trim())
  if (filters.minScore !== "") params.set("min_score", filters.minScore)
  filters.classification.forEach((value) => params.append("classification", value))
  if (filters.website !== "any") params.set("website", filters.website)
  filters.tag.forEach((value) => params.append("tag", value))
  filters.status.forEach((value) => params.append("status", value))
  return params
}

export function toLeadQuery(filters: FilterState): LeadQuery {
  const minScore = Number.parseInt(filters.minScore, 10)
  return {
    q: filters.q.trim() || undefined,
    min_score: Number.isFinite(minScore) ? Math.min(100, Math.max(0, minScore)) : undefined,
    classification: filters.classification,
    website: filters.website === "any" ? undefined : filters.website,
    tag: filters.tag,
    status: filters.status,
  }
}

export const activeFilterCount = (filters: FilterState) =>
  [filters.q.trim(), filters.minScore, filters.website !== "any" ? "1" : ""].filter(Boolean).length +
  filters.classification.length + filters.tag.length + filters.status.length

type Text = Pick<FilterState, "q" | "minScore">
const same = (a: Text, b: Text) => a.q === b.q && a.minScore === b.minScore

function FilterMenu<T extends string>({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  selected: T[]
  onChange: (values: T[]) => void
}) {
  const toggle = (value: T) =>
    onChange(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value])
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className={cn("h-9", selected.length > 0 && "border-gold/40 text-foreground")}>
          {label}
          {selected.length > 0 && (
            <span className="rounded bg-gold/15 px-1.5 font-mono text-[11px] text-gold">{selected.length}</span>
          )}
          <ChevronDown className="text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-56 p-1.5">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
          >
            <Checkbox checked={selected.includes(option.value)} onCheckedChange={() => toggle(option.value)} />
            {option.label}
          </label>
        ))}
        {selected.length > 0 && (
          <Button variant="ghost" size="sm" className="mt-1 w-full justify-start text-muted-foreground" onClick={() => onChange([])}>
            Clear selection
          </Button>
        )}
      </PopoverContent>
    </Popover>
  )
}

export function LeadFilters({
  value,
  onChange,
  showStatus = true,
}: {
  value: FilterState
  onChange: (value: FilterState) => void
  showStatus?: boolean
}) {
  // Text inputs are debounced so typing doesn't fire one request per key.
  const [draft, setDraft] = useState<Text>({ q: value.q, minScore: value.minScore })
  const [seen, setSeen] = useState<Text>(draft)
  const [sent, setSent] = useState<Text | null>(null)
  if (!same(seen, value)) {
    // Adopt external changes (e.g. "Clear filters") but not the echo of our own debounced update,
    // which may arrive while the user is still typing.
    setSeen({ q: value.q, minScore: value.minScore })
    if (!sent || !same(sent, value)) setDraft({ q: value.q, minScore: value.minScore })
  }

  useEffect(() => {
    if (same(draft, value)) return
    const timer = setTimeout(() => {
      setSent(draft)
      onChange({ ...value, ...draft })
    }, 300)
    return () => clearTimeout(timer)
  }, [draft, value, onChange])

  const set = <K extends keyof FilterState>(key: K, next: FilterState[K]) => onChange({ ...value, [key]: next })
  const count = activeFilterCount(value)

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative w-full sm:w-64">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={draft.q}
          onChange={(event) => setDraft((current) => ({ ...current, q: event.target.value }))}
          placeholder="Search business name"
          aria-label="Search business name"
          className="h-9 pl-8"
        />
      </div>
      <div className="flex h-9 items-center gap-2 rounded-lg border border-input px-2.5 dark:bg-input/30">
        <label htmlFor="min-score" className="text-sm whitespace-nowrap text-muted-foreground">Min score</label>
        <input
          id="min-score"
          type="number"
          min={0}
          max={100}
          inputMode="numeric"
          value={draft.minScore}
          onChange={(event) => setDraft((current) => ({ ...current, minScore: event.target.value }))}
          placeholder="0"
          className="w-10 bg-transparent font-mono text-sm tabular-nums outline-none placeholder:text-muted-foreground/50"
        />
      </div>
      <FilterMenu
        label="Classification"
        options={CLASSIFICATIONS.map((item) => ({ value: item.value, label: `${item.value} (${item.min}–${item.max})` }))}
        selected={value.classification}
        onChange={(next) => set("classification", next)}
      />
      <Select value={value.website} onValueChange={(next) => set("website", next as FilterState["website"])}>
        <SelectTrigger className="h-9! w-auto min-w-36" aria-label="Website">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Any website</SelectItem>
          <SelectItem value="has">Has website</SelectItem>
          <SelectItem value="none">Website not detected</SelectItem>
        </SelectContent>
      </Select>
      <FilterMenu
        label="Opportunity"
        options={TAG_VALUES.map((tag) => ({ value: tag, label: TAG_LABELS[tag] }))}
        selected={value.tag}
        onChange={(next) => set("tag", next)}
      />
      {showStatus && (
        <FilterMenu
          label="Status"
          options={STATUS_VALUES.map((status) => ({ value: status, label: STATUS_LABELS[status] }))}
          selected={value.status}
          onChange={(next) => set("status", next)}
        />
      )}
      {count > 0 && (
        <Button
          variant="ghost"
          className="h-9 text-muted-foreground"
          onClick={() => onChange({ q: "", minScore: "", classification: [], website: "any", tag: [], status: [] })}
        >
          <X /> Clear filters
        </Button>
      )}
    </div>
  )
}
