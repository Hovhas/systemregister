import { useId } from "react"

interface FormFieldProps {
  label: string
  required?: boolean
  error?: string
  helpText?: string
  children: React.ReactNode | ((id: string) => React.ReactNode)
}

export function FormField({ label, required, error, helpText, children }: FormFieldProps) {
  const id = useId()
  const errorId = `${id}-error`
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium leading-none">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </label>
      {typeof children === "function" ? children(id) : children}
      {helpText && !error && (
        <p className="text-xs text-muted-foreground leading-relaxed">{helpText}</p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-destructive flex items-center gap-1" role="alert">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="size-3 shrink-0">
            <path fillRule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14Zm.75-10.25a.75.75 0 0 0-1.5 0v4.5a.75.75 0 0 0 1.5 0v-4.5ZM8 12a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  )
}
