from django.urls import path
from . import views

urlpatterns = [
    # Root dispatcher
    path('', views.home, name='home'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('manager/', views.manager_home, name='manager_home'),
    path('employee/', views.employee_home, name='employee_home'),

    # Employee management (manager-only)
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/toggle/', views.employee_toggle_active, name='employee_toggle_active'),
]