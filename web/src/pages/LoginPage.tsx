import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'

import { Button, Card, CardBody, Field, Input } from '@/components/ui'
import { setTokens, errorMessage, type Schema } from '@/lib/api/client'
import { useLogin } from '@/lib/api/queries'
import { useAuth } from '@/lib/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const login = useLogin()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const result = await login.mutateAsync(form as Schema['FaceTrackTokenObtainPair'])
      if ('mfa_required' in result) {
        navigate('/mfa', { state: { mfaToken: result.mfa_token } })
        return
      }
      setTokens(result.access, result.refresh)
      signIn(result.access, result.refresh)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent/15 text-accent">
            <Activity size={22} />
          </span>
          <div>
            <p className="text-lg font-semibold">FaceTrack AI</p>
            <p className="text-xs text-muted">Workforce attendance, secured</p>
          </div>
        </div>
        <Card>
          <CardBody className="space-y-5">
            <div>
              <h1 className="text-lg font-semibold">Sign in</h1>
              <p className="mt-1 text-sm text-muted">Use your organization account.</p>
            </div>
            <form onSubmit={submit} className="space-y-4">
              <Field label="Work email">
                <Input
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) => setForm({ ...form, email: event.target.value })}
                  placeholder="you@company.com"
                />
              </Field>
              <Field label="Password">
                <Input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={form.password}
                  onChange={(event) => setForm({ ...form, password: event.target.value })}
                  placeholder="••••••••"
                />
              </Field>
              {error && <p className="text-sm text-rose-300">{error}</p>}
              <Button type="submit" className="w-full" disabled={login.isPending}>
                {login.isPending ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
            <p className="text-center text-sm text-muted">
              New organization? <Link className="text-emerald-300 hover:underline" to="/onboard">Create one</Link>
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
