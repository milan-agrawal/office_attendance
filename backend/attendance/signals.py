from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings  # keep this for EMAIL_BACKEND
from .models import Leave, NotificationLog, AuditLog, Employee, Setting
from django.utils import timezone


@receiver(pre_save, sender=Leave)
def detect_leave_amend(sender, instance, **kwargs):
    """
    Mark amended True if an existing leave is changed by a boss (amended_by should be set by the caller),
    and create an audit log and notification.
    """
    if not instance.pk:
        # new leave - no amendment
        return
    try:
        old = Leave.objects.get(pk=instance.pk)
    except Leave.DoesNotExist:
        return

    changed = False
    changed_fields = []
    for field in ['start_date', 'end_date', 'is_paid', 'status', 'leave_type', 'days_count', 'reason']:
        old_val = getattr(old, field)
        new_val = getattr(instance, field)
        if old_val != new_val:
            changed = True
            changed_fields.append((field, old_val, new_val))

    if changed:
        instance.amended = True

@receiver(post_save, sender=Leave)
def leave_post_save(sender, instance, created, **kwargs):
    # create audit log
    actor = instance.amended_by or "system"
    AuditLog.objects.create(
        actor=actor,
        action='created' if created else 'amended' if instance.amended else 'updated',
        model_name='Leave',
        object_id=instance.pk,
        details=f"Leave {('created' if created else 'updated')}. start:{instance.start_date} end:{instance.end_date} paid:{instance.is_paid}"
    )

    # create notification entry
    # notify boss (manager) and employee
    subject = f"Leave {'created' if created else 'amended'} for {instance.employee.name}"
    message = f"Leave details:\nEmployee: {instance.employee.name} ({instance.employee.emp_id})\nFrom: {instance.start_date}\nTo: {instance.end_date}\nDays: {instance.days_count}\nStatus: {instance.status}\nAmended: {instance.amended}\nBy: {instance.amended_by or 'N/A'}"
    # send to employee
    if instance.employee.email:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [instance.employee.email], fail_silently=False)
            NotificationLog.objects.create(recipient=instance.employee.email, method='email', subject=subject, body=message, status='sent')
        except Exception as e:
            NotificationLog.objects.create(recipient=instance.employee.email, method='email', subject=subject, body=str(e), status='failed')
    # notify boss (settings)
    boss_email = Setting.get('boss_email', None)
    if boss_email:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [boss_email], fail_silently=False)
            NotificationLog.objects.create(recipient=boss_email, method='email', subject=subject, body=message, status='sent')
        except Exception as e:
            NotificationLog.objects.create(recipient=boss_email, method='email', subject=subject, body=str(e), status='failed')
