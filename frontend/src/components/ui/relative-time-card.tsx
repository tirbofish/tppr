import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"
import * as React from "react"

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"

function pluralize(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`
}

function formatRelativeTime(date: Date, nowTime = Date.now()): string {
  const diff = nowTime - date.getTime()
  const isInFuture = diff < 0
  const absDiff = Math.abs(diff)
  const seconds = Math.floor(absDiff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 5) {
    return "just now"
  }

  if (isInFuture) {
    if (seconds < 60) return `in ${pluralize(seconds, "second")}`
    if (minutes < 60) return `in ${pluralize(minutes, "minute")}`
    if (hours < 24) return `in ${pluralize(hours, "hour")}`
    if (days < 7) return `in ${pluralize(days, "day")}`
    return date.toLocaleDateString()
  }

  if (seconds < 60) return `${pluralize(seconds, "second")} ago`
  if (minutes < 60) return `${pluralize(minutes, "minute")} ago`
  if (hours < 24) return `${pluralize(hours, "hour")} ago`
  if (days < 7) return `${pluralize(days, "day")} ago`
  return date.toLocaleDateString()
}

interface TimezoneCardProps extends React.ComponentProps<"div"> {
  date: Date
  timezone?: string
}

function TimezoneCard({ date, timezone, className, ...props }: TimezoneCardProps) {
  const locale = React.useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().locale,
    []
  )
  const timezoneName = React.useMemo(
    () =>
      timezone ??
      new Intl.DateTimeFormat(locale, { timeZoneName: "shortOffset" })
        .formatToParts(date)
        .find((part) => part.type === "timeZoneName")?.value ??
      "Local",
    [date, timezone, locale]
  )
  const { formattedDate, formattedTime } = React.useMemo(
    () => ({
      formattedDate: new Intl.DateTimeFormat(locale, {
        month: "long",
        day: "numeric",
        year: "numeric",
        timeZone: timezone,
      }).format(date),
      formattedTime: new Intl.DateTimeFormat(locale, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
        timeZone: timezone,
      }).format(date),
    }),
    [date, timezone, locale]
  )

  return (
    <div
      role="region"
      aria-label={`Time in ${timezoneName}: ${formattedDate} ${formattedTime}`}
      className={cn(
        "flex items-center justify-between gap-2 text-sm text-muted-foreground",
        className
      )}
      {...props}
    >
      <span className="w-fit rounded bg-accent px-1 text-xs font-medium">
        {timezoneName}
      </span>
      <div className="flex items-center gap-2">
        <time dateTime={date.toISOString()}>{formattedDate}</time>
        <time className="tabular-nums" dateTime={date.toISOString()}>
          {formattedTime}
        </time>
      </div>
    </div>
  )
}

const triggerVariants = cva(
  "inline-flex w-fit items-center justify-center text-sm text-foreground/70 transition-colors hover:text-foreground/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default: "",
        muted: "text-foreground/50 hover:text-foreground/70",
        ghost: "hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

type HoverRootProps = Omit<React.ComponentProps<typeof HoverCard>, "children">
type HoverContentProps = React.ComponentProps<typeof HoverCardContent>

type RelativeTimeCardProps = Omit<React.ComponentProps<"button">, "children"> &
  HoverRootProps &
  Pick<
    HoverContentProps,
    | "align"
    | "side"
    | "alignOffset"
    | "sideOffset"
    | "avoidCollisions"
    | "collisionBoundary"
    | "collisionPadding"
  > &
  VariantProps<typeof triggerVariants> & {
    date: Date | string | number
    timezones?: string[]
    updateInterval?: number
    asChild?: boolean
    children?: React.ReactNode
    details?: React.ReactNode
  }

function RelativeTimeCard({
  date: dateProp,
  variant,
  timezones = ["UTC"],
  open,
  defaultOpen,
  onOpenChange,
  openDelay = 500,
  closeDelay = 300,
  align,
  side,
  alignOffset,
  sideOffset,
  avoidCollisions,
  collisionBoundary,
  collisionPadding,
  updateInterval = 1000,
  asChild,
  children,
  className,
  details,
  ...triggerProps
}: RelativeTimeCardProps) {
  const date = React.useMemo(
    () => (dateProp instanceof Date ? dateProp : new Date(dateProp)),
    [dateProp]
  )
  const locale = React.useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().locale,
    []
  )
  const [nowTime, setNowTime] = React.useState(() => Date.now())
  const formattedTime = React.useMemo(
    () => formatRelativeTime(date, nowTime),
    [date, nowTime]
  )

  React.useEffect(() => {
    const timer = window.setInterval(() => {
      setNowTime(Date.now())
    }, updateInterval)

    return () => window.clearInterval(timer)
  }, [updateInterval])

  const TriggerPrimitive = asChild ? Slot.Root : "button"

  return (
    <HoverCard
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={onOpenChange}
      openDelay={openDelay}
      closeDelay={closeDelay}
    >
      <HoverCardTrigger asChild>
        <TriggerPrimitive
          {...triggerProps}
          className={cn(triggerVariants({ variant, className }))}
        >
          {children ?? (
            <time dateTime={date.toISOString()} suppressHydrationWarning>
              {new Intl.DateTimeFormat(locale, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              }).format(date)}
            </time>
          )}
        </TriggerPrimitive>
      </HoverCardTrigger>
      <HoverCardContent
        side={side}
        align={align}
        sideOffset={sideOffset}
        alignOffset={alignOffset}
        avoidCollisions={avoidCollisions}
        collisionBoundary={collisionBoundary}
        collisionPadding={collisionPadding}
        className="flex w-full max-w-[420px] flex-col gap-3 p-3"
      >
        <time dateTime={date.toISOString()} className="text-sm text-muted-foreground">
          {formattedTime}
        </time>
        {details ? <div className="border-b pb-3">{details}</div> : null}
        <div role="list" className="flex flex-col gap-1">
          {timezones.map((timezone) => (
            <TimezoneCard
              key={timezone}
              role="listitem"
              date={date}
              timezone={timezone}
            />
          ))}
          <TimezoneCard role="listitem" date={date} />
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}

export { RelativeTimeCard }
