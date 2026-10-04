import { Suspense } from "react"
import type { Metadata } from "next"

import { TableSkeleton } from "@/components/states"
import { LeadsView } from "./leads-view"

export const metadata: Metadata = { title: "Leads" }

export default function LeadsPage() {
  return (
    <Suspense fallback={<TableSkeleton />}>
      <LeadsView />
    </Suspense>
  )
}
