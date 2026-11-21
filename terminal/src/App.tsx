import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"

import { api, clearDeviceToken, getDeviceToken, getQueue, setDeviceToken, setQueue, type QueuedEvent, type Schema } from "./lib/api"

type Status = { tone: string; text: string }

export default function App() {
  const [token, setToken] = useState("")
  const [pairing, setPairing] = useState(!getDeviceToken())
  const [device, setDevice] = useState<Schema["Device"] | null>(null)
  const [people, setPeople] = useState<Schema["Person"][]>([])
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<Schema["Person"] | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [queue, setQueueState] = useState<QueuedEvent[]>(getQueue())
  const [online, setOnline] = useState(navigator.onLine)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [cameraOn, setCameraOn] = useState(false)

  const refreshQueue = useCallback(() => setQueueState(getQueue()), [])

  const load = useCallback(async () => {
    try {
      const [current, listed] = await Promise.all([api.current(), api.people()])
      setDevice(current)
      setPeople(listed)
    } catch (error) {
      setStatus({ tone: "error", text: error instanceof Error ? error.message : "Could not load device" })
      if (error instanceof Error && /device|token/i.test(error.message)) {
        clearDeviceToken()
        setPairing(true)
      }
    }
  }, [])

  useEffect(() => {
    if (!pairing) void load()
  }, [pairing, load])

  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener("online", on)
    window.addEventListener("offline", off)
    return () => {
      window.removeEventListener("online", on)
      window.removeEventListener("offline", off)
    }
  }, [])

  const flush = useCallback(async () => {
    const pending = getQueue()
    if (!pending.length || !navigator.onLine) return
    try {
      const result = await api.sync(pending)
      const accepted = new Set(result.results.filter((r) => r.status !== "rejected").map((r) => r.idempotency_key))
      setQueue(pending.filter((event) => !accepted.has(event.idempotency_key)))
      refreshQueue()
      setStatus({ tone: "ok", text: `Synced ${accepted.size} offline event(s)` })
    } catch (error) {
      setStatus({ tone: "error", text: error instanceof Error ? error.message : "Sync failed" })
    }
  }, [refreshQueue])

  useEffect(() => {
    if (online && queue.length) void flush()
  }, [online, queue.length, flush])

  const pair = async (event: FormEvent) => {
    event.preventDefault()
    setStatus(null)
    try {
      const result = await api.auth(token.trim())
      setDeviceToken(result.access)
      setPairing(false)
      setToken("")
    } catch (error) {
      setStatus({ tone: "error", text: error instanceof Error ? error.message : "Pairing failed" })
    }
  }

  const toggleCamera = async () => {
    if (cameraOn) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setCameraOn(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraOn(true)
    } catch {
      setStatus({ tone: "error", text: "Camera unavailable. Use the ID fallback below." })
    }
  }

  useEffect(() => () => streamRef.current?.getTracks().forEach((track) => track.stop()), [])

  const record = async (eventType: Schema["AttendanceEventInput"]["event_type"]) => {
    if (!selected) {
      setStatus({ tone: "error", text: "Select a person first" })
      return
    }
    const event: QueuedEvent = {
      person_id: selected.id,
      event_type: eventType,
      occurred_at: new Date().toISOString(),
      source: "terminal",
      idempotency_key: crypto.randomUUID(),
      verification_status: "verified_device",
      metadata: { kiosk: true },
    }
    try {
      await api.event(event)
      setStatus({ tone: "ok", text: `${selected.full_name}: ${eventType.replace("_", " ")} recorded` })
    } catch {
      setQueue([...getQueue(), event])
      refreshQueue()
      setStatus({ tone: "warn", text: "Offline — event queued for synchronization" })
    }
  }

  const filtered = people.filter((person) =>
    `${person.full_name} ${person.employee_id ?? ""}`.toLowerCase().includes(query.toLowerCase()),
  )

  if (pairing) {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <form onSubmit={pair} className="w-full max-w-md rounded-xl border border-line bg-surface p-6">
          <h1 className="text-lg font-semibold">Pair this terminal</h1>
          <p className="mt-1 text-sm text-slate-400">Enter the one-time token from the organization dashboard.</p>
          <input
            required
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Pairing token"
            className="mt-5 h-11 w-full rounded-lg border border-line bg-slate-950 px-3 text-sm outline-none focus:border-emerald-500"
          />
          <button type="submit" className="mt-4 h-11 w-full rounded-lg bg-emerald-500 font-medium text-slate-950">
            Pair device
          </button>
          {status && <p className={`mt-3 text-sm ${status.tone === "error" ? "text-rose-300" : "text-emerald-300"}`}>{status.text}</p>}
        </form>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 lg:p-8">
      <header className="mx-auto mb-6 flex max-w-5xl items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">FaceTrack Terminal</h1>
          <p className="text-xs text-slate-400">{device?.name ?? "Loading device…"} · {device?.branch_name ?? "Unassigned branch"}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">{online ? "Online" : "Offline"} · {queue.length} queued</span>
          <button
            onClick={() => void flush()}
            disabled={!online || !queue.length}
            className="rounded-lg border border-line px-3 py-2 text-xs text-slate-200 disabled:opacity-40"
          >
            Sync now
          </button>
          <button
            onClick={() => { clearDeviceToken(); setPairing(true) }}
            className="rounded-lg border border-line px-3 py-2 text-xs text-slate-400"
          >
            Forget device
          </button>
        </div>
      </header>

      <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-sm font-semibold">Camera</h2>
          <video ref={videoRef} muted playsInline className="mt-4 aspect-video w-full rounded-lg bg-slate-950 object-cover" />
          <button onClick={() => void toggleCamera()} className="mt-4 w-full rounded-lg border border-line py-2.5 text-sm text-slate-200">
            {cameraOn ? "Stop camera" : "Start camera"}
          </button>
          <p className="mt-3 text-xs text-slate-500">Frames are shown for operator verification only and are never stored by the terminal.</p>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-sm font-semibold">Identify person</h2>
          <input
            value={query}
            onChange={(event) => { setQuery(event.target.value); setSelected(null) }}
            placeholder="Search by name or employee ID"
            className="mt-4 h-11 w-full rounded-lg border border-line bg-slate-950 px-3 text-sm outline-none focus:border-emerald-500"
          />
          <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto">
            {filtered.map((person) => (
              <li key={person.id}>
                <button
                  onClick={() => setSelected(person)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                    selected?.id === person.id ? "bg-emerald-500/15 text-emerald-200" : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  <span className="font-medium">{person.full_name}</span>
                  <span className="ml-2 text-xs text-slate-500">{person.employee_id}</span>
                </button>
              </li>
            ))}
          </ul>
          {selected && <p className="mt-2 text-xs text-emerald-300">Selected: {selected.full_name}</p>}

          <div className="mt-5 grid grid-cols-2 gap-3">
            <button onClick={() => void record("check_in")} className="rounded-lg bg-emerald-500 py-3 text-sm font-semibold text-slate-950">
              Check in
            </button>
            <button onClick={() => void record("check_out")} className="rounded-lg border border-line py-3 text-sm font-semibold text-slate-200">
              Check out
            </button>
          </div>
          {status && (
            <p className={`mt-4 text-sm ${
              status.tone === "error" ? "text-rose-300" : status.tone === "warn" ? "text-amber-300" : "text-emerald-300"
            }`}>{status.text}</p>
          )}
        </section>
      </div>
    </div>
  )
}
