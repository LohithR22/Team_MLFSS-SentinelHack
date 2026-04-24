import { useEffect, useRef, useState } from 'react'
import type { AlertPayload } from '../types'

interface State {
  connected: boolean
  last: AlertPayload | null
}

export function useAlertStream(): State {
  const [state, setState] = useState<State>({ connected: false, last: null })
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/alerts/`
    const socket = new WebSocket(url)
    ws.current = socket

    socket.onopen = () => setState(s => ({ ...s, connected: true }))
    socket.onclose = () => setState(s => ({ ...s, connected: false }))
    socket.onmessage = ev => {
      try {
        const data = JSON.parse(ev.data)
        if (data && data.code) {
          setState({ connected: true, last: data as AlertPayload })
        }
      } catch {
        /* ignore non-JSON frames (like the hello greeting) */
      }
    }

    return () => socket.close()
  }, [])

  return state
}
