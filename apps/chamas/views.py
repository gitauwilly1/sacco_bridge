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
from apps.chamas.models import (
    Chama, ChamaMember, Contribution, Loan, LoanRepayment,
    Meeting, MeetingAttendance, MemberRole, LoanStatus,
    PaymentMethod, ContributionStatus,
)
from apps.chamas.serializers import (
    ChamaSerializer, ChamaCreateSerializer, ChamaMemberSerializer,
    ContributionSerializer, ContributionCreateSerializer,
    LoanSerializer, LoanCreateSerializer, LoanRepaymentSerializer,
    MeetingSerializer, MeetingAttendanceSerializer,
    PayoutSerializer, PayoutRecipientSerializer,
)
from apps.users.permissions import IsChamaAdmin

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(tags=['Chamas'], summary='List user chamas'),
    create=extend_schema(tags=['Chamas'], summary='Create a new chama'),
    retrieve=extend_schema(tags=['Chamas'], summary='Get chama details'),
    update=extend_schema(tags=['Chamas'], summary='Update chama'),
    partial_update=extend_schema(tags=['Chamas'], summary='Partial update chama'),
    destroy=extend_schema(tags=['Chamas'], summary='Delete chama'),
)
class ChamaViewSet(viewsets.ModelViewSet):

    serializer_class = ChamaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        return Chama.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
            is_deleted=False
        ).distinct()

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


@extend_schema_view(
    list=extend_schema(tags=['Chamas'], summary='List chama members'),
    retrieve=extend_schema(tags=['Chamas'], summary='Get member details'),
    partial_update=extend_schema(tags=['Chamas'], summary='Update member role'),
)
class ChamaMemberViewSet(viewsets.ModelViewSet):

    serializer_class = ChamaMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return ChamaMember.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        )

    def perform_update(self, serializer):
        member = self.get_object()
        if not IsChamaAdmin().has_permission(self.request, None):
            raise PermissionDeniedError(_('Only chama admins can change member roles.'))
        serializer.save()


@extend_schema_view(
    list=extend_schema(tags=['Contributions'], summary='List contributions'),
    create=extend_schema(tags=['Contributions'], summary='Record contribution'),
    retrieve=extend_schema(tags=['Contributions'], summary='Get contribution details'),
)
class ContributionViewSet(viewsets.ModelViewSet):

    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Contribution.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        return ContributionSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            contribution = serializer.save()
            payment_ref = serializer.validated_data.get('payment_reference', '')

            if not contribution.chama.require_contribution_verification:
                contribution.mark_as_paid(payment_ref)
            logger.info(f"Contribution recorded: {contribution.id}")

    @action(detail=True, methods=['post'])
    def verify(self, request, chama_pk=None, pk=None):
        """Verify a pending contribution (chama admin only)."""
        contribution = self.get_object()

        if not IsChamaAdmin().has_permission(request, None):
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
class LoanViewSet(viewsets.ModelViewSet):

    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Loan.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return LoanCreateSerializer
        return LoanSerializer

    def perform_create(self, serializer):
        chama_id = self.kwargs.get('chama_pk')
        chama = Chama.objects.get(id=chama_id)

        borrower = ChamaMember.objects.get(chama=chama, user=self.request.user)

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

        if not IsChamaAdmin().has_permission(request, None):
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

        if not IsChamaAdmin().has_permission(request, None):
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
            LoanRepayment.objects.create(
                loan=loan,
                amount=amount,
                payment_method=request.data.get('payment_method', PaymentMethod.MPESA),
                payment_reference=request.data.get('payment_reference', ''),
            )

        return Response({
            'success': True,
            'data': LoanSerializer(loan).data,
            'message': _('Repayment recorded.'),
        })


@extend_schema_view(
    list=extend_schema(tags=['Meetings'], summary='List meetings'),
    create=extend_schema(tags=['Meetings'], summary='Schedule meeting'),
    retrieve=extend_schema(tags=['Meetings'], summary='Get meeting details'),
)
class MeetingViewSet(viewsets.ModelViewSet):

    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_pk')
        return Meeting.objects.filter(
            chama_id=chama_id,
            chama__is_deleted=False
        )

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
                        logger.warning(f"Failed to generate receipt: {e}")

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