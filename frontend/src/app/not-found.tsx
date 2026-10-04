import { Compass } from "lucide-react"

import { EmptyState } from "@/components/states"

export default function NotFound() {
  return (
    <EmptyState
      icon={Compass}
      title="Nothing to dig up here."
      description="This page does not exist."
      action={{ href: "/", label: "Back to Dashboard" }}
      className="mt-10"
    />
  )
}
