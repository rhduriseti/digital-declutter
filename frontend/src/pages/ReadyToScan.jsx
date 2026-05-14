import { useNavigate, useLocation } from 'react-router-dom'
import { API, apiFetch } from '../config.js'

const FEATURES = [
  'Find duplicates',
  'Group similar files',
  'Organize by class and topic',
  'Clean up clutter',
]

export default function ReadyToScan() {
  const navigate = useNavigate()
  const location = useLocation()
  const { folders = [], connectedAccounts = [] } = location.state || {}

  async function handleStartScan() {
    // RAM check — warn if free RAM is under 4GB (Gemma 3 needs ~3GB)
    if (window.electron?.checkRAM) {
      const { freeGB, totalGB, freePct } = await window.electron.checkRAM()
      if (freePct < 20) {
        const proceed = window.confirm(
          `Low available memory: ${freeGB} GB free out of ${totalGB} GB total (${freePct}%).\n\n` +
          `Gemma 3 needs ~3 GB to run. To free up memory before scanning, try:\n` +
          `  • Close extra Chrome or Safari tabs\n` +
          `  • Quit Zoom or any video calls\n` +
          `  • Close any other open apps\n\n` +
          `Then click Cancel and try again. Continue anyway?`
        )
        if (!proceed) return
      }
    }

    const jobs = []

    for (const folder of folders) {
      const res = await apiFetch(`${API}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder, source: 'local' }),
      })
      const data = await res.json()
      jobs.push({ jobId: data.job_id, label: folder })
    }

    for (const account of connectedAccounts) {
      const res = await apiFetch(`${API}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: `gdrive:${account}` }),
      })
      const data = await res.json()
      jobs.push({ jobId: data.job_id, label: `${account} Drive` })
    }

    navigate('/scanning', { state: { jobs, folders } })
  }

  return (
    <div className="min-h-screen bg-[#E8EBF8] flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-sm w-full max-w-md p-8 flex flex-col gap-6">

        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-gray-900">All set!</h1>
          <p className="mt-2 text-gray-500 text-base leading-relaxed">
            Claire is ready to scan your files<br />and clean things up.
          </p>
        </div>

        <hr className="border-gray-100" />

        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-bold text-gray-900">Claire will:</h2>
          <ul className="flex flex-col gap-3">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-center gap-4 text-gray-700 text-base">
                <svg className="w-5 h-5 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <hr className="border-gray-100" />

        <div className="flex flex-col items-center gap-2">
          <button
            onClick={handleStartScan}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg rounded-2xl py-4 flex items-center justify-center gap-2 transition-colors"
          >
            Start Scan
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
          <p className="text-gray-400 text-sm text-center">This may take a few minutes.</p>
          <p className="text-gray-400 text-sm italic text-center">You can keep using your computer.</p>
        </div>

      </div>
    </div>
  )
}
