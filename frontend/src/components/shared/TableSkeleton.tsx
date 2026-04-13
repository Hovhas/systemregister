import { TableRow, TableCell } from "@/components/ui/table"

interface Props {
  columns: number
  rows?: number
}

export function TableSkeleton({ columns, rows = 8 }: Props) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: columns }).map((_, j) => (
            <TableCell key={j}>
              <div className="skeleton h-4 w-full max-w-[120px]" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
