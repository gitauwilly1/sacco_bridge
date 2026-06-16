import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.exceptions import (
    ChamaMembershipError, InsufficientFundsError, LoanEligibilityError,
    PermissionDeniedError
)
from apps.core.pagination import SmallPagination
from apps.core.mixins import SoftDeleteMixin
from apps.chamas.models import (
    Chama, ChamaMember, ConstitutionAgreement, Contribution, Loan, LoanRepayment,
    Meeting, MeetingAttendance, MemberRole, LoanStatus,
    PaymentMethod, ContributionStatus,Poll, PollOption, Vote,
)
from apps.chamas.serializers import (
    ChamaSerializer, ChamaCreateSerializer, ChamaMemberSerializer,
    ContributionSerializer, ContributionCreateSerializer,
    LoanSerializer, LoanCreateSerializer, LoanRepaymentSerializer,
    MeetingSerializer, MeetingAttendanceSerializer,
    PayoutSerializer, PayoutRecipientSerializer,
    PollSerializer, PollOptionSerializer, VoteSerializer
)
from apps.users.permissions import IsChamaAdmin, IsPlatformStaff

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(tags=['Chamas'], summary='List user chamas'),
    create=extend_schema(tags=['Chamas'], summary='Create a new chama'),
    retrieve=extend_schema(tags=['Chamas'], summary='Get chama details'),
    update=extend_schema(tags=['Chamas'], summary='Update chama'),
    partial_update=extend_schema(tags=['Chamas'], summary='Partial update chama'),
    destroy=extend_schema(tags=['Chamas'], summary='Delete chama'),
)
class ChamaViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = ChamaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['name', 'description', 'chama_type']
    ordering_fields = ['name', 'created_at', 'total_savings', 'status']

    def get_queryset(self):
        return Chama.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_deleted=False
        ).distinct().prefetch_related('memberships')

    def get_serializer_class(self):
        if self.action == 'create':
            return ChamaCreateSerializer
        return ChamaSerializer

    def perform_create(self, serializer):
        chama = serializer.save(created_by=self.request.user)
        ChamaMember.objects.create(
            chama=chama,
            user=self.request.user,
            role=MemberRole.CHAIRPERSON
        )
        logger.info(f"Chama created: {chama.name} by {self.request.user.email}")

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        chama = self.get_object()

        if chama.memberships.filter(user=request.user, is_active=True).exists():
            return Response({
                'success': False,
                'error': {'code': 'already_member', 'message': _('You are already a member.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        if chama.memberships.filter(is_active=True).count() >= chama.max_members:
            return Response({
                'success': False,
                'error': {'code': 'chama_full', 'message': _('This chama has reached maximum members.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        ChamaMember.objects.create(chama=chama, user=request.user, role=MemberRole.MEMBER)
        return Response({'success': True, 'data': {}, 'message': _('Joined chama successfully.')})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        chama = self.get_object()

        try:
            membership = chama.memberships.get(user=request.user, is_active=True)
        except ChamaMember.DoesNotExist:
            raise ChamaMembershipError(_('You are not an active member.'))

        if membership.outstanding_loans > 0:
            return Response({
                'success': False,
                'error': {
                    'code': 'outstanding_loans',
                    'message': _('Cannot leave with outstanding loans of KSh %(amount)s.') % {
                        'amount': membership.outstanding_loans
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        membership.is_active = False
        membership.left_at = timezone.now()
        membership.save()
        return Response({'success': True, 'data': {}, 'message': _('Left chama.')})
    
    @action(detail=True, methods=['post'])
    def refresh_health(self, request, pk=None):
        from apps.chamas.services import ChamaHealthService

        chama = self.get_object()
        result = ChamaHealthService.update_chama_health(chama)

        return Response({
            'success': True,
            'data': {
                'health_score': str(result['score']),
                'health_score_grade': result['grade'],
                'health_score_breakdown': result['breakdown'],
            },
            'message': _('Health score refreshed.'),
        })

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        chama = self.get_object()

        # Basic stats
        members = chama.memberships.filter(is_active=True)
        total_members = members.count()
        
        # Recent contributions
        recent_contributions = chama.contributions.filter(
            is_deleted=False
        ).select_related('member__user').order_by('-created_at')[:5]

        # Upcoming meetings
        upcoming_meetings = chama.meetings.filter(
            date__gte=timezone.now().date(),
            is_deleted=False,
        ).order_by('date', 'start_time')[:3]

        # Active loans summary
        active_loans = chama.loans.filter(
            status__in=[LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID],
            is_deleted=False,
        )

        # Active polls
        active_polls = chama.polls.filter(is_active=True).count()

        # Health score
        health = {
            'score': str(chama.health_score) if chama.health_score else 'N/A',
            'grade': chama.health_score_grade or 'N/A',
        }

        from apps.chamas.serializers import (
            ContributionSerializer, MeetingSerializer
        )

        return Response({
            'success': True,
            'data': {
                'chama_name': chama.name,
                'chama_type': chama.get_chama_type_display(),
                'total_members': total_members,
                'total_savings': str(chama.total_savings),
                'available_balance': str(chama.available_balance),
                'outstanding_loans': str(chama.outstanding_loans),
                'active_loans_count': active_loans.count(),
                'active_polls': active_polls,
                'health': health,
                'contribution_amount': str(chama.contribution_amount),
                'contribution_frequency': chama.get_contribution_frequency_display(),
                'invite_code': chama.invite_code,
                'recent_contributions': ContributionSerializer(recent_contributions, many=True).data,
                'upcoming_meetings': MeetingSerializer(upcoming_meetings, many=True).data,
            },
        })

    @action(detail=True, methods=['get'])
    def invite_link(self, request, pk=None):
        chama = self.get_object()

        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        invite_url = f"{frontend_url}/join-chama/{chama.invite_code}"

        # Generate deep link for mobile
        deep_link = f"saccobridge://join/{chama.invite_code}"

        return Response({
            'success': True,
            'data': {
                'invite_code': chama.invite_code,
                'invite_url': invite_url,
                'deep_link': deep_link,
                'chama_name': chama.name,
                'share_text': _('Join my chama "{name}" on Sacco Bridge! Use code: {code}').format(
                    name=chama.name, code=chama.invite_code
                ),
            },
        })
    
    @action(detail=True, methods=['post'])
    def upload_constitution(self, request, pk=None):
        chama = self.get_object()

        # Check admin
        try:
            membership = chama.memberships.get(user=request.user, is_active=True)
            is_admin = membership.role in [
                MemberRole.CHAIRPERSON, MemberRole.TREASURER, MemberRole.SECRETARY,
            ]
        except ChamaMember.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_member', 'message': _('You are not a member.')}
            }, status=status.HTTP_403_FORBIDDEN)

        if not is_admin:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': _('Only chama officials can upload.')}
            }, status=status.HTTP_403_FORBIDDEN)

        if 'constitution' not in request.FILES:
            return Response({
                'success': False,
                'error': {'code': 'missing_file', 'message': _('No file uploaded.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['constitution']

        if file.size > 10 * 1024 * 1024:
            return Response({
                'success': False,
                'error': {'code': 'file_too_large', 'message': _('File must be under 10MB.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        allowed_types = ['application/pdf', 'application/msword',
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            return Response({
                'success': False,
                'error': {'code': 'invalid_format', 'message': _('Only PDF and DOC/DOCX files accepted.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        version = request.data.get('version', '1.0')

        if chama.constitution:
            chama.constitution.delete(save=False)

        chama.constitution = file
        chama.constitution_version = version
        chama.constitution_uploaded_at = timezone.now()
        chama.save(update_fields=['constitution', 'constitution_version', 'constitution_uploaded_at'])

        return Response({
            'success': True,
            'data': {
                'constitution_url': chama.constitution.url if chama.constitution else None,
                'version': version,
                'uploaded_at': chama.constitution_uploaded_at.isoformat(),
            },
            'message': _('Constitution uploaded.'),
        })

    @action(detail=True, methods=['post'])
    def agree_constitution(self, request, pk=None):
        chama = self.get_object()

        if not chama.constitution:
            return Response({
                'success': False,
                'error': {'code': 'no_constitution', 'message': _('No constitution uploaded yet.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = chama.memberships.get(user=request.user, is_active=True)
        except ChamaMember.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_member', 'message': _('You are not a member.')}
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if already agreed to this version
        existing = ConstitutionAgreement.objects.filter(
            member=member,
            version=chama.constitution_version,
        ).first()

        if existing:
            return Response({
                'success': True,
                'data': {
                    'already_agreed': True,
                    'agreed_at': existing.agreed_at.isoformat(),
                },
                'message': _('You have already agreed to this version.'),
            })

        agreement = ConstitutionAgreement.objects.create(
            member=member,
            chama=chama,
            version=chama.constitution_version,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return Response({
            'success': True,
            'data': {
                'agreed_at': agreement.agreed_at.isoformat(),
                'version': chama.constitution_version,
            },
            'message': _('Constitution agreed.'),
        })

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    @action(detail=True, methods=['get'])
    def constitution_status(self, request, pk=None):
        chama = self.get_object()

        if not chama.constitution:
            return Response({
                'success': True,
                'data': {'has_constitution': False},
            })

        members = chama.memberships.filter(is_active=True).select_related('user')
        member_status = []

        for m in members:
            agreed = ConstitutionAgreement.objects.filter(
                member=m,
                version=chama.constitution_version,
            ).exists()
            member_status.append({
                'member_id': str(m.id),
                'member_name': m.user.get_full_name(),
                'has_agreed': agreed,
            })

        total = len(member_status)
        agreed_count = sum(1 for ms in member_status if ms['has_agreed'])

        return Response({
            'success': True,
            'data': {
                'has_constitution': True,
                'version': chama.constitution_version,
                'total_members': total,
                'agreed_count': agreed_count,
                'pending_count': total - agreed_count,
                'members': member_status,
            },
        })


@extend_schema_view(
    list=extend_schema(tags=['Chamas'], summary='List chama members'),
    retrieve=extend_schema(tags=['Chamas'], summary='Get member details'),
    partial_update=extend_schema(tags=['Chamas'], summary='Update member role'),
)
class ChamaMemberViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = ChamaMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'role']
    ordering_fields = ['joined_at', 'total_contributions', 'standing_score', 'role']

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return ChamaMember.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        ).select_related('user', 'chama')

    def perform_update(self, serializer):
        member = self.get_object()
        if not IsChamaAdmin().has_permission(self.request, self):
            raise PermissionDeniedError(_('Only chama admins can change member roles.'))
        serializer.save()


@extend_schema_view(
    list=extend_schema(tags=['Contributions'], summary='List contributions'),
    create=extend_schema(tags=['Contributions'], summary='Record contribution'),
    retrieve=extend_schema(tags=['Contributions'], summary='Get contribution details'),
)
class ContributionViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['payment_reference', 'notes', 'member__user__first_name', 'member__user__last_name']
    ordering_fields = ['period_start', 'amount', 'status', 'created_at', 'paid_at']

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Contribution.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        ).select_related('member__user', 'chama', 'verified_by__user')

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        return ContributionSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            contribution = serializer.save()
            
            # Verify the member belongs to this chama
            if contribution.member.chama_id != contribution.chama_id:
                raise ChamaMembershipError(
                    _('This member does not belong to this chama.')
                )
            
            payment_ref = serializer.validated_data.get('payment_reference', '')

            if not contribution.chama.require_contribution_verification:
                contribution.mark_as_paid(payment_ref)
            
            # Generate receipt
            try:
                from apps.receipts.services import ReceiptPDFGenerator
                ReceiptPDFGenerator.generate_contribution_receipt(
                    contribution=contribution,
                    user=contribution.member.user,
                    chama_name=contribution.chama.name,
                )
            except Exception as e:
                logger.error(f"Failed to generate contribution receipt: {e}", exc_info=True)
            
            logger.info(f"Contribution recorded: {contribution.id}")

            
    @action(detail=True, methods=['post'])
    def verify(self, request, chama_pk=None, pk=None):
        contribution = self.get_object()

        if not IsChamaAdmin().has_permission(request, self):
            raise PermissionDeniedError()

        if contribution.status != ContributionStatus.PENDING:
            return Response({
                'success': False,
                'error': {'code': 'invalid_state', 'message': _('Only pending contributions can be verified.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        contribution.verified_by = ChamaMember.objects.get(
            chama=contribution.chama, user=request.user
        )
        contribution.verified_at = timezone.now()
        contribution.mark_as_paid(contribution.payment_reference)
        contribution.save()

        return Response({
            'success': True,
            'data': ContributionSerializer(contribution).data,
            'message': _('Contribution verified.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Loans'], summary='List loans'),
    create=extend_schema(tags=['Loans'], summary='Apply for loan'),
    retrieve=extend_schema(tags=['Loans'], summary='Get loan details'),
)
class LoanViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['purpose', 'borrower__user__first_name', 'borrower__user__last_name']
    ordering_fields = ['created_at', 'principal', 'outstanding_balance', 'status', 'due_date']

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Loan.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        ).select_related('borrower__user', 'chama', 'approved_by__user')

    def get_serializer_class(self):
        if self.action == 'create':
            return LoanCreateSerializer
        return LoanSerializer

    def perform_create(self, serializer):
        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)

        borrower = ChamaMember.objects.get(chama=chama, user=self.request.user)

        # Check constitution agreement
        if chama.constitution:
            has_agreed = ConstitutionAgreement.objects.filter(
                member=borrower,
                version=chama.constitution_version,
            ).exists()

            if not has_agreed:
                raise PermissionDeniedError(
                    _('You must agree to the chama constitution before applying for a loan.')
                )

        max_loan = borrower.total_contributions * chama.max_loan_multiple
        if serializer.validated_data['principal'] > max_loan:
            raise LoanEligibilityError(
                _('Loan amount exceeds maximum of KSh %(max)s.') % {'max': max_loan}
            )

        loan = serializer.save(
            chama=chama,
            borrower=borrower,
            interest_rate=chama.loan_interest_rate
        )
        loan.calculate_terms()
        logger.info(f"Loan application created: {loan.id}")

    @action(detail=True, methods=['post'])
    def approve(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        if not IsChamaAdmin().has_permission(request, self):
            raise PermissionDeniedError()

        if loan.status != LoanStatus.PENDING:
            return Response({
                'success': False,
                'error': {'code': 'invalid_state', 'message': _('Only pending loans can be approved.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        approver = ChamaMember.objects.get(chama=loan.chama, user=request.user)
        loan.approve(approver)

        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Loan approved.'),
        })

    @action(detail=True, methods=['post'])
    def disburse(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        if not IsChamaAdmin().has_permission(request, self):
            raise PermissionDeniedError()

        if loan.status != LoanStatus.APPROVED:
            return Response({
                'success': False,
                'error': {'code': 'invalid_state', 'message': _('Only approved loans can be disbursed.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        loan.disburse()
        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Loan disbursed.'),
        })

    @action(detail=True, methods=['post'])
    def repay(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        amount = request.data.get('amount')
        if not amount:
            return Response({
                'success': False,
                'error': {'code': 'missing_amount', 'message': _('Repayment amount is required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        from decimal import Decimal
        amount = Decimal(str(amount))

        if amount <= Decimal('0'):
            raise InsufficientFundsError(_('Amount must be greater than zero.'))

        if amount > loan.outstanding_balance:
            raise InsufficientFundsError(_('Amount exceeds outstanding balance.'))

        with transaction.atomic():
            loan.record_repayment(amount)
            repayment = LoanRepayment.objects.create(
                loan=loan,
                amount=amount,
                payment_method=request.data.get('payment_method', PaymentMethod.MPESA),
                payment_reference=request.data.get('payment_reference', ''),
            )

            # Generate receipt
            try:
                from apps.receipts.services import ReceiptPDFGenerator
                ReceiptPDFGenerator.generate_loan_repayment_receipt(
                    repayment=repayment,
                    user=request.user,
                    chama_name=loan.chama.name,
                )
            except Exception as e:
                logger.error(f"Failed to generate loan repayment receipt: {e}", exc_info=True)

                
        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Repayment recorded.'),
        })

    @action(detail=True, methods=['get'])
    def early_repayment_calculation(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        try:
            calculation = loan.calculate_early_repayment()
        except ValueError as e:
            return Response({
                'success': False,
                'error': {'code': 'invalid_state', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'data': calculation,
        })

    @action(detail=True, methods=['post'])
    def early_repay(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        try:
            calculation = loan.calculate_early_repayment()
        except ValueError as e:
            return Response({
                'success': False,
                'error': {'code': 'invalid_state', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

        from decimal import Decimal
        amount = request.data.get('amount')
        if not amount:
            return Response({
                'success': False,
                'error': {'code': 'missing_amount', 'message': _('Payment amount required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        amount = Decimal(str(amount))
        early_payoff = Decimal(calculation['early_payoff_amount'])

        if amount < early_payoff:
            return Response({
                'success': False,
                'error': {
                    'code': 'insufficient_amount',
                    'message': _('Early payoff requires KSh %(amount)s.') % {'amount': early_payoff}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            LoanRepayment.objects.create(
                loan=loan,
                amount=amount,
                payment_method=request.data.get('payment_method', PaymentMethod.MPESA),
                payment_reference=request.data.get('payment_reference', ''),
            )
            loan.early_repay()

        return Response({
            'success': True,
            'data': {
                'message': _('Loan fully repaid.'),
                'savings': calculation['savings'],
            },
            'message': _('Early repayment successful.'),
        })

    @action(detail=True, methods=['post'])
    def restructure(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        if not IsChamaAdmin().has_permission(request, self):
            raise PermissionDeniedError()

        new_duration = request.data.get('new_duration_months')
        reason = request.data.get('reason', '')

        if not new_duration or int(new_duration) <= loan.duration_months:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_duration',
                    'message': _('New duration must be longer than current duration.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if loan.is_restructured:
            return Response({
                'success': False,
                'error': {
                    'code': 'already_restructured',
                    'message': _('Loan has already been restructured.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)
        approver = ChamaMember.objects.get(chama=chama, user=request.user)

        loan.restructure(int(new_duration), reason, approver)

        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Loan restructured.'),
        })

    @action(detail=True, methods=['post'])
    def mark_default(self, request, chama_pk=None, pk=None):
        loan = self.get_object()

        if not IsChamaAdmin().has_permission(request, self):
            raise PermissionDeniedError()

        if loan.status in [LoanStatus.FULLY_REPAID, LoanStatus.DEFAULTED, LoanStatus.WRITTEN_OFF]:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_state',
                    'message': _('This loan cannot be marked as defaulted.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', 'Manually marked by admin')
        loan.mark_defaulted(reason)

        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Loan marked as defaulted.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Meetings'], summary='List meetings'),
    create=extend_schema(tags=['Meetings'], summary='Schedule meeting'),
    retrieve=extend_schema(tags=['Meetings'], summary='Get meeting details'),
)
class MeetingViewSet(SoftDeleteMixin, viewsets.ModelViewSet):

    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'start_time', 'status']

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Meeting.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        ).select_related('organizer__user', 'chama')

    def perform_create(self, serializer):
        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)

        organizer = ChamaMember.objects.get(chama=chama, user=self.request.user)
        serializer.save(chama=chama, organizer=organizer)

    @action(detail=True, methods=['post'])
    def record_attendance(self, request, chama_pk=None, pk=None):
        meeting = self.get_object()
        member_id = request.data.get('member_id')
        attended = request.data.get('attended', True)

        try:
            member = ChamaMember.objects.get(id=member_id, chama=meeting.chama)
        except ChamaMember.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'invalid_member', 'message': _('Invalid member.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        attendance, created = MeetingAttendance.objects.update_or_create(
            meeting=meeting,
            member=member,
            defaults={
                'attended': attended,
                'arrived_at': timezone.now() if attended else None,
                'apology': request.data.get('apology', ''),
            }
        )

        return Response({
            'success': True,
            'data': MeetingAttendanceSerializer(attendance).data,
            'message': _('Attendance recorded.'),
        })

class BulkContributionView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Contributions'],
        summary='Record bulk contributions',
        description='Record contributions for multiple members in a single request.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'contributions': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'member_id': {'type': 'string', 'format': 'uuid'},
                                'amount': {'type': 'number'},
                                'payment_method': {'type': 'string', 'enum': ['MPESA', 'CASH', 'BANK_TRANSFER', 'OTHER']},
                                'payment_reference': {'type': 'string'},
                                'notes': {'type': 'string'},
                            },
                            'required': ['member_id', 'amount']
                        }
                    },
                    'period_start': {'type': 'string', 'format': 'date'},
                    'period_end': {'type': 'string', 'format': 'date'},
                },
                'required': ['contributions', 'period_start', 'period_end']
            }
        }
    )
    def post(self, request, chama_pk):
        from apps.chamas.models import Chama, ChamaMember, Contribution, ContributionStatus, PaymentMethod
        from apps.chamas.serializers import ContributionSerializer
        from apps.receipts.services import ReceiptPDFGenerator

        # Validate chama exists and user is authorized
        try:
            chama = Chama.objects.get(id=chama_pk, is_deleted=False)
        except Chama.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('Chama not found.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user is chama admin or treasurer
        try:
            user_membership = chama.memberships.get(
                user=request.user,
                is_active=True,
            )
            is_admin = user_membership.role in [
                MemberRole.CHAIRPERSON,
                MemberRole.TREASURER,
                MemberRole.SECRETARY,
            ]
        except ChamaMember.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': _('You are not a member of this chama.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        if not is_admin:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': _('Only chama officials can record bulk contributions.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate request data
        contributions_data = request.data.get('contributions', [])
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')

        if not contributions_data:
            return Response({
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': _('At least one contribution is required.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not period_start or not period_end:
            return Response({
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': _('period_start and period_end are required.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(contributions_data) > 100:
            return Response({
                'success': False,
                'error': {
                    'code': 'limit_exceeded',
                    'message': _('Maximum 100 contributions per bulk request.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Process each contribution
        results = []
        success_count = 0
        failure_count = 0

        with transaction.atomic():
            for idx, contrib_data in enumerate(contributions_data):
                result = {
                    'index': idx,
                    'member_id': contrib_data.get('member_id'),
                    'status': 'pending',
                }

                try:
                    # Validate member
                    member_id = contrib_data.get('member_id')
                    if not member_id:
                        result['status'] = 'failed'
                        result['error'] = _('member_id is required.')
                        failure_count += 1
                        results.append(result)
                        continue

                    try:
                        member = ChamaMember.objects.get(
                            id=member_id,
                            chama=chama,
                            is_active=True,
                        )
                    except ChamaMember.DoesNotExist:
                        result['status'] = 'failed'
                        result['error'] = _('Member not found or not active in this chama.')
                        failure_count += 1
                        results.append(result)
                        continue

                    # Validate amount
                    amount = contrib_data.get('amount')
                    if not amount or float(amount) <= 0:
                        result['status'] = 'failed'
                        result['error'] = _('Amount must be greater than zero.')
                        failure_count += 1
                        results.append(result)
                        continue

                    from decimal import Decimal
                    amount = Decimal(str(amount))

                    # Determine payment method
                    payment_method = contrib_data.get(
                        'payment_method',
                        PaymentMethod.CASH
                    )
                    payment_reference = contrib_data.get('payment_reference', '')
                    notes = contrib_data.get('notes', '')

                    # Create contribution
                    contribution = Contribution.objects.create(
                        chama=chama,
                        member=member,
                        amount=amount,
                        expected_amount=chama.contribution_amount,
                        status=ContributionStatus.PAID,
                        payment_method=payment_method,
                        payment_reference=payment_reference,
                        period_start=period_start,
                        period_end=period_end,
                        paid_at=timezone.now(),
                        notes=notes,
                    )

                    # Update member stats
                    member.total_contributions += amount
                    member.current_balance += amount
                    member.last_contribution_date = timezone.now().date()
                    member.contribution_streak += 1
                    member.is_overdue = False
                    member.overdue_amount = Decimal('0.00')
                    member.save()

                    # Generate receipt
                    try:
                        ReceiptPDFGenerator.generate_contribution_receipt(
                            contribution=contribution,
                            user=member.user,
                            chama_name=chama.name,
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate receipt: {e}", exc_info=True)

                    result['status'] = 'success'
                    result['contribution_id'] = str(contribution.id)
                    result['amount'] = str(amount)
                    result['member_name'] = member.user.get_full_name()
                    success_count += 1

                except Exception as e:
                    logger.error(f"Bulk contribution error at index {idx}: {e}")
                    result['status'] = 'failed'
                    result['error'] = str(e)
                    failure_count += 1

                results.append(result)

            # Update chama financials
            chama.update_financials()

        return Response({
            'success': True,
            'data': {
                'total': len(contributions_data),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results,
            },
            'message': _(
                'Bulk contribution recorded: %(success)d succeeded, %(failed)d failed.'
            ) % {'success': success_count, 'failed': failure_count},
        }, status=status.HTTP_200_OK if failure_count == 0 else status.HTTP_207_MULTI_STATUS)
    

class BulkInviteMembersView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Chamas'],
        summary='Bulk invite members',
        description='Invite multiple members via JSON array or CSV file upload.',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'members': {
                        'type': 'string',
                        'description': 'JSON array of {name, phone_number, email} objects'
                    },
                    'csv_file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'CSV file with columns: name, phone_number, email'
                    },
                }
            }
        }
    )
    def post(self, request, chama_pk):
        from apps.chamas.models import Chama, ChamaMember, MemberRole
        from apps.notifications.services import NotificationService
        from apps.notifications.models import NotificationCategory, NotificationPriority

        # Validate chama exists and user is admin
        try:
            chama = Chama.objects.get(id=chama_pk, is_deleted=False)
        except Chama.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Chama not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        # Check authorization
        try:
            membership = chama.memberships.get(user=request.user, is_active=True)
            is_admin = membership.role in [
                MemberRole.CHAIRPERSON,
                MemberRole.TREASURER,
                MemberRole.SECRETARY,
            ]
        except ChamaMember.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_member',
                    'message': _('You are not a member of this chama.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        if not is_admin:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': _('Only chama officials can invite members.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Parse invitees from request
        invitees = []

        # Check for CSV file upload
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            invitees = self._parse_csv(csv_file)
        else:
            # Check for JSON array
            members_data = request.data.get('members')
            if isinstance(members_data, str):
                import json
                try:
                    members_data = json.loads(members_data)
                except json.JSONDecodeError:
                    return Response({
                        'success': False,
                        'error': {
                            'code': 'invalid_json',
                            'message': _('Invalid JSON format for members data.')
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

            if isinstance(members_data, list):
                invitees = members_data

        if not invitees:
            return Response({
                'success': False,
                'error': {
                    'code': 'no_data',
                    'message': _('No members provided. Send a JSON array or CSV file.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(invitees) > 200:
            return Response({
                'success': False,
                'error': {
                    'code': 'limit_exceeded',
                    'message': _('Maximum 200 invites per batch.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check capacity
        current_count = chama.memberships.filter(is_active=True).count()
        available_slots = chama.max_members - current_count
        if len(invitees) > available_slots:
            return Response({
                'success': False,
                'error': {
                    'code': 'capacity_exceeded',
                    'message': _('Only %(slots)d slots available. Cannot invite %(count)d members.') % {
                        'slots': available_slots,
                        'count': len(invitees)
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Process each invitee
        results = []
        success_count = 0
        failure_count = 0

        for idx, invitee in enumerate(invitees):
            result = {
                'index': idx,
                'name': invitee.get('name', invitee.get('Name', 'Unknown')),
                'status': 'pending',
            }

            try:
                phone = invitee.get('phone_number', invitee.get('Phone', invitee.get('phone', '')))
                email = invitee.get('email', invitee.get('Email', ''))
                name = invitee.get('name', invitee.get('Name', ''))

                if not phone:
                    result['status'] = 'failed'
                    result['error'] = _('Phone number is required.')
                    failure_count += 1
                    results.append(result)
                    continue

                # Format phone number
                import re
                phone = re.sub(r'\s+', '', str(phone))
                
                # Validate Kenyan phone format
                if not re.match(r'^(?:\+?254|0)?[17]\d{8}$', phone):
                    result['status'] = 'failed'
                    result['error'] = _('Invalid Kenyan phone number.')
                    failure_count += 1
                    results.append(result)
                    continue
                
                if phone.startswith('+254'):
                    phone = '0' + phone[4:]
                elif not phone.startswith('0'):
                    if len(phone) == 9:
                        phone = '0' + phone

                # Check if already a member
                from apps.users.models import User
                existing_user = User.objects.filter(phone_number=phone).first()

                if existing_user:
                    # Check if already in this chama
                    if chama.memberships.filter(user=existing_user, is_active=True).exists():
                        result['status'] = 'skipped'
                        result['error'] = _('Already a member.')
                        failure_count += 1
                        results.append(result)
                        continue

                    # Add existing user to chama
                    ChamaMember.objects.create(
                        chama=chama,
                        user=existing_user,
                        role=MemberRole.MEMBER,
                    )

                    # Notify user
                    try:
                        NotificationService.create_notification(
                            user=existing_user,
                            category=NotificationCategory.CHAMA_MEMBER,
                            title=f'Added to {chama.name}',
                            body=f'You have been added to {chama.name} by {request.user.get_full_name()}.',
                            priority=NotificationPriority.HIGH,
                            action_url=f'/chamas/{chama.id}/',
                        )
                    except Exception:
                        pass

                    result['status'] = 'success'
                    result['user_id'] = str(existing_user.id)
                    result['message'] = _('Existing user added.')
                    success_count += 1

                else:
                    # New user - send SMS invitation
                    result['status'] = 'success'
                    result['message'] = _('Invitation will be sent via SMS.')
                    result['phone'] = phone
                    success_count += 1

                    # Queue SMS invitation
                    try:
                        AuthenticationService.send_verification_sms_for_invite(
                            phone_number=phone,
                            chama_name=chama.name,
                            inviter_name=request.user.get_full_name(),
                            invite_code=chama.invite_code,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send invite SMS to {phone}: {e}")

            except Exception as e:
                logger.error(f"Bulk invite error at index {idx}: {e}")
                result['status'] = 'failed'
                result['error'] = str(e)
                failure_count += 1

            results.append(result)

        return Response({
            'success': True,
            'data': {
                'total': len(invitees),
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results,
            },
            'message': _(
                '%(success)d invited successfully, %(failed)d failed.'
            ) % {'success': success_count, 'failed': failure_count},
        }, status=status.HTTP_200_OK if failure_count == 0 else status.HTTP_207_MULTI_STATUS)

    def _parse_csv(self, csv_file):
        import csv
        import io

        invitees = []
        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            for row in reader:
                invitees.append({
                    'name': row.get('name', row.get('Name', '')),
                    'phone_number': row.get('phone_number', row.get('Phone', row.get('phone', ''))),
                    'email': row.get('email', row.get('Email', '')),
                })
        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            raise

        return invitees

class AdminChamaManagementView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] List all chamas')
    def get(self, request):
        from apps.core.pagination import SmallPagination
        chamas = Chama.objects.filter(is_deleted=False).order_by('-created_at')
        paginator = SmallPagination()
        page = paginator.paginate_queryset(chamas, request)

        data = []
        for chama in page:
            data.append({
                'id': str(chama.id),
                'name': chama.name,
                'chama_type': chama.get_chama_type_display(),
                'status': chama.status,
                'total_savings': str(chama.total_savings),
                'member_count': chama.memberships.filter(is_active=True).count(),
                'created_by': chama.created_by.get_full_name() if chama.created_by else 'N/A',
                'created_at': chama.created_at.isoformat(),
            })

        return paginator.get_paginated_response(data)

    @extend_schema(tags=['Admin'], summary='[Admin] Moderate chama')
    def post(self, request):
        chama_id = request.data.get('chama_id')
        action = request.data.get('action')

        if not chama_id or not action:
            return Response({
                'success': False,
                'error': {'code': 'validation_error', 'message': _('chama_id and action are required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            chama = Chama.objects.get(id=chama_id)
        except Chama.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Chama not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if action == 'suspend':
            chama.status = 'SUSPENDED'
            chama.save(update_fields=['status'])
            message = _('Chama suspended.')

        elif action == 'reactivate':
            chama.status = 'ACTIVE'
            chama.save(update_fields=['status'])
            message = _('Chama reactivated.')

        elif action == 'archive':
            chama.status = 'ARCHIVED'
            chama.save(update_fields=['status'])
            message = _('Chama archived.')
        else:
            return Response({
                'success': False,
                'error': {'code': 'invalid_action', 'message': _('Invalid action.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Admin action '{action}' performed on chama {chama.name} by {request.user.email}")

        return Response({
            'success': True,
            'data': {
                'chama_id': str(chama.id),
                'action': action,
                'message': message,
            },
            'message': message,
        })

class PollViewSet(viewsets.ModelViewSet):

    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Poll.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False,
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return PollCreateSerializer
        return PollSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)

        member = ChamaMember.objects.get(chama=chama, user=self.request.user)

        if member.role not in [MemberRole.CHAIRPERSON, MemberRole.TREASURER, MemberRole.SECRETARY]:
            raise PermissionDeniedError(_('Only chama officials can create polls.'))

        serializer.save(chama=chama, created_by=member)

    @action(detail=True, methods=['post'])
    def vote(self, request, chama_pk=None, pk=None):
        poll = self.get_object()

        if not poll.is_active:
            return Response({
                'success': False,
                'error': {'code': 'poll_closed', 'message': _('This poll is closed.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        if poll.closes_at and poll.closes_at < timezone.now():
            poll.close()
            return Response({
                'success': False,
                'error': {'code': 'poll_closed', 'message': _('This poll has closed.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)
        member = ChamaMember.objects.get(chama=chama, user=request.user)

        # Check if already voted
        if Vote.objects.filter(poll=poll, voter=member).exists():
            return Response({
                'success': False,
                'error': {'code': 'already_voted', 'message': _('You have already voted.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            option = poll.options.get(id=serializer.validated_data['option_id'])
        except PollOption.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'invalid_option', 'message': _('Invalid option.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        Vote.objects.create(poll=poll, option=option, voter=member)

        return Response({
            'success': True,
            'data': PollSerializer(poll, context={'request': request}).data,
            'message': _('Vote recorded.'),
        })

    @action(detail=True, methods=['post'])
    def close(self, request, chama_pk=None, pk=None):
        poll = self.get_object()

        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)
        member = ChamaMember.objects.get(chama=chama, user=request.user)

        if member.role not in [MemberRole.CHAIRPERSON, MemberRole.TREASURER, MemberRole.SECRETARY]:
            raise PermissionDeniedError()

        if not poll.is_active:
            return Response({
                'success': False,
                'error': {'code': 'already_closed', 'message': _('Poll is already closed.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        poll.close()

        return Response({
            'success': True,
            'data': PollSerializer(poll, context={'request': request}).data,
            'message': _('Poll closed.'),
        })