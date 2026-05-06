import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Onboarding from './pages/Onboarding'
import ReadyToScan from './pages/ReadyToScan'
import Scanning from './pages/Scanning'
import Dashboard from './pages/Dashboard'
import OrganisedFiles from './pages/OrganisedFiles'
import Duplicates from './pages/Duplicates'
import Privacy from './pages/Privacy'
import { API, apiFetch } from './config.js'

function AppRouter() {
  const [ready, setReady] = useState(false)
  const [isFirstTime, setIsFirstTime] = useState(null)

  useEffect(() => {
    async function checkIndex() {
      try {
        const driveRes = await apiFetch(`${API}/drive/accounts`)
        const driveData = await driveRes.json()
        const accounts = driveData.accounts || []

        // Restore index from Drive appDataFolder for each connected account (if missing locally)
        await Promise.all(
          accounts.map((account) =>
            apiFetch(`${API}/drive/${account}/restore`, { method: 'POST' }).catch(() => {})
          )
        )

        const hasDrives = accounts.length > 0
        const savedFolders = localStorage.getItem('claire_folders')
        const folders = (() => { try { return JSON.parse(savedFolders) } catch { return [] } })()
        const hasFolders = Array.isArray(folders) && folders.length > 0

        setIsFirstTime(!hasFolders && !hasDrives)
      } catch {
        setIsFirstTime(true)
      } finally {
        setReady(true)
      }
    }
    checkIndex()
  }, [])

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#E8EBF8] flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={isFirstTime ? '/onboarding' : '/dashboard'} replace />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/ready" element={<ReadyToScan />} />
      <Route path="/scanning" element={<Scanning />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/organised" element={<OrganisedFiles />} />
      <Route path="/duplicates" element={<Duplicates />} />
      <Route path="/privacy" element={<Privacy />} />
    </Routes>
  )
}

export default function App() {
  return <AppRouter />
}
