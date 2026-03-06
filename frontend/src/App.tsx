import { useState } from 'react'
import './index.css'
import { HomePage } from './pages/HomePage'
import { JobPage } from './pages/JobPage'

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      {selectedJobId ? (
        <JobPage jobId={selectedJobId} onBack={() => setSelectedJobId(null)} />
      ) : (
        <HomePage onSelectJob={setSelectedJobId} />
      )}
    </div>
  )
}
