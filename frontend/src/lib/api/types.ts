// Mirrors the Pydantic models in src/prospector/models.py and src/prospector/api/schemas.py.
// Datetimes and UUIDs arrive as ISO strings.

export type CheckStatus = "present" | "absent" | "unknown"
export type AnalysisStatus = "completed" | "partial" | "failed"
export type WebsiteDiscoveryStatus = "unknown" | "found" | "not_found" | "confirmed_absent"
export type ScanStatus = "pending" | "running" | "completed" | "failed"
export type ScanKind = "discovery" | "manual"
export type ScanStage = "discovery" | "website_analysis" | "opportunity_analysis" | "scoring"
export type Classification = "Low" | "Moderate" | "Good" | "High" | "Gold Nugget"
export type LeadStatus = "new" | "reviewing" | "interesting" | "contacted" | "won" | "lost" | "ignored"
export type OpportunityTag = "landing_page" | "website_redesign" | "performance" | "whatsapp" | "booking" | "seo"

export interface Evidence {
  code: string
  description: string
  source: string
  source_url: string | null
  observed_at: string
}

export interface Business {
  id: string
  discovered_at: string
  name: string
  category: string | null
  address: string | null
  website: string | null
  website_status: WebsiteDiscoveryStatus
  phone: string | null
  rating: number | null
  review_count: number | null
  source: string
  source_id: string | null
  evidence: Evidence[]
  appointment_based: CheckStatus
}

export interface Scan {
  id: string
  /** "manual" re-scores one business with data the user supplied. */
  kind: ScanKind
  query: string
  location: string
  limit: number
  status: ScanStatus
  created_at: string
  finished_at: string | null
  error: string | null
}

export interface ScanProgress {
  stage: ScanStage
  analyzed: number
  total: number | null
  current_business: string | null
  has_website: boolean | null
}

export interface ScanSummary {
  scan: Scan
  analyzed: number
  gold_nuggets: number
  progress: ScanProgress | null
}

export interface LinkCheck {
  url: string
  status_code: number | null
  error: string | null
}

export interface WebsiteAnalysis {
  id: string
  business_id: string
  scan_id: string
  requested_url: string
  final_url: string | null
  analyzed_at: string
  status: AnalysisStatus
  status_code: number | null
  redirect_chain: string[]
  response_time_ms: number | null
  https: CheckStatus
  title: string | null
  title_status: CheckStatus
  meta_description: string | null
  meta_description_status: CheckStatus
  mobile_viewport: CheckStatus
  headings: string[]
  headings_status: CheckStatus
  link_checks: LinkCheck[]
  phone: CheckStatus
  whatsapp: CheckStatus
  cta: CheckStatus
  contact_form: CheckStatus
  booking: CheckStatus
  social_links: string[]
  whatsapp_links: string[]
  social_presence: CheckStatus
  evidence: Evidence[]
  errors: string[]
  mobile_performance_score: number | null
  mobile_performance_source: string | null
}

export interface ScoreContribution {
  rule_code: string
  points: number
  evidence: Evidence[]
}

export interface Opportunity {
  id: string
  business_id: string
  scan_id: string
  rule_code: string
  title: string
  description: string
  evidence: Evidence[]
  suggested_services: string[]
  /** Score points from the same rule; 0 when the rule is not weighted. */
  points: number
}

/** Personal triage plus contact data the user verified; the business snapshot keeps only source data. */
export interface LeadTracking {
  business_id: string
  status: LeadStatus
  notes: string
  website: string | null
  no_website: boolean
  phone: string | null
  whatsapp: string | null
  instagram: string | null
  updated_at: string | null
}

export interface TrackingUpdate {
  status?: LeadStatus
  notes?: string
  website?: string | null
  no_website?: boolean
  phone?: string | null
  whatsapp?: string | null
  instagram?: string | null
}

export interface LeadSummary {
  business_id: string
  scan_id: string
  name: string
  category: string | null
  address: string | null
  query: string
  location: string
  website: string | null
  website_status: WebsiteDiscoveryStatus
  rating: number | null
  review_count: number | null
  score: number
  classification: Classification
  opportunity_count: number
  tags: OpportunityTag[]
  status: LeadStatus
  analyzed_at: string
}

export interface Appearance {
  scan_id: string
  query: string
  location: string
  created_at: string
  score: number
  classification: Classification
}

export interface LeadDetail {
  scan: Scan
  business: Business
  score: number
  classification: Classification
  scoring_version: string
  contributions: ScoreContribution[]
  analysis: WebsiteAnalysis | null
  opportunities: Opportunity[]
  tracking: LeadTracking
  appearances: Appearance[]
}

export interface Stats {
  businesses: number
  opportunities: number
  gold_nuggets: number
  average_score: number | null
  scans: number
}

export interface Health {
  status: string
  version: string
  discovery_configured: boolean
  performance_configured: boolean
}

export interface LeadQuery {
  scan_id?: string
  q?: string
  min_score?: number
  classification?: Classification[]
  website?: "has" | "none"
  tag?: OpportunityTag[]
  status?: LeadStatus[]
  sort?: "score" | "recent"
  limit?: number
}
