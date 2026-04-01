import { useState, useEffect, useRef } from 'react'
import { useReactFlow } from '@xyflow/react'
import { Search, X } from 'lucide-react'
import { useCanvasStore } from '@/stores/canvasStore'
import { NODE_TYPE_LABELS } from '@/types'

export function SearchBar() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { nodes, setSelectedNode } = useCanvasStore()
  const { setCenter } = useReactFlow()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault()
        setOpen(true)
      }
      if (e.key === 'Escape') {
        setOpen(false)
        setQuery('')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const q = query.toLowerCase().trim()
  const results = q
    ? nodes.filter((n) => {
        if (n.data.type === 'groupRect') return false
        return (
          n.data.label?.toLowerCase().includes(q) ||
          n.data.ip?.toLowerCase().includes(q) ||
          n.data.hostname?.toLowerCase().includes(q) ||
          (n.data.services ?? []).some((s) => s.service_name?.toLowerCase().includes(q))
        )
      })
    : []

  const goToNode = (id: string) => {
    const node = nodes.find((n) => n.id === id)
    if (!node) return
    setSelectedNode(id)
    // For grouped nodes, add parent's absolute position
    let absX = node.position.x
    let absY = node.position.y
    if (node.parentId) {
      const parent = nodes.find((n) => n.id === node.parentId)
      if (parent) { absX += parent.position.x; absY += parent.position.y }
    }
    const w = node.measured?.width ?? node.width ?? 200
    const h = node.measured?.height ?? node.height ?? 80
    setCenter(absX + w / 2, absY + h / 2, { zoom: 1.5, duration: 500 })
    setOpen(false)
    setQuery('')
  }

  if (!open) return null

  return (
    <div
      className="nodrag nowheel"
      style={{
        position: 'absolute',
        top: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        width: 360,
        pointerEvents: 'all',
      }}
    >
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: 8,
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
        overflow: 'hidden',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px' }}>
          <Search size={14} style={{ color: '#8b949e', flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, IP, hostname or service…"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#e6edf3',
              fontSize: 13,
            }}
          />
          {query && (
            <span style={{ fontSize: 11, color: '#6e7681', flexShrink: 0 }}>
              {results.length} result{results.length !== 1 ? 's' : ''}
            </span>
          )}
          <button
            onClick={() => { setOpen(false); setQuery('') }}
            aria-label="Close search"
            style={{ color: '#8b949e', background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
          >
            <X size={14} />
          </button>
        </div>

        {results.length > 0 && (
          <div style={{ borderTop: '1px solid #30363d', maxHeight: 260, overflowY: 'auto' }}>
            {results.map((n) => (
              <button
                key={n.id}
                onClick={() => goToNode(n.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '7px 12px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#21262d')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
              >
                <span style={{ fontSize: 12, fontWeight: 600, color: '#e6edf3', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {n.data.label}
                </span>
                {n.data.ip && (
                  <span style={{ fontSize: 11, color: '#8b949e', fontFamily: 'JetBrains Mono, monospace', flexShrink: 0 }}>
                    {n.data.ip}
                  </span>
                )}
                <span style={{ fontSize: 10, color: '#6e7681', flexShrink: 0 }}>
                  {NODE_TYPE_LABELS[n.data.type] ?? n.data.type}
                </span>
              </button>
            ))}
          </div>
        )}

        {q && results.length === 0 && (
          <div style={{ borderTop: '1px solid #30363d', padding: '10px 12px', fontSize: 12, color: '#6e7681', textAlign: 'center' }}>
            No results for &ldquo;{query}&rdquo;
          </div>
        )}
      </div>
    </div>
  )
}
