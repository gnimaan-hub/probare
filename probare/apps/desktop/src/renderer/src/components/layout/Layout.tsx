import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { ToastContainer } from '../ui/ToastContainer'

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-secondary">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  )
}
