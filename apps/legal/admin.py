from django.contrib import admin
from apps.legal.models import LegalDocument, UserLegalAcceptance


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'version', 'is_current', 'published_at']
    list_filter = ['document_type', 'is_current']
    search_fields = ['title', 'version']
    actions = ['publish_selected']

    def publish_selected(self, request, queryset):
        for doc in queryset:
            doc.publish(published_by=request.user)
        self.message_user(request, 'Selected documents published.')
    publish_selected.short_description = 'Publish selected documents'


@admin.register(UserLegalAcceptance)
class UserLegalAcceptanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'document', 'accepted_at', 'ip_address']
    list_filter = ['accepted_at']
    search_fields = ['user__email', 'document__title']
    readonly_fields = ['accepted_at']