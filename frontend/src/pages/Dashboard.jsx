import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const API = 'http://localhost:8000'
const DEFAULT_FOLDERS = []

function formatBytes(bytes) {
  if (!bytes) return '0 MB'
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(0)} MB`
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`
  return `${bytes} B`
}

function timeSince(isoString) {
  if (!isoString) return null
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`
  return `${Math.floor(diff / 86400)} days ago`
}

const isElectron = !!window.electron?.isElectron

export default function Dashboard() {
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [showSettings, setShowSettings] = useState(false)
  const [scanning, setScanning] = useState(false)
  const lastScanned = localStorage.getItem('claire_last_scanned')

  useEffect(() => {
    fetchReport()
    fetchAccounts()
  }, [])

  async function fetchReport() {
    try {
      const res = await fetch(`${API}/report`)
      setReport(await res.json())
    } catch {}
  }

  async function fetchAccounts() {
    try {
      const res = await fetch(`${API}/drive/accounts`)
      const data = await res.json()
      setAccounts(data.accounts || [])
    } catch {}
  }

  async function handleScanNow() {
    setScanning(true)
    try {
      const jobs = []
      let folders
      try {
        const saved = localStorage.getItem('claire_folders')
        folders = saved ? JSON.parse(saved) : DEFAULT_FOLDERS
        if (!Array.isArray(folders)) folders = DEFAULT_FOLDERS
      } catch {
        folders = DEFAULT_FOLDERS
      }

      // Untrack folders removed since the last scan
      try {
        const prevSaved = localStorage.getItem('claire_last_scanned_folders')
        const prevFolders = prevSaved ? JSON.parse(prevSaved) : DEFAULT_FOLDERS
        const removed = prevFolders.filter((f) => !folders.includes(f))
        for (const f of removed) {
          await fetch(`${API}/untrack`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: f }),
          })
        }
      } catch {}
      localStorage.setItem('claire_last_scanned_folders', JSON.stringify(folders))

      for (const folder of folders) {
        const res = await fetch(`${API}/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder, source: 'local' }),
        })
        if (!res.ok) throw new Error(`Scan failed for ${folder}: ${res.status}`)
        const data = await res.json()
        jobs.push({ jobId: data.job_id, label: folder })
      }

      for (const account of accounts) {
        const res = await fetch(`${API}/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: `gdrive:${account}` }),
        })
        if (!res.ok) throw new Error(`Drive scan failed for ${account}: ${res.status}`)
        const data = await res.json()
        jobs.push({ jobId: data.job_id, label: `${account} Drive` })
      }

      localStorage.setItem('claire_last_scanned', new Date().toISOString())
      navigate('/scanning', { state: { jobs, folders } })
    } catch (err) {
      alert(`Could not start scan: ${err.message}\n\nMake sure the backend is running (declutter-api).`)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#E8EBF8] flex items-start justify-center p-8">
      <div className="w-full max-w-4xl flex flex-col gap-4">

      {/* Header */}
      <div className="bg-white rounded-2xl px-6 py-4 flex items-center justify-between shadow-sm">
        <h1 className="text-3xl font-extrabold text-gray-900">Claire</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={handleScanNow}
            disabled={scanning}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors"
          >
            {scanning ? 'Starting…' : 'Scan Now'}
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 border border-gray-200 hover:border-gray-300 text-gray-700 font-medium px-5 py-2.5 rounded-xl transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="bg-white rounded-2xl px-6 py-4 shadow-sm">
        {report ? (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-4 text-gray-700 text-base">
              <svg className="w-5 h-5 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="font-medium">{report.total_files} files</span>
              <span className="text-gray-200">|</span>
              <span>{formatBytes(report.total_size_bytes)}</span>
              <span className="text-gray-200">|</span>
              <span>{report.duplicates?.length ?? 0} duplicate{report.duplicates?.length !== 1 ? 's' : ''} found</span>
            </div>
            {lastScanned && (
              <p className="text-sm text-gray-400">Last scanned: {timeSince(lastScanned)}</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Loading stats...</p>
        )}
      </div>

      {/* Source cards */}
      <div className={`grid grid-cols-1 gap-4 ${isElectron ? 'md:grid-cols-3' : 'md:grid-cols-2'}`}>
        {isElectron && <SourceCard icon="computer" title="My Computer" source="local" />}
        <SourceCard icon="cloud" title="School Drive" source="gdrive:school" connected={accounts.includes('school')} />
        <SourceCard icon="cloud" title="Personal Drive" source="gdrive:personal" connected={accounts.includes('personal')} />
      </div>

      {/* AI Instincts */}
      <div className="bg-white rounded-2xl px-6 py-5 shadow-sm flex items-center gap-4">
        <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div>
          <p className="font-bold text-gray-900">AI Instincts</p>
          <p className="text-sm text-gray-400">Smart insights about your files — coming soon.</p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={() => navigate('/organised')}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 rounded-2xl transition-colors"
        >
          View Organised Files
        </button>
        <button
          onClick={() => navigate('/duplicates')}
          className="border-2 border-blue-600 text-blue-600 hover:bg-blue-50 font-semibold py-4 rounded-2xl transition-colors"
        >
          View Duplicates
        </button>
      </div>

      {/* Study Help */}
      <button
        disabled
        className="w-full bg-purple-50 border-2 border-purple-200 text-purple-400 font-semibold py-4 rounded-2xl cursor-not-allowed flex items-center justify-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        Study Help — coming soon
      </button>

      {showSettings && (
        <SettingsModal
          accounts={accounts}
          fetchAccounts={fetchAccounts}
          onClose={async (addedFolders = []) => {
            setShowSettings(false)
            if (addedFolders.length === 0) return
            const jobs = []
            for (const folder of addedFolders) {
              try {
                const res = await fetch(`${API}/scan`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ folder, source: 'local' }),
                })
                const data = await res.json()
                jobs.push({ jobId: data.job_id, label: folder })
              } catch {}
            }
            if (jobs.length > 0) {
              localStorage.setItem('claire_last_scanned', new Date().toISOString())
              navigate('/scanning', { state: { jobs, folders: addedFolders } })
            }
          }}
        />
      )}
      </div>
    </div>
  )
}

function SourceCard({ icon, title, source, connected }) {
  const [report, setReport] = useState(null)

  useEffect(() => {
    if (source !== 'local' && !connected) return
    async function load() {
      try {
        const res = await fetch(`${API}/report?source=${source}`)
        setReport(await res.json())
      } catch {}
    }
    load()
  }, [source, connected])

  const CloudIcon = () => (
    <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
    </svg>
  )

  const ComputerIcon = () => (
    <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  )

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {icon === 'computer' ? <ComputerIcon /> : <CloudIcon />}
        <span className="font-bold text-gray-900">{title}</span>
      </div>
      {source !== 'local' && !connected ? (
        <p className="text-sm text-gray-400">Not connected</p>
      ) : report ? (
        <>
          <p className="text-gray-700">{report.total_files} files</p>
          <p className="text-gray-700">{formatBytes(report.total_size_bytes)}</p>
          <p className="text-gray-700">{report.duplicates?.length ?? 0} dupe{report.duplicates?.length !== 1 ? 's' : ''}</p>
        </>
      ) : (
        <p className="text-sm text-gray-400">Loading...</p>
      )}
    </div>
  )
}

function SettingsModal({ accounts, fetchAccounts, onClose }) {
  const [connecting, setConnecting] = useState(null)
  const [autoScan, setAutoScan] = useState(localStorage.getItem('claire_auto_scan') === 'true')
  const [blacklist, setBlacklist] = useState([])
  const [newIgnored, setNewIgnored] = useState('')
  const [folders, setFolders] = useState(() => {
    try {
      const saved = localStorage.getItem('claire_folders')
      return saved ? JSON.parse(saved) : DEFAULT_FOLDERS
    } catch {
      return DEFAULT_FOLDERS
    }
  })
  const [initialFolders] = useState(() => {
    try {
      const saved = localStorage.getItem('claire_folders')
      return saved ? JSON.parse(saved) : DEFAULT_FOLDERS
    } catch {
      return DEFAULT_FOLDERS
    }
  })
  const [newFolder, setNewFolder] = useState('')
  const pollRef = useRef(null)

  function updateFolders(updated) {
    setFolders(updated)
    localStorage.setItem('claire_folders', JSON.stringify(updated))
  }

  async function handleRemoveFolder(path) {
    try {
      await fetch(`${API}/untrack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: path }),
      })
    } catch {}
    updateFolders(folders.filter((p) => p !== path))
  }

  function handleAddFolder() {
    const path = newFolder.trim()
    if (!path || folders.includes(path)) return
    updateFolders([...folders, path])
    setNewFolder('')
  }

  async function handleBrowseFolder() {
    const path = await window.electron.openFolderPicker()
    if (path && !folders.includes(path)) updateFolders([...folders, path])
  }

  useEffect(() => {
    fetchBlacklist()
    return () => clearInterval(pollRef.current)
  }, [])

  async function fetchBlacklist() {
    try {
      const res = await fetch(`${API}/blacklist`)
      const data = await res.json()
      setBlacklist(data.folders || [])
    } catch {}
  }

  async function handleAddIgnored() {
    const path = newIgnored.trim()
    if (!path) return
    try {
      await fetch(`${API}/blacklist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: path }),
      })
      setNewIgnored('')
      await fetchBlacklist()
    } catch {}
  }

  async function handleRemoveIgnored(path) {
    try {
      await fetch(`${API}/blacklist`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: path }),
      })
      await fetchBlacklist()
    } catch {}
  }

  async function handleConnect(accountName) {
    setConnecting(accountName)
    try {
      const res = await fetch(`${API}/drive/login/start/${accountName}`)
      const data = await res.json()
      const popup = window.open(data.auth_url, '_blank')
      pollRef.current = setInterval(async () => {
        await fetchAccounts()
        const closed = !popup || popup.closed
        if (closed) {
          clearInterval(pollRef.current)
          await fetchAccounts()
          setConnecting(null)
        }
      }, 2000)
    } catch {
      setConnecting(null)
    }
  }

  async function handleDisconnect(accountName) {
    await fetch(`${API}/drive/${accountName}`, { method: 'DELETE' })
    await fetchAccounts()
  }

  const shortPath = (p) => p.replace(/^\/Users\/[^/]+/, '~')

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-3xl w-full max-w-xl p-8 flex flex-col gap-6 max-h-[90vh] overflow-y-auto">

        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
          <button onClick={() => onClose(folders.filter(f => !initialFolders.includes(f)))} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <hr className="border-gray-100" />

        {/* Local Folders */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="font-bold text-gray-900">Local Folders</h3>
          </div>
          {folders.map((f) => (
            <div key={f} className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                </svg>
                <span className="text-sm text-gray-500">{f}</span>
              </div>
              <button
                onClick={() => handleRemoveFolder(f)}
                className="text-gray-300 hover:text-red-400 transition-colors ml-3 shrink-0"
              >
                ✕
              </button>
            </div>
          ))}
          {isElectron ? (
            <button
              onClick={handleBrowseFolder}
              className="w-full border border-dashed border-gray-300 hover:border-blue-400 rounded-xl px-4 py-3 text-sm text-gray-400 hover:text-blue-500 transition-colors text-left"
            >
              + Browse for folder…
            </button>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddFolder()}
                placeholder="~/Documents_DD"
                className="flex-1 border border-dashed border-gray-300 rounded-xl px-4 py-3 text-sm text-gray-500 focus:outline-none focus:border-blue-400"
              />
              <button
                onClick={handleAddFolder}
                disabled={!newFolder.trim()}
                className="rounded-xl px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors disabled:bg-gray-100 disabled:text-gray-300 bg-blue-600 hover:bg-blue-700 text-white"
              >
                + Add
              </button>
            </div>
          )}
        </div>

        <hr className="border-gray-100" />

        {/* Ignored Folders — blacklist */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            <h3 className="font-bold text-gray-900">Ignored Folders</h3>
          </div>

          {blacklist.length === 0 && (
            <p className="text-sm text-gray-400">No folders ignored yet.</p>
          )}

          {blacklist.map((f) => (
            <div key={f} className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
              <div className="flex items-center gap-2 text-gray-700 text-sm">
                <svg className="w-4 h-4 text-red-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                </svg>
                {shortPath(f)}
              </div>
              <button
                onClick={() => handleRemoveIgnored(f)}
                className="text-gray-300 hover:text-red-400 transition-colors ml-3 shrink-0"
              >
                ✕
              </button>
            </div>
          ))}

          <div className="flex gap-2">
            <input
              type="text"
              value={newIgnored}
              onChange={(e) => setNewIgnored(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddIgnored()}
              placeholder="~/Downloads/Archive"
              className="flex-1 border border-dashed border-gray-300 rounded-xl px-4 py-3 text-sm text-gray-500 focus:outline-none focus:border-red-300"
            />
            <button
              onClick={handleAddIgnored}
              disabled={!newIgnored.trim()}
              className="rounded-xl px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors disabled:bg-gray-100 disabled:text-gray-300 bg-red-400 hover:bg-red-500 text-white"
            >
              Ignore
            </button>
          </div>
        </div>

        <hr className="border-gray-100" />

        {/* Connected Drives */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
            </svg>
            <h3 className="font-bold text-gray-900">Connected Drives</h3>
          </div>

          {['school', 'personal'].map((name) => {
            const connected = accounts.includes(name)
            const isConnecting = connecting === name
            return (
              <div key={name} className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
                <div className="flex items-center gap-2 text-gray-700 text-sm">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                  </svg>
                  {name.charAt(0).toUpperCase() + name.slice(1)} Drive
                </div>
                {connected ? (
                  <button onClick={() => handleDisconnect(name)} className="text-sm text-red-400 hover:text-red-600 font-medium transition-colors">
                    Disconnect
                  </button>
                ) : (
                  <button
                    onClick={() => handleConnect(name)}
                    disabled={isConnecting}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
                  >
                    {isConnecting ? 'Connecting…' : 'Connect'}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        <hr className="border-gray-100" />

        {/* Scan Preferences */}
        <div className="flex flex-col gap-3">
          <h3 className="font-bold text-gray-900">Scan Preferences</h3>
          <label className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3 cursor-pointer">
            <span className="text-sm text-gray-700">Auto-scan on startup</span>
            <input
              type="checkbox"
              checked={autoScan}
              onChange={(e) => {
                setAutoScan(e.target.checked)
                localStorage.setItem('claire_auto_scan', e.target.checked)
              }}
              className="w-4 h-4 accent-blue-600"
            />
          </label>
        </div>

      </div>
    </div>
  )
}
