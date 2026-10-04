const dateFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" })
const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
})

export const formatDate = (iso: string) => dateFormat.format(new Date(iso))
export const formatDateTime = (iso: string) => dateTimeFormat.format(new Date(iso))

export function formatDuration(ms: number) {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)}s`
}

const CATEGORY_NAMES: Record<string, string> = {
  "service.beauty.hairdresser": "Barbershop / Hair salon",
  "catering.restaurant": "Restaurant",
  "catering.cafe": "Cafe",
  "healthcare.dentist": "Dentist",
  "sport.fitness": "Gym",
  "accommodation.hotel": "Hotel",
  "commercial.food_and_drink.bakery": "Bakery",
  "commercial.pet": "Pet shop",
}

/** Turns a Geoapify category ("catering.fast_food") into a readable label. */
export function formatCategory(category: string | null) {
  if (!category) return null
  if (CATEGORY_NAMES[category]) return CATEGORY_NAMES[category]
  const last = category.split(".").pop() ?? category
  return last.replace(/_/g, " ").replace(/^\w/, (char) => char.toUpperCase())
}

export function formatHost(url: string) {
  try {
    return new URL(url).host.replace(/^www\./, "")
  } catch {
    return url
  }
}
