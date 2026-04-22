import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout/Layout'
import LogTable from '../components/LogTable'
import { getLogs } from '../api/logs'
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'

const SOURCES = ['', 'ssh', 'nginx', 'apache', 'docker', 'mysql']
const SEVERITIES = ['', 'information', 'warning', 'medium', 'high', 'disaster']

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    source: '', severity: '', search: '', is_anomaly: '',
  })

  const pageSize = 50
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize }
      if (filters.source) params.source = filters.source
      if (filters.severity) params.severity = filters.severity
      if (filters.search) params.search = filters.search
      if (filters.is_anomaly !== '') params.is_anomaly = filters.is_anomaly === 'true'
      const { data } = await getLogs(params)
      setLogs(data.data)
      setTotal(data.total)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  // Reset to page 1 on filter change
  const handleFilterChange = (key, val) => {
    setPage(1)
    setFilters((f) => ({ ...f, [key]: val }))
  }

  return (
    <Layout onRefresh={fetchLogs}>
      <div className="space-y-4 max-w-screen-2xl">
        {/* Filter bar */}
        <div className="card py-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                id="log-search"
                type="text"
                placeholder="Search message, IP, user…"
                className="input pl-9 text-sm"
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>

            <select
              id="filter-source"
              value={filters.source}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="input w-36"
            >
              {SOURCES.map((s) => (
                <option key={s} value={s}>{s || 'All sources'}</option>
              ))}
            </select>

            <select
              id="filter-severity"
              value={filters.severity}
              onChange={(e) => handleFilterChange('severity', e.target.value)}
              className="input w-36"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s} className="capitalize">{s || 'All severities'}</option>
              ))}
            </select>

            <select
              id="filter-anomaly"
              value={filters.is_anomaly}
              onChange={(e) => handleFilterChange('is_anomaly', e.target.value)}
              className="input w-36"
            >
              <option value="">All logs</option>
              <option value="true">Anomalies only</option>
              <option value="false">Normal only</option>
            </select>

            <div className="ml-auto text-xs text-slate-500">
              {total.toLocaleString()} logs
            </div>
          </div>
        </div>

        {/* Table */}
        <LogTable logs={logs} loading={loading} />

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Page {page} of {totalPages} · {total.toLocaleString()} total
          </p>
          <div className="flex items-center gap-2">
            <button
              id="prev-page"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost p-2 rounded-lg disabled:opacity-40"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm text-slate-400 w-12 text-center">{page}</span>
            <button
              id="next-page"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-ghost p-2 rounded-lg disabled:opacity-40"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
