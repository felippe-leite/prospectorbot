"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import useSWR from "swr"
import { Gem, History, LayoutDashboard, Menu, Pickaxe, Radar, Rows3 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import type { Health } from "@/lib/api/types"
import { healthPath } from "@/lib/api/system"
import { cn } from "@/lib/utils"

const NAVIGATION = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/prospect", label: "Prospect", icon: Radar },
  { href: "/leads", label: "Leads", icon: Rows3 },
  { href: "/gold-nuggets", label: "Gold Nuggets", icon: Gem },
  { href: "/history", label: "History", icon: History },
]

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 px-2">
      <span className="flex size-8 items-center justify-center rounded-lg border border-gold/30 bg-gold/10 text-gold">
        <Pickaxe className="size-4" />
      </span>
      <span className="font-semibold tracking-tight">ProspectorBot</span>
    </Link>
  )
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  return (
    <nav className="flex flex-col gap-0.5">
      {NAVIGATION.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              active && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
            )}
          >
            <Icon className={cn("size-4", active && href === "/gold-nuggets" && "text-gold")} />
            {label}
          </Link>
        )
      })}
    </nav>
  )
}

function ApiStatus() {
  const { data, error, isLoading } = useSWR<Health>(healthPath, { refreshInterval: 15_000 })
  const online = Boolean(data) && !error
  return (
    <div className="flex flex-col gap-1 px-3 text-xs text-muted-foreground">
      <div className="flex items-center gap-2">
        <span>API</span>
        <span
          className={cn(
            "size-1.5 rounded-full",
            isLoading ? "bg-muted-foreground/50" : online ? "bg-positive shadow-[0_0_6px_var(--positive)]" : "bg-negative",
          )}
        />
        <span className={cn(online ? "text-foreground/80" : !isLoading && "text-negative")}>
          {isLoading ? "Checking" : online ? "Online" : "Offline"}
        </span>
      </div>
      <span>v{data?.version.split(".").slice(0, 2).join(".") ?? "0.1"}</span>
    </div>
  )
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 px-3 py-5">
      <Brand />
      <NavLinks onNavigate={onNavigate} />
      <div className="mt-auto flex flex-col gap-4">
        <Separator className="bg-sidebar-border" />
        <ApiStatus />
      </div>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-sidebar-border bg-sidebar md:block">
      <SidebarBody />
    </aside>
  )
}

export function MobileHeader() {
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur md:hidden">
      <Brand />
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="Open navigation">
            <Menu />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 border-sidebar-border bg-sidebar p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarBody onNavigate={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </header>
  )
}

