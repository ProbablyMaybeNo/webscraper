import { useEffect, useState } from 'react'
import { ArrowLeft, Download } from 'lucide-react'
import { api } from '../api/client'
import type { Job, Item } from '../api/client'
import { JobProgress } from '../components/JobProgress'
import { ResultsTable } from '../components/ResultsTable'

interface Props {
  jobId: string
  onBack: () => void
}

export function JobPage({ jobId, onBack }: Props) {
  const [job, setJob] = useState<Job | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [showStream, setShowStream] = useState(false)

  const load = async () => {
    const j = await api.getJob(jobId)
    setJob(j)
    if (j.status === 'done' || j.status === 'error') {
      const its = await api.getItems(jobId)
      setItems(its)
    }
  }

  useEffect(() => {
    load()
    api.getJob(jobId).then(j => {
      if (j.status === 'pending' || j.status === 'running') setShowStream(true)
    })
  }, [jobId])

  const handleDone = async () => {
    await load()
    setShowStream(false)
  }

  const statusColor = job?.status === 'done' ? '#4ade80'
    : job?.status === 'error' ? '#f87171'
    : job?.status === 'running' ? '#60a5fa' : '#666'

  return (
    <div className="flex flex-col gap-4 p-6 max-w-7xl mx-auto">
      <button onClick={onBack} className="flex items-center gap-1 text-[#666] hover:text-[#e8e8e8] text-xs font-mono w-fit">
        <ArrowLeft size={12} /> Back to jobs
      </button>

      {job && (
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[#4ade80] font-mono text-sm font-bold tracking-widest uppercase">
              {job.label || job.url}
            </h1>
            <p className="text-[#444] text-xs font-mono mt-1">{job.url}</p>
            <div className="flex gap-4 mt-2 text-xs font-mono">
              <span style={{ color: statusColor }}>{job.status.toUpperCase()}</span>
              <span className="text-[#666]">mode: {job.mode}</span>
              <span className="text-[#666]">{job.item_count} items</span>
              <span className="text-[#444]">{new Date(job.created_at).toLocaleString()}</span>
            </div>
            {job.error && <p className="text-[#f87171] text-xs font-mono mt-1">{job.error}</p>}
          </div>

          {job.status === 'done' && job.item_count > 0 && (
            <div className="flex gap-2 shrink-0">
              <a
                href={api.exportJson(jobId)}
                download
                className="flex items-center gap-1 border border-[#2a2a2a] text-[#666] hover:border-[#4ade80] hover:text-[#4ade80] px-3 py-1.5 text-xs font-mono rounded transition-colors"
              >
                <Download size={10} /> JSON
              </a>
              <a
                href={api.exportCsv(jobId)}
                download
                className="flex items-center gap-1 border border-[#2a2a2a] text-[#666] hover:border-[#4ade80] hover:text-[#4ade80] px-3 py-1.5 text-xs font-mono rounded transition-colors"
              >
                <Download size={10} /> CSV
              </a>
            </div>
          )}
        </div>
      )}

      {showStream && <JobProgress jobId={jobId} onDone={handleDone} />}

      {items.length > 0 && <ResultsTable items={items} />}
      {job?.status === 'done' && items.length === 0 && (
        <p className="text-[#444] text-sm font-mono">No items extracted.</p>
      )}
    </div>
  )
}
