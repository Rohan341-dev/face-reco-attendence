"""Development-only realistic seed data.

Usage: python manage.py seed
Refuses to run when DEBUG is false.
"""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.attendance.engine import EventInput, process_event
from apps.core.middleware import set_tenant
from apps.people.models import ConsentRecord, Person
from apps.schedules.models import Holiday, Shift, WorkSchedule
from apps.tenants.models import Branch, Department, Organization, OrganizationSettings


class Command(BaseCommand):
    help = "Create realistic development data (refuses in production)."

    def handle(self, *args, **options):  # noqa: ANN002, ANN003, ANN201
        if not settings.DEBUG:
            raise CommandError("Seeding is disabled outside DEBUG mode.")
        if Organization.objects.filter(slug="demo").exists():
            self.stdout.write("Demo organization already exists; nothing to do.")
            return

        with transaction.atomic():
            org = Organization.objects.create(
                name="Demo Manufacturing Pvt Ltd",
                slug="demo",
                industry="factory",
                timezone="Asia/Kolkata",
            )
            set_tenant(str(org.id))
            OrganizationSettings.objects.create(organization=org, dedupe_window_seconds=120)
            hq = Branch.objects.create(organization=org, name="Headquarters", code="HQ", is_headquarters=True)
            plant = Branch.objects.create(organization=org, name="Plant 2", code="P2")
            production = Department.objects.create(organization=org, name="Production", branch=plant)
            admin_dept = Department.objects.create(organization=org, name="Administration", branch=hq)

            morning = Shift.objects.create(
                organization=org, name="Morning", start_time=time(8, 0), end_time=time(17, 0),
                break_minutes=60, grace_minutes=10,
            )
            night = Shift.objects.create(
                organization=org, name="Night", start_time=time(22, 0), end_time=time(6, 0),
                break_minutes=45, grace_minutes=10,
            )
            Holiday.objects.create(organization=org, name="Republic Day", date=date(2026, 1, 26))

            names = [
                ("Asha", "Kumar", hq, admin_dept, morning),
                ("Ravi", "Sharma", plant, production, morning),
                ("Meera", "Iyer", plant, production, night),
                ("Arjun", "Patel", plant, production, morning),
                ("Priya", "Nair", hq, admin_dept, morning),
            ]
            today = timezone.localdate()
            for index, (first, last, branch, department, shift) in enumerate(names):
                person = Person.objects.create(
                    organization=org,
                    employee_id=f"DEMO-{index + 1:03d}",
                    first_name=first,
                    last_name=last,
                    email=f"{first.lower()}.{last.lower()}@demo.test",
                    branch=branch,
                    department=department,
                    status=Person.Status.ACTIVE,
                    date_of_joining=today - timedelta(days=90),
                )
                ConsentRecord.objects.create(
                    organization=org, person=person, purpose="biometric_attendance", granted=True,
                    evidence="Development seed",
                )
                WorkSchedule.objects.create(
                    organization=org, person=person, shift=shift, effective_from=today - timedelta(days=90)
                )

                check_in = timezone.now().replace(hour=8, minute=5 + index, second=0, microsecond=0)
                process_event(
                    str(org.id),
                    EventInput(
                        person_id=str(person.id),
                        event_type="check_in",
                        occurred_at=check_in,
                        source="import",
                        idempotency_key=f"seed-in-{uuid.uuid4()}",
                        verification_status="verified_manual",
                    ),
                )
                if index % 2 == 0:
                    process_event(
                        str(org.id),
                        EventInput(
                            person_id=str(person.id),
                            event_type="check_out",
                            occurred_at=check_in + timedelta(hours=9),
                            source="import",
                            idempotency_key=f"seed-out-{uuid.uuid4()}",
                            verification_status="verified_manual",
                        ),
                    )

        self.stdout.write(self.style.SUCCESS("Seeded organization 'demo' with 5 people and attendance events."))
