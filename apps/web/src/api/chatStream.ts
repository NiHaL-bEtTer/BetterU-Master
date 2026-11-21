import type { ChatAction, Source } from './client'

export type ChatEvent =
  | { event: 'token'; data: { text: string } }
  | { event: 'status'; data: { text: string } }
  | { event: 'sources'; data: { sources: Source[] } }
  | { event: 'actions'; data: { actions: ChatAction[] } }
  | { event: 'video'; data: { video_id: string } }
  | { event: 'done'; data: { message_id: number } }
  | { event: 'error'; data: { message: string } }

/**
 * POST a chat message and yield Server-Sent Events as they arrive.
 * (EventSource only supports GET, so we parse the stream from fetch.)
 */
export async function* streamChat(message: string, signal: AbortSignal): AsyncGenerator<ChatEvent> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ message }),
    signal,
  })
  if (!res.ok || !res.body) {
    let detail = `Server error (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* not JSON */
    }
    yield { event: 'error', data: { message: detail } }
    return
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += value
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      let event = 'message'
      const dataLines: string[] = []
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (!dataLines.length) continue
      try {
        yield { event, data: JSON.parse(dataLines.join('\n')) } as ChatEvent
      } catch {
        /* ignore malformed event */
      }
    }
  }
}
