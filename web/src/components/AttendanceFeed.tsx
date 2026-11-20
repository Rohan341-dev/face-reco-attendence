import { useEffect, useRef, useState } from 'react'

import { Badge, Card, CardHeader, CardTitle } from '@/components/ui'
import { getAccessToken } from '@/lib/api/client'
import { formatDateTime, titleCase } from '@/lib/utils'

type FeedEvent = {
  id: string
  person_id: string
  event_type: string
  occurred_at: string
  verification_status: string
  source: string
  date: string
}

export function AttendanceFeed() {
  const [events, setEvents] = useState<FeedEvent[]>([])
  const [connected, setConnected] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    let socket: WebSocket | undefined
    let stopped = false

    const connect = () => {
      const token = getAccessToken()
      if (!token || stopped) return
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/attendance/?token=${encodeURIComponent(token)}`)
      socket.onopen = () => setConnected(true)
      socket.onclose = () => {
        setConnected(false)
        if (!stopped) timer.current = window.setTimeout(connect, 3000)
      }
      socket.onmessage = (message) => {
        try {
          const payload = JSON.parse(message.data) as FeedEvent
          setEvents((current) => [payload, ...current].slice(0, 12))
        } catch {
          // Ignore malformed frames; the feed is best-effort.
        }
      }
    }

    connect()
    return () => {
      stopped = true
      if (timer.current) window.clearTimeout(timer.current)
      socket?.close()
    }
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live attendance feed</CardTitle>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className={connected ? 'h-2 w-2 rounded-full bg-accent' : 'h-2 w-2 rounded-full bg-slate-600'} />
          {connected ? 'Connected' : 'Reconnecting'}
        </div>
      </CardHeader>
      {events.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-muted">Waiting for attendance events…</p>
      ) : (
        <ul className="divide-y divide-line">
          {events.map((event) => (
            <li key={event.id} className="flex items-center gap-3 px-5 py-3">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">
                <span className="text-[10px] font-semibold uppercase">{event.event_type.slice(0, 2)}</span>
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-slate-200">{titleCase(event.event_type)}</p>
                <p className="truncate text-xs text-muted">{formatDateTime(event.occurred_at)}</p>
              </div>
              <Badge tone={event.verification_status === 'verified_face' ? 'success' : 'info'}>
                {titleCase(event.source)}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
