import uuid
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
    """
    Abstract base model that provides a UUID primary key field
    instead of the default auto-incrementing integer.
    """

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
        """
        Mark the record as deleted without removing it from the database.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """
        Restore a soft-deleted record.
        """
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

    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Primary address line.")
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Secondary address line.")
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("City or town.")
    )
    county = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("County of residence.")
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("Postal code.")
    )

    class Meta:
        abstract = True


class ContactMixin(models.Model):

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("Primary phone number in international format.")
    )
    alternative_phone_number = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("Alternative phone number.")
    )
    email = models.EmailField(
        blank=True,
        default='',
        help_text=_("Email address.")
    )

    class Meta:
        abstract = True