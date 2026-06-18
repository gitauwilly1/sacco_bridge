from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from apps.legal.models import (
    LegalDocument,
    LegalDocumentType,
    SignableDocumentType,
    Signature,
    UserLegalAcceptance,
)
from apps.legal.serializers import AcceptDocumentSerializer, LegalDocumentSerializer
from apps.users.permissions import IsPlatformStaff
from apps.users.services import AuthenticationService


class LatestTermsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Legal'],
        summary='Get current Terms & Conditions',
        description='Returns the latest published Terms & Conditions.'
    )
    def get(self, request):
        try:
            document = LegalDocument.objects.get(
                document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
                is_current=True,
            )
        except LegalDocument.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('No Terms & Conditions published yet.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = LegalDocumentSerializer(document)
        return Response({
            'success': True,
            'data': serializer.data,
        })


class LatestPrivacyView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Legal'],
        summary='Get current Privacy Policy',
        description='Returns the latest published Privacy Policy.'
    )
    def get(self, request):
        try:
            document = LegalDocument.objects.get(
                document_type=LegalDocumentType.PRIVACY_POLICY,
                is_current=True,
            )
        except LegalDocument.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_found',
                    'message': _('No Privacy Policy published yet.')
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = LegalDocumentSerializer(document)
        return Response({
            'success': True,
            'data': serializer.data,
        })


class AcceptDocumentView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Legal'],
        summary='Accept legal document',
        description='Record user acceptance of T&C or Privacy Policy.'
    )
    def post(self, request):
        serializer = AcceptDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data['document_id']

        try:
            document = LegalDocument.objects.get(id=document_id, is_current=True)
        except LegalDocument.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_document',
                    'message': _('Document not found or not current.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        acceptance, created = UserLegalAcceptance.objects.get_or_create(
            user=request.user,
            document=document,
            defaults={
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )

        return Response({
            'success': True,
            'data': {
                'accepted': True,
                'document_version': document.version,
                'accepted_at': acceptance.accepted_at.isoformat(),
                'message': _('Document accepted successfully.'),
            },
            'message': _('Document accepted.'),
        })

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class AcceptanceStatusView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Legal'],
        summary='Check acceptance status',
        description='Check if user has accepted current T&C and Privacy Policy.'
    )
    def get(self, request):
        terms_accepted = False
        privacy_accepted = False

        try:
            current_terms = LegalDocument.objects.get(
                document_type=LegalDocumentType.TERMS_AND_CONDITIONS,
                is_current=True,
            )
            terms_accepted = UserLegalAcceptance.objects.filter(
                user=request.user,
                document=current_terms,
            ).exists()
        except LegalDocument.DoesNotExist:
            pass

        try:
            current_privacy = LegalDocument.objects.get(
                document_type=LegalDocumentType.PRIVACY_POLICY,
                is_current=True,
            )
            privacy_accepted = UserLegalAcceptance.objects.filter(
                user=request.user,
                document=current_privacy,
            ).exists()
        except LegalDocument.DoesNotExist:
            pass

        return Response({
            'success': True,
            'data': {
                'terms_accepted': terms_accepted,
                'privacy_accepted': privacy_accepted,
                'all_accepted': terms_accepted and privacy_accepted,
            },
        })


class LegalDocumentViewSet(viewsets.ModelViewSet):

    serializer_class = LegalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    def get_queryset(self):
        return LegalDocument.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(tags=['Legal'], summary='[Admin] List all legal documents')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Legal'], summary='[Admin] Create legal document')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=['Legal'], summary='[Admin] Update legal document')
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=['Legal'], summary='[Admin] Delete legal document')
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(tags=['Legal'], summary='[Admin] Publish legal document')
    def publish(self, request, pk=None):
        document = self.get_object()
        document.publish(published_by=request.user)

        serializer = self.get_serializer(document)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': _('Document published successfully.'),
        })


class SignatureRequestView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Legal'],
        summary='Request digital signature',
        description='Initiate digital signing with OTP verification.'
    )
    def post(self, request):
        document_type = request.data.get('document_type')
        document_reference = request.data.get('document_reference')
        document_title = request.data.get('document_title', 'Document')

        if document_type not in dict(SignableDocumentType.choices):
            return Response({
                'success': False,
                'error': {'code': 'invalid_type', 'message': _('Invalid document type.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if already signed
        existing = Signature.objects.filter(
            signer=request.user,
            document_type=document_type,
            document_reference=document_reference,
            is_verified=True,
        ).first()

        if existing:
            return Response({
                'success': True,
                'data': {
                    'signature_id': str(existing.id),
                    'already_signed': True,
                    'signed_at': existing.signed_at.isoformat(),
                    'certificate_hash': existing.certificate_hash,
                },
                'message': _('Document already signed.'),
            })

        # Generate OTP
        from apps.core.utils import generate_otp
        otp = generate_otp()

        signature = Signature.objects.create(
            signer=request.user,
            document_type=document_type,
            document_reference=str(document_reference),
            document_title=document_title,
            verification_code=otp,
            verification_expiry=timezone.now() + timezone.timedelta(minutes=10),
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        # Send OTP via SMS
        try:
            AuthenticationService.send_verification_sms_for_signature(
                user=request.user,
                otp=otp,
                document_title=document_title,
            )
        except Exception:
            pass

        return Response({
            'success': True,
            'data': {
                'signature_id': str(signature.id),
                'message': _('OTP sent. Verify to complete signing.'),
            },
            'message': _('Verification code sent.'),
        })

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class SignatureConfirmView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Legal'],
        summary='Confirm digital signature',
        description='Verify OTP and complete the digital signature.'
    )
    def post(self, request):
        signature_id = request.data.get('signature_id')
        otp = request.data.get('otp')

        if not signature_id or not otp:
            return Response({
                'success': False,
                'error': {'code': 'missing_params', 'message': _('signature_id and otp required.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            signature = Signature.objects.get(
                id=signature_id,
                signer=request.user,
                is_verified=False,
            )
        except Signature.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Signature request not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if signature.verification_expiry and signature.verification_expiry < timezone.now():
            return Response({
                'success': False,
                'error': {'code': 'expired', 'message': _('OTP expired. Request a new signature.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        if signature.verification_code != otp:
            return Response({
                'success': False,
                'error': {'code': 'invalid_otp', 'message': _('Invalid verification code.')}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Complete signature
        signature.verification_code = ''
        signature.is_verified = True
        signature.signed_at = timezone.now()
        signature.certificate_hash = signature.generate_certificate()
        signature.save()

        return Response({
            'success': True,
            'data': {
                'signature_id': str(signature.id),
                'signed_at': signature.signed_at.isoformat(),
                'certificate_hash': signature.certificate_hash,
                'document_type': signature.get_document_type_display(),
                'document_title': signature.document_title,
            },
            'message': _('Document signed successfully.'),
        })


class SignatureVerifyView(APIView):

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Legal'],
        summary='Verify signature',
        description='Verify a digital signature by certificate hash.'
    )
    def get(self, request, certificate_hash):
        try:
            signature = Signature.objects.get(
                certificate_hash=certificate_hash,
                is_verified=True,
            )
        except Signature.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'invalid_certificate', 'message': _('Invalid or unverified signature.')}
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'data': {
                'signer_name': signature.signer.get_full_name(),
                'document_type': signature.get_document_type_display(),
                'document_title': signature.document_title,
                'signed_at': signature.signed_at.isoformat(),
                'ip_address': signature.ip_address,
                'is_valid': True,
            },
        })