"""Row-Level Security helpers.

Every tenant-scoped table gets:

- ``ALTER TABLE ... ENABLE ROW LEVEL SECURITY`` + ``FORCE ROW LEVEL SECURITY``
  so even the table owner is subject to filtering.
- A policy scoped on ``organization_id`` compared against the transaction-local
  GUC ``app.current_tenant`` (set per-request by ``TenantContextMiddleware``
  and per-task by Celery consumers).

Tables that also need a "current user" escape hatch (e.g. Membership, which is
read before the tenant is resolved) add a second predicate against
``app.current_user``.

``app.platform_admin`` = 'on' opts the connection out of tenant filtering and
is only ever set for explicit platform (super-admin) scopes, audited in
``AuditLog``.

The ``tenants_organization`` table itself is the tenant registry: RLS is
enabled (so a policy exists for documentation/platform scopes) but NOT forced,
because the owner must be able to insert the first row of a new tenant during
onboarding. All child tables are FORCEd.
"""

from __future__ import annotations

from django.db import connection

TENANT_GUC = "app.current_tenant"
USER_GUC = "app.current_user"
PLATFORM_GUC = "app.platform_admin"

TENANT_PRED = f"nullif(current_setting('{TENANT_GUC}', true), '')::uuid"
USER_PRED = f"nullif(current_setting('{USER_GUC}', true), '')::uuid"
PLATFORM_PRED = f"current_setting('{PLATFORM_GUC}', true) = 'on'"


def _tenant_using(column: str, user_column: str | None = None) -> str:
    parts = [f"{column} = {TENANT_PRED}"]
    if user_column:
        parts.append(f"{user_column} = {USER_PRED}")
    parts.append(PLATFORM_PRED)
    return "(" + " OR ".join(parts) + ")"


def rls_sql_for_table(
    table: str,
    *,
    column: str = "organization_id",
    user_column: str | None = None,
    force: bool = True,
    reverse: bool = False,
) -> str:
    policy = f"tenant_isolation_{table.replace('.', '_')}"
    if reverse:
        return f"DROP POLICY IF EXISTS {policy} ON {table}; ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"
    cond = _tenant_using(column, user_column)
    force_clause = "FORCE " if force else ""
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; "
        f"ALTER TABLE {table} {force_clause}ROW LEVEL SECURITY; "
        f"DROP POLICY IF EXISTS {policy} ON {table}; "
        f"CREATE POLICY {policy} ON {table} USING {cond} WITH CHECK {cond};"
    )


def rls_sql_for_model(model, *, user_column: str | None = None, reverse: bool = False) -> list[str]:  # noqa: ANN001
    return [rls_sql_for_table(model._meta.db_table, user_column=user_column, reverse=reverse)]


def enforce_rls_now(table: str, **kwargs) -> None:  # noqa: ANN003
    """Apply RLS to a table outside of migrations (used by bootstrap tasks)."""
    with connection.cursor() as cursor:
        cursor.execute(rls_sql_for_table(table, **kwargs))
