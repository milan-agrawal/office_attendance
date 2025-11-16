# backend/attendance/models.py
from decimal import Decimal
from datetime import date, timedelta
import calendar

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser

# small key/value settings table
class Setting(models.Model):
    key = models.CharField(max_length=120, unique=True)
    value = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.key}={self.value}"

    @staticmethod
    def get(key, default=None):
        try:
            return Setting.objects.get(key=key).value
        except Setting.DoesNotExist:
            return default


# choices
EMPLOYMENT_TYPES = (
    ('full_time', 'Full Time'),
    ('part_time', 'Part Time'),
    ('hourly', 'Hourly'),
)

ATTENDANCE_STATUS = (
    ('present', 'Present'),
    ('absent', 'Absent'),
    ('leave', 'Leave'),
    ('half_day', 'Half Day'),
    ('late', 'Late'),
)

LEAVE_STATUS = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)

LEAVE_TYPE_CHOICES = (
    ('normal', 'Normal'),   # default (employee uses is_paid flag to indicate paid/unpaid)
    ('sick', 'Sick'),
    ('emergency', 'Emergency'),
    ('other', 'Other'),
)


class Employee(AbstractUser):
    """
    Single table for Django auth + employee details.
    Keep the class named `Employee` to minimize changes elsewhere.
    Set in settings.py: AUTH_USER_MODEL = 'attendance.Employee'
    """

    # unique employee code
    emp_id = models.CharField(max_length=32, unique=True)

    # contact
    phone_number = models.CharField(max_length=32, blank=True, null=True)

    # employment specifics
    employee_type = models.CharField(max_length=16, choices=EMPLOYMENT_TYPES, default='full_time')

    # salary fields (Decimal)
    base_salary = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonus_eligible = models.BooleanField(default=False)

    # shift / working hours
    shift_start_time = models.TimeField(null=True, blank=True)
    working_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('8.00'))

    # paid leave quota (default set in save())
    paid_leave_quota = models.IntegerField(default=0)

    # timestamps
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Note: AbstractUser already has: username, password, first_name, last_name, email,
    # is_staff, is_superuser, is_active, date_joined, etc.

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{self.emp_id} - {name or self.username}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # set default paid_leave_quota by employment_type if not explicitly provided
        if not self.paid_leave_quota:
            if self.employee_type == 'full_time':
                self.paid_leave_quota = 22
            elif self.employee_type == 'part_time':
                self.paid_leave_quota = 11
            else:  # hourly
                self.paid_leave_quota = 0
        super().save(*args, **kwargs)

    def get_daily_rate(self):
        """
        Returns per-day rate for full/part-time. For hourly returns 0.
        """
        try:
            wd = int(Setting.get('working_days_per_month', 22))
        except Exception:
            wd = 22

        if self.employee_type == 'full_time':
            return (Decimal(self.base_salary) / Decimal(wd)) if self.base_salary else Decimal('0.00')
        if self.employee_type == 'part_time':
            return Decimal(self.base_salary) if self.base_salary else Decimal('0.00')
        return Decimal('0.00')


class Attendance(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=16, choices=ATTENDANCE_STATUS, default='present')
    remarks = models.TextField(blank=True, default='')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.emp_id} - {self.date} - {self.status}"

    def calculate_hours(self):
        """
        Calculate hours_worked from time_in/time_out if provided.
        Otherwise, for full/part-time present -> default working_hours.
        """
        if self.time_in and self.time_out:
            dt_in = timezone.datetime.combine(self.date, self.time_in)
            dt_out = timezone.datetime.combine(self.date, self.time_out)
            if dt_out < dt_in:
                dt_out += timedelta(days=1)
            delta = dt_out - dt_in
            hours = Decimal(delta.total_seconds() / 3600)
            self.hours_worked = round(hours, 2)
        else:
            emp = self.employee
            if emp.employee_type in ('full_time', 'part_time') and self.status == 'present':
                self.hours_worked = Decimal(emp.working_hours)
            else:
                self.hours_worked = None

    def save(self, *args, **kwargs):
        self.calculate_hours()
        super().save(*args, **kwargs)


class Leave(models.Model):
    """
    One row per leave-day. That allows flexible random, non-sequential days.
    Use leave_type='normal' by default. is_paid default False (unpaid).
    Manager/admin can mark is_paid=True for paid leaves.
    """
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField()
    leave_type = models.CharField(max_length=32, choices=LEAVE_TYPE_CHOICES, default='normal')
    is_paid = models.BooleanField(default=False)   # default unpaid
    status = models.CharField(max_length=16, choices=LEAVE_STATUS, default='pending')
    reason = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    amended = models.BooleanField(default=False)
    amended_by = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.emp_id} - {self.date} ({self.leave_type})"


