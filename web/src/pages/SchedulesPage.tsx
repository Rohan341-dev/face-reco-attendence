import { useState, type FormEvent } from 'react'

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, DialogContent, DialogTrigger, Field, Input, PageHeader, Table, Td, Th } from '@/components/ui'
import { errorMessage } from '@/lib/api/client'
import { useCreateHoliday, useCreateShift, useDecideLeave, useHolidays, useLeaves, useShifts } from '@/lib/api/queries'
import { titleCase } from '@/lib/utils'

export function SchedulesPage() {
  const shifts = useShifts()
  const holidays = useHolidays()
  const leaves = useLeaves()
  const createShift = useCreateShift()
  const createHoliday = useCreateHoliday()
  const decide = useDecideLeave()
  const [shiftOpen, setShiftOpen] = useState(false)
  const [holidayOpen, setHolidayOpen] = useState(false)
  const [error, setError] = useState('')
  const [shift, setShift] = useState({ name: '', start_time: '09:00', end_time: '18:00', grace_minutes: '10' })
  const [holiday, setHoliday] = useState({ name: '', date: '', is_working_day: false })

  const saveShift = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await createShift.mutateAsync({
        name: shift.name,
        start_time: `${shift.start_time}:00`,
        end_time: `${shift.end_time}:00`,
        grace_minutes: Number(shift.grace_minutes),
      })
      setShiftOpen(false)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const saveHoliday = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await createHoliday.mutateAsync({ name: holiday.name, date: holiday.date, is_working_day: holiday.is_working_day })
      setHolidayOpen(false)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <>
      <PageHeader
        title="Schedules"
        description="Shifts, holidays and leave approvals that drive attendance eligibility."
        action={
          <div className="flex gap-2">
            <Dialog open={holidayOpen} onOpenChange={setHolidayOpen}>
              <DialogTrigger asChild><Button variant="secondary">Add holiday</Button></DialogTrigger>
              <DialogContent title="Add a holiday">
                <form onSubmit={saveHoliday} className="grid gap-4">
                  <Field label="Name"><Input required value={holiday.name} onChange={(e) => setHoliday({ ...holiday, name: e.target.value })} /></Field>
                  <Field label="Date"><Input required type="date" value={holiday.date} onChange={(e) => setHoliday({ ...holiday, date: e.target.value })} /></Field>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input type="checkbox" checked={holiday.is_working_day} onChange={(e) => setHoliday({ ...holiday, is_working_day: e.target.checked })} />
                    Working day
                  </label>
                  {error && <p className="text-sm text-rose-300">{error}</p>}
                  <Button type="submit">Save holiday</Button>
                </form>
              </DialogContent>
            </Dialog>
            <Dialog open={shiftOpen} onOpenChange={setShiftOpen}>
              <DialogTrigger asChild><Button>Add shift</Button></DialogTrigger>
              <DialogContent title="Create a shift">
                <form onSubmit={saveShift} className="grid gap-4 sm:grid-cols-2">
                  <Field label="Name"><Input required value={shift.name} onChange={(e) => setShift({ ...shift, name: e.target.value })} /></Field>
                  <Field label="Grace (minutes)"><Input type="number" min={0} value={shift.grace_minutes} onChange={(e) => setShift({ ...shift, grace_minutes: e.target.value })} /></Field>
                  <Field label="Start time"><Input required type="time" value={shift.start_time} onChange={(e) => setShift({ ...shift, start_time: e.target.value })} /></Field>
                  <Field label="End time"><Input required type="time" value={shift.end_time} onChange={(e) => setShift({ ...shift, end_time: e.target.value })} /></Field>
                  {error && <p className="text-sm text-rose-300 sm:col-span-2">{error}</p>}
                  <div className="sm:col-span-2"><Button type="submit">Save shift</Button></div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Shifts</CardTitle><Badge>{shifts.data?.length ?? 0}</Badge></CardHeader>
          {(shifts.data ?? []).length === 0 ? <CardBody><p className="text-center text-sm text-muted">No shifts defined.</p></CardBody> : (
            <Table>
              <thead><tr><Th>Name</Th><Th>Hours</Th><Th>Grace</Th><Th>Type</Th></tr></thead>
              <tbody className="divide-y divide-line">
                {shifts.data!.map((item) => (
                  <tr key={item.id}>
                    <Td className="font-medium text-slate-200">{item.name}</Td>
                    <Td>{item.start_time} – {item.end_time}</Td>
                    <Td>{item.grace_minutes}m</Td>
                    <Td><Badge tone={item.is_overnight ? 'warning' : 'info'}>{item.is_overnight ? 'Overnight' : 'Standard'}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>Holidays</CardTitle><Badge>{holidays.data?.length ?? 0}</Badge></CardHeader>
          {(holidays.data ?? []).length === 0 ? <CardBody><p className="text-center text-sm text-muted">No holidays defined.</p></CardBody> : (
            <Table>
              <thead><tr><Th>Name</Th><Th>Date</Th><Th>Type</Th></tr></thead>
              <tbody className="divide-y divide-line">
                {holidays.data!.map((item) => (
                  <tr key={item.id}>
                    <Td className="font-medium text-slate-200">{item.name}</Td>
                    <Td>{item.date}</Td>
                    <Td><Badge tone={item.is_working_day ? 'info' : 'success'}>{item.is_working_day ? 'Working' : 'Day off'}</Badge></Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Leave requests</CardTitle><Badge>{leaves.data?.length ?? 0}</Badge></CardHeader>
        {(leaves.data ?? []).length === 0 ? <CardBody><p className="text-center text-sm text-muted">No leave requests.</p></CardBody> : (
          <Table>
            <thead><tr><Th>Person</Th><Th>Type</Th><Th>From</Th><Th>To</Th><Th>Status</Th><Th>Action</Th></tr></thead>
            <tbody className="divide-y divide-line">
              {leaves.data!.map((leave) => (
                <tr key={leave.id}>
                  <Td className="font-medium text-slate-200">{leave.person_name ?? '—'}</Td>
                  <Td>{titleCase(leave.leave_type)}</Td>
                  <Td>{leave.start_date}</Td>
                  <Td>{leave.end_date}</Td>
                  <Td><Badge tone={leave.status === 'approved' ? 'success' : leave.status === 'rejected' ? 'danger' : 'warning'}>{titleCase(leave.status)}</Badge></Td>
                  <Td>
                    {leave.status === 'pending' ? (
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => decide.mutate({ id: leave.id, decision: 'approved' })}>Approve</Button>
                        <Button size="sm" variant="danger" onClick={() => decide.mutate({ id: leave.id, decision: 'rejected' })}>Reject</Button>
                      </div>
                    ) : <span className="text-muted">—</span>}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}
