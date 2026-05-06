import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { API, apiFetch } from '../config.js'

const isElectron = !!window.electron?.isElectron

function formatBytes(bytes) {
  if (!bytes) return '0 MB'
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(0)} MB`
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`
  return `${bytes} B`
}

function formatDate(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function friendlyPath(file) {
  if (file.source === 'gdrive:school') return `Google Drive/School/${file.name}`
  if (file.source === 'gdrive:personal') return `Google Drive/Personal/${file.name}`
  return file.path ? file.path.replace(/^\/Users\/[^/]+/, '~') : file.name
}

function sourceLabel(source) {
  if (!source || source === 'local') return 'My Computer'
  if (source === 'gdrive:school') return 'School Drive'
  if (source === 'gdrive:personal') return 'Personal Drive'
  return source
}

function fileIcon(name, size = 'md') {
  const ext = (name || '').split('.').pop().toLowerCase()
  const cls = size === 'lg' ? 'w-8 h-8' : 'w-5 h-5'
  if (ext === 'pdf') return (
    <svg className={`${cls} text-red-400 shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
  if (['jpg','jpeg','png','heic','gif','webp'].includes(ext)) return (
    <svg className={`${cls} text-purple-400 shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
  if (['xls','xlsx'].includes(ext)) return (
    <svg className={`${cls} text-green-400 shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
  return (
    <svg className={`${cls} text-blue-400 shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

function sourceIcon(source) {
  if (!source || source === 'local') return (
    <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  )
  return (
    <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
    </svg>
  )
}

export default function Duplicates() {
  const navigate = useNavigate()
  const [groups, setGroups] = useState([])
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(true)
  const [totalWasted, setTotalWasted] = useState(0)
  const [sources, setSources] = useState(() => {
    const opts = [{ label: 'All', value: '' }]
    if (isElectron) opts.push({ label: 'My Computer', value: 'local' })
    return opts
  })

  useEffect(() => {
    async function loadAccounts() {
      try {
        const res = await apiFetch(`${API}/drive/accounts`)
        const data = await res.json()
        const accounts = data.accounts || []
        const opts = [{ label: 'All', value: '' }]
        if (isElectron) opts.push({ label: 'My Computer', value: 'local' })
        if (accounts.includes('school')) opts.push({ label: 'School Drive', value: 'gdrive:school' })
        if (accounts.includes('personal')) opts.push({ label: 'Personal Drive', value: 'gdrive:personal' })
        setSources(opts)
      } catch {}
    }
    loadAccounts()
  }, [])

  useEffect(() => {
    load()
  }, [source])

  async function load() {
    setLoading(true)
    try {
      const url = source
        ? `${API}/report/duplicates?source=${source}`
        : `${API}/report/duplicates`
      const res = await apiFetch(url)
      const data = await res.json()
      setGroups(data)
      setTotalWasted(data.reduce((sum, g) => sum + g.space_wasted_bytes, 0))
    } catch {}
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-[#E8EBF8] p-6">
      <div className="bg-white rounded-3xl shadow-sm w-full max-w-3xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-1 text-gray-500 hover:text-gray-800 transition-colors text-sm font-medium"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>
            <h1 className="text-xl font-bold text-gray-900">Duplicates</h1>
            {totalWasted > 0 && (
              <span className="text-sm text-gray-400">· {formatBytes(totalWasted)} wasted</span>
            )}
          </div>

          <div className="relative">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="appearance-none border border-gray-200 rounded-xl px-4 py-2 pr-8 text-sm text-gray-700 bg-white focus:outline-none focus:border-blue-400 cursor-pointer"
            >
              {sources.map((s) => (
                <option key={s.value} value={s.value}>Filter: {s.label}</option>
              ))}
            </select>
            <svg className="w-4 h-4 text-gray-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="px-6 py-12 text-center text-gray-400 text-sm">Loading...</div>
        ) : groups.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-gray-400 text-sm">No duplicates found. Your files are clean!</p>
          </div>
        ) : (
          <ul>
            {groups.map((group, i) => (
              <DuplicateGroup
                key={i}
                group={group}
                isLast={i === groups.length - 1}
                onDeleted={load}
              />
            ))}
          </ul>
        )}

      </div>
    </div>
  )
}

function DuplicateGroup({ group, isLast, onDeleted }) {
  const [deleting, setDeleting] = useState(null)

  async function handleDelete(file) {
    setDeleting(file.path)
    try {
      await apiFetch(`${API}/staging/stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: file.path, source: file.source }),
      })
      onDeleted()
    } catch {
      setDeleting(null)
    }
  }

  return (
    <li className={!isLast ? 'border-b border-gray-100' : ''}>
      {/* Group header */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          {fileIcon(group.name, 'lg')}
          <div>
            <p className="font-semibold text-gray-900">{group.name}</p>
            <p className="text-sm text-gray-400">{group.copies} copies · {formatBytes(group.size_bytes)}</p>
          </div>
        </div>
        <span className="text-sm text-gray-400 whitespace-nowrap">Space wasted: {formatBytes(group.space_wasted_bytes)}</span>
      </div>

      {/* Individual copies */}
      <ul>
        {group.files.map((file, j) => (
          <li
            key={j}
            className="flex items-center justify-between px-6 py-3 border-t border-gray-100 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              {sourceIcon(file.source)}
              <div className="min-w-0">
                {file.web_view_link ? (
                  <a
                    href={file.web_view_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline truncate block transition-colors"
                  >
                    {friendlyPath(file)}
                  </a>
                ) : (
                  <p className="text-sm text-gray-700 truncate">{friendlyPath(file)}</p>
                )}
                {file.modified_at && (
                  <p className="text-xs text-gray-400">Modified: {formatDate(file.modified_at)}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0 ml-4">
              <span className="text-sm text-gray-500 whitespace-nowrap">{sourceLabel(file.source)}</span>
              {j > 0 && file.web_view_link && (
                <a
                  href={file.web_view_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-500 hover:text-blue-700 font-medium transition-colors whitespace-nowrap"
                >
                  Review & Delete
                </a>
              )}
              {j > 0 && !file.web_view_link && (
                <button
                  onClick={() => handleDelete(file)}
                  disabled={deleting === file.path}
                  className="text-xs text-red-400 hover:text-red-600 font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
                >
                  {deleting === file.path ? 'Removing…' : 'Remove'}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </li>
  )
}
