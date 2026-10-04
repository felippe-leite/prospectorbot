"use client"

import { useState } from "react"
import { Loader2, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { useSWRConfig } from "swr"

import {
  AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { clearData } from "@/lib/api/system"

export function ClearDataButton() {
  const { mutate } = useSWRConfig()
  const [open, setOpen] = useState(false)
  const [clearing, setClearing] = useState(false)

  async function confirm() {
    setClearing(true)
    try {
      await clearData()
      await mutate(() => true)
      toast.success("All prospecting data was deleted")
      setOpen(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not clear the data.")
    } finally {
      setClearing(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !clearing && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" className="text-muted-foreground hover:text-negative">
          <Trash2 /> Clear data
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete all prospecting data?</AlertDialogTitle>
          <AlertDialogDescription>
            Every prospecting session, lead, analysis and score will be removed, together with your statuses, notes and
            contact data. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={clearing}>Cancel</AlertDialogCancel>
          <Button variant="destructive" onClick={confirm} disabled={clearing}>
            {clearing ? <Loader2 className="animate-spin" /> : <Trash2 />} Delete everything
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
