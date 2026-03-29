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
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </label>
      {typeof children === "function" ? children(id) : children}
      {helpText && !error && (
        <p className="text-xs text-muted-foreground">{helpText}</p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-destructive" role="alert">{error}</p>
      )}
    </div>
  )
}
