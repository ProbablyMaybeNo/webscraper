import { useEffect, useState } from 'react'
import { Globe, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import type { Job } from '../api/client'
import { ScrapeForm } from '../components/ScrapeForm'

interface Props {
  onSelectJob: (id: string) => void
}

function StatusIcon({ status }: { status: Job['status'] }) {
  if (status === 'done') return <CheckCircle size={12} className="text-[#4ade80]" />
  if (status === 'error') return <AlertCircle size={12} className="text-[#f87171]" />
  if (status === 'running') return <Loader2 size={12} className="text-[#60a5fa] animate-spin" />
  return <Clock size={12} className="text-[#666]" />
}

export function HomePage({ onSelectJob }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])

  const loadJobs = async () => {
    try {
      const j = await api.getJobs()
      setJobs(j)
    } catch { /* server may not be up yet */ }
  }

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleJobStarted = (jobId: string) => {
    loadJobs()
    if (jobId) onSelectJob(jobId)
  }

  const presetFWW = () => {
    const input = document.querySelector('input[type=url]') as HTMLInputElement | null
    if (input) {
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
      nativeInputValueSetter?.call(input, 'https://fallout.maloric.com/fww/library')
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.focus()
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto">
      <div className="border-b border-[#2a2a2a] pb-4">
        <div className="flex items-center gap-3 mb-1">
          <Globe size={18} className="text-[#4ade80]" />
          <h1 className="text-[#4ade80] font-mono font-bold tracking-widest uppercase text-sm">
            Webscraper
          </h1>
        </div>
        <p className="text-[#444] text-xs font-mono">
          Extract text, images, and data from any website. Auto-detects JS-rendered pages.
        </p>
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        <span className="text-[#444] text-xs font-mono">Quick:</span>
        <button
          type="button"
          onClick={presetFWW}
          className="text-xs font-mono border border-[#2a2a2a] text-[#666] hover:border-[#60a5fa] hover:text-[#60a5fa] px-3 py-1 rounded transition-colors"
        >
          FWW Card Library
        </button>
      </div>

      <ScrapeForm onJobStarted={handleJobStarted} />

      {jobs.length > 0 && (
        <div className="flex flex-col gap-1">
          <h2 className="text-[#60a5fa] text-xs font-mono uppercase tracking-widest mb-2">Recent Jobs</h2>
          {jobs.map(job => (
            <button
              key={job.id}
              onClick={() => onSelectJob(job.id)}
              className="flex items-center gap-3 text-left bg-[#141414] border border-[#2a2a2a] hover:border-[#4ade80] rounded px-4 py-3 transition-colors w-full"
            >
              <StatusIcon status={job.status} />
              <div className="flex-1 min-w-0">
                <p className="text-[#e8e8e8] text-xs font-mono font-bold truncate">{job.label || job.url}</p>
                <p className="text-[#444] text-xs font-mono truncate">{job.url}</p>
              </div>
              <div className="flex gap-3 shrink-0 text-xs font-mono text-[#444]">
                <span>{job.item_count} items</span>
                <span>{job.mode}</span>
                <span>{new Date(job.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
