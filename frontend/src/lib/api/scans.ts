import { request } from "./client"
import type { ScanSummary } from "./types"

export interface ScanInput {
  query: string
  location: string
  limit: number
}

export const scansPath = "/api/scans"
export const scanPath = (id: string) => `/api/scans/${encodeURIComponent(id)}`

export const startScan = (input: ScanInput) =>
  request<ScanSummary>(scansPath, { method: "POST", body: JSON.stringify(input) })

export const isActive = (summary: ScanSummary) =>
  summary.scan.status === "running" || summary.scan.status === "pending"
