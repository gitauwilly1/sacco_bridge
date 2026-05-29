
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel
from apps.core.validators import validate_positive_amount, validate_share_quantity, validate_percentage


class SASRATier(models.TextChoices):

    TIER_1 = 'TIER_1', _('Tier 1 - Large SACCOs')
    TIER_2 = 'TIER_2', _('Tier 2 - Medium SACCOs')
    TIER_3 = 'TIER_3', _('Tier 3 - Small SACCOs')
    UNRATED = 'UNRATED', _('Unrated')


class SACCOStatus(models.TextChoices):

    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    HALTED = 'HALTED', _('Trading Halted')


class ShareClass(models.TextChoices):

    NON_WITHDRAWABLE = 'NON_WITHDRAWABLE', _('Non-Withdrawable Deposit')
    WITHDRAWABLE = 'WITHDRAWABLE', _('Withdrawable Deposit')
    DEVELOPMENT = 'DEVELOPMENT', _('Development Shares')
    SPECIAL = 'SPECIAL', _('Special Class Shares')


class LiquidityRequestStatus(models.TextChoices):

    ACTIVE = 'ACTIVE', _('Active - Seeking Buyers')
    MATCHED = 'MATCHED', _('Matched - Buyer Found')
    IN_NEGOTIATION = 'IN_NEGOTIATION', _('In Negotiation')
    ACCEPTED = 'ACCEPTED', _('Offer Accepted')
    SETTLED = 'SETTLED', _('Settled')
    CANCELLED = 'CANCELLED', _('Cancelled')
    EXPIRED = 'EXPIRED', _('Expired')


class UrgencyLevel(models.TextChoices):

    STANDARD = 'STANDARD', _('Standard - Within 1 Week')
    PRIORITY = 'PRIORITY', _('Priority - Within 48 Hours')
    URGENT = 'URGENT', _('Urgent - Within 24 Hours')


class ConnectionStatus(models.TextChoices):

    PENDING_SELLER_REVIEW = 'PENDING_SELLER_REVIEW', _('Pending Seller Review')
    CONNECTED = 'CONNECTED', _('Connected - In Discussion')
    OFFER_MADE = 'OFFER_MADE', _('Offer Made')
    OFFER_COUNTERED = 'OFFER_COUNTERED', _('Offer Countered')
    OFFER_ACCEPTED = 'OFFER_ACCEPTED', _('Offer Accepted')
    OFFER_DECLINED = 'OFFER_DECLINED', _('Offer Declined')
    SETTLEMENT_INITIATED = 'SETTLEMENT_INITIATED', _('Settlement Initiated')
    SETTLED = 'SETTLED', _('Settled')
    CLOSED = 'CLOSED', _('Closed')


class SACCO(BaseModel):

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text=_("Official name of the SACCO.")
    )

    registration_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("SASRA registration number.")
    )

    sasra_tier = models.CharField(
        max_length=20,
        choices=SASRATier.choices,
        default=SASRATier.UNRATED,
        help_text=_("SASRA regulatory tier classification.")
    )

    status = models.CharField(
        max_length=20,
        choices=SACCOStatus.choices,
        default=SACCOStatus.UNDER_REVIEW,
        db_index=True,
        help_text=_("Current operational status on the platform.")
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_("Description of the SACCO and its services.")
    )

    website = models.URLField(
        blank=True,
        default='',
        help_text=_("SACCO website URL.")
    )

    logo = models.ImageField(
        upload_to='sacco_logos/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("SACCO logo image.")
    )

    total_assets = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total assets under management.")
    )

    total_members = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of registered members.")
    )

    total_shares_outstanding = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text=_("Total shares issued by the SACCO.")
    )

    dividend_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[validate_percentage],
        help_text=_("Most recent annual dividend rate (percentage).")
    )

    dividend_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Year of the most recent dividend declaration.")
    )

    last_disclosure_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of the last financial disclosure submission.")
    )

    disclosure_due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when the next financial disclosure is due.")
    )

    trading_halted = models.BooleanField(
        default=False,
        help_text=_("Whether trading is currently halted for this SACCO.")
    )

    halt_reason = models.TextField(
        blank=True,
        default='',
        help_text=_("Reason for trading halt if applicable.")
    )

    verified_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_saccos',
        help_text=_("Platform admin who verified this SACCO.")
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the SACCO was verified.")
    )

    class Meta:
        verbose_name = _('SACCO')
        verbose_name_plural = _('SACCOs')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['sasra_tier']),
            models.Index(fields=['status']),
            models.Index(fields=['trading_halted']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_sasra_tier_display()})"

    def check_disclosure_status(self):
        if self.disclosure_due_date and self.disclosure_due_date < timezone.now().date():
            if not self.trading_halted:
                self.trading_halted = True
                self.halt_reason = _(
                    'Trading halted due to stale financial disclosures. '
                    'Updated disclosures are required to resume trading.'
                )
                self.save(update_fields=['trading_halted', 'halt_reason'])
                return False
        return True


