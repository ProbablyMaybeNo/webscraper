import { useState } from 'react'
import { Loader2, Play } from 'lucide-react'
import { api } from '../api/client'

interface Props {
  onJobStarted: (jobId: string) => void
}

export function ScrapeForm({ onJobStarted }: Props) {
  const [url, setUrl] = useState('')
  const [label, setLabel] = useState('')
  const [mode, setMode] = useState<'auto' | 'html' | 'browser'>('auto')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError('')
    try {
      const job = await api.startScrape({ url: url.trim(), label: label || undefined, mode })
      onJobStarted(job.id)
      setUrl('')
      setLabel('')
    } catch (err: any) {
      setError(err.message || 'Failed to start scrape')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://example.com/page-to-scrape"
          required
          className="flex-1 bg-[#1a1a1a] border border-[#2a2a2a] text-[#e8e8e8] px-3 py-2 text-sm font-mono rounded focus:outline-none focus:border-[#4ade80]"
        />
        <input
          type="text"
          value={label}
          onChange={e => setLabel(e.target.value)}
          placeholder="Label (optional)"
          className="w-44 bg-[#1a1a1a] border border-[#2a2a2a] text-[#e8e8e8] px-3 py-2 text-sm font-mono rounded focus:outline-none focus:border-[#4ade80]"
        />
        <select
          value={mode}
          onChange={e => setMode(e.target.value as any)}
          className="bg-[#1a1a1a] border border-[#2a2a2a] text-[#e8e8e8] px-3 py-2 text-sm font-mono rounded focus:outline-none focus:border-[#4ade80]"
        >
          <option value="auto">Auto</option>
          <option value="html">HTML only</option>
          <option value="browser">Browser (JS)</option>
        </select>
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="flex items-center gap-2 bg-[#4ade80] text-black px-4 py-2 text-sm font-mono font-bold rounded hover:bg-[#22c55e] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Scrape
        </button>
      </div>
      {error && <p className="text-[#f87171] text-xs font-mono">{error}</p>}
    </form>
  )
}
