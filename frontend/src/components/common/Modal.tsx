import { X } from 'lucide-react'
import type { ReactNode } from 'react'

interface ModalProps {
  /** Whether the modal is visible. Caller still owns the source of truth. */
  open: boolean
  /** Called when the user requests close (X button, scrim click, future Escape). */
  onClose: () => void
  /** Panel body — caller provides header/form/footer/list markup. */
  children: ReactNode
  /** Panel max-width. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg'
  /** Extra classes appended to the PANEL div (padding, overflow, max-height, flex layout). Never the scrim. */
  className?: string
}

const SIZE_CLASS = {
  sm: 'max-w-sm',   // 384px
  md: 'max-w-lg',   // 512px
  lg: 'max-w-2xl',  // 672px
} as const

export default function Modal({
  open,
  onClose,
  children,
  size = 'md',
  className = '',
}: ModalProps) {
  if (!open) return null

  return (
    <>
      {/* Backdrop — fixed sibling BELOW the panel. Click dismisses. */}
      <div
        className="fixed inset-0 z-modal-backdrop bg-scrim backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel wrapper — centers the panel, sits ABOVE the backdrop. Mobile: bottom sheet. */}
      <div className="fixed inset-0 z-modal flex items-center justify-center p-4 max-sm:items-end max-sm:p-0">
        <div
          className={`relative bg-surface border border-border rounded-sm w-full ${SIZE_CLASS[size]} ${className} max-sm:rounded-t-sm max-sm:rounded-b-none max-sm:max-h-[92dvh] max-sm:overflow-y-auto`}
        >
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-4 top-4 -mr-1 flex items-center justify-center p-1 rounded-none text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
          >
            <X size={14} strokeWidth={1.5} />
          </button>

          {children}
        </div>
      </div>
    </>
  )
}
