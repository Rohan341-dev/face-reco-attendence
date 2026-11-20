"""RLS for the attendance ledger and its derived records."""

from django.db import migrations

from apps.core.rls import rls_sql_for_table

TABLES = (
    "attendance_attendanceevent",
    "attendance_attendancerecord",
    "attendance_correctionrecord",
    "attendance_missingcheckoutalert",
)


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="; ".join(rls_sql_for_table(table) for table in TABLES),
            reverse_sql="; ".join(rls_sql_for_table(table, reverse=True) for table in TABLES),
        ),
    ]
