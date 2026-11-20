import { useState, type FormEvent } from 'react'

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, DialogContent, DialogTrigger, ErrorState, Field, Input, PageHeader, Table, Td, Th } from '@/components/ui'
import { errorMessage } from '@/lib/api/client'
import { useConsent, useConsentRecords, useCreatePerson, usePeople, useBranches } from '@/lib/api/queries'
import { formatDate, titleCase } from '@/lib/utils'

export function PeoplePage() {
  const people = usePeople()
  const branches = useBranches()
  const createPerson = useCreatePerson()
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ first_name: '', last_name: '', employee_id: '', email: '', branch: '' })

  const filtered = (people.data ?? []).filter((person) =>
    `${person.full_name} ${person.employee_id} ${person.email}`.toLowerCase().includes(search.toLowerCase()),
  )

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await createPerson.mutateAsync({
        first_name: form.first_name,
        last_name: form.last_name,
        employee_id: form.employee_id,
        email: form.email,
        branch: form.branch || null,
      })
      setOpen(false)
      setForm({ first_name: '', last_name: '', employee_id: '', email: '', branch: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <>
      <PageHeader
        title="People"
        description="Employees, consent state and biometric enrollment."
        action={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button>Add person</Button></DialogTrigger>
            <DialogContent title="Add a person" description="Creates their employment record as well.">
              <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
                <Field label="First name"><Input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></Field>
                <Field label="Last name"><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></Field>
                <Field label="Employee ID"><Input required value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} /></Field>
                <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
                <Field label="Branch">
                  <select className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm" value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value })}>
                    <option value="">Unassigned</option>
                    {(branches.data ?? []).map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
                  </select>
                </Field>
                {error && <p className="text-sm text-rose-300 sm:col-span-2">{error}</p>}
                <div className="sm:col-span-2"><Button type="submit" disabled={createPerson.isPending}>{createPerson.isPending ? 'Saving…' : 'Save person'}</Button></div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>{filtered.length} people</CardTitle>
          <Input className="h-9 w-64" placeholder="Search people…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </CardHeader>
        {people.isError ? (
          <ErrorState message="Could not load people." onRetry={() => people.refetch()} />
        ) : people.isLoading ? (
          <CardBody><p className="text-sm text-muted">Loading…</p></CardBody>
        ) : filtered.length === 0 ? (
          <CardBody><p className="text-center text-sm text-muted">No people match this view.</p></CardBody>
        ) : (
          <Table>
            <thead><tr><Th>Name</Th><Th>Employee ID</Th><Th>Branch</Th><Th>Status</Th><Th>Joined</Th><Th>Consent</Th></tr></thead>
            <tbody className="divide-y divide-line">
              {filtered.map((person) => <PersonRow key={person.id} personId={person.id} person={person} />)}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  )
}

type PersonRowProps = {
  personId: string
  person: NonNullable<ReturnType<typeof usePeople>['data']>[number]
}

function PersonRow({ personId, person }: PersonRowProps) {
  const consent = useConsent(personId)
  const records = useConsentRecords(personId)
  const [busy, setBusy] = useState(false)
  const granted = (records.data ?? []).find((record) => record.purpose === 'biometric_attendance')?.granted ?? false

  const toggle = async () => {
    setBusy(true)
    try {
      if (granted) await consent.withdraw('biometric_attendance', 'Withdrawn from web dashboard')
      else await consent.grant('biometric_attendance', 'Granted via web dashboard')
      await records.refetch()
    } finally {
      setBusy(false)
    }
  }

  return (
    <tr>
      <Td className="font-medium text-slate-200">{person.full_name}</Td>
      <Td>{person.employee_id || '—'}</Td>
      <Td>{person.branch_name ?? '—'}</Td>
      <Td><Badge tone={person.status === 'active' ? 'success' : 'warning'}>{titleCase(person.status)}</Badge></Td>
      <Td>{formatDate(person.date_of_joining)}</Td>
      <Td>
        <div className="flex items-center gap-2">
          <Badge tone={granted ? 'success' : 'neutral'}>{granted ? 'Consented' : 'Not consented'}</Badge>
          <Button variant="secondary" size="sm" onClick={toggle} disabled={busy}>
            {granted ? 'Withdraw' : 'Grant'}
          </Button>
        </div>
      </Td>
    </tr>
  )
}
