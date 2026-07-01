import * as React from "react"
import { Avatar as AvatarPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

const avatarObjectUrlCache = new Map<string, string>()
const avatarFetchCache = new Map<string, Promise<string>>()

function shouldCacheAvatar(src: string | undefined): src is string {
  return !!src && /^https?:\/\//i.test(src)
}

function cachedAvatarSrc(src: string): Promise<string> {
  const cached = avatarObjectUrlCache.get(src)
  if (cached) return Promise.resolve(cached)

  const pending = avatarFetchCache.get(src)
  if (pending) return pending

  const request = fetch(src)
    .then((res) => {
      if (!res.ok) throw new Error("Avatar request failed")
      return res.blob()
    })
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      avatarObjectUrlCache.set(src, objectUrl)
      avatarFetchCache.delete(src)
      return objectUrl
    })
    .catch(() => {
      avatarFetchCache.delete(src)
      return src
    })

  avatarFetchCache.set(src, request)
  return request
}

function Avatar({
  className,
  size = "default",
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Root> & {
  size?: "default" | "sm" | "lg"
}) {
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      data-size={size}
      className={cn(
        "group/avatar relative flex size-8 shrink-0 rounded-full select-none after:absolute after:inset-0 after:rounded-full after:border after:border-border after:mix-blend-darken data-[size=lg]:size-10 data-[size=sm]:size-6 dark:after:mix-blend-lighten",
        className
      )}
      {...props}
    />
  )
}

function AvatarImage({
  className,
  src,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Image>) {
  const [resolvedSrc, setResolvedSrc] = React.useState(src)

  React.useEffect(() => {
    if (!shouldCacheAvatar(src)) {
      setResolvedSrc(src)
      return
    }

    let active = true
    cachedAvatarSrc(src).then((nextSrc) => {
      if (active) setResolvedSrc(nextSrc)
    })

    return () => {
      active = false
    }
  }, [src])

  return (
    <AvatarPrimitive.Image
      data-slot="avatar-image"
      src={resolvedSrc}
      className={cn(
        "aspect-square size-full rounded-full object-cover",
        className
      )}
      {...props}
    />
  )
}

function AvatarFallback({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Fallback>) {
  return (
    <AvatarPrimitive.Fallback
      data-slot="avatar-fallback"
      className={cn(
        "flex size-full items-center justify-center rounded-full bg-muted text-sm text-muted-foreground group-data-[size=sm]/avatar:text-xs",
        className
      )}
      {...props}
    />
  )
}

function AvatarBadge({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="avatar-badge"
      className={cn(
        "absolute right-0 bottom-0 z-10 inline-flex items-center justify-center rounded-full bg-primary text-primary-foreground bg-blend-color ring-2 ring-background select-none",
        "group-data-[size=sm]/avatar:size-2 group-data-[size=sm]/avatar:[&>svg]:hidden",
        "group-data-[size=default]/avatar:size-2.5 group-data-[size=default]/avatar:[&>svg]:size-2",
        "group-data-[size=lg]/avatar:size-3 group-data-[size=lg]/avatar:[&>svg]:size-2",
        className
      )}
      {...props}
    />
  )
}

function AvatarGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="avatar-group"
      className={cn(
        "group/avatar-group flex -space-x-2 *:data-[slot=avatar]:ring-2 *:data-[slot=avatar]:ring-background",
        className
      )}
      {...props}
    />
  )
}

function AvatarGroupCount({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="avatar-group-count"
      className={cn(
        "relative flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm text-muted-foreground ring-2 ring-background group-has-data-[size=lg]/avatar-group:size-10 group-has-data-[size=sm]/avatar-group:size-6 [&>svg]:size-4 group-has-data-[size=lg]/avatar-group:[&>svg]:size-5 group-has-data-[size=sm]/avatar-group:[&>svg]:size-3",
        className
      )}
      {...props}
    />
  )
}

export {
  Avatar,
  AvatarImage,
  AvatarFallback,
  AvatarGroup,
  AvatarGroupCount,
  AvatarBadge,
}
