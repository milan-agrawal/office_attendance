from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    emp_id = models.CharField(max_length=12, unique=True)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    department = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=80, blank=True)
    date_joined = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.emp_id} - {self.name}"

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=[('Present','Present'),('Absent','Absent'),('Late','Late')], default='Present')
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.emp_id} - {self.date}"
