"""Enable PostgreSQL Row-Level Security on every tenant-scoped table.

Policy source of truth: apps.core.rls. The Organization registry table is
enabled but not FORCEd (owner may insert the first tenant during onboarding).
"""

from django.db import migrations

from apps.core.rls import rls_sql_for_table

TABLES = (
    ("tenants_organization", {"column": "id", "force": False}),
    ("tenants_branch", {}),
    ("tenants_department", {}),
    ("tenants_membership", {"user_column": "user_id"}),
    ("tenants_organizationsettings", {}),
    ("core_auditlog", {}),
)


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="; ".join(rls_sql_for_table(table, **options) for table, options in TABLES),
            reverse_sql="; ".join(
                rls_sql_for_table(table, reverse=True) for table, _ in TABLES
            ),
        ),
    ]
