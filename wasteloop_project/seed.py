"""
WasteLoop — Demo Seed Data
Run with: python manage.py shell < seed.py
Creates 1 admin + 2 collectors + 3 recyclers + sample entries
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wasteloop_project.settings')
django.setup()

from core.models import User, WasteEntry, Payment, Recycler, ImpactStat
from decimal import Decimal
import datetime

print("Seeding WasteLoop demo data...")

# Guard: skip if already seeded
if User.objects.filter(username='admin').exists():
    print("   Seed data already loaded. Skipping.")
else:
    admin = User.objects.create_superuser(
        username='admin', password='admin1234',
        role='admin', first_name='Site', last_name='Admin',
        phone_number='0700000001', location='Kakuma HQ'
    )
    aisha = User.objects.create_user(
        username='aisha', password='pass1234', role='collector',
        first_name='Aisha', last_name='Kamau',
        phone_number='0712345678', location='Kakuma Zone 3'
    )
    john = User.objects.create_user(
        username='john', password='pass1234', role='collector',
        first_name='John', last_name='Okello',
        phone_number='0723456789', location='Kakuma Zone 1'
    )

    Recycler.objects.bulk_create([
        Recycler(name='GreenCycle Kenya',  materials_accepted='Plastic, Metal',
                 price_per_kg=Decimal('35'), phone_number='0733001001', email='info@greencycle.co.ke'),
        Recycler(name='EcoReclaim Ltd',    materials_accepted='Paper, Organic',
                 price_per_kg=Decimal('20'), phone_number='0733002002', email='buy@ecoreclaim.co.ke'),
        Recycler(name='MetalWorks Africa', materials_accepted='Metal, Electronic',
                 price_per_kg=Decimal('45'), phone_number='0722003003', email='hello@metalworks.africa'),
    ])

    today = datetime.date.today()
    seed_entries = [
        (aisha, 'plastic', Decimal('12.5'), today-datetime.timedelta(days=1), True,  Decimal('437.50'), True),
        (aisha, 'metal',   Decimal('6.0'),  today-datetime.timedelta(days=3), True,  Decimal('270.00'), True),
        (aisha, 'paper',   Decimal('8.0'),  today,                            False, Decimal('160.00'), False),
        (john,  'plastic', Decimal('20.0'), today-datetime.timedelta(days=2), True,  Decimal('700.00'), True),
        (john,  'metal',   Decimal('4.5'),  today-datetime.timedelta(days=5), True,  Decimal('202.50'), False),
        (john,  'organic', Decimal('15.0'), today,                            False, Decimal('300.00'), False),
    ]
    for collector, wtype, weight, date, verified, amount, paid in seed_entries:
        entry = WasteEntry.objects.create(
            collector=collector, waste_type=wtype,
            weight_kg=weight, date_collected=date,
            verified_by_admin=verified
        )
        p = Payment.objects.create(collector=collector, waste_entry=entry, amount=amount, is_paid=paid)
        if paid:
            p.date_paid = date; p.save()

    ImpactStat.refresh()
    print("  Seed complete.")
    print("  Admin    -> username: admin    / password: admin1234")
    print("  Collector-> username: aisha    / password: pass1234")
    print("  Collector-> username: john     / password: pass1234")
