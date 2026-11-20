import { Activity, CheckCircle2, Clock3, Users } from 'lucide-react'

import { AttendanceFeed } from '@/components/AttendanceFeed'
import { Badge, Card, CardBody, CardHeader, CardTitle, ErrorState, PageHeader, Skeleton, Table, Td, Th } from '@/components/ui'
import { useCurrentOrg, useEvents, usePeople, useRecords } from '@/lib/api/queries'
import { formatDate, formatDuration, titleCase } from '@/lib/utils'

function Stat({ label, value, hint, icon: Icon }: { label: string; value: string; hint: string; icon: typeof Users }) {
  return (
    <Card>
      <CardBody className="flex items-start gap-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">
          <Icon size={19} />
        </span>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">{value}</p>
          <p className="mt-1 text-xs text-muted">{hint}</p>
        </div>
      </CardBody>
    </Card>
  )
}

export function DashboardPage() {
  const org = useCurrentOrg()
  const people = usePeople({ status: 'active' })
  const records = useRecords()
  const events = useEvents()

  if (records.isError) {
    return <ErrorState message="Could not load attendance data." onRetry={() => records.refetch()} />
  }

  const today = new Date().toISOString().slice(0, 10)
  const todayRecords = (records.data ?? []).filter((record) => record.date === today)
  const present = todayRecords.filter((record) =>
    ['present', 'late', 'early_departure'].includes(record.status),
  ).length
  const late = todayRecords.filter((record) => record.status === 'late').length
  const onLeave = todayRecords.filter((record) => record.status === 'on_leave').length
  const worked = todayRecords.reduce((sum, record) => sum + record.total_work_seconds, 0)
  const verified = (events.data ?? []).filter((event) => event.verification_status.startsWith('verified')).length

  return (
    <>
      <PageHeader
        title={`Good day${org.data ? `, ${org.data.name}` : ''}`}
        description="Real-time view of attendance across your organization."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {people.isLoading || records.isLoading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)
        ) : (
          <>
            <Stat label="Active people" value={String(people.data?.length ?? 0)} hint="Registered in this tenant" icon={Users} />
            <Stat label="Present today" value={String(present)} hint={`${late} late arrival${late === 1 ? '' : 's'}`} icon={CheckCircle2} />
            <Stat label="Hours worked today" value={formatDuration(worked)} hint="From verified events" icon={Clock3} />
            <Stat label="On leave" value={String(onLeave)} hint="Approved for today" icon={Activity} />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent attendance</CardTitle>
            <Badge tone="info">{verified} verified events loaded</Badge>
          </CardHeader>
          {events.isLoading ? (
            <div className="space-y-2 p-5"><Skeleton className="h-8" /><Skeleton className="h-8" /><Skeleton className="h-8" /></div>
          ) : (events.data ?? []).length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted">No events recorded yet. Events appear here as people check in.</p>
          ) : (
            <Table>
              <thead><tr><Th>Person</Th><Th>Event</Th><Th>When</Th><Th>Verification</Th><Th>Source</Th></tr></thead>
              <tbody className="divide-y divide-line">
                {events.data!.slice(0, 8).map((event) => (
                  <tr key={event.id}>
                    <Td className="font-medium text-slate-200">{event.person_name ?? '—'}</Td>
                    <Td>{titleCase(event.event_type)}</Td>
                    <Td>{new Date(event.occurred_at).toLocaleString()}</Td>
                    <Td><Badge tone={event.verification_status === 'verified_face' ? 'success' : 'neutral'}>{titleCase(event.verification_status)}</Badge></Td>
                    <Td>{titleCase(event.source)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
        <AttendanceFeed />
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Daily status</CardTitle><Badge>{todayRecords.length} records today</Badge></CardHeader>
        {todayRecords.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-muted">No daily records for {formatDate(today)} yet.</p>
        ) : (
          <Table>
            <thead><tr><Th>Person</Th><Th>Status</Th><Th>Check in</Th><Th>Check out</Th><Th>Worked</Th></tr></thead>
            <tbody className="divide-y divide-line">
              {todayRecords.map((record) => (
                <tr key={record.id}>
                  <Td className="font-medium text-slate-200">{record.person_name ?? '—'}</Td>
                  <Td><Badge tone={record.status === 'present' ? 'success' : record.status === 'absent' ? 'danger' : 'warning'}>{titleCase(record.status)}</Badge></Td>
                  <Td>{record.first_check_in ? new Date(record.first_check_in).toLocaleTimeString() : '—'}</Td>
                  <Td>{record.last_check_out ? new Date(record.last_check_out).toLocaleTimeString() : '—'}</Td>
                  <Td className="tabular-nums">{formatDuration(record.total_work_seconds)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}
