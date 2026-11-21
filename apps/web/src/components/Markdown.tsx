import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useMemo } from 'react'
import type { Source } from '../api/client'

marked.setOptions({ gfm: true, breaks: true })

/** Render Alden's markdown safely, turning [F12] / [S1] / [W1] citations into links. */
export function Markdown({ text, sources = [] }: { text: string; sources?: Source[] }) {
  const html = useMemo(() => {
    const byId = new Map(sources.map((s) => [s.id, s]))
    const rendered = marked.parse(text, { async: false }) as string
    const withCites = rendered.replace(/[[【]\s*([FSW]\d+)\s*[\]】]/g, (_match, id: string) => {
      const s = byId.get(id)
      if (!s) return ''
      const title = s.title.replace(/"/g, '&quot;')
      return s.url
        ? `<a class="cite" href="${s.url}" target="_blank" rel="noopener noreferrer" title="${title}">${id}</a>`
        : `<span class="cite" title="${title}">${id}</span>`
    })
    return DOMPurify.sanitize(withCites, { ADD_ATTR: ['target'] })
  }, [text, sources])
  return <div dangerouslySetInnerHTML={{ __html: html }} />
}
