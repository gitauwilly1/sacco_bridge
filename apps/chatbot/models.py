from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class SessionType(models.TextChoices):

    GENERAL_SUPPORT = 'GENERAL_SUPPORT', _('General Support')
    CHAMA_SETUP = 'CHAMA_SETUP', _('Chama Setup Help')
    CHAMA_MANAGEMENT = 'CHAMA_MANAGEMENT', _('Chama Management')
    INVESTMENT_GUIDANCE = 'INVESTMENT_GUIDANCE', _('Investment Guidance')
    SETTLEMENT_HELP = 'SETTLEMENT_HELP', _('Settlement Help')
    DISPUTE_ASSISTANCE = 'DISPUTE_ASSISTANCE', _('Dispute Assistance')
    ONBOARDING = 'ONBOARDING', _('Onboarding Help')


class MessageRole(models.TextChoices):

    USER = 'USER', _('User')
    ASSISTANT = 'ASSISTANT', _('Assistant')
    SYSTEM = 'SYSTEM', _('System')


class ChatSession(BaseModel):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        help_text=_("The user in this conversation.")
    )

    session_type = models.CharField(
        max_length=30,
        choices=SessionType.choices,
        default=SessionType.GENERAL_SUPPORT,
        help_text=_("Type of support session.")
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Auto-generated or user-provided session title.")
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether the session is still active.")
    )

    context_data = models.JSONField(
        default=dict,
        help_text=_("Additional context for the AI (user profile, platform data).")
    )

    total_tokens_used = models.PositiveIntegerField(
        default=0,
        help_text=_("Total tokens consumed in this session.")
    )

    resolved = models.BooleanField(
        default=False,
        help_text=_("Whether the user's issue was resolved.")
    )

    feedback_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')],
        help_text=_("User feedback rating for the session.")
    )

    class Meta:
        verbose_name = _('Chat Session')
        verbose_name_plural = _('Chat Sessions')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_type']),
        ]

    def __str__(self):
        return f"Chat: {self.user.email} - {self.get_session_type_display()}"

    def add_context(self, key, value):
        """Add context data for the AI."""
        self.context_data[key] = value
        self.save(update_fields=['context_data'])


class ChatMessage(BaseModel):

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text=_("The session this message belongs to.")
    )

    role = models.CharField(
        max_length=20,
        choices=MessageRole.choices,
        help_text=_("Who sent this message.")
    )

    content = models.TextField(
        help_text=_("Message content.")
    )

    tokens_used = models.PositiveIntegerField(
        default=0,
        help_text=_("Tokens consumed for this message.")
    )

    ai_model = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("AI model used to generate this response.")
    )

    intent_detected = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Intent classified by the AI.")
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Confidence score for intent classification.")
    )

    action_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Action triggered by this message (if any).")
    )

    action_data = models.JSONField(
        default=dict,
        help_text=_("Data for the triggered action.")
    )

    sources = models.JSONField(
        default=list,
        help_text=_("Knowledge base sources used for the response.")
    )

    class Meta:
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."


class KnowledgeCategory(models.TextChoices):

    CHAMA_BASICS = 'CHAMA_BASICS', _('Chama Basics')
    CHAMA_SETUP = 'CHAMA_SETUP', _('Chama Setup')
    CONTRIBUTIONS = 'CONTRIBUTIONS', _('Contributions')
    LOANS = 'LOANS', _('Loans')
    MEETINGS = 'MEETINGS', _('Meetings')
    SACCO_SHARES = 'SACCO_SHARES', _('SACCO Shares')
    BUYING_SHARES = 'BUYING_SHARES', _('Buying Shares')
    SELLING_SHARES = 'SELLING_SHARES', _('Selling Shares')
    SETTLEMENTS = 'SETTLEMENTS', _('Settlements')
    DISPUTES = 'DISPUTES', _('Disputes')
    ACCOUNT_SECURITY = 'ACCOUNT_SECURITY', _('Account Security')
    FEES_PRICING = 'FEES_PRICING', _('Fees & Pricing')
    PLATFORM_BASICS = 'PLATFORM_BASICS', _('Platform Basics')
    REGULATIONS = 'REGULATIONS', _('Regulations & Compliance')


class KnowledgeArticle(BaseModel):

    title = models.CharField(
        max_length=255,
        help_text=_("Article title.")
    )

    content = models.TextField(
        help_text=_("Article content in markdown format.")
    )

    category = models.CharField(
        max_length=30,
        choices=KnowledgeCategory.choices,
        help_text=_("Knowledge category.")
    )

    tags = models.JSONField(
        default=list,
        help_text=_("Search tags for retrieval.")
    )

    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether this article is published and usable by the AI.")
    )

    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text=_("Priority for retrieval (higher = more important).")
    )

    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times this article was used in responses.")
    )

    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this article was last used in a response.")
    )

    authored_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_articles',
        help_text=_("Who wrote this article.")
    )

    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_articles',
        help_text=_("Who reviewed this article.")
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the article was last reviewed.")
    )

    class Meta:
        verbose_name = _('Knowledge Article')
        verbose_name_plural = _('Knowledge Articles')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def record_usage(self):
        from django.utils import timezone
        self.view_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['view_count', 'last_used_at'])