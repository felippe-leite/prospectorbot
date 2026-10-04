import { Suspense } from "react"
import type { Metadata } from "next"

import { TableSkeleton } from "@/components/states"
import { ScanView } from "./scan-view"

export const metadata: Metadata = { title: "Prospecting session" }

export default async function ScanPage({ params }: PageProps<"/history/[id]">) {
  const { id } = await params
  return (
    <Suspense fallback={<TableSkeleton />}>
      <ScanView id={id} />
    </Suspense>
  )
}
