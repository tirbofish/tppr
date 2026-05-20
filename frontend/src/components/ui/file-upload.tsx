import { Slot } from "radix-ui"
import * as React from "react"
import { FileText, Trash2, UploadCloud, X } from "lucide-react"

import { cn } from "@/lib/utils"

type FileUploadContextValue = {
  value: File[]
  accept?: string
  disabled?: boolean
  invalid?: boolean
  inputRef: React.RefObject<HTMLInputElement | null>
  removeFile: (file: File) => void
  clearFiles: () => void
  openFileDialog: () => void
  setFilesFromList: (files: FileList | File[]) => void
  dragging: boolean
  setDragging: (dragging: boolean) => void
}

type FileUploadItemContextValue = {
  value: File
}

const FileUploadContext = React.createContext<FileUploadContextValue | null>(null)
const FileUploadItemContext = React.createContext<FileUploadItemContextValue | null>(
  null
)

function useFileUpload() {
  const context = React.useContext(FileUploadContext)

  if (!context) {
    throw new Error("FileUpload components must be used inside <FileUpload>.")
  }

  return context
}

function useFileUploadItem() {
  const context = React.useContext(FileUploadItemContext)

  if (!context) {
    throw new Error("FileUpload item components must be used inside <FileUploadItem>.")
  }

  return context
}

function formatBytes(bytes: number) {
  if (bytes === 0) {
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB"]
  const sizeIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  )
  const size = bytes / 1024 ** sizeIndex

  return `${size.toFixed(size >= 10 || sizeIndex === 0 ? 0 : 1)} ${units[sizeIndex]}`
}

function matchesAccept(file: File, accept?: string) {
  if (!accept) {
    return true
  }

  return accept.split(",").some((rawRule) => {
    const rule = rawRule.trim().toLowerCase()

    if (!rule) {
      return false
    }

    if (rule.startsWith(".")) {
      return file.name.toLowerCase().endsWith(rule)
    }

    if (rule.endsWith("/*")) {
      return file.type.toLowerCase().startsWith(rule.slice(0, -1))
    }

    return file.type.toLowerCase() === rule
  })
}

type FileUploadProps = Omit<React.ComponentProps<"div">, "defaultValue"> & {
  value?: File[]
  defaultValue?: File[]
  onValueChange?: (files: File[]) => void
  onAccept?: (files: File[]) => void
  onFileAccept?: (file: File) => void
  onFileReject?: (file: File, message: string) => void
  onFileValidate?: (file: File) => string | null | undefined
  accept?: string
  maxFiles?: number
  maxSize?: number
  multiple?: boolean
  disabled?: boolean
  invalid?: boolean
  name?: string
  required?: boolean
}

function FileUpload({
  value,
  defaultValue = [],
  onValueChange,
  onAccept,
  onFileAccept,
  onFileReject,
  onFileValidate,
  accept,
  maxFiles,
  maxSize,
  multiple,
  disabled,
  invalid,
  name,
  required,
  className,
  children,
  ...props
}: FileUploadProps) {
  const inputRef = React.useRef<HTMLInputElement | null>(null)
  const [internalValue, setInternalValue] = React.useState<File[]>(defaultValue)
  const [dragging, setDragging] = React.useState(false)
  const files = value ?? internalValue

  const commitFiles = React.useCallback(
    (nextFiles: File[]) => {
      if (value === undefined) {
        setInternalValue(nextFiles)
      }

      onValueChange?.(nextFiles)
    },
    [onValueChange, value]
  )

  const setFilesFromList = React.useCallback(
    (fileList: FileList | File[]) => {
      const incoming = Array.from(fileList)
      const accepted: File[] = []
      const limit = multiple ? maxFiles : 1

      for (const file of incoming) {
        const validationMessage = onFileValidate?.(file)

        if (validationMessage) {
          onFileReject?.(file, validationMessage)
          continue
        }

        if (!matchesAccept(file, accept)) {
          onFileReject?.(file, "File type is not accepted.")
          continue
        }

        if (maxSize && file.size > maxSize) {
          onFileReject?.(file, `File must be ${formatBytes(maxSize)} or smaller.`)
          continue
        }

        if (limit && accepted.length >= limit) {
          onFileReject?.(file, `Upload up to ${limit} file${limit === 1 ? "" : "s"}.`)
          continue
        }

        accepted.push(file)
        onFileAccept?.(file)
      }

      if (accepted.length > 0) {
        const nextFiles = multiple ? accepted : accepted.slice(0, 1)
        commitFiles(nextFiles)
        onAccept?.(nextFiles)
      }
    },
    [accept, commitFiles, maxFiles, maxSize, multiple, onAccept, onFileAccept, onFileReject, onFileValidate]
  )

  const removeFile = React.useCallback(
    (file: File) => {
      commitFiles(files.filter((item) => item !== file))
    },
    [commitFiles, files]
  )

  const clearFiles = React.useCallback(() => {
    commitFiles([])
  }, [commitFiles])

  const openFileDialog = React.useCallback(() => {
    if (!disabled) {
      inputRef.current?.click()
    }
  }, [disabled])

  const contextValue = React.useMemo<FileUploadContextValue>(
    () => ({
      value: files,
      accept,
      disabled,
      invalid,
      inputRef,
      removeFile,
      clearFiles,
      openFileDialog,
      setFilesFromList,
      dragging,
      setDragging,
    }),
    [accept, clearFiles, disabled, dragging, files, invalid, openFileDialog, removeFile, setFilesFromList]
  )

  return (
    <FileUploadContext.Provider value={contextValue}>
      <div
        data-slot="file-upload"
        data-disabled={disabled ? "" : undefined}
        data-invalid={invalid ? "" : undefined}
        className={cn("grid gap-3", className)}
        {...props}
      >
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          name={name}
          required={required}
          onChange={(event) => {
            if (event.target.files) {
              setFilesFromList(event.target.files)
            }

            event.target.value = ""
          }}
        />
        {children}
      </div>
    </FileUploadContext.Provider>
  )
}

