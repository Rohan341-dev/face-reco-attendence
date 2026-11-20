import { useState, type FormEvent } from 'react'

import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Dialog, DialogContent, DialogTrigger, ErrorState, Field, Input, PageHeader, Select, Table, Td, Th } from '@/components/ui'
import { errorMessage } from '@/lib/api/client'
import { useBranches, useDeactivateDevice, useDevices, usePairDevice, useRotateDevice } from '@/lib/api/queries'
import { formatDateTime, titleCase } from '@/lib/utils'

export function DevicesPage() {
  const devices = useDevices()
  const branches = useBranches()
  const pair = usePairDevice()
  const rotate = useRotateDevice()
  const deactivate = useDeactivateDevice()
  const [open, setOpen] = useState(false)
  const [newToken, setNewToken] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', kind: 'terminal', branch: '' })

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const result = await pair.mutateAsync({
        name: form.name,
        kind: form.kind,
        branch: form.branch || undefined,
      })
      setNewToken(result.token)
      setForm({ name: '', kind: 'terminal', branch: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <>
      <PageHeader
        title="Devices"
        description="Paired web cameras, kiosk terminals and mobile devices."
        action={
          <Dialog open={open} onOpenChange={(value) => { setOpen(value); if (!value) setNewToken('') }}>
            <DialogTrigger asChild><Button>Pair device</Button></DialogTrigger>
            <DialogContent title="Pair a device" description="The pairing token is shown once and cannot be recovered.">
              {newToken ? (
                <div className="space-y-4">
                  <p className="text-sm text-muted">Save this token and enter it on the device:</p>
                  <code className="block break-all rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-200">{newToken}</code>
                  <Button variant="secondary" onClick={() => navigator.clipboard.writeText(newToken)}>Copy token</Button>
                </div>
              ) : (
                <form onSubmit={submit} className="grid gap-4">
                  <Field label="Device name"><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Front desk kiosk" /></Field>
                  <Field label="Kind">
                    <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                      {['terminal', 'camera', 'mobile'].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
                    </Select>
                  </Field>
                  <Field label="Branch">
                    <Select value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value })}>
                      <option value="">Unassigned</option>
                      {(branches.data ?? []).map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
                    </Select>
                  </Field>
                  {error && <p className="text-sm text-rose-300">{error}</p>}
                  <Button type="submit" disabled={pair.isPending}>{pair.isPending ? 'Pairing…' : 'Pair device'}</Button>
                </form>
              )}
            </DialogContent>
          </Dialog>
        }
      />

      <Card>
        <CardHeader><CardTitle>{devices.data?.length ?? 0} registered devices</CardTitle></CardHeader>
        {devices.isError ? (
          <ErrorState message="Could not load devices." onRetry={() => devices.refetch()} />
        ) : (devices.data ?? []).length === 0 ? (
          <CardBody><p className="text-center text-sm text-muted">No devices paired yet.</p></CardBody>
        ) : (
          <Table>
            <thead><tr><Th>Name</Th><Th>Kind</Th><Th>Branch</Th><Th>Status</Th><Th>Last seen</Th><Th>Actions</Th></tr></thead>
            <tbody className="divide-y divide-line">
              {devices.data!.map((device) => (
                <tr key={device.id}>
                  <Td className="font-medium text-slate-200">{device.name}</Td>
                  <Td>{titleCase(device.kind)}</Td>
                  <Td>{device.branch_name ?? '—'}</Td>
                  <Td><Badge tone={device.is_active ? 'success' : 'danger'}>{device.is_active ? 'Active' : 'Inactive'}</Badge></Td>
                  <Td>{formatDateTime(device.last_seen_at)}</Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={async () => {
                        const result = await rotate.mutateAsync(device.id)
                        setNewToken(result.token)
                        setOpen(true)
                      }}>Rotate token</Button>
                      {device.is_active && (
                        <Button variant="danger" size="sm" onClick={() => deactivate.mutate(device.id)}>Deactivate</Button>
                      )}
                    </div>
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
