import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ children, onRefresh, rightSidebar }) {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onRefresh={onRefresh} />
        <div className="flex-1 flex overflow-hidden">
          <main className="flex-1 overflow-y-auto animate-fade-in">
            {children}
          </main>
          {rightSidebar && (
            <aside className="hidden xl:block w-80 flex-shrink-0 bg-surface-900">
              {rightSidebar}
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}
