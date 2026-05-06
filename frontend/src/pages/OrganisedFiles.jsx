import { useState, useEffect, useRef } from 'react'
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

export default function OrganisedFiles() {
  const navigate = useNavigate()
  const [grouped, setGrouped] = useState({})
  const [source, setSource] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dragOver, setDragOver] = useState(null)
  const [sources, setSources] = useState(() => {
    const opts = [{ label: 'All', value: '' }]
    if (isElectron) opts.push({ label: 'My Computer', value: 'local' })
    return opts
  })
  const draggingFile = useRef(null)
  const draggingFromCat = useRef(null)

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
    async function load() {
      setLoading(true)
      try {
        const url = source
          ? `${API}/report/organised?source=${source}`
          : `${API}/report/organised`
        const res = await apiFetch(url)
        setGrouped(await res.json())
      } catch {}
      setLoading(false)
    }
    load()
  }, [source])

  async function handleDrop(targetCat) {
    const file = draggingFile.current
    const fromCat = draggingFromCat.current
    setDragOver(null)

    if (!file || !fromCat || fromCat === targetCat) return

    setGrouped((prev) => {
      const next = { ...prev }
      next[fromCat] = prev[fromCat].filter((f) => f.path !== file.path)
      next[targetCat] = [...(prev[targetCat] || []), { ...file, category: targetCat }]
      if (next[fromCat].length === 0) delete next[fromCat]
      return next
    })

    try {
      await apiFetch(`${API}/files/${encodeURIComponent(file.path)}/category`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: targetCat, source: file.source || 'local' }),
      })
    } catch {
      const url = source ? `${API}/report/organised?source=${source}` : `${API}/report/organised`
      const res = await apiFetch(url)
      setGrouped(await res.json())
    }

    draggingFile.current = null
    draggingFromCat.current = null
  }

  const SCHOOL_SUBJECTS = new Set([
    'math', 'biology', 'physics', 'english', 'history',
    'spanish', 'art', 'band', 'pe', 'science',
  ])

  const allCategories = Object.entries(grouped)
  const schoolCategories = allCategories.filter(([cat]) => SCHOOL_SUBJECTS.has(cat))
  const otherCategories = allCategories.filter(([cat]) => !SCHOOL_SUBJECTS.has(cat))

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
            <h1 className="text-xl font-bold text-gray-900">Organised Files</h1>
          </div>

          <div className="relative">
            <select
              value={source}
              onChange={(e) => { setSource(e.target.value); setExpanded(null) }}
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

        {/* Category list */}
        {loading ? (
          <div className="px-6 py-12 text-center text-gray-400 text-sm">Loading...</div>
        ) : allCategories.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400 text-sm">No files found.</div>
        ) : (
          <>
            {schoolCategories.length > 0 && (
              <>
                <p className="px-6 pt-5 pb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">School</p>
                <ul>
                  {schoolCategories.map(([cat, files], i) => (
                    <CategoryRow
                      key={cat}
                      cat={cat}
                      files={files}
                      isLast={i === schoolCategories.length - 1}
                      expanded={expanded}
                      setExpanded={setExpanded}
                      dragOver={dragOver}
                      setDragOver={setDragOver}
                      draggingFile={draggingFile}
                      draggingFromCat={draggingFromCat}
                      handleDrop={handleDrop}
                    />
                  ))}
                </ul>
              </>
            )}
            {otherCategories.length > 0 && (
              <>
                <p className="px-6 pt-5 pb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Personal</p>
                <ul>
                  {otherCategories.map(([cat, files], i) => (
                    <CategoryRow
                      key={cat}
                      cat={cat}
                      files={files}
                      isLast={i === otherCategories.length - 1}
                      expanded={expanded}
                      setExpanded={setExpanded}
                      dragOver={dragOver}
                      setDragOver={setDragOver}
                      draggingFile={draggingFile}
                      draggingFromCat={draggingFromCat}
                      handleDrop={handleDrop}
                    />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function CategoryRow({ cat, files, isLast, expanded, setExpanded, dragOver, setDragOver, draggingFile, draggingFromCat, handleDrop }) {
  const totalSize = files.reduce((sum, f) => sum + (f.size_bytes || 0), 0)
  const isExpanded = expanded === cat
  const isDragTarget = dragOver === cat

  return (
    <li
      onDragOver={(e) => { e.preventDefault(); setDragOver(cat) }}
      onDragLeave={() => setDragOver(null)}
      onDrop={() => handleDrop(cat)}
    >
      <button
        onClick={() => setExpanded(isExpanded ? null : cat)}
        className={`w-full flex items-center justify-between px-6 py-4 transition-colors
          ${isDragTarget ? 'bg-blue-50 border-l-4 border-blue-400' : 'hover:bg-gray-50'}
          ${!isLast && !isExpanded ? 'border-b border-gray-100' : ''}`}
      >
        <div className="flex items-center gap-3">
          <svg className={`w-6 h-6 shrink-0 ${isDragTarget ? 'text-blue-600' : 'text-blue-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
          </svg>
          <span className="font-medium text-gray-900 capitalize">{cat}</span>
          {isDragTarget && <span className="text-xs text-blue-500 font-medium">Drop here</span>}
        </div>
        <div className="flex items-center gap-6 text-gray-400 text-sm">
          <span>{files.length} file{files.length !== 1 ? 's' : ''}</span>
          <span>{formatBytes(totalSize)}</span>
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {isExpanded && (
        <ul className={!isLast ? 'border-b border-gray-100' : ''}>
          {files.map((file, j) => (
            <FileRow
              key={j}
              file={file}
              onDragStart={() => {
                draggingFile.current = file
                draggingFromCat.current = cat
              }}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (ext === 'pdf') return (
    <svg className="w-8 h-8 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
  if (['jpg', 'jpeg', 'png', 'heic', 'gif', 'webp'].includes(ext)) return (
    <svg className="w-8 h-8 text-purple-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
  return (
    <svg className="w-8 h-8 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

function friendlyPath(file) {
  if (file.source === 'gdrive:school') return `Google Drive/School/${file.name}`
  if (file.source === 'gdrive:personal') return `Google Drive/Personal/${file.name}`
  return file.path ? file.path.replace(/^\/Users\/[^/]+/, '~') : file.name
}

function FileRow({ file, onDragStart }) {
  const openFile = () => {
    if (file.web_view_link) window.open(file.web_view_link, '_blank')
  }

  return (
    <li
      draggable
      onDragStart={onDragStart}
      onClick={openFile}
      className={`flex items-center justify-between px-6 py-4 border-t border-gray-100 hover:bg-blue-50 transition-colors cursor-grab active:cursor-grabbing ${file.web_view_link ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-center gap-4 min-w-0">
        {fileIcon(file.name)}
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{file.name}</p>
          <p className="text-xs text-gray-400 truncate">{friendlyPath(file)}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0 ml-4">
        {file.duplicate_of && (
          <span className="text-xs bg-amber-50 text-amber-500 border border-amber-200 rounded-full px-2 py-0.5">duplicate</span>
        )}
        <span className="text-sm text-gray-400 whitespace-nowrap">{formatBytes(file.size_bytes)}</span>
        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </li>
  )
}
