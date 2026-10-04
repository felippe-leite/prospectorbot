import { request, withQuery } from "./client"
import type { LeadQuery, LeadTracking, ScanSummary, TrackingUpdate } from "./types"

// GET paths double as SWR keys; the global fetcher in components/providers.tsx resolves them.
export const leadsPath = (query: LeadQuery = {}) => withQuery("/api/leads", { ...query })

export const leadPath = (id: string, scanId?: string | null) =>
  withQuery(`/api/leads/${encodeURIComponent(id)}`, { scan_id: scanId ?? undefined })

export const updateTracking = (id: string, changes: TrackingUpdate) =>
  request<LeadTracking>(`/api/leads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  })

/** Re-analyzes one lead with the data the user supplied; runs like a one-business scan. */
export const rescoreLead = (id: string) =>
  request<ScanSummary>(`/api/leads/${encodeURIComponent(id)}/rescore`, { method: "POST" })
