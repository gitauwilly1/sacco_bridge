import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
        help_text=_("Timestamp when the record was created.")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text=_("Timestamp when the record was last modified.")
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDModel(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the record.")
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Soft delete flag. When True, the record is considered deleted.")
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when the record was soft deleted.")
    )
    deleted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_%(class)s_set',
        help_text=_("User who performed the soft delete.")
    )

    class Meta:
        abstract = True

    def soft_delete(self, deleted_by=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):

    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_%(class)s_set',
        help_text=_("User who created the record.")
    )
    updated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_%(class)s_set',
        help_text=_("User who last modified the record.")
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class AddressMixin(models.Model):

    address_line_1 = models.CharField(max_length=255, blank=True, default='')
    address_line_2 = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    county = models.CharField(max_length=100, blank=True, default='')
    postal_code = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        abstract = True


class ContactMixin(models.Model):

    phone_number = models.CharField(max_length=20, blank=True, default='')
    alternative_phone_number = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')

    class Meta:
        abstract = True

class DeletionRequest(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    requested_by = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='deletion_requests'
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )

    object_id = models.UUIDField()

    object_repr = models.CharField(
        max_length=255,
        help_text=_("String representation of the object to delete.")
    )

    reason = models.TextField(
        blank=True, default='',
        help_text=_("Reason for deletion request.")
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending Review'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        default='PENDING',
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_deletions'
    )

    review_notes = models.TextField(blank=True, default='')

    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Deletion Request')
        verbose_name_plural = _('Deletion Requests')
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requested_by', 'status']),
        ]

    def __str__(self):
        return f"Delete {self.object_repr} - {self.status}"

    def approve(self, reviewed_by, notes=''):
        self.status = 'APPROVED'
        self.reviewed_by = reviewed_by
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()

        # Perform the actual deletion
        try:
            obj = self.content_type.get_object_for_this_type(id=self.object_id)
            obj.delete()
            return True
        except Exception:
            return False

    def reject(self, reviewed_by, notes=''):
        self.status = 'REJECTED'
        self.reviewed_by = reviewed_by
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.save()