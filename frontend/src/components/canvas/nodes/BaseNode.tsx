import { Handle, Position, type NodeProps, type Node } from '@xyflow/react'
import { type LucideIcon } from 'lucide-react'
import type { NodeData, NodeStatus } from '@/types'
import { resolveNodeColors } from '@/utils/nodeColors'

const STATUS_COLORS: Record<NodeStatus, string> = {
  online: '#39d353',
  offline: '#f85149',
  pending: '#e3b341',
  unknown: '#8b949e',
}

interface BaseNodeProps extends NodeProps<Node<NodeData>> {
  icon: LucideIcon
}

export function BaseNode({ data, selected, icon: Icon }: BaseNodeProps) {
  const colors = resolveNodeColors(data)
  const statusColor = STATUS_COLORS[data.status]
  const isOnline = data.status === 'online'

  return (
    <div
      className="relative flex flex-row items-center gap-2.5 px-2.5 py-2 rounded-lg border transition-all duration-200"
      style={{
        background: colors.background,
        borderColor: selected ? colors.border : '#30363d',
        boxShadow: isOnline
          ? `0 0 10px ${colors.border}2e, 0 0 3px ${colors.border}1a`
          : selected
          ? `0 0 8px ${colors.border}44`
          : 'none',
        opacity: data.status === 'offline' ? 0.55 : 1,
        minWidth: 140,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#30363d] !border-[#8b949e]" />

      {/* Icon */}
      <div
        className="flex items-center justify-center w-7 h-7 rounded-md shrink-0"
        style={{ color: isOnline ? colors.icon : '#8b949e', background: '#161b22' }}
      >
        <Icon size={15} />
      </div>

      {/* Details */}
      <div className="flex flex-col min-w-0">
        <div className="text-xs font-medium leading-tight truncate max-w-[110px]" title={data.label}>
          {data.label}
        </div>
        {data.ip && (
          <div className="font-mono text-[10px] text-[#8b949e] truncate" title={data.ip}>
            {data.ip}
          </div>
        )}
      </div>

      {/* Status dot */}
      <div
        className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full shrink-0"
        style={{ backgroundColor: statusColor }}
        title={data.status}
      />

      <Handle type="source" position={Position.Bottom} className="!bg-[#30363d] !border-[#8b949e]" />
    </div>
  )
}
