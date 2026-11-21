# Threat model (summary)

## Assets

- Biometric templates (sensitive, reversible only by key holder).
- Consent evidence and audit trail.
- Attendance ledger and derived payroll inputs.
- Tenant-scoped people, schedules and device registries.

## Boundaries and controls

| Threat | Control |
|---|---|
| Cross-tenant data access | JWT `org_id` claim (header cannot override), active membership check, RLS `FORCE` policies on all tenant tables, explicit `organization_id` filters in every view. |
| Platform-admin overreach | Separate `platform_admin` claim only when no org scope; every bypass is audit logged. |
| Stolen device token | Short-lived signed JWT, device registry check on every request, token rotation and deactivation, `app.current_device` GUC. |
| Replayed/offline events | Idempotency key unique per org, time-window dedupe, per-item sync results. |
| Tampering with verified events | Append-only ledger; corrections are separate rows; audit log on corrections. |
| Biometric template theft | AES-256-GCM encryption at rest via `apps/core/crypto.py`; serializer never exposes ciphertext; AI service returns plaintext only over internal TLS and backend encrypts immediately. |
| Covert identification / surveillance | Explicit capture consent required by AI service; no continuous capture; no default frame retention. |
| Privilege abuse | RBAC (`IsTenantMember/HR/Admin`, `IsPlatformAdmin`), MFA for privileged accounts, append-only audit log. |
| Automated abuse | DRF throttle classes; production HTTPS + HSTS + secure cookies. |
| Unauthorized metrics scraping | `/api/metrics/` requires a shared bearer token. |

## Residual risks / follow-ups

- Liveness is a heuristic, not certified PAD. Do not enable face attendance for
  a tenant until an evaluated PAD is integrated.
- Billing/subscription enforcement is not yet implemented; do not expose the
  platform publicly until seat/plan limits exist.
- Backup/restore runbook and incident response plan are not yet documented.
