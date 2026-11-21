import { Outlet } from 'react-router-dom'
import { AuthProvider } from './auth'
import { ToastProvider } from './components/Toast'

/** Everything under /app: creates or restores this device's account first. */
export function AppRoot() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Outlet />
      </ToastProvider>
    </AuthProvider>
  )
}