type FileUploadDropzoneProps = React.ComponentProps<"div"> & {
  asChild?: boolean
}

function FileUploadDropzone({
  asChild,
  className,
  onClick,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  onKeyDown,
  children,
  ...props
}: FileUploadDropzoneProps) {
  const upload = useFileUpload()
  const Comp = asChild ? Slot.Root : "div"

  return (
    <Comp
      role="button"
      tabIndex={upload.disabled ? -1 : 0}
      data-slot="file-upload-dropzone"
      data-disabled={upload.disabled ? "" : undefined}
      data-dragging={upload.dragging ? "" : undefined}
      data-invalid={upload.invalid ? "" : undefined}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-muted/20 p-6 text-center transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[dragging]:border-primary data-[dragging]:bg-muted data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[invalid]:border-destructive/60",
        className
      )}
      onClick={(event) => {
        onClick?.(event)
        upload.openFileDialog()
      }}
      onDragEnter={(event) => {
        onDragEnter?.(event)
        event.preventDefault()
        upload.setDragging(true)
      }}
      onDragLeave={(event) => {
        onDragLeave?.(event)
        event.preventDefault()
        upload.setDragging(false)
      }}
      onDragOver={(event) => {
        onDragOver?.(event)
        event.preventDefault()
      }}
      onDrop={(event) => {
        onDrop?.(event)
        event.preventDefault()
        upload.setDragging(false)
        upload.setFilesFromList(event.dataTransfer.files)
      }}
      onKeyDown={(event) => {
        onKeyDown?.(event)

        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          upload.openFileDialog()
        }
      }}
      {...props}
    >
      {children ?? (
        <>
          <UploadCloud className="size-6 text-muted-foreground" />
          <div className="space-y-1">
            <p className="text-sm font-medium">Drag and drop a file here</p>
            <p className="text-xs text-muted-foreground">Or click to browse</p>
          </div>
        </>
      )}
    </Comp>
  )
}

type FileUploadTriggerProps = React.ComponentProps<"button"> & {
  asChild?: boolean
}

function FileUploadTrigger({
  asChild,
  className,
  onClick,
  ...props
}: FileUploadTriggerProps) {
  const upload = useFileUpload()
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      type="button"
      data-slot="file-upload-trigger"
      data-disabled={upload.disabled ? "" : undefined}
      className={cn(
        "inline-flex h-8 items-center justify-center rounded-lg border bg-background px-2.5 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      onClick={(event) => {
        event.stopPropagation()
        onClick?.(event)
        upload.openFileDialog()
      }}
      {...props}
    />
  )
}

type FileUploadListProps = React.ComponentProps<"div"> & {
  orientation?: "horizontal" | "vertical"
  forceMount?: boolean
  asChild?: boolean
}

function FileUploadList({
  orientation = "vertical",
  forceMount,
  asChild,
  className,
  ...props
}: FileUploadListProps) {
  const upload = useFileUpload()
  const Comp = asChild ? Slot.Root : "div"

  if (!forceMount && upload.value.length === 0) {
    return null
  }

  return (
    <Comp
      role="list"
      data-slot="file-upload-list"
      data-orientation={orientation}
      data-state={upload.value.length > 0 ? "active" : "inactive"}
      className={cn(
        "grid gap-2 data-[orientation=horizontal]:flex data-[orientation=horizontal]:flex-wrap",
        className
      )}
      {...props}
    />
  )
}

