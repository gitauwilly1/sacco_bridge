
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.serializers import BaseSerializer, DynamicFieldsMixin
from apps.chamas.models import (
    Chama, ChamaMember, Contribution, Loan, LoanRepayment,
    Meeting, MeetingAttendance, Payout, PayoutRecipient,
)


class ChamaSerializer(BaseSerializer, DynamicFieldsMixin):

    member_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Chama
        fields = [
            'id', 'name', 'slug', 'description', 'chama_type',
            'status', 'invite_code', 'contribution_amount',
            'contribution_frequency', 'max_members',
            'total_savings', 'available_balance', 'outstanding_loans',
            'loan_interest_rate', 'max_loan_multiple',
            'max_loan_duration_months', 'require_guarantors',
            'min_guarantors', 'loan_approval_method',
            'payout_cycle_months', 'payout_method', 'next_payout_date',
            'late_fee_amount', 'grace_period_days',
            'mpesa_paybill', 'mpesa_account_reference',
            'auto_verify_mpesa', 'allow_member_contributions',
            'require_contribution_verification',
            'member_count', 'created_by_name', 'is_member',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'invite_code', 'total_savings',
            'available_balance', 'outstanding_loans',
            'created_at', 'updated_at',
        ]

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.memberships.filter(
                user=request.user, is_active=True
            ).exists()
        return False


class ChamaCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Chama
        fields = [
            'name', 'description', 'chama_type',
            'contribution_amount', 'contribution_frequency',
            'max_members', 'loan_interest_rate', 'max_loan_multiple',
            'max_loan_duration_months', 'require_guarantors',
            'min_guarantors', 'loan_approval_method',
            'payout_cycle_months', 'payout_method',
            'late_fee_amount', 'grace_period_days',
            'mpesa_paybill', 'mpesa_account_reference',
        ]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(_('Chama name cannot be empty.'))
        return value.strip()


class ChamaMemberSerializer(BaseSerializer, DynamicFieldsMixin):

    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    user_initials = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = ChamaMember
        fields = [
            'id', 'chama', 'user_id', 'user_name', 'user_email',
            'user_phone', 'user_initials', 'role', 'is_active',
            'joined_at', 'total_contributions', 'current_balance',
            'outstanding_loans', 'contribution_streak',
            'last_contribution_date', 'is_overdue', 'overdue_amount',
            'standing_score', 'created_at',
        ]
        read_only_fields = [
            'id', 'total_contributions', 'current_balance',
            'outstanding_loans', 'contribution_streak',
            'last_contribution_date', 'is_overdue', 'overdue_amount',
            'standing_score', 'created_at',
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_user_email(self, obj):
        return obj.user.email

    def get_user_phone(self, obj):
        return obj.user.phone_number

    def get_user_initials(self, obj):
        return obj.user.get_initials()

    def get_user_id(self, obj):
        return str(obj.user.id)


class ContributionSerializer(BaseSerializer, DynamicFieldsMixin):

    member_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = [
            'id', 'chama', 'member', 'member_name', 'amount',
            'expected_amount', 'status', 'payment_method',
            'payment_reference', 'period_start', 'period_end',
            'paid_at', 'verified_by', 'verified_by_name',
            'verified_at', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'paid_at', 'verified_by', 'verified_at',
            'created_at', 'updated_at',
        ]

    def get_member_name(self, obj):
        return obj.member.user.get_full_name()

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.user.get_full_name()
        return None


class ContributionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contribution
        fields = [
            'chama', 'member', 'amount', 'expected_amount',
            'payment_method', 'payment_reference',
            'period_start', 'period_end', 'notes',
        ]
        read_only_fields = ['expected_amount']

    def validate_member(self, value):
        if not value.is_active:
            raise serializers.ValidationError(_('This member is not active in the chama.'))
        return value

    def validate(self, data):
        chama = data.get('chama')
        if chama:
            data['expected_amount'] = chama.contribution_amount
        return data

class LoanSerializer(BaseSerializer, DynamicFieldsMixin):

    borrower_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    guarantor_names = serializers.SerializerMethodField()
    repayment_progress = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'chama', 'borrower', 'borrower_name',
            'principal', 'interest_rate', 'duration_months',
            'total_interest', 'total_repayable', 'monthly_installment',
            'outstanding_balance', 'status', 'purpose',
            'approved_by', 'approved_by_name', 'approved_at',
            'disbursed_at', 'due_date', 'guarantors',
            'guarantor_names', 'repayment_progress',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'total_interest', 'total_repayable',
            'monthly_installment', 'outstanding_balance',
            'approved_by', 'approved_at', 'disbursed_at',
            'due_date', 'created_at', 'updated_at',
        ]

    def get_borrower_name(self, obj):
        return obj.borrower.user.get_full_name()

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.user.get_full_name()
        return None

    def get_guarantor_names(self, obj):
        return [
            g.user.get_full_name() for g in obj.guarantors.all()
        ]

    def get_repayment_progress(self, obj):
        if obj.total_repayable > Decimal('0'):
            paid = obj.total_repayable - obj.outstanding_balance
            return {
                'paid': str(paid.quantize(Decimal('0.01'))),
                'total': str(obj.total_repayable),
                'percentage': str(
                    ((paid / obj.total_repayable) * 100).quantize(Decimal('0.01'))
                ),
            }
        return None


class LoanCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Loan
        fields = [
            'chama', 'borrower', 'principal', 'duration_months',
            'purpose', 'guarantors',
        ]

    def validate_principal(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError(_('Loan amount must be greater than zero.'))
        return value


class LoanRepaymentSerializer(BaseSerializer):

    class Meta:
        model = LoanRepayment
        fields = [
            'id', 'loan', 'amount', 'payment_method',
            'payment_reference', 'paid_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MeetingSerializer(BaseSerializer, DynamicFieldsMixin):

    organizer_name = serializers.SerializerMethodField()
    attendee_count = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'chama', 'title', 'description', 'date',
            'start_time', 'end_time', 'location', 'status',
            'minutes', 'organizer', 'organizer_name',
            'attendee_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_organizer_name(self, obj):
        if obj.organizer:
            return obj.organizer.user.get_full_name()
        return None

    def get_attendee_count(self, obj):
        return obj.attendees.filter(attended=True).count()


class MeetingAttendanceSerializer(BaseSerializer):

    member_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingAttendance
        fields = [
            'id', 'meeting', 'member', 'member_name',
            'attended', 'arrived_at', 'apology',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_member_name(self, obj):
        return obj.member.user.get_full_name()


class PayoutSerializer(BaseSerializer):

    recipient_count = serializers.SerializerMethodField()

    class Meta:
        model = Payout
        fields = [
            'id', 'chama', 'total_amount', 'payout_date',
            'cycle_start', 'cycle_end', 'payout_method',
            'recipient_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_recipient_count(self, obj):
        return obj.recipients.count()


class PayoutRecipientSerializer(BaseSerializer):

    member_name = serializers.SerializerMethodField()

    class Meta:
        model = PayoutRecipient
        fields = [
            'id', 'payout', 'member', 'member_name',
            'amount', 'payment_reference', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_member_name(self, obj):
        return obj.member.user.get_full_name()