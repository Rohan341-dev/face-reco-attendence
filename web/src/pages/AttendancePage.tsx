import { useState, type FormEvent } from 'react'

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, DialogContent, DialogTrigger, ErrorState, Field, Input, PageHeader, Select, Table, Td, Th } from '@/components/ui'
import { errorMessage, type Schema } from '@/lib/api/client'
import { useAlerts, useCorrections, useCreateCorrection, useCreateEvent, usePeople, useRecords, useResolveAlert } from '@/lib/api/queries'
import { formatDateTime, formatDuration, titleCase } from '@/lib/utils'

type EventType = Schema['AttendanceEventInput']['event_type']
type CorrectionType = Schema['CorrectionInput']['new_event_type']

export function AttendancePage() {
  const records = useRecords()
  const alerts = useAlerts({ resolved: 'false' })
  const corrections = useCorrections()
  const people = usePeople({ status: 'active' })

  const [eventOpen, setEventOpen] = useState(false)
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [error, setError] = useState('')
  const [eventForm, setEventForm] = useState<{ person_id: string; event_type: EventType; occurred_at: string }>({
    person_id: '',
    event_type: 'check_in',
    occurred_at: new Date().toISOString().slice(0, 16),
  })
  const [correctionForm, setCorrectionForm] = useState<{ original_event: string; new_occurred_at: string; new_event_type: CorrectionType; reason: string }>({
    original_event: '',
    new_occurred_at: '',
    new_event_type: 'check_in',
    reason: '',
  })
  const createEvent = useCreateEvent()
  const createCorrection = useCreateCorrection()
  const resolveAlert = useResolveAlert()

  const submitEvent = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await createEvent.mutateAsync({
        person_id: eventForm.person_id,
        event_type: eventForm.event_type,
        occurred_at: new Date(eventForm.occurred_at).toISOString(),
        source: 'manual',
        idempotency_key: crypto.randomUUID(),
        verification_status: 'verified_manual',
      })
      setEventOpen(false)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const submitCorrection = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await createCorrection.mutateAsync({
        original_event: correctionForm.original_event,
        new_occurred_at: new Date(correctionForm.new_occurred_at).toISOString(),
        new_event_type: correctionForm.new_event_type,
        reason: correctionForm.reason,
      })
      setCorrectionOpen(false)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  if (records.isError) return <ErrorState message="Could not load attendance records." onRetry={() => records.refetch()} />

  return (
    <>
      <PageHeader
        title="Attendance"
        description="Immutable event ledger, daily records, corrections and missing checkouts."
        action={
          <div className="flex gap-2">
            <Dialog open={correctionOpen} onOpenChange={setCorrectionOpen}>
              <DialogTrigger asChild><Button variant="secondary">New correction</Button></DialogTrigger>
              <DialogContent title="Correct an event" description="The original event stays immutable; a correction record is appended.">
                <form onSubmit={submitCorrection} className="grid gap-4">
                  <Field label="Original event ID"><Input required value={correctionForm.original_event} onChange={(e) => setCorrectionForm({ ...correctionForm, original_event: e.target.value })} placeholder="uuid" /></Field>
                  <Field label="Corrected time"><Input required type="datetime-local" value={correctionForm.new_occurred_at} onChange={(e) => setCorrectionForm({ ...correctionForm, new_occurred_at: e.target.value })} /></Field>
                  <Field label="Corrected event type">
                    <Select value={correctionForm.new_event_type} onChange={(e) => setCorrectionForm({ ...correctionForm, new_event_type: e.target.value as CorrectionType })}>
                      {['check_in', 'check_out', 'break_start', 'break_end'].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
                    </Select>
                  </Field>
                  <Field label="Reason"><Input required value={correctionForm.reason} onChange={(e) => setCorrectionForm({ ...correctionForm, reason: e.target.value })} /></Field>
                  {error && <p className="text-sm text-rose-300">{error}</p>}
                  <Button type="submit" disabled={createCorrection.isPending}>Apply correction</Button>
                </form>
              </DialogContent>
            </Dialog>
            <Dialog open={eventOpen} onOpenChange={setEventOpen}>
              <DialogTrigger asChild><Button>Record manually</Button></DialogTrigger>
              <DialogContent title="Record an event" description="Manually verified events require manual attendance to be enabled.">
                <form onSubmit={submitEvent} className="grid gap-4">
                  <Field label="Person">
                    <Select required value={eventForm.person_id} onChange={(e) => setEventForm({ ...eventForm, person_id: e.target.value })}>
                      <option value="">Select a person</option>
                      {(people.data ?? []).map((person) => <option key={person.id} value={person.id}>{person.full_name}</option>)}
                    </Select>
                  </Field>
                  <Field label="Event type">
                    <Select value={eventForm.event_type} onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value as EventType })}>
                      {['check_in', 'check_out', 'break_start', 'break_end'].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
                    </Select>
                  </Field>
                  <Field label="Occurred at"><Input required type="datetime-local" value={eventForm.occurred_at} onChange={(e) => setEventForm({ ...eventForm, occurred_at: e.target.value })} /></Field>
                  {error && <p className="text-sm text-rose-300">{error}</p>}
                  <Button type="submit" disabled={createEvent.isPending}>Record event</Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader><CardTitle>Daily records</CardTitle><Badge>{records.data?.length ?? 0} total</Badge></CardHeader>
          {(records.data ?? []).length === 0 ? (
            <CardBody><p className="text-center text-sm text-muted">No daily records yet.</p></CardBody>
          ) : (
            <Table>
              <thead><tr><Th>Person</Th><Th>Date</Th><Th>Status</Th><Th>Check in</Th><Th>Check out</Th><Th>Worked</Th></tr></thead>
              <tbody className="divide-y divide-line">
                {(records.data ?? []).slice(0, 25).map((record) => (
                  <tr key={record.id}>
                    <Td className="font-medium text-slate-200">{record.person_name ?? '—'}</Td>
                    <Td>{record.date}</Td>
                    <Td><Badge tone={record.status === 'present' ? 'success' : record.status === 'absent' ? 'danger' : 'warning'}>{titleCase(record.status)}</Badge></Td>
                    <Td>{record.first_check_in ? formatDateTime(record.first_check_in) : '—'}</Td>
                    <Td>{record.last_check_out ? formatDateTime(record.last_check_out) : '—'}</Td>
                    <Td className="tabular-nums">{formatDuration(record.total_work_seconds)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Missing checkouts</CardTitle><Badge tone={(alerts.data ?? []).length ? 'warning' : 'neutral'}>{alerts.data?.length ?? 0}</Badge></CardHeader>
            {(alerts.data ?? []).length === 0 ? (
              <CardBody><p className="text-center text-sm text-muted">No unresolved alerts.</p></CardBody>
            ) : (
              <ul className="divide-y divide-line">
                {alerts.data!.map((alert) => (
                  <li key={alert.id} className="flex items-center gap-3 px-5 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-slate-200">{alert.person_name ?? '—'}</p>
                      <p className="text-xs text-muted">{alert.date}</p>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => resolveAlert.mutate(alert.id)}>Resolve</Button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader><CardTitle>Corrections</CardTitle><Badge>{corrections.data?.length ?? 0}</Badge></CardHeader>
            {(corrections.data ?? []).length === 0 ? (
              <CardBody><p className="text-center text-sm text-muted">No corrections recorded.</p></CardBody>
            ) : (
              <ul className="divide-y divide-line">
                {corrections.data!.slice(0, 6).map((correction) => (
                  <li key={correction.id} className="px-5 py-3">
                    <p className="text-sm text-slate-200">{correction.reason}</p>
                    <p className="mt-0.5 text-xs text-muted">{correction.new_event_type} · {formatDateTime(correction.new_occurred_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  )
}
