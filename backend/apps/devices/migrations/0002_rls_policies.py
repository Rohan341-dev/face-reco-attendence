"""RLS for registered devices and their sync cursors."""

from django.db import migrations

from apps.core.rls import rls_sql_for_table

TABLES = (
    "devices_device",
    "devices_devicesynccursor",
)


class Migration(migrations.Migration):
    dependencies = [
        ("devices", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="; ".join(rls_sql_for_table(table) for table in TABLES),
            reverse_sql="; ".join(rls_sql_for_table(table, reverse=True) for table in TABLES),
        ),
    ]
