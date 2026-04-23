from django.urls import path
from . import views

app_name = 'core'   # namespace — use {% url 'core:home' %} in templates

urlpatterns = [

    # ── Public ────────────────────────────────────────────────
    path('',           views.home,      name='home'),
    path('about/',     views.about,     name='about'),
    path('impact/',    views.impact,    name='impact'),
    path('recyclers/', views.recyclers, name='recyclers'),
    path('contact/',   views.contact,   name='contact'),

    # ── Authentication ────────────────────────────────────────
    path('register/', views.register,    name='register'),
    path('login/',    views.user_login,  name='login'),
    path('logout/',   views.user_logout, name='logout'),

    # ── Dashboard (role-router) ───────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Waste entries ─────────────────────────────────────────
    # NOTE: add/ must come before <int:pk>/ to avoid slug conflicts
    path('waste/',              views.waste_list,      name='waste_list'),
    path('waste/add/',          views.add_waste_entry, name='add_waste_entry'),
    path('waste/verify/<int:pk>/', views.verify_waste, name='verify_waste'),

    # ── Payments (admin only) ─────────────────────────────────
    path('payments/',                       views.payments,  name='payments'),
    path('payments/mark-paid/<int:pk>/',    views.mark_paid, name='mark_paid'),
]