class SACCOShareClass(BaseModel):

    sacco = models.ForeignKey(
        SACCO,
        on_delete=models.CASCADE,
        related_name='share_classes',
        help_text=_("The SACCO these shares belong to.")
    )

    share_class = models.CharField(
        max_length=30,
        choices=ShareClass.choices,
        default=ShareClass.NON_WITHDRAWABLE,
        help_text=_("Type of share class.")
    )

    nominal_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Nominal value per share.")
    )

    total_issued = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text=_("Total shares issued in this class.")
    )

    minimum_holding = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text=_("Minimum shares a member must hold.")
    )

    is_transferable = models.BooleanField(
        default=True,
        help_text=_("Whether shares in this class can be transferred.")
    )

    lock_in_period_months = models.PositiveIntegerField(
        default=0,
        help_text=_("Lock-in period before shares can be sold.")
    )

    dividend_eligible = models.BooleanField(
        default=True,
        help_text=_("Whether these shares earn dividends.")
    )

    voting_rights = models.BooleanField(
        default=True,
        help_text=_("Whether these shares carry voting rights.")
    )

    class Meta:
        verbose_name = _('SACCO Share Class')
        verbose_name_plural = _('SACCO Share Classes')
        unique_together = ['sacco', 'share_class']

    def __str__(self):
        return f"{self.sacco.name} - {self.get_share_class_display()}"


class SACCOMemberHolding(BaseModel):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sacco_holdings',
        help_text=_("The platform user who holds these shares.")
    )

    sacco = models.ForeignKey(
        SACCO,
        on_delete=models.CASCADE,
        related_name='member_holdings',
        help_text=_("The SACCO where shares are held.")
    )

    share_class = models.ForeignKey(
        SACCOShareClass,
        on_delete=models.CASCADE,
        related_name='holdings',
        help_text=_("The share class held.")
    )

    total_shares = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0000'))],
        help_text=_("Total shares owned.")
    )

    reserved_shares = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text=_("Shares reserved for pending transactions.")
    )

    member_since = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when the member joined this SACCO.")
    )

    member_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Member's registration number with the SACCO.")
    )

    last_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When holdings were last verified with the SACCO.")
    )

    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending Verification'),
            ('VERIFIED', 'Verified'),
            ('MISMATCH', 'Mismatch Detected'),
        ],
        default='PENDING',
        help_text=_("Verification status with the SACCO.")
    )

    class Meta:
        verbose_name = _('SACCO Member Holding')
        verbose_name_plural = _('SACCO Member Holdings')
        unique_together = ['user', 'sacco', 'share_class']
        indexes = [
            models.Index(fields=['user', 'sacco']),
            models.Index(fields=['verification_status']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.total_shares} shares in {self.sacco.name}"

    @property
    def available_shares(self):
        return self.total_shares - self.reserved_shares

    def reserve_shares(self, quantity):
        from decimal import Decimal
        quantity = Decimal(str(quantity))

        if quantity > self.available_shares:
            raise ValueError(_('Insufficient available shares.'))

        self.reserved_shares += quantity
        self.save(update_fields=['reserved_shares'])
        return True

    def release_shares(self, quantity):
        from decimal import Decimal
        quantity = Decimal(str(quantity))

        self.reserved_shares -= quantity
        if self.reserved_shares < Decimal('0.0000'):
            self.reserved_shares = Decimal('0.0000')
        self.save(update_fields=['reserved_shares'])

    def transfer_shares(self, quantity, to_holding=None):
        """Transfer shares to another holding (on settlement)."""
        from decimal import Decimal
        quantity = Decimal(str(quantity))

        self.total_shares -= quantity
        self.reserved_shares -= quantity
        if self.reserved_shares < Decimal('0.0000'):
            self.reserved_shares = Decimal('0.0000')
        self.save()

        if to_holding:
            to_holding.total_shares += quantity
            to_holding.save()


class LiquidityRequest(BaseModel):

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='liquidity_requests',
        help_text=_("The member seeking liquidity.")
    )

    sacco = models.ForeignKey(
        SACCO,
        on_delete=models.CASCADE,
        related_name='liquidity_requests',
        help_text=_("The SACCO whose shares are being offered.")
    )

    share_class = models.ForeignKey(
        SACCOShareClass,
        on_delete=models.CASCADE,
        related_name='liquidity_requests',
        help_text=_("The share class being offered.")
    )

    holding = models.ForeignKey(
        SACCOMemberHolding,
        on_delete=models.CASCADE,
        related_name='liquidity_requests',
        help_text=_("The specific holding being sold from.")
    )

    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[validate_share_quantity],
        help_text=_("Number of shares offered.")
    )

    expected_price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Seller's expected price per share (optional).")
    )

    minimum_price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Minimum acceptable price per share (optional).")
    )

    total_expected_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total expected value for the shares.")
    )

    status = models.CharField(
        max_length=30,
        choices=LiquidityRequestStatus.choices,
        default=LiquidityRequestStatus.ACTIVE,
        db_index=True,
        help_text=_("Current status of the request.")
    )

    urgency = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.STANDARD,
        help_text=_("How quickly the seller needs funds.")
    )

    allow_institutional_buyers = models.BooleanField(
        default=True,
        help_text=_("Whether institutional buyers can express interest.")
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this request expires if not matched.")
    )

    notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Additional notes from the seller.")
    )

    class Meta:
        verbose_name = _('Liquidity Request')
        verbose_name_plural = _('Liquidity Requests')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['sacco', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['urgency']),
        ]

    def __str__(self):
        return f"{self.seller.get_full_name()} - {self.share_quantity} shares in {self.sacco.name}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            urgency_days = {
                UrgencyLevel.STANDARD: 7,
                UrgencyLevel.PRIORITY: 2,
                UrgencyLevel.URGENT: 1,
            }
            days = urgency_days.get(self.urgency, 7)
            self.expires_at = timezone.now() + timezone.timedelta(days=days)

        if self.share_quantity and self.expected_price_per_share:
            self.total_expected_value = self.share_quantity * self.expected_price_per_share

        super().save(*args, **kwargs)


