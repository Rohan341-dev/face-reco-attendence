import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Button, Card, CardBody, Field, Input } from '@/components/ui'
import { errorMessage, setTokens } from '@/lib/api/client'
import { useMfaChallenge } from '@/lib/api/queries'
import { useAuth } from '@/lib/auth'

export function MfaPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const challenge = useMfaChallenge()
  const mfaToken = (location.state as { mfaToken?: string } | null)?.mfaToken ?? ''
  const [code, setCode] = useState('')
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      const result = await challenge.mutateAsync({ mfa_token: mfaToken, code })
      setTokens(result.access, result.refresh)
      signIn(result.access, result.refresh)
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  if (!mfaToken) {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <Card className="w-full max-w-md">
          <CardBody>
            <p className="text-sm text-rose-300">No MFA challenge found. Please sign in again.</p>
            <Button className="mt-4" onClick={() => navigate('/login')}>Back to sign in</Button>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-4">
      <Card className="w-full max-w-md">
        <CardBody className="space-y-5">
          <div>
            <h1 className="text-lg font-semibold">Two-factor verification</h1>
            <p className="mt-1 text-sm text-muted">Enter the 6-digit code from your authenticator app.</p>
          </div>
          <form onSubmit={submit} className="space-y-4">
            <Field label="Verification code">
              <Input
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                placeholder="000000"
              />
            </Field>
            {error && <p className="text-sm text-rose-300">{error}</p>}
            <Button type="submit" className="w-full" disabled={challenge.isPending}>
              {challenge.isPending ? 'Verifying…' : 'Verify'}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
