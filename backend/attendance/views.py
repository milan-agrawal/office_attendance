# backend/attendance/views.py

from datetime import date, timedelta
import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test

from django.db.models import Count, Sum, Q
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Employee,
    Attendance,
    Leave,
    SalaryRecord,
    AuditLog,
    NotificationLog
)
from .forms import EmployeeForm


# ----------------------
# Authentication
# ----------------------

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('manager_home')
        if hasattr(request.user, 'employee_profile'):
            return redirect('employee_home')
        return redirect('home')

    next_param = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            if remember_me:
                request.session.set_expiry(60 * 60 * 24)  # 1 day
            else:
                request.session.set_expiry(0)

            # safe redirect
            if next_param:
                if url_has_allowed_host_and_scheme(next_param, allowed_hosts={request.get_host()}):
                    return redirect(next_param)

            if user.is_staff:
                return redirect('manager_home')
            if hasattr(user, 'employee_profile'):
                return redirect('employee_home')

            return redirect('home')

        else:
            messages.error(request, "Invalid credentials.")

    return render(request, 'login.html', {'next': next_param})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Logged out.")
    return redirect('login')


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.user.is_staff:
        return redirect('manager_home')

    if hasattr(request.user, 'employee_profile'):
        return redirect('employee_home')

    return redirect('login')


def is_manager(user):
    return user.is_authenticated and user.is_staff


# ----------------------
# Manager Dashboard
# ----------------------

@user_passes_test(is_manager, login_url='login')
def manager_home(request):
    ctx = _build_dashboard_context()
    return render(request, 'dashboard.html', ctx)


def _build_dashboard_context():
    today = date.today()

    # Employee count (use built-in is_active)
    total_employees = Employee.objects.filter(is_active=True).count()

    # Pending leaves
    pending_leaves_count = Leave.objects.filter(status='pending').count()

    # On leave today
    on_leave_today_count = Leave.objects.filter(
        status='approved',
        date=today
    ).count()

    # Upcoming leaves (next 7 days)
    end_date = today + timedelta(days=7)
    upcoming_leaves = (
        Leave.objects.filter(status='approved', date__range=(today, end_date))
        .select_related('employee')
        .order_by('date')[:10]
    )

    # Payroll for current month
    year = today.year
    month = today.month
    payroll_sum = (
        SalaryRecord.objects.filter(year=year, month=month)
        .aggregate(total=Sum('net_salary'))['total'] or 0
    )

    # Late comers (group by employee)
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    late_qs = (
        Attendance.objects.filter(status='late', date__range=(first_day, last_day))
        .select_related('employee')
        .values('employee__first_name', 'employee__last_name', 'employee__emp_id')
        .annotate(late_count=Count('id'))
        .order_by('-late_count')[:10]
    )

    # Build labels properly
    late_labels = [
        f"{x['employee__first_name']} {x['employee__last_name']} ({x['employee__emp_id']})"
        for x in late_qs
    ]

    late_values = [x['late_count'] for x in late_qs]

    # Logs
    audit_logs = AuditLog.objects.all().order_by('-timestamp')[:10]
    notifications = NotificationLog.objects.all().order_by('-timestamp')[:10]

    return {
        'total_employees': total_employees,
        'on_leave_today_count': on_leave_today_count,
        'pending_leaves_count': pending_leaves_count,
        'payroll_sum': payroll_sum,
        'upcoming_leaves': upcoming_leaves,
        'late_labels': late_labels,
        'late_values': late_values,
        'audit_logs': audit_logs,
        'notifications': notifications,
    }


# ----------------------
# Employee Dashboard
# ----------------------

@login_required
def employee_home(request):
    emp = getattr(request.user, 'employee_profile', None)

    if not emp:
        return render(request, 'employee_home.html', {'employee': None})

    today = date.today()

    upcoming = emp.leaves.filter(
        status='approved',
        date__gte=today
    ).order_by('date')[:10]

    salaries = emp.salary_records.order_by('-year', '-month')[:6]

    notifications = NotificationLog.objects.filter(
        recipient__icontains=emp.email
    ).order_by('-timestamp')[:10]

    return render(request, 'employee_home.html', {
        'employee': emp,
        'upcoming_leaves': upcoming,
        'salaries': salaries,
        'notifications': notifications,
    })


# ----------------------
# Employees CRUD (Manager)
# ----------------------

@user_passes_test(is_manager)
def employees_list(request):
    qs = Employee.objects.all().order_by('emp_id')

    q = request.GET.get('q')
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(emp_id__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(qs, 20)
    employees = paginator.get_page(request.GET.get('page'))

    return render(request, 'employees_list.html', {
        'employees': employees,
        'form': EmployeeForm(),
    })


@user_passes_test(is_manager)
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee created.")
            return redirect('employees_list')

        messages.error(request, "Fix the errors below.")
        qs = Employee.objects.all().order_by('emp_id')
        employees = Paginator(qs, 20).get_page(1)

        return render(request, 'employees_list.html', {
            'employees': employees,
            'form': form
        })

    return redirect('employees_list')


@user_passes_test(is_manager)
def employee_edit(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated.")
            return redirect('employees_list')

        messages.error(request, "Fix the errors below.")
    else:
        form = EmployeeForm(instance=emp)

    return render(request, 'employee_form.html', {
        'form': form,
        'employee': emp
    })


@user_passes_test(is_manager)
def employee_toggle_active(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.is_active = not emp.is_active
    emp.save()
    messages.success(request, f"Employee {'activated' if emp.is_active else 'deactivated'}.")
    return redirect('employees_list')