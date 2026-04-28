import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const API = 'http://localhost:8000'

export default function Scanning() {
  const navigate = useNavigate()
  const location = useLocation()
  const { jobs = [], folders = [] } = location.state || {}

  const [filesScanned, setFilesScanned] = useState(0)
  const [total, setTotal] = useState(0)
  const [percent, setPercent] = useState(0)
  const [currentFile, setCurrentFile] = useState('')

  useEffect(() => {
    if (jobs.length === 0) {
      navigate('/dashboard')
      return
    }

    const interval = setInterval(async () => {
      const statuses = await Promise.all(
        jobs.map((j) => fetch(`${API}/scan/status/${j.jobId}`).then((r) => r.json()))
      )

      // Aggregate progress across all jobs
      let totalScanned = 0
      let totalFiles = 0
      let latestFile = ''

      for (const s of statuses) {
        if (s.progress) {
          totalScanned += s.progress.files_scanned
          totalFiles += s.progress.total
          if (s.progress.current_file) latestFile = s.progress.current_file
        }
      }

      if (totalFiles > 0) {
        setFilesScanned(totalScanned)
        setTotal(totalFiles)
        setPercent(Math.round((totalScanned / totalFiles) * 100))
      }
      if (latestFile) setCurrentFile(latestFile)

      const allDone = statuses.every((s) => s.status === 'done' || s.status === 'error')
      if (allDone) {
        clearInterval(interval)
        navigate('/dashboard')
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const shortPath = (p) => p.replace(/^\/Users\/[^/]+/, '~')

  return (
    <div className="min-h-screen bg-[#E8EBF8] flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-sm w-full max-w-md p-8 flex flex-col gap-6">

        {/* Icon */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
          </div>
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">Scanning your files...</h1>
          <p className="mt-1 text-gray-400 text-base">This may take a few moments</p>
        </div>

        {/* Progress */}
        <div className="flex flex-col gap-2">
          {total === 0 ? (
            <>
              <p className="text-sm text-gray-400 text-center">Counting files…</p>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div className="h-3 rounded-full bg-blue-300 animate-pulse w-full" />
              </div>
            </>
          ) : (
            <>
              <div className="flex justify-between text-sm text-gray-500">
                <span>{filesScanned} of {total} files scanned</span>
                <span>{percent}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div
                  className="h-3 rounded-full bg-blue-600 transition-all duration-500"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </>
          )}
        </div>

        {/* Currently scanning */}
        {currentFile && (
          <div className="bg-[#EEF0FB] rounded-2xl px-5 py-4 flex items-center gap-3">
            <svg className="w-6 h-6 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div>
              <p className="text-sm text-gray-400">Currently scanning:</p>
              <p className="text-sm font-medium text-gray-700 break-all">{shortPath(currentFile)}</p>
            </div>
          </div>
        )}

        {/* Scanning folders */}
        {folders.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-gray-400">Scanning folders:</p>
            <ul className="flex flex-col gap-1">
              {folders.map((f, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                  <svg className="w-5 h-5 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
                  </svg>
                  {shortPath(f)}
                </li>
              ))}
            </ul>
          </div>
        )}

      </div>
    </div>
  )
}