class SalaryRecord(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='salary_records')
    year = models.IntegerField()
    month = models.IntegerField()
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonus_applied = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    half_day_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unpaid_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    generated_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.employee.emp_id} - {self.year}-{self.month:02d}"

    def calculate_for_month(self):
        """
        Recalculate salary for the month.
        Uses Leave.date rows (one per leave-day) and Attendance rows.
        """
        emp = self.employee
        gross = Decimal('0.00')
        deductions = Decimal('0.00')
        bonus_amount = Decimal('0.00')
        unpaid_leave_days = Decimal('0.00')
        half_day_deductions = Decimal('0.00')

        # month boundaries
        first_day = date(self.year, self.month, 1)
        last_day = date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

        # attendance and leaves in month
        atts = Attendance.objects.filter(employee=emp, date__range=(first_day, last_day))
        leaves_in_month = Leave.objects.filter(employee=emp, date__range=(first_day, last_day), status='approved')

        if emp.employee_type == 'full_time':
            gross = Decimal(emp.base_salary)
            # Unpaid leave days: those leave rows with is_paid=False
            unpaid_leaves_qs = leaves_in_month.filter(is_paid=False)
            unpaid_leave_days = Decimal(unpaid_leaves_qs.count())
            # absent attendance rows
            absent_count = atts.filter(status='absent').count()
            unpaid_leave_days += Decimal(absent_count)
            # half-days
            half_days = atts.filter(status='half_day').count()
            per_day_rate = emp.get_daily_rate()
            half_day_deductions = Decimal(half_days) * per_day_rate * Decimal('0.5')
            deductions = unpaid_leave_days * per_day_rate + half_day_deductions

        elif emp.employee_type == 'part_time':
            per_day_rate = Decimal(emp.base_salary)  # base_salary treated as per-day
            present_days = atts.filter(status='present').count()
            gross = per_day_rate * Decimal(present_days)
            unpaid_leaves_qs = leaves_in_month.filter(is_paid=False)
            deductions = Decimal(unpaid_leaves_qs.count()) * per_day_rate
            half_days = atts.filter(status='half_day').count()
            half_day_deductions = Decimal(half_days) * (per_day_rate * Decimal('0.5'))
            deductions += half_day_deductions

        else:  # hourly
            total_hours = atts.aggregate(total=models.Sum('hours_worked'))['total'] or Decimal('0.00')
            gross = Decimal(total_hours) * Decimal(emp.base_salary)
            # unpaid leaves: left as business-rule; default no automatic deduction

        # Bonus logic
        if emp.bonus_eligible:
            if emp.bonus_amount and emp.bonus_amount > 0:
                bonus_amount = Decimal(emp.bonus_amount)
            else:
                global_bonus = Setting.get('global_bonus', None)
                if global_bonus:
                    try:
                        bonus_amount = Decimal(global_bonus)
                    except Exception:
                        bonus_amount = Decimal('0.00')

            # disqualify bonus if unpaid leaves OR any late marks this month
            if unpaid_leave_days > 0 or atts.filter(status='late').exists():
                bonus_amount = Decimal('0.00')

        net = gross - deductions + bonus_amount

        self.gross_salary = round(gross, 2)
        self.deductions = round(deductions, 2)
        self.bonus_applied = round(bonus_amount, 2)
        self.net_salary = round(net, 2)
        self.half_day_deductions = round(half_day_deductions, 2)
        self.unpaid_leave_days = round(unpaid_leave_days, 2)
        self.save()
        return self


class NotificationLog(models.Model):
    recipient = models.CharField(max_length=300)
    method = models.CharField(max_length=20, default='email')  # email / sms / ui
    subject = models.CharField(max_length=300, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=50, default='pending')  # pending/sent/failed
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient} - {self.method} - {self.status}"


class AuditLog(models.Model):
    actor = models.CharField(max_length=200, blank=True, null=True)  # who performed action
    action = models.CharField(max_length=200)  # created/updated/deleted
    model_name = models.CharField(max_length=200)
    object_id = models.CharField(max_length=200, blank=True, null=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} | {self.actor} | {self.action} | {self.model_name}"