"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, Pickaxe } from "lucide-react"
import { useSWRConfig } from "swr"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api/client"
import { scansPath, startScan } from "@/lib/api/scans"

// All of these are aliases accepted by the backend (src/prospector/discovery/geoapify.py).
const SUGGESTIONS = ["Barbershops", "Beauty salons", "Restaurants", "Cafes", "Dentists", "Gyms", "Bakeries", "Pet shops", "Hotels"]

export function ProspectingForm({ disabled = false }: { disabled?: boolean }) {
  const router = useRouter()
  const { mutate } = useSWRConfig()
  const [query, setQuery] = useState("Barbershops")
  const [location, setLocation] = useState("")
  const [limit, setLimit] = useState("30")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const summary = await startScan({ query: query.trim(), location: location.trim(), limit: Number(limit) })
      await mutate(scansPath)
      router.push(`/history/${summary.scan.id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Unable to start prospecting.")
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Label htmlFor="query">Business type</Label>
        <Input id="query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Barbershops" required maxLength={120} className="h-10" />
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setQuery(suggestion)}
              className="rounded-md border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-gold/40 hover:text-foreground data-[active=true]:border-gold/50 data-[active=true]:text-gold"
              data-active={query === suggestion}
            >
              {suggestion}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Pick a suggestion, or enter a Geoapify category such as <code className="font-mono">catering.fast_food</code>.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="location">Location</Label>
        <Input id="location" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Campinas, SP" required maxLength={120} className="h-10" />
        <p className="text-xs text-muted-foreground">City and state work best.</p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="limit">Maximum results</Label>
        <Input id="limit" type="number" min={1} max={50} value={limit} onChange={(event) => setLimit(event.target.value)} required className="h-10 w-32 font-mono" />
        <p className="text-xs text-muted-foreground">Between 1 and 50. Websites are visited politely, one request per second at most.</p>
      </div>

      {error && <p className="rounded-lg border border-negative/25 bg-negative/5 px-3 py-2 text-sm text-negative" role="alert">{error}</p>}

      <Button type="submit" size="lg" className="h-10 self-start px-4" disabled={disabled || submitting}>
        {submitting ? <Loader2 className="animate-spin" /> : <Pickaxe />}
        Start Prospecting
      </Button>
    </form>
  )
}
