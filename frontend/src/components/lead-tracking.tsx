"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { updateTracking } from "@/lib/api/leads"
import type { LeadStatus, LeadTracking as Tracking } from "@/lib/api/types"
import { formatDateTime } from "@/lib/format"
import { STATUS_LABELS, STATUS_STYLES } from "@/lib/labels"
import { cn } from "@/lib/utils"

const STATUSES = Object.keys(STATUS_LABELS) as LeadStatus[]

export function StatusSelect({ tracking, onSaved }: { tracking: Tracking; onSaved: (tracking: Tracking) => void }) {
  const [saving, setSaving] = useState(false)

  async function change(status: LeadStatus) {
    setSaving(true)
    try {
      onSaved(await updateTracking(tracking.business_id, { status }))
      toast.success(`Status set to ${STATUS_LABELS[status]}`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update status.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Select value={tracking.status} onValueChange={(value) => change(value as LeadStatus)} disabled={saving}>
      <SelectTrigger className="h-9! w-full sm:w-44" aria-label="Lead status">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {STATUSES.map((status) => (
          <SelectItem key={status} value={status}>
            <span className={cn("size-1.5 rounded-full bg-current", STATUS_STYLES[status])} />
            {STATUS_LABELS[status]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function NotesEditor({ tracking, onSaved }: { tracking: Tracking; onSaved: (tracking: Tracking) => void }) {
  const [notes, setNotes] = useState(tracking.notes)
  const [saving, setSaving] = useState(false)
  const dirty = notes.trim() !== tracking.notes

  async function save() {
    setSaving(true)
    try {
      const saved = await updateTracking(tracking.business_id, { notes })
      setNotes(saved.notes)
      onSaved(saved)
      toast.success("Notes saved")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save notes.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Textarea
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && dirty) save()
        }}
        placeholder="What makes this lead interesting? What to check before reaching out?"
        maxLength={10_000}
        className="min-h-32 resize-y text-sm"
        aria-label="Personal notes"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">
          {dirty ? "Unsaved changes" : tracking.updated_at ? `Saved ${formatDateTime(tracking.updated_at)}` : "Private to you"}
        </span>
        <Button size="sm" variant="secondary" onClick={save} disabled={!dirty || saving}>
          {saving && <Loader2 className="animate-spin" />} Save notes
        </Button>
      </div>
    </div>
  )
}
