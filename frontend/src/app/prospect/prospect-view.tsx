"use client"

import Link from "next/link"
import useSWR from "swr"
import { ArrowRight, Gauge, KeyRound, Loader2, ShieldCheck } from "lucide-react"

import { PageHeader } from "@/components/layout/page-header"
import { ProspectingForm } from "@/components/prospecting-form"
import { ErrorState } from "@/components/states"
import { Skeleton } from "@/components/ui/skeleton"
import { isActive, scansPath } from "@/lib/api/scans"
import { healthPath } from "@/lib/api/system"
import type { Health, ScanSummary } from "@/lib/api/types"

export function ProspectView() {
  const health = useSWR<Health>(healthPath)
  const scans = useSWR<ScanSummary[]>(scansPath, { refreshInterval: (data) => (data?.some(isActive) ? 2000 : 0) })
  const running = scans.data?.find(isActive)

  return (
    <>
      <PageHeader title="New Prospect" description="Discover local businesses, analyze their websites and rank the opportunities." />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-xl border bg-card p-6 sm:p-8">
          {health.error ? (
            <ErrorState error={health.error} onRetry={() => health.mutate()} className="border-0 bg-transparent" />
          ) : !health.data || !scans.data ? (
            <div className="flex flex-col gap-6">
              {[0, 1, 2].map((index) => <Skeleton key={index} className="h-16" />)}
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {!health.data.discovery_configured && (
                <div className="flex gap-3 rounded-lg border border-gold/25 bg-gold/[0.05] p-4 text-sm">
                  <KeyRound className="mt-0.5 size-4 shrink-0 text-gold" />
                  <p>
                    Discovery is not configured. Set <code className="font-mono text-xs">GEOAPIFY_API_KEY</code> in the backend
                    <code className="font-mono text-xs"> .env</code> and restart <code className="font-mono text-xs">prospector serve</code>.
                  </p>
                </div>
              )}
              {health.data.discovery_configured && !health.data.performance_configured && (
                <div className="flex gap-3 rounded-lg border p-4 text-sm text-muted-foreground">
                  <Gauge className="mt-0.5 size-4 shrink-0" />
                  <p>
                    Mobile performance is not measured, so the &ldquo;Poor mobile performance&rdquo; criterion (+20) never applies and
                    scores stay lower. Set <code className="font-mono text-xs">PAGESPEED_API_KEY</code> in the backend to enable it.
                  </p>
                </div>
              )}
              {running && (
                <Link href={`/history/${running.scan.id}`} className="flex items-center gap-3 rounded-lg border border-gold/25 bg-gold/[0.05] p-4 text-sm hover:bg-gold/[0.08]">
                  <Loader2 className="size-4 shrink-0 animate-spin text-gold" />
                  <span className="flex-1">
                    A session is already running ({running.scan.query} · {running.scan.location}). Wait for it to finish before starting another.
                  </span>
                  <ArrowRight className="size-4 text-muted-foreground" />
                </Link>
              )}
              <ProspectingForm disabled={!health.data.discovery_configured || Boolean(running)} />
            </div>
          )}
        </div>

        <aside className="flex flex-col gap-4 text-sm text-muted-foreground">
          <h2 className="font-medium text-foreground">How it works</h2>
          <ol className="flex flex-col gap-3">
            {[
              "Businesses are discovered through Geoapify (OpenStreetMap data).",
              "Each public website's homepage is checked: HTTPS, mobile viewport, calls to action, booking, WhatsApp and more. Mobile performance is measured with PageSpeed Insights when configured.",
              "Evidence-based rules find opportunities and compute a 0–100 Prospector Score.",
            ].map((text, index) => (
              <li key={index} className="flex gap-3">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]">{index + 1}</span>
                {text}
              </li>
            ))}
          </ol>
          <div className="flex gap-3 rounded-lg border p-4">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-positive" />
            <p>ProspectorBot respects robots.txt, never bypasses CAPTCHAs or logins and never contacts anyone. You decide who to approach.</p>
          </div>
        </aside>
      </div>
    </>
  )
}
