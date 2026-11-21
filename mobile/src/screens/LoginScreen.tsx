import { useState } from "react"
import { ActivityIndicator, Button, StyleSheet, Text, TextInput, View } from "react-native"

import { api, saveTokens } from "../lib/api"

export function LoginScreen({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    setError("")
    try {
      const result = await api.login(email.trim(), password)
      if ("mfa_required" in result) {
        setError("MFA is enabled. Approve this sign-in from a device that supports TOTP, then sign in again.")
        return
      }
      await saveTokens(result.access, result.refresh)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>FaceTrack AI</Text>
      <Text style={styles.subtitle}>Attendance, wherever you work.</Text>
      <TextInput style={styles.input} placeholder="Work email" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} />
      <TextInput style={styles.input} placeholder="Password" secureTextEntry value={password} onChangeText={setPassword} />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {busy ? <ActivityIndicator /> : <Button title="Sign in" onPress={submit} />}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#080d18", gap: 12 },
  title: { color: "#e6edf7", fontSize: 26, fontWeight: "700" },
  subtitle: { color: "#8b9ab4", fontSize: 14, marginBottom: 18 },
  input: { borderColor: "#1e2a40", borderWidth: 1, borderRadius: 10, padding: 12, color: "#e6edf7", backgroundColor: "#0f1727" },
  error: { color: "#fda4af", fontSize: 13 },
})
