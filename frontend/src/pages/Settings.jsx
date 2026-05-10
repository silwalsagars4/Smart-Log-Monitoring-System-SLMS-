import Layout from '../components/Layout/Layout'
import { useAuth } from '../contexts/AuthContext'
import { useState } from 'react'
import { Settings as SettingsIcon, User, Shield, Bell, Database, Cpu, HardDrive, Users } from 'lucide-react'
import LogConfigManager from '../components/LogConfigManager'
import UserManager from '../components/UserManager'

function Section({ title, icon: Icon, children }) {
  return (
    <div className="card backdrop-blur-md bg-surface-800/60 border border-surface-600/50 shadow-xl">
      <div className="card-header border-b border-surface-600/50 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-brand-400" />
          <h3 className="text-sm font-semibold text-white">{title}</h3>
        </div>
      </div>
      {children}
    </div>
  )
}

function SettingRow({ label, value, description }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-surface-600/50 last:border-0">
      <div>
        <p className="text-sm text-white">{label}</p>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
      <span className="text-xs font-mono text-slate-300 bg-surface-700/80 px-2 py-1 rounded">{value}</span>
    </div>
  )
}

export default function Settings() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('account')

  const tabs = [
    { id: 'account', label: 'Account & Security', icon: Shield },
    ...(user?.role === 'admin' ? [{ id: 'users', label: 'User Management', icon: Users }] : []),
    ...(user?.role === 'admin' ? [{ id: 'sources', label: 'Log Sources', icon: HardDrive }] : []),
    { id: 'system', label: 'System & ML', icon: Cpu },
  ]

  return (
    <Layout>
      <div className="p-6">
        <div className="max-w-6xl mx-auto space-y-6">



          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-surface-800/50 p-1 rounded-lg border border-surface-600/50">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all duration-200 flex-1 justify-center
                  ${activeTab === tab.id
                      ? 'bg-surface-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-surface-700/50'}`}
                >
                  <Icon size={16} /> {tab.label}
                </button>
              )
            })}
          </div>

          {/* Tab Content */}
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            {activeTab === 'account' && (
              <div className="space-y-4">
                <Section title="Account Profile" icon={User}>
                  <SettingRow label="Username" value={user?.username} />
                  <SettingRow label="Role" value={user?.role} description="Your access level in the system" />
                </Section>
                <Section title="Security Policies" icon={Shield}>
                  <SettingRow label="Authentication" value="JWT" description="Token-based auth with 60-minute expiry" />
                  <SettingRow label="Rate Limiting" value="Enabled" description="1,000 req/min on logs endpoint" />
                  <SettingRow label="Role-Based Access" value="Admin / Analyst / User" description="Tiered access model" />
                </Section>
              </div>
            )}

            {activeTab === 'users' && user?.role === 'admin' && (
              <Section title="Role-Based Access Control" icon={Users}>
                <UserManager />
              </Section>
            )}

            {activeTab === 'sources' && user?.role === 'admin' && (
              <Section title="Dynamic Log Sources" icon={HardDrive}>
                <p className="text-xs text-slate-400 mb-4">
                  Configure log paths for agents to tail dynamically. The backend automatically translates host paths for the Docker container.
                </p>
                <LogConfigManager />
              </Section>
            )}

            {activeTab === 'system' && (
              <div className="space-y-4">
                <Section title="ML Engine (Phase 1.1)" icon={Cpu}>
                  <SettingRow label="Algorithm" value="Ensemble (IF + LOF + SVM)" description="Multi-model unsupervised anomaly detection" />
                  <SettingRow label="Contamination" value="5%" description="Expected anomaly fraction in training data" />
                  <SettingRow label="Retrain Interval" value="Every 6 hours" description="Model automatically retrains on accumulated logs" />
                  <SettingRow label="Feature Window" value="5 minutes" description="Sliding window for event frequency features" />
                </Section>
                <Section title="Notifications" icon={Bell}>
                  <SettingRow label="Email Alerts" value={import.meta.env.VITE_ENABLE_EMAIL || "Configure in .env"} description="Triggered on High and Disaster severity" />
                  <SettingRow label="Telegram Bot" value="Configure TELEGRAM_BOT_TOKEN" description="Set ENABLE_TELEGRAM=true in .env" />
                </Section>
                <Section title="Data Stores" icon={Database}>
                  <SettingRow label="Log Storage" value="MongoDB" description="All parsed log documents" />
                  <SettingRow label="Users & Alerts" value="PostgreSQL" description="Relational structured data" />
                  <SettingRow label="Pipeline Queue" value="Redis Streams" description="Message queue between agents and backend" />
                </Section>
                <div className="card border-brand-500/30 bg-gradient-to-br from-brand-500/10 to-transparent p-4">
                  <p className="text-xs text-slate-400 leading-relaxed flex justify-between items-center">
                    <span>
                      <strong className="text-brand-300">SLMS v1.1.0</strong> — Smart Log Monitoring System.
                      Configuration is managed via environment variables.
                    </span>
                    <span className="text-brand-400 font-mono bg-brand-400/10 px-2 py-1 rounded">/api/docs</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
