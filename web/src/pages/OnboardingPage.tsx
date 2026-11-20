import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button, Card, CardBody, Field, Input, Select } from '@/components/ui'
import { errorMessage, setTokens, type Schema } from '@/lib/api/client'
import { useOnboard } from '@/lib/api/queries'
import { useAuth } from '@/lib/auth'

const initial: Schema['Onboarding'] = {
  organization_name: '',
  slug: '',
  industry: 'office',
  timezone: 'UTC',
  owner_email: '',
  owner_username: '',
  owner_first_name: '',
  owner_last_name: '',
  password: '',
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const onboard = useOnboard()
  const [form, setForm] = useState<Schema['Onboarding']>(initial)
  const [error, setError] = useState('')

  const update = (key: keyof Schema['Onboarding'], value: string) => setForm((state) => ({ ...state, [key]: value }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const result = await onboard.mutateAsync(form)
      setTokens(result.access, result.refresh)
      signIn(result.access, result.refresh)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="min-h-screen bg-canvas px-4 py-12">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="text-xl font-semibold">Create your workspace</h1>
        <p className="mt-1 text-sm text-muted">Sets up your organization, first branch, settings and owner account.</p>
        <Card className="mt-6">
          <CardBody>
            <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
              <Field label="Organization name">
                <Input required value={form.organization_name} onChange={(e) => update('organization_name', e.target.value)} />
              </Field>
              <Field label="URL slug">
                <Input required pattern="[a-z0-9-]+" value={form.slug} onChange={(e) => update('slug', e.target.value)} />
              </Field>
              <Field label="Industry">
                <Select value={form.industry} onChange={(e) => update('industry', e.target.value)}>
                  {['school', 'college', 'office', 'factory', 'hospital', 'retail', 'other'].map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Timezone" hint="IANA name, e.g. Asia/Kolkata">
                <Input value={form.timezone} onChange={(e) => update('timezone', e.target.value)} />
              </Field>
              <Field label="Owner first name">
                <Input required value={form.owner_first_name} onChange={(e) => update('owner_first_name', e.target.value)} />
              </Field>
              <Field label="Owner last name">
                <Input value={form.owner_last_name} onChange={(e) => update('owner_last_name', e.target.value)} />
              </Field>
              <Field label="Owner email">
                <Input required type="email" value={form.owner_email} onChange={(e) => update('owner_email', e.target.value)} />
              </Field>
              <Field label="Username">
                <Input required value={form.owner_username} onChange={(e) => update('owner_username', e.target.value)} />
              </Field>
              <Field label="Password" hint="Use at least 12 characters with mixed case and symbols.">
                <Input required type="password" minLength={12} value={form.password} onChange={(e) => update('password', e.target.value)} />
              </Field>
              {error && <p className="text-sm text-rose-300 sm:col-span-2">{error}</p>}
              <div className="flex items-center gap-4 sm:col-span-2">
                <Button type="submit" disabled={onboard.isPending}>
                  {onboard.isPending ? 'Creating…' : 'Create workspace'}
                </Button>
                <Link to="/login" className="text-sm text-muted hover:text-slate-200">I already have an account</Link>
              </div>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
