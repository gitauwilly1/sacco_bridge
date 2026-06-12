from rest_framework import serializers
from apps.legal.models import LegalDocument, LegalDocumentType, UserLegalAcceptance


class LegalDocumentSerializer(serializers.ModelSerializer):

    document_type_display = serializers.SerializerMethodField()
    published_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = [
            'id', 'document_type', 'document_type_display',
            'title', 'version', 'content', 'summary',
            'is_current', 'published_at', 'effective_from',
            'published_by_name',
        ]
        read_only_fields = ['id', 'published_at', 'published_by_name']

    def get_document_type_display(self, obj):
        return obj.get_document_type_display()

    def get_published_by_name(self, obj):
        if obj.published_by:
            return obj.published_by.get_full_name()
        return None


class AcceptDocumentSerializer(serializers.Serializer):

    document_id = serializers.UUIDField(required=True)