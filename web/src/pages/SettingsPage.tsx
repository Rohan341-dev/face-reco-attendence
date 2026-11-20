import { useEffect, useState, type FormEvent } from 'react'

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorState, Field, Input, PageHeader } from '@/components/ui'
import { errorMessage } from '@/lib/api/client'
import { useCurrentOrg, useSettings, useUpdateSettings } from '@/lib/api/queries'

export function SettingsPage() {
  const org = useCurrentOrg()
  const settings = useSettings()
  const update = useUpdateSettings()
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState({
    grace_minutes_late: '0',
    grace_minutes_early: '0',
    require_liveness: true,
    allow_manual_attendance: true,
    biometric_retention_days: '365',
    image_retention_hours: '24',
    dedupe_window_seconds: '120',
  })

  useEffect(() => {
    const data = settings.data
    if (!data) return
    setForm({
      grace_minutes_late: String(data.grace_minutes_late ?? 0),
      grace_minutes_early: String(data.grace_minutes_early ?? 0),
      require_liveness: Boolean(data.require_liveness),
      allow_manual_attendance: Boolean(data.allow_manual_attendance),
      biometric_retention_days: String(data.biometric_retention_days ?? 365),
      image_retention_hours: String(data.image_retention_hours ?? 24),
      dedupe_window_seconds: String(data.dedupe_window_seconds ?? 120),
    })
  }, [settings.data])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    try {
      await update.mutateAsync({
        grace_minutes_late: Number(form.grace_minutes_late),
        grace_minutes_early: String(form.grace_minutes_early) ? Number(form.grace_minutes_early) : undefined,
        require_liveness: form.require_liveness,
        allow_manual_attendance: form.allow_manual_attendance,
        biometric_retention_days: Number(form.biometric_retention_days),
        image_retention_hours: Number(form.image_retention_hours),
        dedupe_window_seconds: Number(form.dedupe_window_seconds),
      })
      setSuccess('Settings saved.')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  if (settings.isError) return <ErrorState message="Could not load organization settings." onRetry={() => settings.refetch()} />

  return (
    <>
      <PageHeader title="Organization settings" description="Verification, retention and grace rules for this tenant." />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Organization</CardTitle><Badge tone="info">{org.data?.industry ?? '—'}</Badge></CardHeader>
          <CardBody className="space-y-2 text-sm">
            <p className="text-slate-200">{org.data?.name ?? 'Loading…'}</p>
            <p className="text-muted">Slug: {org.data?.slug ?? '—'}</p>
            <p className="text-muted">Timezone: {org.data?.timezone ?? '—'}</p>
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader><CardTitle>Attendance policy</CardTitle></CardHeader>
          <CardBody>
            <form onSubmit={submit} className="grid gap-5 sm:grid-cols-2">
              <Field label="Late grace (minutes)"><Input type="number" min={0} value={form.grace_minutes_late} onChange={(e) => setForm({ ...form, grace_minutes_late: e.target.value })} /></Field>
              <Field label="Early grace (minutes)"><Input type="number" min={0} value={form.grace_minutes_early} onChange={(e) => setForm({ ...form, grace_minutes_early: e.target.value })} /></Field>
              <Field label="Dedupe window (seconds)"><Input type="number" min={0} value={form.dedupe_window_seconds} onChange={(e) => setForm({ ...form, dedupe_window_seconds: e.target.value })} /></Field>
              <Field label="Biometric retention (days)"><Input type="number" min={1} value={form.biometric_retention_days} onChange={(e) => setForm({ ...form, biometric_retention_days: e.target.value })} /></Field>
              <Field label="Image retention (hours)"><Input type="number" min={0} value={form.image_retention_hours} onChange={(e) => setForm({ ...form, image_retention_hours: e.target.value })} /></Field>
              <div className="space-y-3 pt-6">
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={form.require_liveness} onChange={(e) => setForm({ ...form, require_liveness: e.target.checked })} />
                  Require liveness for face verification
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={form.allow_manual_attendance} onChange={(e) => setForm({ ...form, allow_manual_attendance: e.target.checked })} />
                  Allow manually verified attendance
                </label>
              </div>
              {error && <p className="text-sm text-rose-300 sm:col-span-2">{error}</p>}
              {success && <p className="text-sm text-emerald-300 sm:col-span-2">{success}</p>}
              <div className="sm:col-span-2"><Button type="submit" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save settings'}</Button></div>
            </form>
          </CardBody>
        </Card>
      </div>
    </>
  )
}
