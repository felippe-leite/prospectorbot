import type { Metadata } from "next"

import { GoldNuggetsView } from "./gold-nuggets-view"

export const metadata: Metadata = { title: "Gold Nuggets" }

export default function GoldNuggetsPage() {
  return <GoldNuggetsView />
}
