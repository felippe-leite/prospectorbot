"use client"

import { SWRConfig } from "swr"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { request } from "@/lib/api/client"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher: (path: string) => request(path),
        // Errors surface as an ErrorState with an explicit Retry instead of silent retries.
        shouldRetryOnError: false,
        keepPreviousData: true,
      }}
    >
      <TooltipProvider delayDuration={200}>
        {children}
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </SWRConfig>
  )
}
