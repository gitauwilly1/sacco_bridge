from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class SoftDeleteMixin:
    def perform_destroy(self, instance):
        instance.soft_delete(deleted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = self.get_object()

        if not instance.is_deleted:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_deleted',
                    'message': _('This record is not deleted.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        instance.restore()

        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': _('Record restored successfully.'),
        })

    @action(detail=True, methods=['delete'])
    def permanent(self, request, pk=None):
        from apps.users.models import Role

        is_admin = (
            request.user.is_staff or
            request.user.has_role(Role.PLATFORM_ADMIN)
        )

        if not is_admin:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': _('Only platform administrators can permanently delete records.')
                }
            }, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        instance.delete()

        return Response({
            'success': True,
            'data': {},
            'message': _('Record permanently deleted.'),
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def trash(self, request):
        queryset = self.get_queryset().filter(is_deleted=True)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': _('Trash bin retrieved.'),
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        
        include_deleted = self.request.query_params.get('include_deleted', '').lower() == 'true'
        
        if not include_deleted and self.action != 'trash':
            queryset = queryset.filter(is_deleted=False)
        
        return queryset