import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface Props {
  jobId: string
  onDone: (count: number) => void
}

export function JobProgress({ jobId, onDone }: Props) {
  const [messages, setMessages] = useState<string[]>([])
  const [count, setCount] = useState(0)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const es = new EventSource(api.streamUrl(jobId))

    es.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data)
      setMessages(prev => [...prev, data.message])
      if (data.count) setCount(data.count)
    })

    es.addEventListener('done', (e) => {
      const data = JSON.parse(e.data)
      setDone(true)
      setCount(data.count || count)
      onDone(data.count || 0)
      es.close()
    })

    es.addEventListener('error', (e: any) => {
      const data = e.data ? JSON.parse(e.data) : {}
      setError(data.message || 'Stream error')
      es.close()
    })

    es.onerror = () => {
      if (!done) {
        setError('Connection lost')
        es.close()
      }
    }

    return () => es.close()
  }, [jobId])

  return (
    <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded p-3 font-mono text-xs">
      <div className="text-[#60a5fa] mb-2 text-xs uppercase tracking-widest">
        {done ? '✓ Complete' : error ? '✗ Error' : '⟳ Running'}
        {count > 0 && ` — ${count} items`}
      </div>
      <div className="space-y-0.5 max-h-32 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className="text-[#666]">
            <span className="text-[#4ade80] mr-2">›</span>{m}
          </div>
        ))}
        {error && <div className="text-[#f87171]">✗ {error}</div>}
      </div>
    </div>
  )
}
