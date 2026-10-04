import type { LeadDetail } from "@/lib/api/types"

// Every URL here originates from third parties: only plain http(s) links are rendered.
export function safeUrl(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null
  } catch {
    return null
  }
}

const hostIs = (url: string, domains: string[]) => {
  const host = new URL(url).hostname.toLowerCase()
  return domains.some((domain) => host === domain || host.endsWith(`.${domain}`))
}

/** Brazilian mobile numbers (DDD + 9 digits starting with 9) almost always have WhatsApp. */
function probableWhatsapp(phone: string | null): string | null {
  const digits = (phone ?? "").replace(/\D/g, "")
  const national = digits.startsWith("55") && digits.length === 13 ? digits.slice(2) : digits
  return /^\d{2}9\d{8}$/.test(national) ? `https://wa.me/55${national}` : null
}

export interface LeadLinks {
  website: string | null
  maps: string
  instagram: string | null
  /** `confirmed` is false when only inferred from a mobile phone number. */
  whatsapp: { url: string; confirmed: boolean } | null
  phone: string | null
}

export function leadLinks(lead: LeadDetail): LeadLinks {
  const { business, analysis, scan, tracking } = lead
  const evidence = business.evidence.map((item) => item.source_url)
  const find = (urls: (string | null | undefined)[], domains: string[]) =>
    urls.map(safeUrl).find((url): url is string => url !== null && hostIs(url, domains)) ?? null
  const phone = tracking.phone ?? business.phone
  const confirmed = find([tracking.whatsapp, ...(analysis?.whatsapp_links ?? []), ...evidence], ["wa.me", "whatsapp.com"])
  const probable = confirmed ? null : probableWhatsapp(phone)
  const place = [business.name, business.address ?? scan.location].join(", ")
  return {
    website: safeUrl(tracking.website ?? business.website),
    maps: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place)}`,
    instagram: find([tracking.instagram, ...(analysis?.social_links ?? []), ...evidence], ["instagram.com"]),
    whatsapp: confirmed ? { url: confirmed, confirmed: true } : probable ? { url: probable, confirmed: false } : null,
    phone,
  }
}
