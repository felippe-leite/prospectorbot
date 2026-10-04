import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"

import { MobileHeader, Sidebar } from "@/components/layout/sidebar"
import { Providers } from "@/components/providers"
import "./globals.css"

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: { default: "ProspectorBot", template: "%s · ProspectorBot" },
  description: "Evidence-based discovery of web development opportunities in local businesses.",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable} antialiased`}>
      <body className="min-h-screen">
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <MobileHeader />
              <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-4 py-6 sm:px-8 sm:py-10">{children}</main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}
