import { useState, useEffect, useRef, useCallback } from 'react'

export interface StepProgress {
  name: string
  status: 'pending' | 'running' | 'completed' | 'error'
  percent: number
  message: string
}

export interface PipelineProgressData {
  project_id: string
  overall_percent: number
  current_step: string
  done: boolean
  error: string | null
  steps: Record<string, StepProgress>
}

async function getBase(): Promise<string> {
  if (window.electronAPI?.getBackendUrl) {
    return await window.electronAPI.getBackendUrl()
  }
  return ''
}

export function usePipelineProgress(projectId: string | null) {
  const [progress, setProgress] = useState<PipelineProgressData | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(async () => {
    if (!projectId) return

    const base = await getBase()
    const url = `${base}/api/progress/${encodeURIComponent(projectId)}`

    try {
      const es = new EventSource(url)
      eventSourceRef.current = es

      es.onopen = () => {
        setIsConnected(true)
      }

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as PipelineProgressData
          setProgress(data)
        } catch (err) {
          console.error('Failed to parse progress data:', err)
        }
      }

      es.onerror = () => {
        setIsConnected(false)
        es.close()
        eventSourceRef.current = null

        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 3000)
      }
    } catch (err) {
      console.error('Failed to connect to progress stream:', err)
    }
  }, [projectId])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsConnected(false)
  }, [])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  const reset = useCallback(() => {
    setProgress(null)
  }, [])

  return {
    progress,
    isConnected,
    reset,
  }
}
