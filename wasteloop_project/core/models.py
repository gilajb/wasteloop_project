from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator


# ─────────────────────────────────────────────────────────────
# 1. CUSTOM USER MODEL
# ─────────────────────────────────────────────────────────────

class User(AbstractUser):
    ROLE_CHOICES = [
        ('collector', 'Collector'),
        ('admin',     'Admin'),
    ]

    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='collector')
    phone_number = models.CharField(max_length=20, blank=True)
    location     = models.CharField(max_length=200, blank=True)

    # Convenience properties used in views + templates
    @property
    def is_collector(self):
        return self.role == 'collector'

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


# ─────────────────────────────────────────────────────────────
# 2. WASTE ENTRY MODEL
# ─────────────────────────────────────────────────────────────

class WasteEntry(models.Model):
    WASTE_TYPE_CHOICES = [
        ('plastic',    'Plastic'),
        ('metal',      'Metal'),
        ('paper',      'Paper'),
        ('glass',      'Glass'),
        ('organic',    'Organic'),
        ('electronic', 'Electronic'),
        ('other',      'Other'),
    ]

    collector        = models.ForeignKey(
                           User,
                           on_delete=models.CASCADE,
                           related_name='waste_entries',
                           limit_choices_to={'role': 'collector'}
                       )
    waste_type       = models.CharField(max_length=50, choices=WASTE_TYPE_CHOICES)
    weight_kg        = models.DecimalField(
                           max_digits=8, decimal_places=2,
                           validators=[MinValueValidator(0.01)]
                       )
    date_collected   = models.DateField()
    verified_by_admin = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_collected', '-created_at']
        verbose_name = 'Waste Entry'
        verbose_name_plural = 'Waste Entries'

    def __str__(self):
        return f"{self.collector.username} — {self.waste_type} — {self.weight_kg}kg ({self.date_collected})"


# ─────────────────────────────────────────────────────────────
# 3. PAYMENT MODEL
# ─────────────────────────────────────────────────────────────

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid',    'Paid'),
    ]

    collector     = models.ForeignKey(
                        User,
                        on_delete=models.CASCADE,
                        related_name='payments',
                        limit_choices_to={'role': 'collector'}
                    )
    waste_entry   = models.OneToOneField(
                        WasteEntry,
                        on_delete=models.CASCADE,
                        related_name='payment',
                        null=True, blank=True
                    )
    amount        = models.DecimalField(
                        max_digits=10, decimal_places=2,
                        validators=[MinValueValidator(0)]
                    )
    is_paid       = models.BooleanField(default=False)
    date_recorded = models.DateField(auto_now_add=True)
    date_paid     = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-date_recorded']

    @property
    def status_display(self):
        return 'Paid' if self.is_paid else 'Pending'

    def __str__(self):
        return f"{self.collector.username} — KES {self.amount} — {self.status_display}"


# ─────────────────────────────────────────────────────────────
# 4. RECYCLER / BUYER MODEL
# ─────────────────────────────────────────────────────────────

class Recycler(models.Model):
    name               = models.CharField(max_length=200)
    materials_accepted = models.CharField(max_length=300, help_text="e.g. Plastic, Metal, Paper")
    price_per_kg       = models.DecimalField(
                             max_digits=8, decimal_places=2,
                             validators=[MinValueValidator(0)]
                         )
    phone_number       = models.CharField(max_length=20, blank=True)
    email              = models.EmailField(blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.materials_accepted}"


# ─────────────────────────────────────────────────────────────
# 5. IMPACT MODEL  (aggregated stats — updated by signal)
# ─────────────────────────────────────────────────────────────

class ImpactStat(models.Model):
    """
    Single-row summary table.
    Always use ImpactStat.get() to read, and
    ImpactStat.refresh() to recalculate from live data.
    """
    total_waste_kg        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_income_generated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    active_collectors     = models.PositiveIntegerField(default=0)
    last_updated          = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Impact Stat'

    @classmethod
    def get(cls):
        """Return the single ImpactStat row, creating it if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def refresh(cls):
        """Recalculate all stats from live data and save."""
        from django.db.models import Sum, Count

        total_waste = (
            WasteEntry.objects
            .filter(verified_by_admin=True)
            .aggregate(total=Sum('weight_kg'))['total'] or 0
        )
        total_income = (
            Payment.objects
            .filter(is_paid=True)
            .aggregate(total=Sum('amount'))['total'] or 0
        )
        active = (
            User.objects
            .filter(role='collector', waste_entries__isnull=False)
            .distinct()
            .count()
        )

        stat = cls.get()
        stat.total_waste_kg         = total_waste
        stat.total_income_generated = total_income
        stat.active_collectors      = active
        stat.save()
        return stat

    def __str__(self):
        return f"ImpactStat — {self.total_waste_kg}kg | KES {self.total_income_generated} | {self.active_collectors} collectors"


# ─────────────────────────────────────────────────────────────
# SIGNALS — keep ImpactStat fresh automatically
# ─────────────────────────────────────────────────────────────

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=WasteEntry)
@receiver([post_save, post_delete], sender=Payment)
def refresh_impact_on_change(sender, **kwargs):
    ImpactStat.refresh()
