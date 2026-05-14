import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const isElectron = !!window.electron?.isElectron

const API = 'http://localhost:8000'
const DEFAULT_FOLDERS = []

async function loadFolders() {
  if (window.electron?.getSettings) {
    const settings = await window.electron.getSettings()
    return Array.isArray(settings.folders) ? settings.folders : DEFAULT_FOLDERS
  }
  try {
    const saved = localStorage.getItem('claire_folders')
    const parsed = saved ? JSON.parse(saved) : DEFAULT_FOLDERS
    return Array.isArray(parsed) ? parsed : DEFAULT_FOLDERS
  } catch {
    return DEFAULT_FOLDERS
  }
}

async function persistFolders(folders) {
  if (window.electron?.saveSettings) {
    await window.electron.saveSettings({ folders })
  }
  localStorage.setItem('claire_folders', JSON.stringify(folders))
}

export default function Onboarding() {
  const navigate = useNavigate()
  const [folders, setFolders] = useState(DEFAULT_FOLDERS)
  const [newFolder, setNewFolder] = useState('')
  const [connectedAccounts, setConnectedAccounts] = useState([])
  const [connecting, setConnecting] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    loadFolders().then(setFolders)
    fetchAccounts()
    return () => clearInterval(pollRef.current)
  }, [])

  async function fetchAccounts() {
    try {
      const res = await fetch(`${API}/drive/accounts`)
      const data = await res.json()
      setConnectedAccounts(data.accounts || [])
    } catch {}
  }

  async function updateFolders(updated) {
    setFolders(updated)
    await persistFolders(updated)
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

  async function handleConnectDrive(accountName) {
    setConnecting(accountName)
    try {
      const res = await fetch(`${API}/drive/login/start/${accountName}`)
      const data = await res.json()
      const popup = window.open(data.auth_url, '_blank')
      pollRef.current = setInterval(async () => {
        const r = await fetch(`${API}/drive/accounts`).then(x => x.json()).catch(() => ({ accounts: [] }))
        const currentAccounts = r.accounts || []
        fetchAccounts()
        const closed = !popup || popup.closed
        const connected = currentAccounts.includes(accountName)
        if (closed || connected) {
          clearInterval(pollRef.current)
          await fetchAccounts()
          setConnecting(null)
        }
      }, 2000)
    } catch {
      alert('Could not reach the backend. Make sure the API is running (declutter-api).')
      setConnecting(null)
    }
  }

  const schoolConnected = connectedAccounts.includes('school')
  const personalConnected = connectedAccounts.includes('personal')

  return (
    <div className="min-h-screen bg-[#E8EBF8] flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-sm w-full max-w-md p-8 flex flex-col gap-6">

        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-gray-900">Welcome to Claire!</h1>
          <p className="mt-2 text-gray-400 text-base">Let's get your workspace organized</p>
        </div>

        {/* Step 1: Local folders */}
        <div className="flex flex-col gap-3">
          <h2 className="text-base font-bold text-gray-900">Step 1: Add your local folders</h2>

          {folders.map((f) => (
            <div key={f} className="flex items-center justify-between bg-gray-50 rounded-2xl px-4 py-3 border border-gray-100">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                </svg>
                <span className="text-sm text-gray-600">{f}</span>
              </div>
              <button
                onClick={() => updateFolders(folders.filter((p) => p !== f))}
                className="text-gray-300 hover:text-red-400 transition-colors ml-2 shrink-0"
              >
                ✕
              </button>
            </div>
          ))}

          {isElectron ? (
            <button
              onClick={handleBrowseFolder}
              className="w-full border-2 border-dashed border-gray-200 hover:border-blue-400 rounded-2xl px-4 py-3 text-sm text-gray-400 hover:text-blue-500 transition-colors flex items-center justify-center gap-2"
            >
              <span className="text-lg leading-none">+</span> Add Folder
            </button>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={newFolder}
                onChange={(e) => setNewFolder(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddFolder()}
                placeholder="e.g. ~/Documents_DD"
                className="flex-1 border-2 border-dashed border-gray-200 rounded-2xl px-4 py-3 text-sm text-gray-500 focus:outline-none focus:border-blue-400"
              />
              <button
                onClick={handleAddFolder}
                disabled={!newFolder.trim()}
                className="rounded-2xl px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors disabled:bg-gray-100 disabled:text-gray-300 bg-blue-600 hover:bg-blue-700 text-white"
              >
                + Add
              </button>
            </div>
          )}
        </div>

        {/* Step 2: Connect Google Drive */}
        <div className="flex flex-col gap-3">
          <h2 className="text-base font-bold text-gray-900">Step 2: Connect Google Drive</h2>

          <DriveButton
            label="School Drive"
            connected={schoolConnected}
            loading={connecting === 'school'}
            onClick={() => handleConnectDrive('school')}
          />

          <DriveButton
            label="Personal Drive"
            connected={personalConnected}
            loading={connecting === 'personal'}
            onClick={() => handleConnectDrive('personal')}
          />
        </div>

        {/* Get Started */}
        <button
          onClick={() => navigate('/ready', { state: { folders, connectedAccounts } })}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg rounded-2xl py-4 flex items-center justify-center gap-2 transition-colors"
        >
          Get Started
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>

      </div>
    </div>
  )
}

function DriveButton({ label, connected, loading, onClick }) {
  return (
    <button
      onClick={!connected ? onClick : undefined}
      disabled={loading}
      className={`w-full flex items-center justify-between rounded-2xl px-5 py-4 border transition-colors ${
        connected
          ? 'bg-green-50 border-green-300 text-green-600 cursor-default'
          : loading
          ? 'bg-gray-50 border-gray-200 text-gray-400 cursor-wait'
          : 'bg-white border-gray-200 text-gray-500 hover:border-blue-300 hover:text-blue-500'
      }`}
    >
      <span className="font-medium">
        {connected ? `${label} Connected` : loading ? `Connecting ${label}...` : `Connect ${label}`}
      </span>
      {connected && (
        <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {loading && (
        <svg className="w-5 h-5 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
      )}
    </button>
  )
}
