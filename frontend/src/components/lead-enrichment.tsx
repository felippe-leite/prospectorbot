"use client"

import { useEffect, useRef, useState } from "react"
import useSWR from "swr"
import { Loader2, RefreshCw } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { rescoreLead, updateTracking } from "@/lib/api/leads"
import { isActive, scanPath } from "@/lib/api/scans"
import type { LeadTracking, ScanSummary } from "@/lib/api/types"

interface Form {
  website: string
  noWebsite: boolean
  phone: string
  whatsapp: string
  instagram: string
}

function fromTracking(tracking: LeadTracking): Form {
  return {
    website: tracking.website ?? "",
    noWebsite: tracking.no_website,
    phone: tracking.phone ?? "",
    whatsapp: tracking.whatsapp ? `+${tracking.whatsapp.replace(/\D/g, "")}` : "",
    instagram: tracking.instagram ? `@${new URL(tracking.instagram).pathname.replace(/\//g, "")}` : "",
  }
}

const same = (a: Form, b: Form) => (Object.keys(a) as (keyof Form)[]).every((key) => a[key] === b[key])

/**
 * Contact data the user verified (e.g. on Google Maps or Instagram). Saving starts a
 * one-business analysis so the score reflects it.
 */
export function LeadEnrichment({
  tracking,
  onSaved,
  onRescored,
}: {
  tracking: LeadTracking
  onSaved: (tracking: LeadTracking) => void
  onRescored: () => void
}) {
  const [form, setForm] = useState(() => fromTracking(tracking))
  const [saving, setSaving] = useState(false)
  const [scanId, setScanId] = useState<string | null>(null)
  const { data: scan } = useSWR<ScanSummary>(scanId ? scanPath(scanId) : null, {
    refreshInterval: (summary) => (!summary || isActive(summary) ? 1000 : 0),
  })
  const running = Boolean(scanId) && (!scan || isActive(scan))
  const dirty = !same(form, fromTracking(tracking))

  // Report the outcome once the one-business analysis finishes.
  const reported = useRef<string | null>(null)
  useEffect(() => {
    if (!scan || isActive(scan) || reported.current === scan.scan.id) return
    reported.current = scan.scan.id
    if (scan.scan.status === "completed") toast.success("Score updated")
    else toast.error(scan.scan.error ?? "Could not update the score.")
    onRescored()
  }, [scan, onRescored])

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((current) => ({ ...current, [key]: value }))

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      if (dirty) {
        const saved = await updateTracking(tracking.business_id, {
          website: form.website.trim() || null,
          no_website: form.website.trim() ? false : form.noWebsite,
          phone: form.phone.trim() || null,
          whatsapp: form.whatsapp.trim() || null,
          instagram: form.instagram.trim() || null,
        })
        onSaved(saved)
        setForm(fromTracking(saved))
      }
      const summary = await rescoreLead(tracking.business_id)
      reported.current = null
      setScanId(summary.scan.id)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save.")
    } finally {
      setSaving(false)
    }
  }

  const busy = saving || running
  const stage = scan?.progress?.stage === "website_analysis" ? "Analyzing website…" : "Updating score…"

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="enrich-website" className="text-xs text-muted-foreground">Website</Label>
        <Input
          id="enrich-website"
          value={form.website}
          onChange={(event) => set("website", event.target.value)}
          placeholder="barbearia.com.br"
          disabled={busy}
          maxLength={500}
        />
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <Checkbox
            checked={form.noWebsite && !form.website.trim()}
            onCheckedChange={(checked) => set("noWebsite", checked === true)}
            disabled={busy || Boolean(form.website.trim())}
          />
          I checked: this business has no website
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="enrich-whatsapp" className="text-xs text-muted-foreground">WhatsApp</Label>
          <Input id="enrich-whatsapp" value={form.whatsapp} onChange={(event) => set("whatsapp", event.target.value)}
            placeholder="(61) 99999-0000" inputMode="tel" disabled={busy} maxLength={500} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="enrich-phone" className="text-xs text-muted-foreground">Phone</Label>
          <Input id="enrich-phone" value={form.phone} onChange={(event) => set("phone", event.target.value)}
            placeholder="(61) 3333-4444" inputMode="tel" disabled={busy} maxLength={500} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="enrich-instagram" className="text-xs text-muted-foreground">Instagram</Label>
          <Input id="enrich-instagram" value={form.instagram} onChange={(event) => set("instagram", event.target.value)}
            placeholder="@barbearia" disabled={busy} maxLength={500} />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground" aria-live="polite">
          {running ? stage : dirty ? "Unsaved changes" : "Stored locally"}
        </span>
        <Button type="submit" size="sm" variant={dirty ? "default" : "secondary"} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          {dirty ? "Save & update score" : "Update score"}
        </Button>
      </div>
    </form>
  )
}
