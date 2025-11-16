from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .models import Attendance, Leave, SalaryRecord, NotificationLog, AuditLog, Setting

Employee = get_user_model()


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    """Admin panel for the custom Employee User model."""

    list_display = (
        'emp_id', 'full_name', 'employee_type',
        'email', 'phone_number', 'is_active', 'is_staff'
    )
    list_filter = ('employee_type', 'is_active', 'is_staff')

    search_fields = (
        'username', 'emp_id', 'first_name',
        'last_name', 'email', 'phone_number'
    )
    ordering = ('emp_id',)

    readonly_fields = ('created_on', 'updated_on')

    fieldsets = (
        (None, {
            'fields': ('emp_id', 'username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Employment Details', {
            'fields': (
                'employee_type', 'base_salary', 'bonus_amount', 'bonus_eligible',
                'shift_start_time', 'working_hours', 'paid_leave_quota',
                'is_active', 'is_staff', 'is_superuser'
            )
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions')
        }),
        ('Timestamps', {
            'fields': ('created_on', 'updated_on', 'last_login',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'emp_id', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'email', 'phone_number',
                'employee_type', 'is_staff', 'is_active'
            ),
        }),
    )

    def full_name(self, obj):
        return f"{(obj.first_name or '')} {(obj.last_name or '')}".strip()
    full_name.short_description = 'Name'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'hours_worked', 'time_in', 'time_out')
    list_filter = ('status', 'date')
    search_fields = ('employee__emp_id', 'employee__first_name', 'employee__last_name')
    ordering = ('-date',)
    readonly_fields = ('created_on', 'updated_on')


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'leave_type', 'is_paid', 'status')
    list_filter = ('leave_type', 'is_paid', 'status')
    search_fields = ('employee__emp_id', 'employee__first_name', 'employee__last_name')
    ordering = ('-date',)
    readonly_fields = ('created_on', 'updated_on')


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month', 'net_salary')
    list_filter = ('year', 'month')
    search_fields = ('employee__emp_id', 'employee__first_name', 'employee__last_name')
    ordering = ('-year', '-month')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'method', 'status', 'timestamp')
    list_filter = ('method', 'status')
    search_fields = ('recipient', 'subject')
    ordering = ('-timestamp',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'model_name', 'object_id')
    search_fields = ('actor', 'action', 'model_name', 'object_id')
    ordering = ('-timestamp',)


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    search_fields = ('key',)
