import { useState, useEffect } from 'react'
import { getLogConfigs, createLogConfig, deleteLogConfig } from '../api/config'
import { Plus, Trash2, CheckCircle, XCircle } from 'lucide-react'

export default function LogConfigManager() {
  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ label: '', log_path: '', collector_type: 'generic' })

  const fetchConfigs = async () => {
    try {
      const { data } = await getLogConfigs()
      setConfigs(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchConfigs()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await createLogConfig(form)
      setForm({ label: '', log_path: '', collector_type: 'generic' })
      fetchConfigs()
    } catch (e) {
      const detail = e.response?.data?.detail
      let msg = "Failed to create config."
      if (typeof detail === 'string') msg = detail
      else if (Array.isArray(detail)) msg = detail.map(d => `${d.loc[1]}: ${d.msg}`).join(', ')
      alert('Failed to create config: ' + msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure?')) return
    setLoading(true)
    try {
      await deleteLogConfig(id)
      fetchConfigs()
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-2 flex-col sm:flex-row">
        <input 
          required 
          className="input-field bg-surface-700 flex-1" 
          placeholder="Label (e.g. Auth Logs)" 
          value={form.label} 
          onChange={e => setForm({...form, label: e.target.value})} 
        />
        <input 
          required 
          className="input-field bg-surface-700 flex-1 font-mono text-sm" 
          placeholder="/var/log/auth.log" 
          value={form.log_path} 
          onChange={e => setForm({...form, log_path: e.target.value})} 
        />
        <select 
          className="input-field bg-surface-700 w-full sm:w-32" 
          value={form.collector_type} 
          onChange={e => setForm({...form, collector_type: e.target.value})}
        >
          <option value="generic">generic</option>
          <option value="ssh">ssh</option>
          <option value="nginx">nginx</option>
          <option value="apache">apache</option>
          <option value="docker">docker</option>
          <option value="mysql">mysql</option>
        </select>
        <button type="submit" disabled={loading} className="btn-primary flex items-center justify-center gap-1">
          <Plus size={16} /> Add
        </button>
      </form>

      <div className="rounded border border-surface-600 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-700 text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">Label</th>
              <th className="px-3 py-2 font-medium">Path</th>
              <th className="px-3 py-2 font-medium">Parser</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-600">
            {configs.length === 0 && (
              <tr><td colSpan={5} className="px-3 py-4 text-center text-slate-500">No dynamic sources configured.</td></tr>
            )}
            {configs.map(c => (
              <tr key={c.id} className="hover:bg-surface-700/30">
                <td className="px-3 py-2 text-white">{c.label}</td>
                <td className="px-3 py-2 font-mono text-xs text-brand-300">{c.log_path}</td>
                <td className="px-3 py-2">
                  <span className="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-xs">
                    {c.collector_type}
                  </span>
                </td>
                <td className="px-3 py-2">
                  {c.is_active ? 
                    <span className="text-emerald-400 flex items-center gap-1 text-xs"><CheckCircle size={12}/> Active</span> : 
                    <span className="text-red-400 flex items-center gap-1 text-xs"><XCircle size={12}/> Disabled</span>
                  }
                </td>
                <td className="px-3 py-2 text-right">
                  <button 
                    onClick={() => handleDelete(c.id)}
                    disabled={loading || !c.is_active}
                    className="text-slate-500 hover:text-red-400 disabled:opacity-50"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
