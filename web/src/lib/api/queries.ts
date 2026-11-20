import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'

import { request, type RequestOptions, type Schema } from './client'

type Params = RequestOptions['params']

function useGet<T>(key: string, path: string, params?: Params, options?: Partial<UseQueryOptions<T>>) {
  return useQuery<T>({
    queryKey: [key, params ?? {}],
    queryFn: () => request<T>(path, { params }),
    ...options,
  })
}

function useInvalidate() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries()
}

export const keys = {
  me: 'me',
  org: 'org',
  settings: 'settings',
  people: 'people',
  events: 'events',
  records: 'records',
  corrections: 'corrections',
  alerts: 'alerts',
  devices: 'devices',
  shifts: 'shifts',
  holidays: 'holidays',
  leaves: 'leaves',
  branches: 'branches',
}

export const useMe = (options?: Partial<UseQueryOptions<Schema['User']>>) =>
  useGet<Schema['User']>(keys.me, '/api/auth/me/', undefined, options)
export const useCurrentOrg = () => useGet<Schema['Organization']>(keys.org, '/api/organizations/current/')
export const useSettings = () => useGet<Schema['OrganizationSettings']>(keys.settings, '/api/organizations/settings/')

export const usePeople = (params?: Params) => useGet<Schema['Person'][]>(keys.people, '/api/people/', params)
export const useEvents = (params?: Params) => useGet<Schema['AttendanceEvent'][]>(keys.events, '/api/attendance/events/', params)
export const useRecords = (params?: Params) => useGet<Schema['AttendanceRecord'][]>(keys.records, '/api/attendance/records/', params)
export const useCorrections = () => useGet<Schema['CorrectionRecord'][]>(keys.corrections, '/api/attendance/corrections/')
export const useAlerts = (params?: Params) =>
  useGet<Schema['MissingCheckoutAlert'][]>(keys.alerts, '/api/attendance/missing-checkouts/', params)
export const useDevices = () => useGet<Schema['Device'][]>(keys.devices, '/api/devices/')
export const useShifts = () => useGet<Schema['Shift'][]>(keys.shifts, '/api/shifts/')
export const useHolidays = (params?: Params) => useGet<Schema['Holiday'][]>(keys.holidays, '/api/holidays/', params)
export const useLeaves = () => useGet<Schema['LeaveRequest'][]>(keys.leaves, '/api/leave-requests/')
export const useBranches = () => useGet<Schema['Branch'][]>(keys.branches, '/api/branches/')

export const useLogin = () =>
  useMutation({
    mutationFn: (body: Schema['FaceTrackTokenObtainPair']) =>
      request<Schema['AuthTokens'] | { mfa_required: boolean; mfa_token: string }>('/api/auth/login/', {
        method: 'POST',
        body,
      }),
  })

export const useMfaChallenge = () =>
  useMutation({
    mutationFn: (body: { mfa_token: string; code: string }) =>
      request<Schema['MFAVerifyResponse']>('/api/auth/mfa/challenge/', { method: 'POST', body }),
  })

export const useOnboard = () =>
  useMutation({
    mutationFn: (body: Schema['Onboarding']) =>
      request<Schema['AuthTokens']>('/api/organizations/onboarding/', { method: 'POST', body }),
  })

export const useCreatePerson = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Partial<Schema['Person']>) =>
      request<Schema['Person']>('/api/people/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useConsentRecords = (personId: string) =>
  useGet<Schema['ConsentRecord'][]>(`consents-${personId}`, `/api/people/${personId}/consents/`)

export const useConsent = (personId: string) => ({
  grant: (purpose: string, evidence: string) =>
    request(`/api/people/${personId}/consents/grant/`, { method: 'POST', body: { purpose, evidence } }),
  withdraw: (purpose: string, evidence: string) =>
    request(`/api/people/${personId}/consents/withdraw/`, { method: 'POST', body: { purpose, evidence } }),
})

export const useCreateEvent = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Schema['AttendanceEventInput']) =>
      request<Schema['AttendanceEvent']>('/api/attendance/events/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useCreateCorrection = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Schema['CorrectionInput']) =>
      request<Schema['CorrectionRecord']>('/api/attendance/corrections/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useResolveAlert = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) =>
      request(`/api/attendance/missing-checkouts/${id}/resolve/`, { method: 'POST', body: {} }),
    onSuccess: invalidate,
  })
}

export const usePairDevice = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: { name: string; kind: string; branch?: string }) =>
      request<Schema['Device'] & { token: string }>('/api/devices/pair/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useRotateDevice = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => request<{ token: string }>(`/api/devices/${id}/rotate/`, { method: 'POST', body: {} }),
    onSuccess: invalidate,
  })
}

export const useDeactivateDevice = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => request(`/api/devices/${id}/deactivate/`, { method: 'POST', body: {} }),
    onSuccess: invalidate,
  })
}

export const useCreateShift = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Partial<Schema['Shift']>) => request<Schema['Shift']>('/api/shifts/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useCreateHoliday = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Partial<Schema['Holiday']>) =>
      request<Schema['Holiday']>('/api/holidays/', { method: 'POST', body }),
    onSuccess: invalidate,
  })
}

export const useDecideLeave = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: string }) =>
      request(`/api/leave-requests/${id}/decision/`, { method: 'POST', body: { decision } }),
    onSuccess: invalidate,
  })
}

export const useUpdateSettings = () => {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (body: Partial<Schema['OrganizationSettings']>) =>
      request<Schema['OrganizationSettings']>('/api/organizations/settings/', { method: 'PATCH', body }),
    onSuccess: invalidate,
  })
}
