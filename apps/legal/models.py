import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class LegalDocumentType(models.TextChoices):
    TERMS_AND_CONDITIONS = 'TERMS', _('Terms & Conditions')
    PRIVACY_POLICY = 'PRIVACY', _('Privacy Policy')


class LegalDocument(BaseModel):

    document_type = models.CharField(
        max_length=20,
        choices=LegalDocumentType.choices,
        help_text=_("Type of legal document.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Document title (e.g., 'Terms & Conditions v2.1').")
    )

    version = models.CharField(
        max_length=20,
        help_text=_("Semantic version (e.g., '2.1.0').")
    )

    content = models.TextField(
        help_text=_("Full document content in markdown or HTML.")
    )

    summary = models.TextField(
        blank=True,
        default='',
        help_text=_("Plain-language summary of key changes.")
    )

    is_current = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether this is the currently active version.")
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this version was published.")
    )

    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this version takes effect.")
    )

    published_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_legal_docs',
        help_text=_("Admin who published this version.")
    )

    class Meta:
        verbose_name = _('Legal Document')
        verbose_name_plural = _('Legal Documents')
        ordering = ['-version']
        unique_together = ['document_type', 'version']
        indexes = [
            models.Index(fields=['document_type', 'is_current']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} v{self.version}"

    def publish(self, published_by=None):
        self.is_current = True
        self.published_at = timezone.now()
        self.published_by = published_by
        if not self.effective_from:
            self.effective_from = timezone.now()
        self.save()

        # Deprecate other versions of same type
        LegalDocument.objects.filter(
            document_type=self.document_type,
            is_current=True,
        ).exclude(id=self.id).update(is_current=False)

    def save(self, *args, **kwargs):
        if self.is_current and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class UserLegalAcceptance(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='legal_acceptances',
        help_text=_("The user who accepted.")
    )

    document = models.ForeignKey(
        LegalDocument,
        on_delete=models.PROTECT,
        related_name='acceptances',
        help_text=_("The document version that was accepted.")
    )

    accepted_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the user accepted.")
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address at time of acceptance.")
    )

    user_agent = models.TextField(
        blank=True,
        default='',
        help_text=_("Browser/device info at time of acceptance.")
    )

    class Meta:
        verbose_name = _('User Legal Acceptance')
        verbose_name_plural = _('User Legal Acceptances')
        unique_together = ['user', 'document']
        ordering = ['-accepted_at']

    def __str__(self):
        return f"{self.user.email} accepted {self.document}"


class SignableDocumentType(models.TextChoices):
    LOAN_AGREEMENT = 'LOAN_AGREEMENT', _('Loan Agreement')
    SHARE_TRANSFER = 'SHARE_TRANSFER', _('Share Transfer Form')
    TERMS_ACCEPTANCE = 'TERMS_ACCEPTANCE', _('Terms & Conditions')
    PRIVACY_ACCEPTANCE = 'PRIVACY_ACCEPTANCE', _('Privacy Policy')
    CHAMA_CONSTITUTION = 'CHAMA_CONSTITUTION', _('Chama Constitution')


class Signature(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    signer = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='signatures'
    )

    document_type = models.CharField(
        max_length=30, choices=SignableDocumentType.choices
    )

    document_reference = models.CharField(
        max_length=255,
        help_text=_("Reference to the signed document (e.g., loan ID).")
    )

    document_title = models.CharField(max_length=255)

    verification_method = models.CharField(
        max_length=20,
        choices=[('SMS_OTP', 'SMS OTP'), ('EMAIL_OTP', 'Email OTP'), ('TOTP', '2FA Code')],
        default='SMS_OTP',
    )

    verification_code = models.CharField(
        max_length=6, blank=True, default='',
        help_text=_("OTP sent for verification (cleared after signing).")
    )

    verification_expiry = models.DateTimeField(null=True, blank=True)

    signed_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    user_agent = models.TextField(blank=True, default='')

    certificate_hash = models.CharField(
        max_length=64, blank=True, default='',
        help_text=_("SHA256 hash of the signature certificate.")
    )

    is_verified = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Signature')
        verbose_name_plural = _('Signatures')
        ordering = ['-created_at']
        unique_together = ['signer', 'document_type', 'document_reference']

    def __str__(self):
        return f"{self.signer.get_full_name()} - {self.get_document_type_display()}"

    def generate_certificate(self):
        import hashlib
        data = (
            f"{self.signer.id}|{self.document_type}|{self.document_reference}|"
            f"{self.signed_at.isoformat() if self.signed_at else ''}|{self.ip_address}"
        )
        return hashlib.sha256(data.encode()).hexdigest()