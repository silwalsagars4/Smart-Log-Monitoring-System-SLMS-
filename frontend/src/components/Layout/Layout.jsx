import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ children, onRefresh }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onRefresh={onRefresh} />
        <main className="flex-1 overflow-y-auto p-6 animate-fade-in">
          {children}
        </main>
      </div>
    </div>
  )
}
