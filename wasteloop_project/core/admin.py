from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Sum
from .models import User, WasteEntry, Payment, Recycler, ImpactStat


# ─────────────────────────────────────────────────────────────
# 1. USER ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display    = ('username', 'get_full_name', 'role', 'phone_number', 'location', 'is_active', 'date_joined')
    list_filter     = ('role', 'is_active', 'date_joined')
    search_fields   = ('username', 'first_name', 'last_name', 'phone_number', 'location')
    ordering        = ('-date_joined',)
    list_per_page   = 25

    # Extend the default fieldsets to include our custom fields
    fieldsets = BaseUserAdmin.fieldsets + (
        ('WasteLoop Profile', {
            'fields': ('role', 'phone_number', 'location')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('WasteLoop Profile', {
            'fields': ('role', 'phone_number', 'location')
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or '—'
    get_full_name.short_description = 'Name'


# ─────────────────────────────────────────────────────────────
# 2. WASTE ENTRY ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(WasteEntry)
class WasteEntryAdmin(admin.ModelAdmin):
    list_display    = ('collector', 'waste_type', 'weight_kg', 'date_collected', 'verified_badge', 'created_at')
    list_filter     = ('waste_type', 'verified_by_admin', 'date_collected')
    search_fields   = ('collector__username', 'collector__first_name', 'collector__last_name')
    ordering        = ('-date_collected',)
    date_hierarchy  = 'date_collected'
    list_per_page   = 30
    actions         = ['mark_verified', 'mark_unverified']

    readonly_fields = ('created_at',)

    fieldsets = (
        ('Collection Details', {
            'fields': ('collector', 'waste_type', 'weight_kg', 'date_collected', 'notes')
        }),
        ('Verification', {
            'fields': ('verified_by_admin',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def verified_badge(self, obj):
        if obj.verified_by_admin:
            return format_html('<span style="color:#198754;font-weight:600;">✔ Verified</span>')
        return format_html('<span style="color:#dc3545;">✘ Pending</span>')
    verified_badge.short_description = 'Status'

    @admin.action(description='✔ Mark selected entries as verified')
    def mark_verified(self, request, queryset):
        updated = queryset.update(verified_by_admin=True)
        ImpactStat.refresh()
        self.message_user(request, f'{updated} entr{"y" if updated == 1 else "ies"} marked as verified.')

    @admin.action(description='✘ Mark selected entries as unverified')
    def mark_unverified(self, request, queryset):
        updated = queryset.update(verified_by_admin=False)
        ImpactStat.refresh()
        self.message_user(request, f'{updated} entr{"y" if updated == 1 else "ies"} marked as unverified.')


# ─────────────────────────────────────────────────────────────
# 3. PAYMENT ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display    = ('collector', 'amount_display', 'status_badge', 'date_recorded', 'date_paid', 'waste_entry')
    list_filter     = ('is_paid', 'date_recorded')
    search_fields   = ('collector__username', 'collector__first_name', 'collector__last_name')
    ordering        = ('-date_recorded',)
    list_per_page   = 30
    actions         = ['mark_as_paid', 'mark_as_pending']

    fieldsets = (
        ('Payment Info', {
            'fields': ('collector', 'waste_entry', 'amount')
        }),
        ('Status', {
            'fields': ('is_paid', 'date_paid')
        }),
    )

    def amount_display(self, obj):
        return f'KES {obj.amount:,.2f}'
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="color:#198754;font-weight:600;">✔ Paid</span>')
        return format_html('<span style="color:#F5A623;font-weight:600;">⏳ Pending</span>')
    status_badge.short_description = 'Status'

    @admin.action(description='✔ Mark selected payments as paid')
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_paid=False).update(
            is_paid=True,
            date_paid=timezone.now().date()
        )
        ImpactStat.refresh()
        self.message_user(request, f'{updated} payment{"s" if updated != 1 else ""} marked as paid.')

    @admin.action(description='✘ Mark selected payments as pending')
    def mark_as_pending(self, request, queryset):
        updated = queryset.filter(is_paid=True).update(is_paid=False, date_paid=None)
        ImpactStat.refresh()
        self.message_user(request, f'{updated} payment{"s" if updated != 1 else ""} reset to pending.')


# ─────────────────────────────────────────────────────────────
# 4. RECYCLER ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Recycler)
class RecyclerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'materials_accepted', 'price_per_kg_display', 'phone_number', 'email')
    search_fields = ('name', 'materials_accepted')
    ordering      = ('name',)
    list_per_page = 25

    def price_per_kg_display(self, obj):
        return f'KES {obj.price_per_kg}/kg'
    price_per_kg_display.short_description = 'Price per kg'
    price_per_kg_display.admin_order_field = 'price_per_kg'


# ─────────────────────────────────────────────────────────────
# 5. IMPACT STAT ADMIN  (read-only summary panel)
# ─────────────────────────────────────────────────────────────

@admin.register(ImpactStat)
class ImpactStatAdmin(admin.ModelAdmin):
    list_display  = ('total_waste_kg', 'total_income_display', 'active_collectors', 'last_updated')
    readonly_fields = (
        'total_waste_kg', 'total_income_generated',
        'active_collectors', 'last_updated'
    )

    # Prevent adding / deleting the singleton row
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def total_income_display(self, obj):
        return f'KES {obj.total_income_generated:,.2f}'
    total_income_display.short_description = 'Total Income Generated'


# ─────────────────────────────────────────────────────────────
# ADMIN SITE BRANDING
# ─────────────────────────────────────────────────────────────

admin.site.site_header  = '♻ WasteLoop Admin'
admin.site.site_title   = 'WasteLoop'
admin.site.index_title  = 'Platform Management'
