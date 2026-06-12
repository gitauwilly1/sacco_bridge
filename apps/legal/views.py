from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.legal.models import LegalDocument, LegalDocumentType, UserLegalAcceptance
from apps.legal.serializers import LegalDocumentSerializer, AcceptDocumentSerializer
from apps.users.permissions import IsPlatformStaff


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