type FileUploadItemProps = React.ComponentProps<"div"> & {
  value: File
  asChild?: boolean
}

function FileUploadItem({ value, asChild, className, ...props }: FileUploadItemProps) {
  const Comp = asChild ? Slot.Root : "div"

  return (
    <FileUploadItemContext.Provider value={{ value }}>
      <Comp
        role="listitem"
        data-slot="file-upload-item"
        className={cn(
          "flex items-center gap-3 rounded-lg border bg-background p-2 text-sm",
          className
        )}
        {...props}
      />
    </FileUploadItemContext.Provider>
  )
}

type FileUploadItemPreviewProps = React.ComponentProps<"div"> & {
  asChild?: boolean
}

function FileUploadItemPreview({
  asChild,
  className,
  ...props
}: FileUploadItemPreviewProps) {
  const { value } = useFileUploadItem()
  const Comp = asChild ? Slot.Root : "div"

  return (
    <Comp
      data-slot="file-upload-item-preview"
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground",
        className
      )}
      {...props}
    >
      {value.type.startsWith("image/") ? (
        <img
          src={URL.createObjectURL(value)}
          alt=""
          className="size-full rounded-md object-cover"
        />
      ) : (
        <FileText className="size-4" />
      )}
    </Comp>
  )
}

type FileUploadItemMetadataProps = React.ComponentProps<"div"> & {
  size?: "default" | "sm"
  asChild?: boolean
}

function FileUploadItemMetadata({
  size = "default",
  asChild,
  className,
  ...props
}: FileUploadItemMetadataProps) {
  const { value } = useFileUploadItem()
  const Comp = asChild ? Slot.Root : "div"

  return (
    <Comp
      data-slot="file-upload-item-metadata"
      data-size={size}
      className={cn("min-w-0 flex-1", className)}
      {...props}
    >
      <p className="truncate font-medium">{value.name}</p>
      <p className="text-xs text-muted-foreground">{formatBytes(value.size)}</p>
    </Comp>
  )
}

type FileUploadItemProgressProps = React.ComponentProps<"div"> & {
  variant?: "linear" | "circular"
  size?: "default" | "sm"
  forceMount?: boolean
  asChild?: boolean
}

function FileUploadItemProgress({
  forceMount,
  asChild,
  className,
  ...props
}: FileUploadItemProgressProps) {
  const Comp = asChild ? Slot.Root : "div"

  if (!forceMount) {
    return null
  }

  return (
    <Comp
      data-slot="file-upload-item-progress"
      className={cn("h-1 rounded-full bg-muted", className)}
      {...props}
    />
  )
}

type FileUploadItemDeleteProps = React.ComponentProps<"button"> & {
  asChild?: boolean
}

function FileUploadItemDelete({
  asChild,
  className,
  onClick,
  children,
  ...props
}: FileUploadItemDeleteProps) {
  const upload = useFileUpload()
  const { value } = useFileUploadItem()
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      type="button"
      data-slot="file-upload-item-delete"
      className={cn(
        "inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className
      )}
      onClick={(event) => {
        onClick?.(event)
        upload.removeFile(value)
      }}
      {...props}
    >
      {children ?? <Trash2 className="size-4" />}
    </Comp>
  )
}

type FileUploadClearProps = React.ComponentProps<"button"> & {
  forceMount?: boolean
  asChild?: boolean
}

function FileUploadClear({
  forceMount,
  asChild,
  className,
  onClick,
  children,
  ...props
}: FileUploadClearProps) {
  const upload = useFileUpload()
  const Comp = asChild ? Slot.Root : "button"

  if (!forceMount && upload.value.length === 0) {
    return null
  }

  return (
    <Comp
      type="button"
      data-slot="file-upload-clear"
      data-disabled={upload.disabled ? "" : undefined}
      className={cn(
        "inline-flex h-8 w-fit items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      onClick={(event) => {
        onClick?.(event)
        upload.clearFiles()
      }}
      {...props}
    >
      {children ?? (
        <>
          <X className="size-4" />
          Clear
        </>
      )}
    </Comp>
  )
}

export {
  FileUpload,
  FileUploadDropzone,
  FileUploadTrigger,
  FileUploadList,
  FileUploadItem,
  FileUploadItemPreview,
  FileUploadItemMetadata,
  FileUploadItemProgress,
  FileUploadItemDelete,
  FileUploadClear,
}
