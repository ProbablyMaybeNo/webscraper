const BASE = '/api'

export interface ScrapeRequest {
  url: string
  label?: string
  mode: 'auto' | 'html' | 'browser'
  download_images?: boolean
}

export interface Job {
  id: string
  url: string
  label: string | null
  mode: string
  status: 'pending' | 'running' | 'done' | 'error'
  created_at: string
  updated_at: string
  item_count: number
  error: string | null
}

export interface Item {
  id: number
  job_id: string
  name: string
  description: string
  source_url: string
  image_url: string
  image_path: string
  extra_data: Record<string, unknown>
  created_at: string
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  startScrape: (body: ScrapeRequest) =>
    req<Job>('/scrape', { method: 'POST', body: JSON.stringify(body) }),

  getJobs: () => req<Job[]>('/jobs'),

  getJob: (id: string) => req<Job>(`/jobs/${id}`),

  getItems: (id: string) => req<Item[]>(`/jobs/${id}/items`),

  exportJson: (id: string) => `${BASE}/jobs/${id}/export/json`,

  exportCsv: (id: string) => `${BASE}/jobs/${id}/export/csv`,

  streamUrl: (id: string) => `${BASE}/jobs/${id}/stream`,
}
