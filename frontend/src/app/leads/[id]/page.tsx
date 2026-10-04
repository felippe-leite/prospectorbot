import { Suspense } from "react"
import type { Metadata } from "next"

import { TableSkeleton } from "@/components/states"
import { LeadView } from "./lead-view"

export const metadata: Metadata = { title: "Lead" }

export default async function LeadPage({ params }: PageProps<"/leads/[id]">) {
  const { id } = await params
  return (
    <Suspense fallback={<TableSkeleton />}>
      <LeadView id={id} />
    </Suspense>
  )
}
