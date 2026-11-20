import * as DialogPrimitive from '@radix-ui/react-dialog'
import { cva, type VariantProps } from 'class-variance-authority'
import { X } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-emerald-500 text-slate-950 hover:bg-emerald-400',
        secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 border border-slate-700',
        ghost: 'text-slate-300 hover:bg-slate-800 hover:text-white',
        danger: 'bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20',
      },
      size: {
        sm: 'h-8 px-3',
        md: 'h-10 px-4',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

type ButtonProps = ComponentProps<'button'> & VariantProps<typeof buttonVariants>

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />
}

export function Card({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('rounded-xl border border-slate-800 bg-slate-900/60', className)} {...props} />
}

export function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('flex items-center justify-between gap-4 px-5 py-4 border-b border-slate-800', className)} {...props} />
}

export function CardTitle({ className, ...props }: ComponentProps<'h3'>) {
  return <h3 className={cn('text-sm font-semibold text-slate-100', className)} {...props} />
}

export function CardBody({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('p-5', className)} {...props} />
}

const badgeTone = {
  neutral: 'bg-slate-800 text-slate-300 border-slate-700',
  success: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  warning: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  danger: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  info: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
} as const

export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: keyof typeof badgeTone
  className?: string
  children: ReactNode
}) {
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium', badgeTone[tone], className)}>
      {children}
    </span>
  )
}

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-10 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-emerald-500/60 focus:outline-none focus:ring-2 focus:ring-emerald-500/20',
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, ...props }: ComponentProps<'select'>) {
  return (
    <select
      className={cn(
        'h-10 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 focus:border-emerald-500/60 focus:outline-none',
        className,
      )}
      {...props}
    />
  )
}

export function Label({ className, ...props }: ComponentProps<'label'>) {
  return <label className={cn('mb-1.5 block text-xs font-medium text-slate-400', className)} {...props} />
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export function Table({ className, ...props }: ComponentProps<'table'>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn('w-full text-left text-sm', className)} {...props} />
    </div>
  )
}

export function Th({ className, ...props }: ComponentProps<'th'>) {
  return <th className={cn('whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500', className)} {...props} />
}

export function Td({ className, ...props }: ComponentProps<'td'>) {
  return <td className={cn('px-4 py-3 text-slate-300', className)} {...props} />
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-100">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-slate-800', className)} />
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <p className="text-sm text-rose-300">{message}</p>
      {onRetry && <Button variant="secondary" size="sm" onClick={onRetry}>Try again</Button>}
    </div>
  )
}

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export function DialogContent({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm" />
      <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <DialogPrimitive.Title className="text-base font-semibold text-slate-100">{title}</DialogPrimitive.Title>
            {description && <DialogPrimitive.Description className="mt-1 text-sm text-slate-500">{description}</DialogPrimitive.Description>}
          </div>
          <DialogPrimitive.Close aria-label="Close" className="rounded-md p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-200">
            <X size={18} />
          </DialogPrimitive.Close>
        </div>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
