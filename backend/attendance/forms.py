# backend/attendance/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

Employee = get_user_model()


class EmployeeForm(forms.ModelForm):
    # compatibility: virtual "name" maps to first_name/last_name
    name = forms.CharField(
        required=True,
        label="Full name",
        help_text="First and last name (space separated)."
    )

    # username is required by AbstractUser — expose it here
    username = forms.CharField(required=True, label="Username")

    # optional password fields (only used on create or when admin wants to reset)
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label="Password",
        help_text="Leave blank to keep existing password (on edit)."
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label="Confirm password"
    )

    class Meta:
        model = Employee
        fields = [
            'emp_id',
            'username',
            'name',               # virtual - mapped in save()
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'employee_type',
            'base_salary',
            'bonus_amount',
            'bonus_eligible',
            'shift_start_time',
            'working_hours',
            'paid_leave_quota',
            'is_active',
        ]
        widgets = {
            'emp_id': forms.TextInput(attrs={'class': 'input'}),
            'username': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'phone_number': forms.TextInput(attrs={'class': 'input'}),
            'base_salary': forms.NumberInput(attrs={'class': 'input', 'step': '0.01'}),
            'bonus_amount': forms.NumberInput(attrs={'class': 'input', 'step': '0.01'}),
            'working_hours': forms.NumberInput(attrs={'class': 'input', 'step': '0.25'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate the virtual 'name' from first_name/last_name on edit
        if self.instance and (self.instance.first_name or self.instance.last_name):
            full = f"{(self.instance.first_name or '')} {(self.instance.last_name or '')}".strip()
            self.fields['name'].initial = full

        # If editing an existing instance, password fields are optional
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
        else:
            # creating a new user - recommend password (but still allow blank if admin wants)
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean_name(self):
        v = self.cleaned_data.get('name', '').strip()
        if not v:
            raise forms.ValidationError("Please provide the employee's full name.")
        return v

    def clean_emp_id(self):
        emp_id = (self.cleaned_data.get('emp_id') or '').strip()
        if not emp_id:
            raise forms.ValidationError("Employee ID is required.")
        qs = Employee.objects.filter(emp_id__iexact=emp_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This Employee ID is already in use.")
        return emp_id

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        qs = Employee.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError("Enter a valid email address.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        # basic check: allow digits, +, -, spaces. enforce length if desired.
        if phone and not all(c.isdigit() or c in "+- ()" for c in phone):
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
            if p1 and len(p1) < 6:
                raise forms.ValidationError("Password is too short (minimum 6 characters).")
        return cleaned

    def save(self, commit=True):
        # map name -> first_name/last_name
        name = self.cleaned_data.pop('name', '')
        parts = name.split(None, 1)
        first = parts[0] if parts else ''
        last = parts[1] if len(parts) > 1 else ''
        self.instance.first_name = first
        self.instance.last_name = last

        # set username/emp_id from cleaned_data (ModelForm will handle most)
        obj = super().save(commit=False)

        # set password if provided
        pwd = self.cleaned_data.get('password1')
        if pwd:
            obj.set_password(pwd)

        if commit:
            obj.save()
            # ensure many-to-many or other m2m saved by parent
            self.save_m2m()
        return obj