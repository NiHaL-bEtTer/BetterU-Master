import type { SVGProps } from 'react'

const base = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', viewBox: '0 0 24 24', 'aria-hidden': true } as const
type P = SVGProps<SVGSVGElement>

export const IconToday = (p: P) => <svg {...base} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
export const IconLog = (p: P) => <svg {...base} {...p}><path d="M4 7h16M4 12h16M4 17h10" /></svg>
export const IconChat = (p: P) => <svg {...base} {...p}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1.1-4.6A8 8 0 1 1 21 12z" /></svg>
export const IconTrain = (p: P) => <svg {...base} {...p}><path d="M6 7v10M18 7v10M3 10v4M21 10v4M6 12h12" /></svg>
export const IconProgress = (p: P) => <svg {...base} {...p}><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></svg>
export const IconMe = (p: P) => <svg {...base} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
export const IconSend = (p: P) => <svg {...base} {...p}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
export const IconStop = (p: P) => <svg {...base} {...p}><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
export const IconTrash = (p: P) => <svg {...base} {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></svg>
export const IconStar = ({ filled, ...p }: P & { filled?: boolean }) => <svg {...base} fill={filled ? 'currentColor' : 'none'} {...p}><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" /></svg>
export const IconUp = (p: P) => <svg {...base} {...p}><path d="M7 10v11M7 10l4-7a2 2 0 0 1 3 2l-1 5h6a2 2 0 0 1 2 2.3l-1.4 7A2 2 0 0 1 17.6 21H7" /></svg>
export const IconDown = (p: P) => <svg {...base} {...p} style={{ transform: 'rotate(180deg)', ...p.style }}><path d="M7 10v11M7 10l4-7a2 2 0 0 1 3 2l-1 5h6a2 2 0 0 1 2 2.3l-1.4 7A2 2 0 0 1 17.6 21H7" /></svg>
export const IconCopy = (p: P) => <svg {...base} {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h8" /></svg>
export const IconBarcode = (p: P) => <svg {...base} {...p}><path d="M4 6v12M8 6v12M12 6v12M15 6v12M19 6v12" /></svg>
export const IconPlus = (p: P) => <svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>
