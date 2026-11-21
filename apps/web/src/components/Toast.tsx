import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import SwipeToast from './rb/SwipeToast/SwipeToast'

interface ToastState { id: number; title: string; description?: string }
const ToastContext = createContext<(title: string, description?: string) => void>(() => {})

/** Confirmation toasts (React Bits SwipeToast): swipe down or wait to dismiss. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null)
  const show = useCallback((title: string, description?: string) => setToast({ id: Date.now(), title, description }), [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <SwipeToast
          key={toast.id}
          open
          title={toast.title}
          description={toast.description}
          duration={2800}
          background="var(--ink)"
          color="var(--paper)"
          fuseColor="var(--avocado)"
          radius={14}
          onClose={() => setToast((t) => (t?.id === toast.id ? null : t))}
        />
      )}
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
