import { useState, useEffect } from 'react'
import { getUsers, createUser, updateUserRole } from '../api/auth'
import { UserPlus, ShieldAlert, Check, X, Shield, ShieldCheck, User } from 'lucide-react'

export default function UserManager() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'user'
  })

  const fetchUsers = async () => {
    try {
      const { data } = await getUsers()
      setUsers(data)
    } catch (err) {
      console.error("Failed to fetch users:", err)
      setError("Failed to load users.")
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await createUser(form)
      setSuccess(`User ${form.username} created successfully!`)
      setForm({ username: '', email: '', password: '', role: 'user' })
      fetchUsers()
    } catch (err) {
      const detail = err.response?.data?.detail
      let msg = "Failed to create user."
      if (typeof detail === 'string') {
        msg = detail
      } else if (Array.isArray(detail)) {
        msg = detail.map(d => `${d.loc[1]}: ${d.msg}`).join(', ')
      } else if (err.response?.data?.message) {
        msg = err.response.data.message
      }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleRoleChange = async (userId, newRole) => {
    try {
      await updateUserRole(userId, newRole)
      setSuccess(`Role updated to ${newRole}`)
      fetchUsers()
    } catch (err) {
      setError("Failed to update role.")
    }
  }

  const roleColors = {
    admin: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
    analyst: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    user: 'text-slate-400 bg-slate-400/10 border-slate-400/20'
  }

  const RoleIcon = ({ role }) => {
    if (role === 'admin') return <ShieldAlert size={14} className="mr-1" />
    if (role === 'analyst') return <ShieldCheck size={14} className="mr-1" />
    return <User size={14} className="mr-1" />
  }

  return (
    <div className="space-y-6">
      {/* Messages */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded flex items-center gap-2">
          <X size={18} /> {error}
        </div>
      )}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded flex items-center gap-2">
          <Check size={18} /> {success}
        </div>
      )}

      {/* Add User Form */}
      <div className="bg-surface-700/50 p-4 rounded-lg border border-surface-600">
        <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
          <UserPlus size={16} className="text-brand-400" />
          Provision New User
        </h4>
        <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input 
            type="text" required placeholder="Username"
            className="input-field bg-surface-800"
            value={form.username}
            onChange={e => setForm({...form, username: e.target.value})}
          />
          <input 
            type="email" required placeholder="Email"
            className="input-field bg-surface-800"
            value={form.email}
            onChange={e => setForm({...form, email: e.target.value})}
          />
          <input 
            type="password" required placeholder="Password"
            className="input-field bg-surface-800"
            value={form.password}
            onChange={e => setForm({...form, password: e.target.value})}
          />
          <select 
            className="input-field bg-surface-800"
            value={form.role}
            onChange={e => setForm({...form, role: e.target.value})}
          >
            <option value="user">User</option>
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Creating...' : 'Create Account'}
          </button>
        </form>
      </div>

      {/* User List */}
      <div className="rounded border border-surface-600 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-700 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Current Role</th>
              <th className="px-4 py-3 font-medium text-right">Assign Role</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-600">
            {users.map(u => (
              <tr key={u.id} className="hover:bg-surface-700/30">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-brand-500/20 to-purple-500/20 border border-brand-500/30 flex items-center justify-center text-xs font-bold text-white">
                      {u.username[0].toUpperCase()}
                    </div>
                    <span className="text-white font-medium">{u.username}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-400">{u.email}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${roleColors[u.role]}`}>
                    <RoleIcon role={u.role} />
                    <span className="capitalize">{u.role}</span>
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <select 
                    className="input-field bg-surface-800 py-1 text-xs w-32 ml-auto"
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  >
                    <option value="user">User</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
