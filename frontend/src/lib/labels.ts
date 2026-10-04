import type { LeadStatus, OpportunityTag, ScanStatus } from "@/lib/api/types"

/** English labels for backend rule codes (src/prospector/opportunities/rules.py). */
export const RULE_LABELS: Record<string, string> = {
  no_website: "No website (confirmed)",
  website_not_listed: "Website not listed by the source",
  no_whatsapp_cta: "No WhatsApp link detected",
  poor_mobile_performance: "Poor mobile performance",
  no_booking: "No booking flow detected",
  no_cta: "No call to action detected",
  missing_viewport: "Mobile viewport missing",
  slow_site: "Slow response time",
  established_reviews: "Established business (reviews)",
  whatsapp_present: "WhatsApp available",
  social_present: "Social media presence",
  http_error: "Website returned an HTTP error",
  no_https: "No HTTPS",
  missing_title: "Page title missing",
  missing_description: "Meta description missing",
  broken_links: "Broken internal links",
}

export const OPPORTUNITY_TITLES: Record<string, string> = {
  no_website: "Landing Page",
  website_not_listed: "Landing Page",
  no_whatsapp_cta: "WhatsApp CTA",
  poor_mobile_performance: "Mobile Performance",
  no_booking: "Online Booking",
  no_cta: "Calls to Action",
  missing_viewport: "Mobile Experience",
  slow_site: "Response Time",
  http_error: "Broken Website Address",
  no_https: "HTTPS Setup",
  missing_title: "Page Title (SEO)",
  missing_description: "Meta Description (SEO)",
  broken_links: "Broken Links",
}

export const ruleLabel = (code: string) => RULE_LABELS[code] ?? code.replace(/_/g, " ")

export const TAG_LABELS: Record<OpportunityTag, string> = {
  landing_page: "Landing Page",
  website_redesign: "Website Redesign",
  performance: "Performance",
  whatsapp: "WhatsApp",
  booking: "Booking",
  seo: "SEO",
}

export const STATUS_LABELS: Record<LeadStatus, string> = {
  new: "New",
  reviewing: "Reviewing",
  interesting: "Interesting",
  contacted: "Contacted",
  won: "Won",
  lost: "Lost",
  ignored: "Ignored",
}

export const STATUS_STYLES: Record<LeadStatus, string> = {
  new: "text-muted-foreground",
  reviewing: "text-sky-300",
  interesting: "text-gold",
  contacted: "text-violet-300",
  won: "text-positive",
  lost: "text-negative",
  ignored: "text-muted-foreground/60",
}

export const MANUAL_SCAN_LABEL = "Manual update"

export const SCAN_STATUS_LABELS: Record<ScanStatus, string> = {
  pending: "Starting",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
}
