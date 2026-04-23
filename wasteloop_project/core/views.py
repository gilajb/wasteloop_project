from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q

from .models import User, WasteEntry, Payment, Recycler, ImpactStat
from .forms  import (RegisterForm, LoginForm, WasteEntryForm,
                     PaymentForm, RecyclerForm, ContactForm)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _admin_required(view_fn):
    """Decorator: login + admin role required."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, 'Access denied — admin only.')
            return redirect('core:dashboard')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


# ─────────────────────────────────────────────────────────────
# PUBLIC PAGES
# ─────────────────────────────────────────────────────────────

def home(request):
    stat = ImpactStat.get()
    return render(request, 'core/public/home.html', {'stat': stat})


def about(request):
    return render(request, 'core/public/about.html')


def impact(request):
    stat = ImpactStat.get()

    # Waste breakdown by type (verified only)
    waste_by_type = (
        WasteEntry.objects
        .filter(verified_by_admin=True)
        .values('waste_type')
        .annotate(total_kg=Sum('weight_kg'))
        .order_by('-total_kg')
    )

    # Top 5 collectors by weight
    top_collectors = (
        User.objects
        .filter(role='collector')
        .annotate(total_kg=Sum('waste_entries__weight_kg'))
        .filter(total_kg__isnull=False)
        .order_by('-total_kg')[:5]
    )

    return render(request, 'core/public/impact.html', {
        'stat':           stat,
        'waste_by_type':  waste_by_type,
        'top_collectors': top_collectors,
    })


def recyclers(request):
    recycler_list = Recycler.objects.all()
    return render(request, 'core/recycler/recyclers.html', {
        'recyclers': recycler_list
    })


def contact(request):
    form = ContactForm()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # MVP: no email backend — just show success message
            messages.success(request,
                'Thanks for reaching out! We\'ll get back to you soon.')
            return redirect('core:contact')
    return render(request, 'core/public/contact.html', {'form': form})


# ─────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request,
                f'Welcome, {user.first_name or user.username}! '
                f'Your account has been created.')
            return redirect('core:dashboard')

    return render(request, 'core/auth/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = LoginForm(request)
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request,
                f'Welcome back, {user.first_name or user.username}!')
            # Honour ?next= param if present
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)

    return render(request, 'core/auth/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:home')


# ─────────────────────────────────────────────────────────────
# ROLE-BASED DASHBOARD ROUTER
# ─────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    if request.user.is_admin_user:
        return _admin_dashboard(request)
    return _collector_dashboard(request)


def _collector_dashboard(request):
    collector = request.user

    entries = WasteEntry.objects.filter(
        collector=collector
    ).select_related('payment').order_by('-date_collected')

    # Paginate
    paginator = Paginator(entries, 10)
    page      = request.GET.get('page', 1)
    entries_page = paginator.get_page(page)

    # Stats for this collector
    total_kg = entries.aggregate(t=Sum('weight_kg'))['t'] or 0
    total_earned = (
        Payment.objects
        .filter(collector=collector, is_paid=True)
        .aggregate(t=Sum('amount'))['t'] or 0
    )
    pending_payment = (
        Payment.objects
        .filter(collector=collector, is_paid=False)
        .aggregate(t=Sum('amount'))['t'] or 0
    )

    return render(request, 'core/dashboard/collector.html', {
        'entries':         entries_page,
        'total_kg':        total_kg,
        'total_earned':    total_earned,
        'pending_payment': pending_payment,
    })


def _admin_dashboard(request):
    # Overview stats
    total_waste_kg = (
        WasteEntry.objects
        .filter(verified_by_admin=True)
        .aggregate(t=Sum('weight_kg'))['t'] or 0
    )
    total_payouts = (
        Payment.objects
        .filter(is_paid=True)
        .aggregate(t=Sum('amount'))['t'] or 0
    )
    pending_payouts = (
        Payment.objects
        .filter(is_paid=False)
        .aggregate(t=Sum('amount'))['t'] or 0
    )
    active_collectors = (
        User.objects
        .filter(role='collector', is_active=True)
        .count()
    )
    unverified_count = WasteEntry.objects.filter(verified_by_admin=False).count()

    # Recent waste entries (last 10)
    recent_entries = (
        WasteEntry.objects
        .select_related('collector')
        .order_by('-created_at')[:10]
    )

    # Pending payments (last 10)
    pending_payments = (
        Payment.objects
        .filter(is_paid=False)
        .select_related('collector')
        .order_by('-date_recorded')[:10]
    )

    return render(request, 'core/dashboard/admin.html', {
        'total_waste_kg':    total_waste_kg,
        'total_payouts':     total_payouts,
        'pending_payouts':   pending_payouts,
        'active_collectors': active_collectors,
        'unverified_count':  unverified_count,
        'recent_entries':    recent_entries,
        'pending_payments':  pending_payments,
    })


# ─────────────────────────────────────────────────────────────
# WASTE ENTRIES
# ─────────────────────────────────────────────────────────────

@login_required
def waste_list(request):
    """
    Collectors see their own entries.
    Admins see all entries with filter controls.
    """
    qs = WasteEntry.objects.select_related('collector').order_by('-date_collected')

    if request.user.is_collector:
        qs = qs.filter(collector=request.user)

    # Admin filters
    waste_type = request.GET.get('waste_type', '')
    verified   = request.GET.get('verified', '')
    if waste_type:
        qs = qs.filter(waste_type=waste_type)
    if verified == '1':
        qs = qs.filter(verified_by_admin=True)
    elif verified == '0':
        qs = qs.filter(verified_by_admin=False)

    paginator    = Paginator(qs, 15)
    entries_page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/waste/list.html', {
        'entries':    entries_page,
        'waste_types': WasteEntry.WASTE_TYPE_CHOICES,
        'filter_type': waste_type,
        'filter_verified': verified,
    })


@_admin_required
def add_waste_entry(request):
    form = WasteEntryForm()
    if request.method == 'POST':
        form = WasteEntryForm(request.POST)
        if form.is_valid():
            entry = form.save()

            # Auto-create a pending payment using the recycler's best price
            best_recycler = (
                Recycler.objects
                .filter(materials_accepted__icontains=entry.waste_type)
                .order_by('-price_per_kg')
                .first()
            )
            price_per_kg = best_recycler.price_per_kg if best_recycler else 20  # KES fallback
            amount = entry.weight_kg * price_per_kg

            Payment.objects.create(
                collector=entry.collector,
                waste_entry=entry,
                amount=amount,
            )

            messages.success(request,
                f'Waste entry added — {entry.weight_kg}kg of '
                f'{entry.get_waste_type_display()} for '
                f'{entry.collector.get_full_name() or entry.collector.username}. '
                f'Payment of KES {amount:,.2f} created as pending.')
            return redirect('core:waste_list')

    return render(request, 'core/waste/add.html', {'form': form})


@_admin_required
def verify_waste(request, pk):
    entry = get_object_or_404(WasteEntry, pk=pk)
    if request.method == 'POST':
        entry.verified_by_admin = not entry.verified_by_admin
        entry.save()
        status = 'verified' if entry.verified_by_admin else 'unverified'
        messages.success(request, f'Entry #{pk} marked as {status}.')
    return redirect(request.POST.get('next', 'waste_list'))


# ─────────────────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────────────────

@_admin_required
def payments(request):
    qs = Payment.objects.select_related('collector', 'waste_entry').order_by('-date_recorded')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'paid':
        qs = qs.filter(is_paid=True)
    elif status_filter == 'pending':
        qs = qs.filter(is_paid=False)

    # Summary totals
    total_paid    = qs.filter(is_paid=True).aggregate(t=Sum('amount'))['t'] or 0
    total_pending = qs.filter(is_paid=False).aggregate(t=Sum('amount'))['t'] or 0

    paginator     = Paginator(qs, 15)
    payments_page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/payments/payments.html', {
        'payments':       payments_page,
        'total_paid':     total_paid,
        'total_pending':  total_pending,
        'status_filter':  status_filter,
    })


@_admin_required
def mark_paid(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        if not payment.is_paid:
            payment.is_paid   = True
            payment.date_paid = timezone.now().date()
            payment.save()
            messages.success(request,
                f'Payment of KES {payment.amount:,.2f} for '
                f'{payment.collector.get_full_name() or payment.collector.username} '
                f'marked as paid.')
        else:
            messages.info(request, 'This payment is already marked as paid.')
    return redirect(request.POST.get('next', 'payments'))
