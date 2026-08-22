/**
 * 素净雅致的书籍封面兜底配色方案
 * 采用低饱和度的纸墨风、莫兰迪色系（素纸米、竹青素、霁蓝灰、浅茶檀、烟霞素、浅黛青、素雪紫、墨云灰）
 */
export const MUTED_BOOK_PALETTES = [
  { from: '#f3efe9', to: '#ded7cd', text: '#363028', sub: '#7c7365', border: 'rgba(90, 78, 64, 0.14)', spine: 'rgba(90, 78, 64, 0.09)' }, // 素纸米
  { from: '#ebf0ea', to: '#d3ddd2', text: '#28362a', sub: '#677769', border: 'rgba(60, 80, 62, 0.14)', spine: 'rgba(60, 80, 62, 0.09)' }, // 竹青素
  { from: '#eaeff3', to: '#ced9e3', text: '#263442', sub: '#637485', border: 'rgba(50, 70, 90, 0.14)', spine: 'rgba(50, 70, 90, 0.09)' }, // 霁蓝灰
  { from: '#f4ede7', to: '#e3d6cc', text: '#403026', sub: '#826e62', border: 'rgba(90, 65, 50, 0.14)', spine: 'rgba(90, 65, 50, 0.09)' }, // 浅茶檀
  { from: '#ebe9ef', to: '#d4d2de', text: '#342a42', sub: '#746886', border: 'rgba(70, 55, 90, 0.14)', spine: 'rgba(70, 55, 90, 0.09)' }, // 烟霞素
  { from: '#e7eded', to: '#cdd7d8', text: '#243738', sub: '#607778', border: 'rgba(50, 80, 80, 0.14)', spine: 'rgba(50, 80, 80, 0.09)' }, // 浅黛青
  { from: '#efebf1', to: '#ddd7e0', text: '#3c3040', sub: '#7b6c7f', border: 'rgba(80, 60, 85, 0.14)', spine: 'rgba(80, 60, 85, 0.09)' }, // 素雪紫
  { from: '#ececed', to: '#d6d7da', text: '#2e3138', sub: '#6f737c', border: 'rgba(65, 70, 80, 0.14)', spine: 'rgba(65, 70, 80, 0.09)' }, // 墨云灰
]

export function getMutedCoverPalette(name: string) {
  const str = name || '书'
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }
  const idx = Math.abs(hash) % MUTED_BOOK_PALETTES.length
  return MUTED_BOOK_PALETTES[idx]
}

export function getMutedCoverStyle(name: string): Record<string, string> {
  const p = getMutedCoverPalette(name)
  return {
    background: `linear-gradient(150deg, ${p.from} 0%, ${p.to} 100%)`,
    color: p.text,
    '--cover-text': p.text,
    '--cover-sub': p.sub,
    '--cover-border': p.border,
    '--cover-spine': p.spine,
  }
}