class BuyerInterest(BaseModel):

    liquidity_request = models.ForeignKey(
        LiquidityRequest,
        on_delete=models.CASCADE,
        related_name='buyer_interests',
        help_text=_("The liquidity request the buyer is interested in.")
    )

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='expressed_interests',
        help_text=_("The potential buyer.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this interest is still active.")
    )

    buyer_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Optional message from the buyer to the seller.")
    )

    viewed_by_seller = models.BooleanField(
        default=False,
        help_text=_("Whether the seller has viewed this interest.")
    )

    class Meta:
        verbose_name = _('Buyer Interest')
        verbose_name_plural = _('Buyer Interests')
        unique_together = ['liquidity_request', 'buyer']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.buyer.get_full_name()} interested in {self.liquidity_request}"


class Connection(BaseModel):

    liquidity_request = models.ForeignKey(
        LiquidityRequest,
        on_delete=models.CASCADE,
        related_name='connections',
        help_text=_("The liquidity request.")
    )

    buyer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='buyer_connections',
        help_text=_("The buyer in this connection.")
    )

    seller = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='seller_connections',
        help_text=_("The seller in this connection.")
    )

    status = models.CharField(
        max_length=30,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING_SELLER_REVIEW,
        db_index=True,
        help_text=_("Current connection status.")
    )

    agreed_price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Agreed price per share (if accepted).")
    )

    agreed_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=_("Agreed share quantity (if accepted).")
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total transaction amount.")
    )

    settlement_intent_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_("Reference to the settlement intent when initiated.")
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the offer was accepted.")
    )

    settled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When settlement completed.")
    )

    class Meta:
        verbose_name = _('Connection')
        verbose_name_plural = _('Connections')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Connection: {self.seller.get_full_name()} - {self.buyer.get_full_name()}"


class Offer(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    connection = models.ForeignKey(
        Connection,
        on_delete=models.CASCADE,
        related_name='offers',
        help_text=_("The connection this offer belongs to.")
    )

    offered_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='offers_made',
        help_text=_("The user who made this offer.")
    )

    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Offered price per share.")
    )

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[validate_share_quantity],
        help_text=_("Quantity of shares in this offer.")
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Total offer amount.")
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('ACCEPTED', 'Accepted'),
            ('COUNTERED', 'Countered'),
            ('DECLINED', 'Declined'),
            ('EXPIRED', 'Expired'),
        ],
        default='PENDING',
        help_text=_("Current offer status.")
    )

    message = models.TextField(
        blank=True,
        default='',
        help_text=_("Optional message accompanying the offer.")
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text=_("When the offer was created.")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("When the offer was last modified.")
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the offer was responded to.")
    )

    class Meta:
        verbose_name = _('Offer')
        verbose_name_plural = _('Offers')
        ordering = ['-created_at']

    def __str__(self):
        return f"Offer: KSh {self.price_per_share}/share x {self.quantity}"

    def save(self, *args, **kwargs):
        if self.price_per_share and self.quantity:
            self.total_amount = self.price_per_share * self.quantity
        super().save(*args, **kwargs)

    def accept(self):
        self.status = 'ACCEPTED'
        self.responded_at = timezone.now()
        self.save()

        self.connection.agreed_price_per_share = self.price_per_share
        self.connection.agreed_quantity = self.quantity
        self.connection.total_amount = self.total_amount
        self.connection.status = ConnectionStatus.OFFER_ACCEPTED
        self.connection.accepted_at = timezone.now()
        self.connection.save()

    def decline(self):
        self.status = 'DECLINED'
        self.responded_at = timezone.now()
        self.save()

    def counter(self, new_price_per_share, new_quantity=None, message=''):
        self.status = 'COUNTERED'
        self.responded_at = timezone.now()
        self.save()

        counter_offer = Offer.objects.create(
            connection=self.connection,
            offered_by=self.connection.seller if self.offered_by == self.connection.buyer else self.connection.buyer,
            price_per_share=new_price_per_share,
            quantity=new_quantity or self.quantity,
            message=message,
        )

        self.connection.status = ConnectionStatus.OFFER_COUNTERED
        self.connection.save()

        return counter_offer