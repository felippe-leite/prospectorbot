import type { Metadata } from "next"

import { ProspectView } from "./prospect-view"

export const metadata: Metadata = { title: "Prospect" }

export default function ProspectPage() {
  return <ProspectView />
}
