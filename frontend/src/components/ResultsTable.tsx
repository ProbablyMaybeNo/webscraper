import { useState } from 'react'
import { ExternalLink, Image as ImageIcon } from 'lucide-react'
import type { Item } from '../api/client'

interface Props {
  items: Item[]
}

export function ResultsTable({ items }: Props) {
  const [view, setView] = useState<'table' | 'gallery'>('table')
  const [search, setSearch] = useState('')

  const filtered = items.filter(it =>
    !search || it.name.toLowerCase().includes(search.toLowerCase()) ||
    it.description.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2 items-center">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search…"
          className="flex-1 bg-[#1a1a1a] border border-[#2a2a2a] text-[#e8e8e8] px-3 py-1.5 text-sm font-mono rounded focus:outline-none focus:border-[#4ade80]"
        />
        <span className="text-[#666] text-xs font-mono">{filtered.length} items</span>
        <button
          onClick={() => setView('table')}
          className={`px-3 py-1.5 text-xs font-mono border rounded transition-colors ${view === 'table' ? 'border-[#4ade80] text-[#4ade80]' : 'border-[#2a2a2a] text-[#666] hover:border-[#4ade80]'}`}
        >
          Table
        </button>
        <button
          onClick={() => setView('gallery')}
          className={`px-3 py-1.5 text-xs font-mono border rounded transition-colors ${view === 'gallery' ? 'border-[#4ade80] text-[#4ade80]' : 'border-[#2a2a2a] text-[#666] hover:border-[#4ade80]'}`}
        >
          Gallery
        </button>
      </div>

      {view === 'table' && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-[#2a2a2a] text-[#60a5fa]">
                <th className="text-left py-2 pr-4 w-8">#</th>
                <th className="text-left py-2 pr-4 w-16">Image</th>
                <th className="text-left py-2 pr-4">Name</th>
                <th className="text-left py-2 pr-4 max-w-xs">Description</th>
                <th className="text-left py-2">Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => (
                <tr key={item.id} className="border-b border-[#1a1a1a] hover:bg-[#141414]">
                  <td className="py-2 pr-4 text-[#444]">{i + 1}</td>
                  <td className="py-2 pr-4">
                    {item.image_url ? (
                      <img
                        src={item.image_path ? `/images/${item.image_path.split('images/')[1] || item.image_path}` : item.image_url}
                        alt={item.name}
                        className="w-12 h-12 object-cover rounded border border-[#2a2a2a]"
                        onError={(e: React.SyntheticEvent<HTMLImageElement>) => { (e.target as HTMLImageElement).src = item.image_url }}
                      />
                    ) : (
                      <div className="w-12 h-12 bg-[#1a1a1a] border border-[#2a2a2a] rounded flex items-center justify-center text-[#333]">
                        <ImageIcon size={16} />
                      </div>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-[#e8e8e8] font-bold max-w-[180px] truncate">{item.name}</td>
                  <td className="py-2 pr-4 text-[#999] max-w-xs">
                    <span title={item.description} className="line-clamp-2">{item.description || '—'}</span>
                  </td>
                  <td className="py-2">
                    {item.source_url ? (
                      <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                        className="text-[#60a5fa] hover:text-[#93c5fd] flex items-center gap-1">
                        <ExternalLink size={10} /> link
                      </a>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="text-center text-[#444] py-8 text-sm font-mono">No items match your search.</p>
          )}
        </div>
      )}

      {view === 'gallery' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {filtered.map(item => (
            <div key={item.id} className="bg-[#141414] border border-[#2a2a2a] rounded overflow-hidden hover:border-[#4ade80] transition-colors">
              {item.image_url ? (
                <img
                  src={item.image_path ? `/images/${item.image_path.split('images/')[1] || item.image_path}` : item.image_url}
                  alt={item.name}
                  className="w-full aspect-square object-cover"
                  onError={(e: React.SyntheticEvent<HTMLImageElement>) => { (e.target as HTMLImageElement).src = item.image_url }}
                />
              ) : (
                <div className="w-full aspect-square bg-[#0d0d0d] flex items-center justify-center text-[#2a2a2a]">
                  <ImageIcon size={32} />
                </div>
              )}
              <div className="p-2">
                <p className="text-[#e8e8e8] text-xs font-bold font-mono truncate">{item.name}</p>
                {item.description && (
                  <p className="text-[#666] text-xs font-mono mt-0.5 line-clamp-2">{item.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
