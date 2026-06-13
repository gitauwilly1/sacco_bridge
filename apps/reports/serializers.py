from rest_framework import serializers
from apps.reports.models import ReportRequest, ReportType, ReportFormat


class ReportRequestSerializer(serializers.ModelSerializer):

    report_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportRequest
        fields = [
            'id', 'report_type', 'report_type_display', 'report_format',
            'status', 'status_display', 'title', 'filters',
            'file_size', 'record_count', 'queued_at',
            'started_at', 'completed_at', 'expires_at',
            'error_message', 'download_url',
        ]
        read_only_fields = [
            'id', 'status', 'file_size', 'record_count',
            'queued_at', 'started_at', 'completed_at',
            'expires_at', 'error_message',
        ]

    def get_report_type_display(self, obj):
        return obj.get_report_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_download_url(self, obj):
        if obj.status == 'COMPLETED' and obj.report_file:
            return f"/api/v1/reports/{obj.id}/download/"
        return None


class ReportRequestCreateSerializer(serializers.Serializer):

    report_type = serializers.ChoiceField(choices=ReportType.choices)
    report_format = serializers.ChoiceField(
        choices=ReportFormat.choices,
        default=ReportFormat.CSV
    )
    title = serializers.CharField(max_length=255, required=False)
    chama_id = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)