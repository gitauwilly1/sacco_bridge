from django.http import FileResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.reports.models import ReportRequest, ReportStatus
from apps.reports.serializers import (
    ReportRequestSerializer, ReportRequestCreateSerializer,
)
from apps.reports.tasks import generate_report

class ReportRequestView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reports'],
        summary='List my reports',
        description='Get all report requests for the authenticated user.'
    )
    def get(self, request):
        reports = ReportRequest.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by('-queued_at')[:20]

        serializer = ReportRequestSerializer(reports, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
        })

    @extend_schema(
        tags=['Reports'],
        summary='Request a report',
        description='Queue a report for async generation. Returns report ID immediately.',
        request=ReportRequestCreateSerializer,
    )
    def post(self, request):
        serializer = ReportRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_type = serializer.validated_data['report_type']
        report_format = serializer.validated_data['report_format']
        title = serializer.validated_data.get(
            'title',
            f"{report_type} - {request.user.get_full_name()}"
        )

        filters = {}
        if serializer.validated_data.get('chama_id'):
            filters['chama_id'] = str(serializer.validated_data['chama_id'])
        if serializer.validated_data.get('date_from'):
            filters['date_from'] = str(serializer.validated_data['date_from'])
        if serializer.validated_data.get('date_to'):
            filters['date_to'] = str(serializer.validated_data['date_to'])

        report = ReportRequest.objects.create(
            user=request.user,
            report_type=report_type,
            report_format=report_format,
            title=title,
            filters=filters,
        )

        # Queue async generation
        task = generate_report.delay(str(report.id))
        report.task_id = task.id
        report.save(update_fields=['task_id'])

        return Response({
            'success': True,
            'data': {
                'report_id': str(report.id),
                'status': report.status,
                'message': _('Report queued. Poll /reports/{id}/status/ for completion.'),
            },
            'message': _('Report request queued.'),
        }, status=status.HTTP_202_ACCEPTED)


class ReportStatusView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reports'],
        summary='Check report status',
        description='Poll this endpoint to check if report generation is complete.'
    )
    def get(self, request, report_id):
        try:
            report = ReportRequest.objects.get(id=report_id, user=request.user)
        except ReportRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Report not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ReportRequestSerializer(report)
        return Response({
            'success': True,
            'data': serializer.data,
        })


class ReportDownloadView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reports'],
        summary='Download report',
        description='Download the generated report file.'
    )
    def get(self, request, report_id):
        try:
            report = ReportRequest.objects.get(
                id=report_id,
                user=request.user,
                status=ReportStatus.COMPLETED,
            )
        except ReportRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Report not found or not ready.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if report.expires_at and report.expires_at < __import__('django.utils.timezone').now():
            return Response({
                'success': False,
                'error': {'code': 'expired', 'message': _('Report download link has expired.')}
            }, status=status.HTTP_410_GONE)

        response = FileResponse(
            report.report_file.open('rb'),
            content_type='text/csv',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="SaccoBridge_{report.title.replace(" ", "_")}.csv"'
        )
        return response