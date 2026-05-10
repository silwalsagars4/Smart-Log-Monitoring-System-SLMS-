import { useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ children, onRefresh, rightSidebar }) {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header 
          onRefresh={onRefresh} 
        />
        <div className="flex-1 flex overflow-hidden relative">
          <main className="flex-1 overflow-y-auto animate-fade-in no-scrollbar">
            {/* On small screens, show the right sidebar content at the top of the main area */}
            {rightSidebar && (
              <div className="xl:hidden border-b border-surface-700/50 bg-surface-900/50">
                {rightSidebar}
              </div>
            )}
            <div className="max-w-full overflow-x-hidden">
              {children}
            </div>
          </main>
          
          {rightSidebar && (
            <aside className="hidden xl:block w-80 flex-shrink-0 bg-surface-900 border-l border-surface-700/50">
              {rightSidebar}
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}
