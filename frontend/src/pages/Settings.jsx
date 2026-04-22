import Layout from '../components/Layout/Layout'
import { useAuth } from '../contexts/AuthContext'
import { Settings as SettingsIcon, User, Shield, Bell, Database, Cpu } from 'lucide-react'

function Section({ title, icon: Icon, children }) {
  return (
    <div className="card">
      <div className="card-header border-b border-surface-600 pb-3 mb-4">
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
    <div className="flex items-start justify-between py-3 border-b border-surface-600 last:border-0">
      <div>
        <p className="text-sm text-white">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <span className="text-xs font-mono text-slate-400 bg-surface-700 px-2 py-1 rounded">{value}</span>
    </div>
  )
}

export default function Settings() {
  const { user } = useAuth()

  return (
    <Layout>
      <div className="max-w-2xl space-y-4">
        <Section title="Account" icon={User}>
          <SettingRow label="Username" value={user?.username} />
          <SettingRow label="Role" value={user?.role} description="Your access level in the system" />
        </Section>

        <Section title="Security" icon={Shield}>
          <SettingRow
            label="Authentication"
            value="JWT"
            description="Token-based auth with 60-minute expiry"
          />
          <SettingRow
            label="Rate Limiting"
            value="Enabled"
            description="1,000 req/min on logs endpoint"
          />
          <SettingRow
            label="Role-Based Access"
            value="Admin / User"
            description="Admins can delete alerts"
          />
        </Section>

        <Section title="Notifications" icon={Bell}>
          <SettingRow
            label="Email Alerts"
            value={import.meta.env.VITE_ENABLE_EMAIL || "Configure in .env"}
            description="Triggered on High and Disaster severity"
          />
          <SettingRow
            label="Telegram Bot"
            value="Configure TELEGRAM_BOT_TOKEN"
            description="Set ENABLE_TELEGRAM=true in .env"
          />
        </Section>

        <Section title="ML Engine" icon={Cpu}>
          <SettingRow
            label="Algorithm"
            value="Isolation Forest"
            description="Scikit-learn unsupervised anomaly detection"
          />
          <SettingRow
            label="Contamination"
            value="5%"
            description="Expected anomaly fraction in training data"
          />
          <SettingRow
            label="Retrain Interval"
            value="Every 6 hours"
            description="Model automatically retrains on accumulated logs"
          />
          <SettingRow
            label="Feature Window"
            value="5 minutes"
            description="Sliding window for event frequency features"
          />
        </Section>

        <Section title="Data Stores" icon={Database}>
          <SettingRow label="Log Storage" value="MongoDB" description="All parsed log documents" />
          <SettingRow label="Users & Alerts" value="PostgreSQL" description="Relational structured data" />
          <SettingRow label="Pipeline Queue" value="Redis Streams" description="Message queue between agents and backend" />
        </Section>

        <div className="card border-brand-500/20 bg-gradient-to-br from-brand-500/5 to-transparent">
          <p className="text-xs text-slate-500 leading-relaxed">
            <strong className="text-slate-300">SLMS v1.0.0</strong> — Smart Log Monitoring System.
            Configuration is managed via environment variables (.env file).
            See <span className="text-brand-400 font-mono">/api/docs</span> for the full API reference.
          </p>
        </div>
      </div>
    </Layout>
  )
}
