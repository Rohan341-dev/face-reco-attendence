"""RLS for people and schedule tables (tenant-scoped)."""

from django.db import migrations

from apps.core.rls import rls_sql_for_table

TABLES = (
    "people_person",
    "people_employment",
    "people_consentrecord",
    "people_biometrictemplate",
    "schedules_shift",
    "schedules_workschedule",
    "schedules_holiday",
    "schedules_leaverequest",
)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("people", "0001_initial"),
        ("schedules", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="; ".join(rls_sql_for_table(table) for table in TABLES),
            reverse_sql="; ".join(rls_sql_for_table(table, reverse=True) for table in TABLES),
        ),
    ]
