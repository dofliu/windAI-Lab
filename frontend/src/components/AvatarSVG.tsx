/**
 * 為每個 agent 生成確定性的 SVG 頭像（基於 ID hash 產生漸層 + 首字縮寫）。
 * 不需要外部圖片或 API，純 inline SVG。
 */

/** 根據字串產生確定性 hash 數值 */
function hashCode(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
    hash |= 0
  }
  return Math.abs(hash)
}

/** 從 hash 產生 HSL 色相 */
function hueFromHash(hash: number, offset: number = 0): number {
  return (hash + offset) % 360
}

/** 42 位代理的頭像漸層色組 — 基於 tier 色系 + agent hash 偏移 */
const tierHueRange: Record<string, [number, number]> = {
  leadership: [30, 50],     // 金/琥珀
  data: [140, 170],         // 綠/翡翠
  'ai-ml': [260, 290],      // 紫/靛
  domain: [330, 350],       // 玫瑰/粉
  engineering: [15, 35],    // 橙
  research: [185, 210],     // 青
}

export interface AvatarColors {
  from: string
  to: string
  text: string
}

export function getAvatarColors(agentId: string, tier: string): AvatarColors {
  const hash = hashCode(agentId)
  const range = tierHueRange[tier] ?? [200, 240]

  const hue1 = range[0] + (hash % (range[1] - range[0]))
  const hue2 = hueFromHash(hash, 40) % 360

  return {
    from: `hsl(${hue1}, 70%, 45%)`,
    to: `hsl(${hue2}, 60%, 35%)`,
    text: `hsl(${hue1}, 30%, 90%)`,
  }
}

export function getInitials(displayName: string): string {
  // 中文名取前 1 字，英文名取前 2 字首字母
  const trimmed = displayName.trim()
  if (/^[\u4e00-\u9fff]/.test(trimmed)) {
    // 中文：取前一個字
    return trimmed.charAt(0)
  }
  // 英文/混合：取首字母
  const words = trimmed.split(/[\s-]+/)
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase()
  }
  return trimmed.slice(0, 2).toUpperCase()
}

interface AvatarSVGProps {
  agentId: string
  tier: string
  displayName: string
  size: number
  className?: string
}

export default function AvatarSVG({ agentId, tier, displayName, size, className = '' }: AvatarSVGProps) {
  const colors = getAvatarColors(agentId, tier)
  const initials = getInitials(displayName)
  const gradId = `grad-${agentId}`

  // 確定性的「臉部特徵」基於 hash
  const hash = hashCode(agentId)
  const hasBang = hash % 3 === 0      // 1/3 機率有瀏海
  const hasGlasses = hash % 5 === 0    // 1/5 機率有眼鏡
  const faceYOffset = 1

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label={displayName}
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={colors.from} />
          <stop offset="100%" stopColor={colors.to} />
        </linearGradient>
        <clipPath id={`clip-${agentId}`}>
          <circle cx="24" cy="24" r="23" />
        </clipPath>
      </defs>

      {/* Background circle */}
      <circle cx="24" cy="24" r="23" fill={`url(#${gradId})`} />

      {/* Simplified face/body silhouette */}
      <g clipPath={`url(#clip-${agentId})`} opacity="0.25">
        {/* Head */}
        <circle cx="24" cy={17 + faceYOffset} r="8" fill="white" />
        {/* Body */}
        <ellipse cx="24" cy={44 + faceYOffset} rx="14" ry="12" fill="white" />

        {/* Optional bang/hair */}
        {hasBang && (
          <path
            d={`M16,${13 + faceYOffset} Q24,${8 + faceYOffset} 32,${13 + faceYOffset}`}
            fill="white"
            opacity="0.5"
          />
        )}

        {/* Optional glasses */}
        {hasGlasses && (
          <g stroke="white" strokeWidth="1" fill="none" opacity="0.5">
            <circle cx="20" cy={17 + faceYOffset} r="3" />
            <circle cx="28" cy={17 + faceYOffset} r="3" />
            <line x1="23" y1={17 + faceYOffset} x2="25" y2={17 + faceYOffset} />
          </g>
        )}
      </g>

      {/* Initials overlay */}
      <text
        x="24"
        y="25"
        textAnchor="middle"
        dominantBaseline="central"
        fill={colors.text}
        fontSize="16"
        fontWeight="700"
        fontFamily="-apple-system, 'Noto Sans TC', sans-serif"
        style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}
      >
        {initials}
      </text>
    </svg>
  )
}
