import { useCallback, useEffect, useState } from "react"
import { Button, ScrollView, StyleSheet, Text, View } from "react-native"

import { api, clearTokens, getQueue, saveQueue, type QueuedEvent, type Schema } from "../lib/api"

async function record(type: "check_in" | "check_out", personId: string) {
  const event: QueuedEvent = {
    person_id: personId,
    event_type: type,
    occurred_at: new Date().toISOString(),
    source: "mobile",
    idempotency_key: `${Date.now()}-${crypto.randomUUID()}`,
    verification_status: "verified_manual",
  }
  try {
    await api.event(event)
    return "Recorded"
  } catch {
    await saveQueue([...(await getQueue()), event])
    return "Queued offline"
  }
}

export function HomeScreen({ onSignOut }: { onSignOut: () => void }) {
  const [me, setMe] = useState<Schema["User"] | null>(null)
  const [personId, setPersonId] = useState("")
  const [people, setPeople] = useState<Schema["Person"][]>([])
  const [message, setMessage] = useState("")
  const [queueCount, setQueueCount] = useState(0)

  const refresh = useCallback(async () => {
    try {
      const [profile, listed, queued] = await Promise.all([api.me(), api.people(), getQueue()])
      setMe(profile)
      setPeople(listed)
      setQueueCount(queued.length)
      const linked = listed.find((person) => person.user === profile.id)
      if (linked) setPersonId(linked.id)
      if (queued.length) {
        const result = await api.sync(queued)
        const accepted = new Set(result.results.filter((r) => r.status !== "rejected").map((r) => r.idempotency_key))
        await saveQueue(queued.filter((event) => !accepted.has(event.idempotency_key)))
        setQueueCount(queued.length - accepted.size)
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not refresh")
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Welcome{me ? `, ${me.first_name || me.email}` : ""}</Text>
      <Text style={styles.muted}>Attendance is verified by your organization before it is recorded.</Text>
      {people.length > 1 && (
        <View style={styles.people}>
          {people.slice(0, 8).map((person) => (
            <Button key={person.id} title={person.full_name} onPress={() => setPersonId(person.id)} />
          ))}
        </View>
      )}
      <View style={styles.actions}>
        <Button title="Check in" onPress={async () => setMessage(await record("check_in", personId))} disabled={!personId} />
        <Button title="Check out" onPress={async () => setMessage(await record("check_out", personId))} disabled={!personId} />
      </View>
      {message ? <Text style={styles.message}>{message}</Text> : null}
      <Text style={styles.muted}>Offline queue: {queueCount} event(s)</Text>
      <Button title="Sign out" onPress={async () => { await clearTokens(); onSignOut() }} />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#080d18" },
  content: { padding: 24, gap: 14 },
  title: { color: "#e6edf7", fontSize: 22, fontWeight: "700" },
  muted: { color: "#8b9ab4", fontSize: 13 },
  message: { color: "#6ee7b7", fontSize: 14 },
  actions: { gap: 10 },
  people: { gap: 6 },
})
