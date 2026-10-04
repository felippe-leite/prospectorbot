"use client"

import { useEffect, useId, useState } from "react"
import useSWR from "swr"
import { Loader2, MapPin } from "lucide-react"

import { Input } from "@/components/ui/input"
import { locationsPath } from "@/lib/api/system"
import { cn } from "@/lib/utils"

/** City/region field with suggestions from the API (Geoapify, Brazil). Free text still works. */
export function LocationInput({
  id,
  value,
  onChange,
  disabled,
}: {
  id: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}) {
  const listId = useId()
  const [term, setTerm] = useState("")
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)

  // Debounced lookup; each request costs a Geoapify credit.
  useEffect(() => {
    const timer = setTimeout(() => setTerm(value.trim()), 300)
    return () => clearTimeout(timer)
  }, [value])

  const { data, isLoading } = useSWR<string[]>(open && term.length >= 2 ? locationsPath(term) : null, {
    revalidateOnFocus: false,
    keepPreviousData: false,
  })
  const suggestions = (data ?? []).filter((item) => item !== value)
  const showList = open && suggestions.length > 0

  const pick = (label: string) => {
    onChange(label)
    setOpen(false)
    setActive(-1)
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!showList) return
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault()
      const step = event.key === "ArrowDown" ? 1 : -1
      setActive((current) => (current + step + suggestions.length) % suggestions.length)
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault()
      pick(suggestions[active])
    } else if (event.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <Input
        id={id}
        value={value}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
          setActive(-1)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
        placeholder="Campinas, SP"
        required
        maxLength={120}
        autoComplete="off"
        disabled={disabled}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        className="h-10 pr-9"
      />
      {isLoading && open && (
        <Loader2 className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
      )}
      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border bg-popover p-1 shadow-lg"
        >
          {suggestions.map((label, index) => (
            <li
              key={label}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              // mousedown keeps focus in the input so blur doesn't close the list first
              onMouseDown={(event) => {
                event.preventDefault()
                pick(label)
              }}
              onMouseEnter={() => setActive(index)}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-sm",
                index === active && "bg-accent",
              )}
            >
              <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
              {label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
