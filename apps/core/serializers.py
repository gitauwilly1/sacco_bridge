from rest_framework import serializers
from django.utils import timezone


class BaseSerializer(serializers.ModelSerializer):

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        abstract = True


class AuditSerializer(serializers.Serializer):

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    def get_created_by_name(self, obj):
        if hasattr(obj, 'created_by') and obj.created_by:
            return obj.created_by.get_full_name()
        return None

    def get_updated_by_name(self, obj):
        if hasattr(obj, 'updated_by') and obj.updated_by:
            return obj.updated_by.get_full_name()
        return None


class DynamicFieldsMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'context') and self.context.get('request'):
            fields_param = self.context['request'].query_params.get('fields', None)
            if fields_param:
                allowed_fields = set(fields_param.split(','))
                existing_fields = set(self.fields.keys())
                for field_name in existing_fields - allowed_fields:
                    self.fields.pop(field_name)


class SuccessResponseSerializer(serializers.Serializer):

    success = serializers.BooleanField(default=True)
    data = serializers.DictField()
    message = serializers.CharField(required=False)
    meta = serializers.DictField(required=False)


class ErrorResponseSerializer(serializers.Serializer):

    success = serializers.BooleanField(default=False)
    error = serializers.DictField()
    meta = serializers.DictField(required=False)


class PaginatedResponseSerializer(serializers.Serializer):

    success = serializers.BooleanField(default=True)
    data = serializers.ListField()
    pagination = serializers.DictField()
    meta = serializers.DictField(required=False)