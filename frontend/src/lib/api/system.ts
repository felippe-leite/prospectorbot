import { request } from "./client"

export const healthPath = "/api/health"
export const statsPath = "/api/stats"
export const categoriesPath = "/api/categories"
export const locationsPath = (q: string) => `/api/locations?q=${encodeURIComponent(q)}`

/** Deletes every scan, lead, status and note. */
export const clearData = () => request<null>("/api/data", { method: "DELETE" })
