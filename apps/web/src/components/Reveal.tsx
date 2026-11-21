import { createElement, useEffect, useRef, useState, type CSSProperties, type ElementType, type ReactNode } from 'react'

type Variant = 'up' | 'left' | 'right' | 'scale' | 'rise'

interface RevealProps {
  as?: ElementType
  variant?: Variant
  /** Delay in ms, e.g. index * 80 for a stagger. */
  delay?: number
  className?: string
  style?: CSSProperties
  children?: ReactNode
  [key: string]: unknown
}

/** Fades content in when it scrolls into view (once). Respects reduced motion via CSS. */
export function Reveal({ as = 'div', variant = 'up', delay = 0, className = '', style, children, ...rest }: RevealProps) {
  const ref = useRef<HTMLElement>(null)
  const [shown, setShown] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) { setShown(true); return }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setShown(true); io.disconnect() } },
      { threshold: 0.18, rootMargin: '0px 0px -8% 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return createElement(
    as,
    { ref, className: `rv rv-${variant}${shown ? ' in' : ''} ${className}`.trim(), style: { ...style, '--rv-delay': `${delay}ms` } as CSSProperties, ...rest },
    children,
  )
}
