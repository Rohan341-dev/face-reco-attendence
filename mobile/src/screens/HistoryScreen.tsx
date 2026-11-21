import { useCallback, useEffect, useState } from "react"
import { FlatList, StyleSheet, Text, View } from "react-native"

import { api, type Schema } from "../lib/api"

export function HistoryScreen() {
  const [records, setRecords] = useState<Schema["AttendanceRecord"][]>([])
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    try {
      setRecords(await api.records())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load history")
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Attendance history</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={records}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={styles.date}>{item.date}</Text>
            <Text style={styles.status}>{item.status.replace("_", " ")}</Text>
            <Text style={styles.muted}>{item.total_work_seconds ? `${Math.round(item.total_work_seconds / 60)} min` : "—"}</Text>
          </View>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#080d18", padding: 20 },
  title: { color: "#e6edf7", fontSize: 20, fontWeight: "700", marginBottom: 12 },
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 12, borderBottomColor: "#1e2a40", borderBottomWidth: 1 },
  date: { color: "#e6edf7" },
  status: { color: "#6ee7b7" },
  muted: { color: "#8b9ab4" },
  error: { color: "#fda4af", marginBottom: 8 },
})
