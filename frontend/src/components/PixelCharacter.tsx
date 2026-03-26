import { memo } from 'react'
import { useTheme, getTierColor, getStatusColor } from '../themes'

/**
 * 像素風格人物角色 — chibi 比例、crispEdges 渲染
 * 走路時整個人物上下彈跳 + 微微搖擺
 */

const HAIR = ['#1a1a2e', '#3d2b1f', '#8b6914', '#5b2c6f', '#2c3e50', '#784212', '#4a1942', '#1b4332']
const SKIN = ['#f5c6a0', '#e8b896', '#d4a574', '#c49a6c', '#f0d5b8']

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (s.charCodeAt(i) + ((h << 5) - h)) | 0
  return Math.abs(h)
}

interface Props {
  agentId: string
  tier: string
  status: string
  isWalking: boolean
  size?: number
}

function PixelCharacter({ agentId, tier, status, isWalking, size = 32 }: Props) {
  const { theme } = useTheme()
  const h = hash(agentId)
  const shirt = (theme.pixelShirtColors?.[tier]) || getTierColor(theme, tier).primary
  const hair = HAIR[h % HAIR.length]
  const skin = SKIN[h % SKIN.length]
  const pants = '#475569'
  const shoes = '#1e293b'

  const svgH = size * (24 / 16)

  return (
    <svg
      viewBox="0 0 16 24"
      width={size}
      height={svgH}
      style={{ shapeRendering: 'crispEdges', overflow: 'visible' }}
      className={isWalking ? 'pixel-char pixel-char-walking' : 'pixel-char'}
    >
      {/* ── Status dot above head ── */}
      {status === 'working' && (
        <circle cx="8" cy="-2" r="1.8" fill={getStatusColor(theme, 'working').dot} style={{ shapeRendering: 'auto' }}>
          <animate attributeName="opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite" />
        </circle>
      )}
      {status === 'waiting' && (
        <circle cx="8" cy="-2" r="1.8" fill={getStatusColor(theme, 'waiting').dot} style={{ shapeRendering: 'auto' }}>
          <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite" />
        </circle>
      )}
      {status === 'error' && (
        <circle cx="8" cy="-2" r="1.8" fill={getStatusColor(theme, 'error').dot} style={{ shapeRendering: 'auto' }} />
      )}

      {/* ── Hair ── */}
      <rect x="4" y="0" width="8" height="3" fill={hair} />
      <rect x="3" y="2" width="10" height="2" fill={hair} />

      {/* ── Head / Face ── */}
      <rect x="4" y="3" width="8" height="5" fill={skin} />

      {/* ── Eyes ── */}
      <rect x="5" y="5" width="2" height="2" fill="#334155" />
      <rect x="9" y="5" width="2" height="2" fill="#334155" />
      {/* Eye highlights */}
      <rect x="5" y="5" width="1" height="1" fill="#94a3b8" opacity="0.6" />
      <rect x="9" y="5" width="1" height="1" fill="#94a3b8" opacity="0.6" />

      {/* ── Body / Shirt ── */}
      <rect x="3" y="8" width="10" height="6" fill={shirt} />
      {/* Shirt collar / detail */}
      <rect x="6" y="8" width="4" height="1" fill={shirt} opacity="0.7" />

      {/* ── Arms ── */}
      <rect x="1" y="9" width="2" height="4" fill={shirt} />
      <rect x="13" y="9" width="2" height="4" fill={shirt} />
      {/* Hands */}
      <rect x="1" y="13" width="2" height="1" fill={skin} />
      <rect x="13" y="13" width="2" height="1" fill={skin} />

      {/* ── Legs (standing frame) ── */}
      <g className="pixel-legs-stand">
        <rect x="4" y="14" width="3" height="5" fill={pants} />
        <rect x="9" y="14" width="3" height="5" fill={pants} />
        {/* Shoes */}
        <rect x="3" y="19" width="4" height="2" fill={shoes} />
        <rect x="9" y="19" width="4" height="2" fill={shoes} />
      </g>

      {/* ── Legs (walk frame A) ── */}
      <g className="pixel-legs-walk-a">
        <rect x="3" y="14" width="3" height="5" fill={pants} />
        <rect x="10" y="14" width="3" height="4" fill={pants} />
        <rect x="2" y="19" width="4" height="2" fill={shoes} />
        <rect x="10" y="18" width="4" height="2" fill={shoes} />
      </g>

      {/* ── Legs (walk frame B) ── */}
      <g className="pixel-legs-walk-b">
        <rect x="4" y="14" width="3" height="4" fill={pants} />
        <rect x="10" y="14" width="3" height="5" fill={pants} />
        <rect x="4" y="18" width="4" height="2" fill={shoes} />
        <rect x="10" y="19" width="4" height="2" fill={shoes} />
      </g>

      {/* ── Ground shadow ── */}
      <ellipse cx="8" cy="22" rx="5" ry="1.2" fill="rgba(0,0,0,0.12)" style={{ shapeRendering: 'auto' }} />
    </svg>
  )
}

export default memo(PixelCharacter)
