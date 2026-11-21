# Attendance engine

`apps/attendance/engine.py` is the single write path for every attendance
channel (web, mobile, terminal, manual corrections, offline sync). No view
writes attendance rows directly.

## Flow

1. `validate_eligibility()` — person active in the tenant; verification status
   checked; for `verified_face` the person must have active
   `biometric_attendance` consent, liveness must pass when required, and a
   score must be present; device-verified events require an authorized device.
2. `process_event()` — idempotency lookup on `(organization, idempotency_key)`,
   then fuzzy dedupe within `dedupe_window_seconds`, then an append-only
   `AttendanceEvent` insert, then daily-record rebuild and realtime broadcast.
3. `recompute_daily_record()` — rebuilds the per-person/day materialized record
   from the event ledger: first check-in, last check-out, breaks, work seconds,
   late/early minutes (with grace), leave and holiday status, missing-checkout
   alerts.
4. `apply_correction()` — appends a `CorrectionRecord` and rebuilds both the old
   and new day. The original event is never modified; corrections are applied
   as overlays during rebuild.

## Guarantees

- Detection or recognition alone never authorizes attendance.
- Verified events are immutable; corrections are separate rows.
- Duplicate prevention is two-layered (exact key + time window).
- Overnight shifts attribute post-midnight events to the shift's start date.
- Every event carries organization, person, branch, device, timestamp, source
  and verification status.

## Offline sync

`POST /api/attendance/sync/` accepts a batch of events with client-generated
idempotency keys and returns a per-item status (`accepted`, `duplicate`,
`rejected`). Replayed batches do not create duplicate events.
