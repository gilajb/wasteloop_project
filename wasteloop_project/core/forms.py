from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, WasteEntry, Payment, Recycler


# ─────────────────────────────────────────────────────────────
# 1. REGISTRATION FORM
# ─────────────────────────────────────────────────────────────

class RegisterForm(UserCreationForm):
    """
    Collector / Admin sign-up.
    Fields: username, first_name, last_name, phone_number, location, role, password1, password2
    """
    first_name = forms.CharField(
        max_length=100, label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'First name',
            'autofocus': True,
        })
    )
    last_name = forms.CharField(
        max_length=100, label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Last name',
        })
    )
    phone_number = forms.CharField(
        max_length=20, label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 0712 345 678',
        })
    )
    location = forms.CharField(
        max_length=200, label='Location / Settlement',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Kakuma Camp, Zone 3',
        })
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES, label='Register as',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'phone_number',
                  'location', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style username and password fields consistently
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Choose a username',
        })
        self.fields['username'].help_text = 'Letters, digits and @/./+/-/_ only.'
        for pw in ('password1', 'password2'):
            self.fields[pw].widget.attrs.update({
                'class': 'form-control form-control-lg',
                'placeholder': 'Password' if pw == 'password1' else 'Confirm password',
            })
            self.fields[pw].help_text = ''

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        digits = phone.replace(' ', '').replace('-', '').replace('+', '')
        if not digits.isdigit():
            raise ValidationError('Enter a valid phone number (digits only).')
        if len(digits) < 9:
            raise ValidationError('Phone number is too short.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name   = self.cleaned_data['first_name']
        user.last_name    = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.location     = self.cleaned_data['location']
        user.role         = self.cleaned_data['role']
        if commit:
            user.save()
        return user


# ─────────────────────────────────────────────────────────────
# 2. LOGIN FORM
# ─────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    """Standard login — username + password with Bootstrap styling."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
        })
        self.fields['username'].label = 'Username'
        self.fields['password'].label = 'Password'


# ─────────────────────────────────────────────────────────────
# 3. WASTE ENTRY FORM
# ─────────────────────────────────────────────────────────────

class WasteEntryForm(forms.ModelForm):
    """
    Admin / collector logs a waste collection.
    Enforces weight > 0 and requires all fields.
    """
    class Meta:
        model  = WasteEntry
        fields = ['collector', 'waste_type', 'weight_kg', 'date_collected', 'notes']
        widgets = {
            'collector': forms.Select(attrs={
                'class': 'form-select form-select-lg',
            }),
            'waste_type': forms.Select(attrs={
                'class': 'form-select form-select-lg',
            }),
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Weight in kg (e.g. 5.50)',
                'min':  '0.01',
                'step': '0.01',
            }),
            'date_collected': forms.DateInput(attrs={
                'class': 'form-control form-control-lg',
                'type':  'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  3,
                'placeholder': 'Optional notes about this collection...',
            }),
        }
        labels = {
            'weight_kg':      'Weight (kg)',
            'date_collected': 'Collection Date',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show collectors in the dropdown
        self.fields['collector'].queryset = User.objects.filter(
            role='collector', is_active=True
        ).order_by('first_name', 'username')
        self.fields['collector'].empty_label = '— Select collector —'
        self.fields['notes'].required = False

    def clean_weight_kg(self):
        weight = self.cleaned_data.get('weight_kg')
        if weight is not None and weight <= 0:
            raise ValidationError('Weight must be greater than 0 kg.')
        return weight

    def clean(self):
        cleaned = super().clean()
        collector = cleaned.get('collector')
        waste_type = cleaned.get('waste_type')
        date = cleaned.get('date_collected')
        weight = cleaned.get('weight_kg')

        # Prevent exact duplicate entries (same collector+type+date+weight)
        if all([collector, waste_type, date, weight]):
            duplicate = WasteEntry.objects.filter(
                collector=collector,
                waste_type=waste_type,
                date_collected=date,
                weight_kg=weight,
            )
            # Exclude self when editing
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError(
                    'A waste entry with these exact details already exists. '
                    'Please check before submitting again.'
                )
        return cleaned


# ─────────────────────────────────────────────────────────────
# 4. PAYMENT FORM
# ─────────────────────────────────────────────────────────────

class PaymentForm(forms.ModelForm):
    """
    Admin creates a payment record linked to a waste entry.
    Amount auto-calculated from waste entry in the view,
    but can be overridden here.
    """
    class Meta:
        model  = Payment
        fields = ['collector', 'waste_entry', 'amount', 'is_paid', 'date_paid']
        widgets = {
            'collector': forms.Select(attrs={
                'class': 'form-select form-select-lg',
            }),
            'waste_entry': forms.Select(attrs={
                'class': 'form-select',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Amount in KES',
                'min':  '0',
                'step': '0.01',
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'date_paid': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
        }
        labels = {
            'is_paid':   'Mark as Paid',
            'date_paid': 'Date Paid',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['collector'].queryset = User.objects.filter(
            role='collector', is_active=True
        ).order_by('first_name', 'username')
        self.fields['collector'].empty_label = '— Select collector —'

        # Only show waste entries that don't yet have a payment
        existing_payment_ids = Payment.objects.exclude(
            pk=self.instance.pk if self.instance.pk else None
        ).values_list('waste_entry_id', flat=True)
        self.fields['waste_entry'].queryset = WasteEntry.objects.filter(
            verified_by_admin=True
        ).exclude(id__in=existing_payment_ids).order_by('-date_collected')
        self.fields['waste_entry'].empty_label = '— Link to waste entry (optional) —'
        self.fields['waste_entry'].required = False
        self.fields['date_paid'].required = False

    def clean(self):
        cleaned  = super().clean()
        is_paid  = cleaned.get('is_paid')
        date_paid = cleaned.get('date_paid')
        amount   = cleaned.get('amount')

        if amount is not None and amount < 0:
            self.add_error('amount', 'Amount cannot be negative.')

        # If marked paid, date_paid should be set — auto-fill if blank
        if is_paid and not date_paid:
            from django.utils import timezone
            cleaned['date_paid'] = timezone.now().date()

        return cleaned


# ─────────────────────────────────────────────────────────────
# 5. RECYCLER FORM
# ─────────────────────────────────────────────────────────────

class RecyclerForm(forms.ModelForm):
    """Admin adds / edits a recycling partner."""
    class Meta:
        model  = Recycler
        fields = ['name', 'materials_accepted', 'price_per_kg', 'phone_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Company / partner name',
            }),
            'materials_accepted': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. Plastic, Metal, Paper',
            }),
            'price_per_kg': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'KES per kg',
                'min':  '0',
                'step': '0.01',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. 0700 000 000',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'contact@recycler.co.ke',
            }),
        }
        labels = {
            'materials_accepted': 'Materials Accepted',
            'price_per_kg':       'Price per kg (KES)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].required = False
        self.fields['email'].required = False

    def clean_price_per_kg(self):
        price = self.cleaned_data.get('price_per_kg')
        if price is not None and price < 0:
            raise ValidationError('Price per kg cannot be negative.')
        return price


# ─────────────────────────────────────────────────────────────
# 6. CONTACT FORM  (no model — message only)
# ─────────────────────────────────────────────────────────────

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=150, label='Your Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Full name',
        })
    )
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'your@email.com',
        })
    )
    message = forms.CharField(
        label='Message',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows':  5,
            'placeholder': 'How can we help you?',
        })
    )

    def clean_message(self):
        msg = self.cleaned_data.get('message', '').strip()
        if len(msg) < 10:
            raise ValidationError('Please write a message of at least 10 characters.')
        return msg
